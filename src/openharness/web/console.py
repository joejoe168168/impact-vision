"""Web console — a lightweight SPA for Impact Vision tools.

We serve a single self-contained HTML document that:

  * lists every registered tool (seeded from ``_TOOL_CATALOGUE`` and
    **extended at runtime by walking ``/openapi.json``** so every new
    ``/api/v1/*`` route automatically shows up);
  * renders a dynamic form for the currently-selected tool. When an
    OpenAPI ``requestBody`` schema is available the form is derived
    from the schema; otherwise we fall back to the hand-curated field
    recipes in ``_FIELD_RECIPES``;
  * submits the form to the matching endpoint;
  * streams the JSON / HTML response back into a results pane with
    collapsible sections, pretty-printing and one-click "copy" /
    "download" buttons;
  * remembers the last 50 runs **client-side in ``localStorage``**
    (Phase 15.6 "Session + artefact inbox v1") so analysts can close
    the tab and come back without losing state.

Design goals:

  * **Zero build step** — the whole UI ships as one HTML string with
    inline CSS + JS; contributors can read it top-to-bottom.
  * **Reuse the REST gateway** — every call goes through ``/api/v1/*``
    so the console automatically picks up new endpoints via the
    OpenAPI walker above.
  * **No external runtime deps** — no React / Vue / HTMX / etc. Just
    the browser, ``fetch`` and ``localStorage``.

This sits alongside the Streamlit dashboard (``openharness.dashboard``)
rather than replacing it: Streamlit is good for analysts who want
interactive charts; the web console is for power users who want the
full 26-tool surface in a browser-native IDE-like layout.
"""
from __future__ import annotations

import json
from typing import Any

try:
    from fastapi import APIRouter
    from fastapi.responses import HTMLResponse
except ImportError as _exc:  # pragma: no cover — optional
    APIRouter = None  # type: ignore[assignment]
    HTMLResponse = None  # type: ignore[assignment]
    _FASTAPI_IMPORT_ERROR: Exception | None = _exc
else:
    _FASTAPI_IMPORT_ERROR = None


# ---------------------------------------------------------------------------
# Curated tool catalogue (labels, descriptions, preferred order).
# At runtime the client also merges in any additional ``/api/v1/*``
# endpoints it discovers from ``/openapi.json``; this table drives the
# *visible order* and the *human-readable labels* for the baseline 26.
# ---------------------------------------------------------------------------

_TOOL_CATALOGUE: list[dict[str, str]] = [
    {"id": "score",               "label": "5-Dimension scoring",
     "endpoint": "/api/v1/score",
     "desc": "IMP 5-dimension impact score (What / Who / How-much / Contribution / Risk)."},
    {"id": "sdg-map",             "label": "SDG alignment map",
     "endpoint": "/api/v1/sdg-map",
     "desc": "Goal- and target-level SDG alignment from company description + metrics."},
    {"id": "data-quality",        "label": "Metric data quality",
     "endpoint": "/api/v1/data-quality",
     "desc": "Grades every reported metric for completeness, consistency and evidence."},
    {"id": "greenwashing",        "label": "Greenwashing screen",
     "endpoint": "/api/v1/greenwashing",
     "desc": "Detect vague / unverifiable / CSR-washing language in marketing copy."},
    {"id": "gap-analysis",        "label": "Core-metric gap analysis",
     "endpoint": "/api/v1/gap-analysis",
     "desc": "Compare reported metrics against the IRIS+ Core Metric Set."},
    {"id": "validate",            "label": "Metric validation pipeline",
     "endpoint": "/api/v1/validate",
     "desc": "Schema + unit + range checks with IRIS+ cross-reference."},
    {"id": "framework",           "label": "Multi-framework assessment",
     "endpoint": "/api/v1/framework",
     "desc": "Check coverage against GRI, SASB, TCFD, SFDR PAI, EDCI, UNPRI, ISSB, ESRS, OPIM, ToC, TNFD, PCAF, EU Tax., CDP, SBTi."},
    {"id": "cross-reference",     "label": "Cross-reference a metric",
     "endpoint": "/api/v1/cross-reference",
     "desc": "Map a metric across IRIS+ / GRI / SASB / SDG / framework codes."},
    {"id": "risk-opportunity",    "label": "Risk / opportunity scan",
     "endpoint": "/api/v1/risk-opportunity",
     "desc": "Surface impact risks and upside opportunities for the deal."},
    {"id": "metric-recommend",    "label": "IRIS+ metric recommender",
     "endpoint": "/api/v1/metric-recommend",
     "desc": "Suggest metrics based on sector, SDG targets, and fund themes."},
    {"id": "exclusion-screen",    "label": "Exclusion screen",
     "endpoint": "/api/v1/exclusion-screen",
     "desc": "Check a deal against the fund's exclusion criteria."},
    {"id": "report",              "label": "Impact report (HTML)",
     "endpoint": "/api/v1/report",
     "desc": "Generate the full impact report bundle — HTML + JSON + metrics."},
    {"id": "decision-workflow",    "label": "IC decision workflow",
     "endpoint": "/api/v1/decision-workflow",
     "desc": "Quick screen, IC memo proof bundle, deal comparison, and LP readiness."},
    {"id": "regulatory-calendar",  "label": "Regulatory calendar",
     "endpoint": "/api/v1/regulatory-calendar",
     "desc": "Jurisdiction-specific reporting deadlines for fund and engagement planning."},
    {"id": "pitch-deck",          "label": "Pitch-deck analyzer",
     "endpoint": "/api/v1/pitch-deck",
     "desc": "Extract company profile + impact thesis from a deck's text."},
    {"id": "ddq-export",          "label": "LP DDQ export",
     "endpoint": "/api/v1/ddq-export",
     "desc": "Export the LP Due-Diligence Questionnaire in multiple formats."},
    {"id": "pipeline",            "label": "Pipeline management",
     "endpoint": "/api/v1/pipeline",
     "desc": "Add, stage, score, rank and query deals in the fund pipeline."},
    {"id": "monitoring",          "label": "Continuous monitoring",
     "endpoint": "/api/v1/monitoring",
     "desc": "Trend, anomaly and alert generation on in-flight portfolio metrics."},
    {"id": "improvement-advisor", "label": "Improvement advisor",
     "endpoint": "/api/v1/improvement-advisor",
     "desc": "Recommend concrete steps to raise the impact score."},
    {"id": "narrative",           "label": "Narrative generator",
     "endpoint": "/api/v1/narrative",
     "desc": "Write LP-ready narrative text for impact assessments."},
    {"id": "batch",               "label": "Batch assessment",
     "endpoint": "/api/v1/batch",
     "desc": "Run 5-D scoring across N companies in one call."},
]


# ---------------------------------------------------------------------------
# Hand-written fallback field recipes. Used only when the OpenAPI schema
# for a given endpoint is unavailable or unparseable (e.g. older gateway
# versions / proxied deployments).
# ---------------------------------------------------------------------------

_COMPANY_FIELDS = [
    {"k": "company_name",        "t": "text",     "label": "Company name"},
    {"k": "company_description", "t": "textarea", "label": "Description / mission"},
    {"k": "sector",              "t": "text",     "label": "Sector (e.g. AgriTech, HealthTech)"},
    {"k": "geography",           "t": "text",     "label": "Geography"},
    {"k": "impact_themes",       "t": "text",     "label": "Impact themes (comma-separated)"},
    {"k": "reported_metrics",    "t": "textarea", "label": "Reported metrics (JSON: {\"PI2822\": 1200})"},
    {"k": "sdg_claims",          "t": "text",     "label": "Claimed SDGs (comma-separated integers, e.g. 2,3,8)"},
]

_FIELD_RECIPES: dict[str, list[dict[str, str]]] = {
    "score":               list(_COMPANY_FIELDS),
    "sdg-map":             list(_COMPANY_FIELDS),
    "data-quality":        list(_COMPANY_FIELDS),
    "greenwashing":        [*_COMPANY_FIELDS,
                            {"k": "claims_text", "t": "textarea", "label": "Claims / marketing copy"}],
    "gap-analysis":        list(_COMPANY_FIELDS),
    "validate":            list(_COMPANY_FIELDS),
    "framework":           [{"k": "framework", "t": "text",
                             "label": "Framework (gri|sasb|tcfd|sfdr|edci|unpri|issb_s1|issb_s2|esrs|opim|toc|tnfd|pcaf|eu_tax|cdp|sbti|all)"},
                            *_COMPANY_FIELDS],
    "cross-reference":     [{"k": "metric_id", "t": "text", "label": "IRIS+ metric ID"},
                            {"k": "framework", "t": "text", "label": "Framework ID (optional)"},
                            {"k": "concept",   "t": "text", "label": "Concept keyword (optional)"}],
    "risk-opportunity":    list(_COMPANY_FIELDS),
    "metric-recommend":    list(_COMPANY_FIELDS),
    "exclusion-screen":    list(_COMPANY_FIELDS),
    "report":              list(_COMPANY_FIELDS),
    "decision-workflow":    [{"k": "action", "t": "text",
                              "label": "Action: quick_screen|ic_workflow|deal_compare|lp_readiness"},
                             *_COMPANY_FIELDS,
                             {"k": "claims", "t": "json", "label": "Claims JSON array"},
                             {"k": "metric_records", "t": "json", "label": "Metric records JSON array"},
                             {"k": "company_a", "t": "json", "label": "Company A JSON (deal_compare)"},
                             {"k": "company_b", "t": "json", "label": "Company B JSON (deal_compare)"},
                             {"k": "thesis_path", "t": "text", "label": "Thesis path"},
                             {"k": "dd_coverage_pct", "t": "number", "label": "DD coverage %"},
                             {"k": "exclusion_pass", "t": "boolean", "label": "Exclusion pass"},
                             {"k": "output_format", "t": "text", "label": "Output format: json|text"}],
    "regulatory-calendar": [{"k": "action", "t": "text", "label": "Action: schedule|list_jurisdictions"},
                            {"k": "jurisdiction", "t": "text", "label": "Jurisdiction: EU|US|UK|Singapore|Canada"},
                            {"k": "fiscal_year_end", "t": "text", "label": "Fiscal year end (YYYY-MM-DD)"},
                            {"k": "engagement_id", "t": "text", "label": "Engagement ID"},
                            {"k": "owner", "t": "text", "label": "Owner"},
                            {"k": "output_format", "t": "text", "label": "Output format: json|text"}],
    "pitch-deck":          [{"k": "deck_text", "t": "textarea", "label": "Pitch deck raw text"}],
    "ddq-export":          [*_COMPANY_FIELDS,
                            {"k": "format", "t": "text", "label": "Format: json|excel|csv|pdf"}],
    "pipeline":            [{"k": "action",  "t": "text",     "label": "Action: add|update|list|score|rank"},
                            {"k": "payload", "t": "textarea", "label": "Payload JSON"}],
    "monitoring":          [{"k": "company_name", "t": "text",     "label": "Company name"},
                            {"k": "history",      "t": "textarea", "label": "Historical metrics JSON"}],
    "improvement-advisor": list(_COMPANY_FIELDS),
    "narrative":           list(_COMPANY_FIELDS),
    "batch":               [{"k": "companies", "t": "textarea", "label": "JSON array of company objects"}],
}


# ---------------------------------------------------------------------------
# CSS and JavaScript bundled as raw strings. Keeping them outside the
# f-string means we do *not* have to double every ``{`` / ``}`` — huge
# readability win for anyone maintaining this file.
# ---------------------------------------------------------------------------

_CSS = r"""
:root {
  --bg:#f7f9fc; --surface:#ffffff; --border:#e4e9f0;
  --text:#1f2937; --text-secondary:#4b5563; --text-muted:#9ca3af;
  --primary:#0d47a1; --primary-light:#e3f2fd;
  --success:#2e7d32; --warning:#ef6c00; --danger:#c62828;
  --radius:10px; --shadow:0 2px 8px rgba(15,23,42,0.06);
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font:system-ui,-apple-system,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
}
*,*::before,*::after { box-sizing:border-box; }
html,body { height:100%; margin:0; }
body { font-family:var(--font); color:var(--text); background:var(--bg);
       display:grid; grid-template-columns:320px 1fr; grid-template-rows:56px 1fr;
       grid-template-areas:"topbar topbar" "sidebar main"; }

header.topbar { grid-area:topbar; background:var(--primary); color:#fff;
       display:flex; align-items:center; padding:0 18px; gap:12px;
       box-shadow:var(--shadow); }
header.topbar h1 { margin:0; font-size:18px; font-weight:700; letter-spacing:0.02em; }
header.topbar .tag { background:rgba(255,255,255,0.18); font-size:11px;
       padding:3px 8px; border-radius:10px; letter-spacing:0.08em;
       text-transform:uppercase; font-weight:600; }
header.topbar .right { margin-left:auto; display:flex; gap:10px; align-items:center; font-size:13px; }
header.topbar input.apikey { background:rgba(255,255,255,0.14); border:0; padding:6px 10px;
       border-radius:6px; color:#fff; width:200px; font-family:var(--mono); font-size:12px; }
header.topbar input.apikey::placeholder { color:rgba(255,255,255,0.7); }
header.topbar a { color:#fff; text-decoration:none; opacity:0.85; font-size:13px; }
header.topbar a:hover { opacity:1; }

aside.sidebar { grid-area:sidebar; background:var(--surface); border-right:1px solid var(--border);
       overflow-y:auto; padding:10px 0; }
.sidebar .search { padding:8px 12px; }
.sidebar .search input { width:100%; padding:8px 10px; border:1px solid var(--border);
       border-radius:8px; font-size:13px; background:var(--bg); }
.sidebar .group-label { font-size:10px; letter-spacing:0.1em;
       text-transform:uppercase; color:var(--text-muted); padding:10px 16px 2px;
       display:flex; justify-content:space-between; align-items:center; }
.sidebar .group-label button.clear { background:transparent; border:0; color:var(--text-muted);
       font-size:10px; cursor:pointer; padding:0; letter-spacing:0.06em; }
.sidebar .group-label button.clear:hover { color:var(--danger); }
.sidebar button.tool { display:block; width:calc(100% - 12px); margin:2px 6px;
       text-align:left; padding:10px 12px; background:transparent; border:0;
       border-radius:8px; cursor:pointer; font-size:13px; color:var(--text);
       border-left:3px solid transparent; }
.sidebar button.tool:hover { background:var(--bg); }
.sidebar button.tool.active { background:var(--primary-light); color:var(--primary);
       border-left-color:var(--primary); font-weight:600; }
.sidebar button.tool .t-desc { display:block; color:var(--text-muted); font-size:11px;
       margin-top:2px; line-height:1.35; }
.sidebar button.tool.active .t-desc { color:var(--primary); opacity:0.8; }
.sidebar button.tool .auto-badge { font-size:9px; background:var(--primary-light);
       color:var(--primary); padding:1px 6px; border-radius:8px; margin-left:6px;
       letter-spacing:0.05em; text-transform:uppercase; font-weight:700; vertical-align:middle; }

.sidebar button.run { display:flex; width:calc(100% - 12px); margin:2px 6px;
       text-align:left; padding:8px 10px; background:transparent; border:0;
       border-radius:8px; cursor:pointer; font-size:12px; color:var(--text);
       gap:8px; align-items:flex-start; }
.sidebar button.run:hover { background:var(--bg); }
.sidebar button.run .run-pill { font-size:9px; font-weight:700; padding:2px 6px;
       border-radius:8px; letter-spacing:0.05em; text-transform:uppercase;
       min-width:34px; text-align:center; flex-shrink:0; }
.sidebar button.run .run-pill.ok { background:#dcfce7; color:#166534; }
.sidebar button.run .run-pill.err { background:#fee2e2; color:#991b1b; }
.sidebar button.run .r-body { flex:1; overflow:hidden; }
.sidebar button.run .r-body b { font-size:12px; color:var(--text); display:block;
       white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sidebar button.run .r-body .r-meta { font-size:10px; color:var(--text-muted); margin-top:1px; }

main.workbench { grid-area:main; overflow:auto; padding:24px; }
.panel { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
       box-shadow:var(--shadow); padding:22px 24px; margin-bottom:20px; }
.panel h2 { margin:0 0 4px; font-size:20px; font-weight:700; }
.panel .panel-sub { color:var(--text-secondary); font-size:13px; margin-bottom:16px; }

form.tool-form label { display:block; font-size:12px; color:var(--text-secondary);
       text-transform:uppercase; letter-spacing:0.06em; margin:10px 0 4px; font-weight:600; }
form.tool-form input[type="text"], form.tool-form input[type="number"],
form.tool-form textarea, form.tool-form select {
       width:100%; border:1px solid var(--border); border-radius:8px; padding:8px 10px;
       font-family:var(--font); font-size:14px; background:var(--bg); color:var(--text); }
form.tool-form textarea { min-height:90px; resize:vertical; font-family:var(--mono); font-size:13px; }
form.tool-form .row { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
form.tool-form .hint { color:var(--text-muted); font-size:11px; margin-top:4px; }
form.tool-form .required::after { content:" *"; color:var(--danger); }
form.tool-form .actions { margin-top:18px; display:flex; gap:10px; align-items:center; }
form.tool-form button[type="submit"] { background:var(--primary); color:#fff; border:0;
       padding:10px 18px; border-radius:8px; cursor:pointer; font-size:14px; font-weight:600;
       letter-spacing:0.02em; }
form.tool-form button[type="submit"]:hover { background:#1565c0; }
form.tool-form button[type="button"].secondary { background:var(--bg); border:1px solid var(--border);
       padding:9px 14px; border-radius:8px; cursor:pointer; font-size:13px; color:var(--text-secondary); }
form.tool-form .spinner { display:none; color:var(--text-secondary); font-size:13px; }
form.tool-form .spinner.on { display:inline-flex; gap:6px; align-items:center; }
form.tool-form .schema-badge { display:inline-block; font-size:10px; padding:2px 7px;
       border-radius:8px; letter-spacing:0.06em; margin-left:8px; font-weight:700;
       text-transform:uppercase; vertical-align:middle; }
form.tool-form .schema-badge.openapi { background:var(--primary-light); color:var(--primary); }
form.tool-form .schema-badge.fallback { background:#fff4e5; color:var(--warning); }

.result-panel pre { background:#0f172a; color:#e2e8f0; padding:14px 16px;
       border-radius:8px; overflow:auto; font-size:12.5px; line-height:1.5;
       max-height:60vh; font-family:var(--mono); margin:0; }
.result-panel .meta { display:flex; gap:12px; align-items:center;
       margin-bottom:10px; font-size:12px; color:var(--text-secondary); flex-wrap:wrap; }
.result-panel .meta .pill { padding:2px 8px; border-radius:10px; font-weight:600;
       font-size:11px; letter-spacing:0.04em; text-transform:uppercase; }
.result-panel .pill.ok { background:#dcfce7; color:#166534; }
.result-panel .pill.err { background:#fee2e2; color:#991b1b; }
.result-panel .actions { margin-left:auto; display:flex; gap:8px; }
.result-panel .actions button { background:var(--bg); border:1px solid var(--border);
       padding:4px 10px; border-radius:6px; cursor:pointer; font-size:12px; }
.result-panel .actions button:hover { background:var(--primary-light); color:var(--primary); }
.empty { color:var(--text-muted); font-style:italic; font-size:13px; text-align:center; padding:28px; }

.welcome-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; margin-top:12px; }
.welcome-card { padding:14px; background:var(--bg); border:1px solid var(--border);
       border-radius:8px; font-size:13px; }
.welcome-card b { color:var(--primary); }

@media (max-width: 900px) {
  body { grid-template-columns:1fr; grid-template-areas:"topbar" "sidebar" "main"; }
  aside.sidebar { max-height:260px; border-right:0; border-bottom:1px solid var(--border); }
}
"""


_JS = r"""
const TOOLS_BOOT = __TOOLS_JSON__;   /* server-injected curated list */
const FIELD_RECIPES = __FIELD_RECIPES_JSON__;
const HISTORY_KEY = "impact_vision_runs_v1";
const HISTORY_MAX = 50;

let TOOLS = TOOLS_BOOT.slice();   /* will be extended by OpenAPI walker */
let ACTIVE_TOOL = null;
let SCHEMA_SOURCE = {};           /* tool id -> "openapi" | "fallback" */

/* ---------------------- Type coercion ---------------------- */
function coerce(v, f) {
  if (v == null || v === "") return undefined;
  if (f && f.t === "number") { const n = Number(v); return Number.isFinite(n) ? n : undefined; }
  if (f && f.t === "boolean") { return v === "true" || v === true; }
  if (f && f.t === "array") {
    if (f.itemType === "number") return v.split(",").map(s => Number(s.trim())).filter(Number.isFinite);
    return v.split(",").map(s => s.trim()).filter(Boolean);
  }
  if (f && (f.t === "object" || f.t === "json")) {
    try { return JSON.parse(v); } catch { return v; }
  }
  /* legacy key-based heuristics for the fallback form */
  const k = f && f.k;
  if (k === "impact_themes") return v.split(",").map(s => s.trim()).filter(Boolean);
  if (k === "sdg_claims") return v.split(",").map(s => Number(s.trim())).filter(Number.isFinite);
  if (k === "reported_metrics" || k === "payload" || k === "history" || k === "companies") {
    try { return JSON.parse(v); } catch { return v; }
  }
  return v;
}

/* ---------------------- OpenAPI walker ---------------------- */
async function discoverFromOpenAPI() {
  const base = document.getElementById("apiBase").value.trim() || "";
  try {
    const res = await fetch(base + "/openapi.json");
    if (!res.ok) throw new Error("openapi " + res.status);
    const spec = await res.json();
    const paths = spec.paths || {};
    const found = [];
    for (const [path, methods] of Object.entries(paths)) {
      if (!path.startsWith("/api/v1/")) continue;
      const m = methods.post || methods.put;
      if (!m) continue;
      const id = path.replace(/^\/api\/v1\//, "");
      const label = m.summary || titleCase(id);
      const desc = m.description || m.summary || "REST endpoint " + path;
      const schema = extractRequestSchema(m, spec);
      found.push({ id, label, endpoint: path, desc, schema, _auto: true });
    }
    /* Merge: curated entries win on label/desc/order, but we attach the
       OpenAPI schema to them for auto-form rendering. */
    const byEndpoint = new Map(found.map(x => [x.endpoint, x]));
    for (const t of TOOLS) {
      const a = byEndpoint.get(t.endpoint);
      if (a) { t.schema = a.schema; SCHEMA_SOURCE[t.id] = "openapi"; byEndpoint.delete(t.endpoint); }
      else { SCHEMA_SOURCE[t.id] = "fallback"; }
    }
    /* Anything left in byEndpoint is a truly new endpoint — surface it at the end. */
    for (const extra of byEndpoint.values()) {
      if (!TOOLS.find(t => t.endpoint === extra.endpoint)) {
        TOOLS.push(extra);
        SCHEMA_SOURCE[extra.id] = "openapi";
      }
    }
  } catch (e) {
    console.warn("OpenAPI discovery failed, using curated catalogue:", e);
    for (const t of TOOLS) SCHEMA_SOURCE[t.id] = "fallback";
  } finally {
    renderToolList();
  }
}

function titleCase(s) {
  return s.replace(/[-_]/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function extractRequestSchema(op, spec) {
  const rb = op.requestBody;
  if (!rb || !rb.content) return null;
  const appJson = rb.content["application/json"];
  if (!appJson || !appJson.schema) return null;
  return resolveRef(appJson.schema, spec);
}

function resolveRef(schema, spec) {
  if (!schema) return null;
  if (schema.$ref) {
    const parts = schema.$ref.replace(/^#\//, "").split("/");
    let cur = spec;
    for (const p of parts) cur = cur && cur[p];
    return resolveRef(cur, spec);
  }
  if (schema.allOf) {
    const merged = { type: "object", properties: {}, required: [] };
    for (const part of schema.allOf) {
      const resolved = resolveRef(part, spec);
      Object.assign(merged.properties, resolved.properties || {});
      if (resolved.required) merged.required.push(...resolved.required);
    }
    return merged;
  }
  return schema;
}

/* ---------------------- Form rendering ---------------------- */
function fieldsFromSchema(schema) {
  if (!schema || !schema.properties) return null;
  const required = new Set(schema.required || []);
  const fields = [];
  for (const [k, prop] of Object.entries(schema.properties)) {
    const title = prop.title || k;
    const desc = prop.description || "";
    const t = jsonTypeToField(prop);
    const itemType = (prop.items && prop.items.type) || undefined;
    fields.push({
      k, t: t.t, itemType,
      label: title + (t.hint ? " (" + t.hint + ")" : ""),
      desc, required: required.has(k),
      default: prop.default, enum: prop.enum,
    });
  }
  return fields;
}

function jsonTypeToField(prop) {
  if (prop.enum) return { t: "enum", hint: prop.enum.join("|") };
  const type = prop.type;
  if (type === "integer" || type === "number") return { t: "number", hint: type };
  if (type === "boolean") return { t: "boolean", hint: "true/false" };
  if (type === "array")   return { t: "array",   hint: "comma-separated" };
  if (type === "object")  return { t: "object",  hint: "JSON object" };
  return { t: "text", hint: type };
}

function renderFormFields(form, fields, preset) {
  form.innerHTML = "";
  for (const f of fields) {
    const wrap = document.createElement("div");
    const labelCls = f.required ? "required" : "";
    const lbl = `<label class="${labelCls}" for="fld-${f.k}">${f.label}</label>`;
    const defVal = preset && preset[f.k] !== undefined
      ? (typeof preset[f.k] === "object" ? JSON.stringify(preset[f.k], null, 2) : String(preset[f.k]))
      : (f.default !== undefined ? String(f.default) : "");
    let control;
    if (f.enum) {
      const opts = f.enum.map(v => `<option value="${escHtml(v)}"${String(v)===defVal?" selected":""}>${escHtml(v)}</option>`).join("");
      control = `<select id="fld-${f.k}" name="${f.k}"><option value=""></option>${opts}</select>`;
    } else if (f.t === "object" || f.t === "array" || f.t === "json"
               || f.k === "reported_metrics" || f.k === "payload" || f.k === "history"
               || f.k === "companies" || f.k === "claims_text" || f.k === "deck_text"
               || f.k === "company_description") {
      control = `<textarea id="fld-${f.k}" name="${f.k}">${escHtml(defVal)}</textarea>`;
    } else if (f.t === "number") {
      control = `<input id="fld-${f.k}" name="${f.k}" type="number" step="any" value="${escHtml(defVal)}">`;
    } else if (f.t === "boolean") {
      const checked = defVal === "true" || defVal === true ? "selected" : "";
      control = `<select id="fld-${f.k}" name="${f.k}">
                   <option value=""></option>
                   <option value="true" ${checked}>true</option>
                   <option value="false">false</option>
                 </select>`;
    } else {
      control = `<input id="fld-${f.k}" name="${f.k}" type="text" value="${escHtml(defVal)}">`;
    }
    wrap.innerHTML = lbl + control + (f.desc ? `<div class="hint">${escHtml(f.desc)}</div>` : "");
    form.appendChild(wrap);
  }
  const actions = document.createElement("div");
  actions.className = "actions";
  actions.innerHTML = `
    <button type="submit">Run</button>
    <button type="button" class="secondary" onclick="fillSampleData()">Fill example</button>
    <span class="spinner" id="spinner">Running…</span>`;
  form.appendChild(actions);
}

function escHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
}

/* ---------------------- Tool list ---------------------- */
function renderToolList() {
  const filter = document.getElementById("search").value;
  const list = document.getElementById("toolList");
  list.innerHTML = "";
  const q = filter.trim().toLowerCase();
  TOOLS
    .filter(t => !q || (t.label + " " + t.desc + " " + t.id).toLowerCase().includes(q))
    .forEach(t => {
      const b = document.createElement("button");
      b.className = "tool" + (ACTIVE_TOOL === t.id ? " active" : "");
      const autoBadge = t._auto ? `<span class="auto-badge">auto</span>` : "";
      b.innerHTML = `<span>${escHtml(t.label)} ${autoBadge}</span>` +
                    `<span class="t-desc">${escHtml(t.desc)}</span>`;
      b.onclick = () => selectTool(t.id);
      list.appendChild(b);
    });
  renderHistoryList();
}

function selectTool(id, preset) {
  ACTIVE_TOOL = id;
  const tool = TOOLS.find(t => t.id === id);
  if (!tool) return;
  document.getElementById("welcome").style.display = "none";
  const panel = document.getElementById("toolPanel");
  panel.style.display = "block";
  document.getElementById("toolTitle").textContent = tool.label;

  const src = SCHEMA_SOURCE[id] || "fallback";
  const badge = src === "openapi"
    ? `<span class="schema-badge openapi">OpenAPI</span>`
    : `<span class="schema-badge fallback">fallback recipe</span>`;
  document.getElementById("toolDesc").innerHTML =
    escHtml(tool.desc) + ` &nbsp;·&nbsp; <code>POST ${escHtml(tool.endpoint)}</code> ${badge}`;

  const form = document.getElementById("toolForm");
  let fields = null;
  if (tool.schema) fields = fieldsFromSchema(tool.schema);
  if (!fields || fields.length === 0) fields = FIELD_RECIPES[id] || [];
  renderFormFields(form, fields, preset);
  form.onsubmit = (e) => { e.preventDefault(); runTool(tool, fields); };
  renderToolList();
}

/* ---------------------- Sample data helpers ---------------------- */
function fillSampleData() {
  const form = document.getElementById("toolForm");
  const sample = {
    company_name: "Acme Solar",
    company_description: "Off-grid solar home systems for smallholder farmers in East Africa. 220k homes electrified since 2019, measured via PI2822 (new energy access clients) and OI2764 (GHG avoided).",
    sector: "energy",
    geography: "KE",
    impact_themes: "climate, energy access",
    reported_metrics: '{"PI2822": 220000, "OI2764": 145000}',
    sdg_claims: "7,13",
    claims_text: "We deliver life-changing clean energy to millions of families. Our mission is to power sustainable futures.",
    deck_text: "Acme Solar. Series B. Deploys solar home systems across Kenya and Uganda.",
    framework: "sfdr",
    metric_id: "PI2822",
    format: "json",
    action: "add",
    payload: '{"deal_id": "ACM-001", "stage": "due_diligence"}',
    history: '{"2024-Q1": {"PI2822": 180000}, "2024-Q2": {"PI2822": 220000}}',
    companies: '[{"company_name": "Acme Solar", "sector": "energy"}, {"company_name": "Blue Agua", "sector": "water"}]',
  };
  for (const el of form.querySelectorAll("input[name], textarea[name], select[name]")) {
    if (sample[el.name] !== undefined) el.value = sample[el.name];
  }
}

/* ---------------------- Run + history ---------------------- */
async function runTool(tool, fields) {
  const form = document.getElementById("toolForm");
  const body = {};
  const fieldByName = new Map((fields || []).map(f => [f.k, f]));
  for (const el of form.querySelectorAll("input[name], textarea[name], select[name]")) {
    const f = fieldByName.get(el.name) || { k: el.name, t: "text" };
    const v = coerce(el.value, f);
    if (v !== undefined && v !== "") body[el.name] = v;
  }
  const base = document.getElementById("apiBase").value.trim() || "";
  const token = document.getElementById("apiToken").value.trim();
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = "Bearer " + token;

  const spinner = document.getElementById("spinner");
  spinner && spinner.classList.add("on");
  const meta = document.getElementById("resultMeta");
  const resultBody = document.getElementById("resultBody");
  document.getElementById("resultPanel").style.display = "block";
  meta.innerHTML = "";
  resultBody.textContent = "";

  const started = performance.now();
  let status = 0, statusText = "NETWORK", elapsed = 0, ok = false, text = "";
  try {
    const res = await fetch(base + tool.endpoint, { method: "POST", headers, body: JSON.stringify(body) });
    elapsed = Math.round(performance.now() - started);
    status = res.status; statusText = res.statusText; ok = res.ok;
    text = await res.text();
    let parsed; try { parsed = JSON.parse(text); } catch { parsed = null; }
    meta.innerHTML =
      `<span class="pill ${ok ? "ok" : "err"}">${status} ${escHtml(statusText)}</span>` +
      `<span>${escHtml(tool.endpoint)}</span>` +
      `<span>${elapsed} ms</span>` +
      `<div class="actions">
         <button type="button" onclick="copyResult()">Copy JSON</button>
         <button type="button" onclick="downloadResult()">Save .json</button>
      </div>`;
    resultBody.textContent = parsed ? JSON.stringify(parsed, null, 2) : text;
  } catch (err) {
    elapsed = Math.round(performance.now() - started);
    meta.innerHTML = `<span class="pill err">NETWORK</span><span>${escHtml(String(err))}</span>`;
    resultBody.textContent = String(err);
    text = String(err);
  } finally {
    spinner && spinner.classList.remove("on");
  }

  /* Persist to localStorage history */
  pushHistory({
    id: String(Date.now()) + "-" + Math.random().toString(36).slice(2, 7),
    tool_id: tool.id,
    tool_label: tool.label,
    endpoint: tool.endpoint,
    body,
    ok,
    status, statusText,
    elapsed_ms: elapsed,
    ts: new Date().toISOString(),
    result_preview: text.slice(0, 4000),
  });
}

function copyResult() {
  navigator.clipboard.writeText(document.getElementById("resultBody").textContent);
}
function downloadResult() {
  const body = document.getElementById("resultBody").textContent;
  const blob = new Blob([body], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = (ACTIVE_TOOL || "result") + "-" + Date.now() + ".json";
  a.click();
}

/* ---------------------- History (localStorage) ---------------------- */
function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); }
  catch { return []; }
}
function saveHistory(items) {
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, HISTORY_MAX))); } catch {}
}
function pushHistory(item) {
  const items = loadHistory();
  items.unshift(item);
  saveHistory(items);
  renderHistoryList();
}
function clearHistory() {
  if (!confirm("Clear all " + loadHistory().length + " recent runs?")) return;
  saveHistory([]); renderHistoryList();
}
function renderHistoryList() {
  const wrap = document.getElementById("historyList");
  const items = loadHistory();
  document.getElementById("historyCount").textContent = items.length ? "(" + items.length + ")" : "";
  wrap.innerHTML = "";
  if (items.length === 0) {
    wrap.innerHTML = `<div class="empty" style="padding:12px;font-size:11px;">No runs yet — kick off a tool to populate.</div>`;
    return;
  }
  for (const h of items.slice(0, 20)) {
    const b = document.createElement("button");
    b.className = "run";
    const date = new Date(h.ts);
    const hhmm = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const pillCls = h.ok ? "ok" : "err";
    b.innerHTML = `
      <span class="run-pill ${pillCls}">${h.status || "ERR"}</span>
      <div class="r-body">
        <b>${escHtml(h.tool_label || h.tool_id)}</b>
        <div class="r-meta">${hhmm} · ${h.elapsed_ms}ms · ${escHtml(h.endpoint)}</div>
      </div>`;
    b.onclick = () => replayHistory(h);
    wrap.appendChild(b);
  }
}
function replayHistory(h) {
  selectTool(h.tool_id, h.body || {});
  const meta = document.getElementById("resultMeta");
  const resultBody = document.getElementById("resultBody");
  document.getElementById("resultPanel").style.display = "block";
  const pillCls = h.ok ? "ok" : "err";
  meta.innerHTML =
    `<span class="pill ${pillCls}">${h.status} ${escHtml(h.statusText || "")}</span>` +
    `<span>${escHtml(h.endpoint)}</span>` +
    `<span>${h.elapsed_ms} ms</span>` +
    `<span style="color:var(--text-muted);">· replay from ${new Date(h.ts).toLocaleString()}</span>`;
  resultBody.textContent = h.result_preview || "(no cached body)";
}

/* ---------------------- Bootstrap ---------------------- */
document.getElementById("search").addEventListener("input", () => renderToolList());
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault(); document.getElementById("search").focus();
  }
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    const f = document.getElementById("toolForm");
    if (f) f.dispatchEvent(new Event("submit", { cancelable: true }));
  }
});
document.getElementById("apiBase").addEventListener("change", () => discoverFromOpenAPI());

renderToolList();
discoverFromOpenAPI();
"""


# ---------------------------------------------------------------------------
# HTML shell. Kept simple: the CSS and JS blocks above are substituted in.
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Impact Vision — Web Console</title>
<style>{css}</style>
</head>
<body>
<header class="topbar">
  <h1>Impact Vision</h1>
  <span class="tag">Web Console</span>
  <div class="right">
    <input id="apiBase"  class="apikey" value="" placeholder="API base (default /)" title="Leave blank to call the same host">
    <input id="apiToken" class="apikey" type="password" placeholder="Bearer token (optional)" title="IMPACT_VISION_API_KEY">
    <a href="/docs" target="_blank">OpenAPI</a>
    <a href="https://github.com/joejoe168168/impact-vision" target="_blank">GitHub</a>
  </div>
</header>

<aside class="sidebar">
  <div class="search"><input id="search" placeholder="Filter tools…"></div>
  <div class="group-label">
    <span>Recent runs <span id="historyCount"></span></span>
    <button type="button" class="clear" onclick="clearHistory()">clear</button>
  </div>
  <div id="historyList"></div>
  <div class="group-label"><span>Tools</span></div>
  <div id="toolList"></div>
</aside>

<main class="workbench">
  <div id="welcome" class="panel">
    <h2>Welcome</h2>
    <p class="panel-sub">Pick a tool on the left to run it against the live
      Impact Vision API. All 26 tools are wired to the FastAPI gateway at
      <code>/api/v1/*</code>. New endpoints are discovered automatically from
      <code>/openapi.json</code> on every page load.</p>
    <div class="welcome-grid">
      <div class="welcome-card"><b>Hotkeys</b><br><code>Ctrl/⌘+K</code> focuses the filter.<br><code>Ctrl/⌘+Enter</code> runs the current tool.</div>
      <div class="welcome-card"><b>Forms</b><br>Each form shows a <em>OpenAPI</em> badge when the gateway is reachable, or <em>fallback recipe</em> when we can't read the schema.</div>
      <div class="welcome-card"><b>Run history</b><br>The last 50 runs are cached in your browser only (<code>localStorage</code>). Click one to replay the form &amp; response.</div>
      <div class="welcome-card"><b>Auth</b><br>If the gateway requires a bearer token set <code>IMPACT_VISION_API_KEY</code>, paste it in the top-right box.</div>
    </div>
  </div>

  <div id="toolPanel" class="panel" style="display:none">
    <h2 id="toolTitle"></h2>
    <p class="panel-sub" id="toolDesc"></p>
    <form class="tool-form" id="toolForm"></form>
  </div>

  <div id="resultPanel" class="panel result-panel" style="display:none">
    <div class="meta" id="resultMeta"></div>
    <pre id="resultBody"></pre>
  </div>
</main>

<script>{js}</script>
</body>
</html>"""


def render_console_html() -> str:
    """Return the self-contained console HTML as a single string."""
    tools_json = json.dumps(_TOOL_CATALOGUE)
    field_recipes_json = json.dumps(_FIELD_RECIPES)
    js = (
        _JS
        .replace("__TOOLS_JSON__", tools_json)
        .replace("__FIELD_RECIPES_JSON__", field_recipes_json)
    )
    return _HTML_TEMPLATE.format(css=_CSS, js=js)


# ---------------------------------------------------------------------------
# FastAPI router — mountable into any existing app.
# ---------------------------------------------------------------------------

def _require_fastapi() -> None:
    if _FASTAPI_IMPORT_ERROR is not None:
        raise ImportError(
            "FastAPI is required for the web console. "
            "Install with: pip install fastapi uvicorn"
        ) from _FASTAPI_IMPORT_ERROR


def _build_router() -> Any:
    _require_fastapi()
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def _console_root() -> str:
        return render_console_html()

    @router.get("/console", response_class=HTMLResponse, include_in_schema=False)
    async def _console_alias() -> str:
        return render_console_html()

    return router


def console_router() -> Any:
    """Return a FastAPI :class:`APIRouter` serving the web console SPA."""
    return _build_router()
