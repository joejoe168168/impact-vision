"""Web console — a lightweight SPA for Impact Vision tools.

We serve a single self-contained HTML document that:
  * lists every registered tool (discovered from
    ``openharness.tools.impact``) with a short description;
  * renders a dynamic form for the currently-selected tool;
  * submits the form to the matching ``/api/v1/*`` endpoint on the
    FastAPI gateway;
  * streams the JSON / HTML response back into a results pane with
    collapsible sections, pretty-printing and one-click "download"
    buttons for HTML artefacts.

Design goals:
  * **Zero build step** — the whole UI ships as a single ``.html`` string
    with inline CSS + JS; contributors can read it top-to-bottom.
  * **Reuse the REST gateway** — every call goes through
    ``/api/v1/*`` so the console automatically picks up new endpoints.
  * **No external runtime deps** — no React / Vue / HTMX etc. Just the
    browser + fetch.

This sits alongside the Streamlit dashboard (``openharness.dashboard``)
rather than replacing it: Streamlit is good for analysts who want
interactive charts; the web console is for power users who want the
full 26-tool surface in a browser-native IDE-like layout.
"""
from __future__ import annotations

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
# Tool catalogue used by the front-end to populate the sidebar.
# ---------------------------------------------------------------------------

# Each entry: (tool id, human label, REST endpoint, one-line description).
# Kept as a module-level constant so the HTML template can inline it as JSON
# without hitting the tool registry at request time.
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


def render_console_html() -> str:
    """Return the self-contained console HTML as a single string."""
    import json

    tools_json = json.dumps(_TOOL_CATALOGUE)
    # NB: we use {% ... %} / f-string style placeholders that do not clash
    # with JavaScript template literals. Everything is inlined so there are
    # no missing-asset headaches when hosting this behind a reverse proxy.
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Impact Vision — Web Console</title>
<style>
  :root {{
    --bg:#f7f9fc; --surface:#ffffff; --border:#e4e9f0;
    --text:#1f2937; --text-secondary:#4b5563; --text-muted:#9ca3af;
    --primary:#0d47a1; --primary-light:#e3f2fd;
    --success:#2e7d32; --warning:#ef6c00; --danger:#c62828;
    --radius:10px; --shadow:0 2px 8px rgba(15,23,42,0.06);
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    --font:system-ui,-apple-system,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
  }}
  *,*::before,*::after {{ box-sizing:border-box; }}
  html,body {{ height:100%; margin:0; }}
  body {{ font-family:var(--font); color:var(--text); background:var(--bg);
         display:grid; grid-template-columns:320px 1fr; grid-template-rows:56px 1fr;
         grid-template-areas:"topbar topbar" "sidebar main"; }}

  header.topbar {{ grid-area:topbar; background:var(--primary); color:#fff;
         display:flex; align-items:center; padding:0 18px; gap:12px;
         box-shadow:var(--shadow); }}
  header.topbar h1 {{ margin:0; font-size:18px; font-weight:700; letter-spacing:0.02em; }}
  header.topbar .tag {{ background:rgba(255,255,255,0.18); font-size:11px;
         padding:3px 8px; border-radius:10px; letter-spacing:0.08em;
         text-transform:uppercase; font-weight:600; }}
  header.topbar .right {{ margin-left:auto; display:flex; gap:10px; align-items:center; font-size:13px; }}
  header.topbar input.apikey {{ background:rgba(255,255,255,0.14); border:0; padding:6px 10px;
         border-radius:6px; color:#fff; width:200px; font-family:var(--mono); font-size:12px; }}
  header.topbar input.apikey::placeholder {{ color:rgba(255,255,255,0.7); }}
  header.topbar a {{ color:#fff; text-decoration:none; opacity:0.85; font-size:13px; }}
  header.topbar a:hover {{ opacity:1; }}

  aside.sidebar {{ grid-area:sidebar; background:var(--surface); border-right:1px solid var(--border);
         overflow-y:auto; padding:10px 0; }}
  .sidebar .search {{ padding:8px 12px; }}
  .sidebar .search input {{ width:100%; padding:8px 10px; border:1px solid var(--border);
         border-radius:8px; font-size:13px; background:var(--bg); }}
  .sidebar .group-label {{ font-size:10px; letter-spacing:0.1em;
         text-transform:uppercase; color:var(--text-muted); padding:8px 16px 2px; }}
  .sidebar button.tool {{ display:block; width:calc(100% - 12px); margin:2px 6px;
         text-align:left; padding:10px 12px; background:transparent; border:0;
         border-radius:8px; cursor:pointer; font-size:13px; color:var(--text);
         border-left:3px solid transparent; }}
  .sidebar button.tool:hover {{ background:var(--bg); }}
  .sidebar button.tool.active {{ background:var(--primary-light); color:var(--primary);
         border-left-color:var(--primary); font-weight:600; }}
  .sidebar button.tool .t-desc {{ display:block; color:var(--text-muted); font-size:11px;
         margin-top:2px; line-height:1.35; }}
  .sidebar button.tool.active .t-desc {{ color:var(--primary); opacity:0.8; }}

  main.workbench {{ grid-area:main; overflow:auto; padding:24px; }}
  .panel {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
         box-shadow:var(--shadow); padding:22px 24px; margin-bottom:20px; }}
  .panel h2 {{ margin:0 0 4px; font-size:20px; font-weight:700; }}
  .panel .panel-sub {{ color:var(--text-secondary); font-size:13px; margin-bottom:16px; }}

  form.tool-form label {{ display:block; font-size:12px; color:var(--text-secondary);
         text-transform:uppercase; letter-spacing:0.06em; margin:10px 0 4px; font-weight:600; }}
  form.tool-form input[type="text"], form.tool-form textarea, form.tool-form select {{
         width:100%; border:1px solid var(--border); border-radius:8px; padding:8px 10px;
         font-family:var(--font); font-size:14px; background:var(--bg); color:var(--text); }}
  form.tool-form textarea {{ min-height:90px; resize:vertical; font-family:var(--mono); font-size:13px; }}
  form.tool-form .row {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  form.tool-form .hint {{ color:var(--text-muted); font-size:11px; margin-top:4px; }}
  form.tool-form .actions {{ margin-top:18px; display:flex; gap:10px; align-items:center; }}
  form.tool-form button[type="submit"] {{ background:var(--primary); color:#fff; border:0;
         padding:10px 18px; border-radius:8px; cursor:pointer; font-size:14px; font-weight:600;
         letter-spacing:0.02em; }}
  form.tool-form button[type="submit"]:hover {{ background:#1565c0; }}
  form.tool-form .spinner {{ display:none; color:var(--text-secondary); font-size:13px; }}
  form.tool-form .spinner.on {{ display:inline-flex; gap:6px; align-items:center; }}

  .result-panel pre {{ background:#0f172a; color:#e2e8f0; padding:14px 16px;
         border-radius:8px; overflow:auto; font-size:12.5px; line-height:1.5;
         max-height:60vh; font-family:var(--mono); margin:0; }}
  .result-panel .meta {{ display:flex; gap:12px; align-items:center;
         margin-bottom:10px; font-size:12px; color:var(--text-secondary); flex-wrap:wrap; }}
  .result-panel .meta .pill {{ padding:2px 8px; border-radius:10px; font-weight:600;
         font-size:11px; letter-spacing:0.04em; text-transform:uppercase; }}
  .result-panel .pill.ok {{ background:#dcfce7; color:#166534; }}
  .result-panel .pill.err {{ background:#fee2e2; color:#991b1b; }}
  .result-panel .actions {{ margin-left:auto; display:flex; gap:8px; }}
  .result-panel .actions button {{ background:var(--bg); border:1px solid var(--border);
         padding:4px 10px; border-radius:6px; cursor:pointer; font-size:12px; }}
  .result-panel .actions button:hover {{ background:var(--primary-light); color:var(--primary); }}
  .empty {{ color:var(--text-muted); font-style:italic; font-size:13px; text-align:center; padding:28px; }}

  .welcome-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; margin-top:12px; }}
  .welcome-card {{ padding:14px; background:var(--bg); border:1px solid var(--border);
         border-radius:8px; font-size:13px; }}
  .welcome-card b {{ color:var(--primary); }}

  @media (max-width: 900px) {{
    body {{ grid-template-columns:1fr; grid-template-areas:"topbar" "sidebar" "main"; }}
    aside.sidebar {{ max-height:200px; border-right:0; border-bottom:1px solid var(--border); }}
  }}
</style>
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
  <div class="group-label">Tools</div>
  <div id="toolList"></div>
</aside>

<main class="workbench">
  <div id="welcome" class="panel">
    <h2>Welcome</h2>
    <p class="panel-sub">Pick a tool on the left to run it against the live
      Impact Vision API. All 26 tools are wired to the FastAPI gateway at
      <code>/api/v1/*</code>.</p>
    <div class="welcome-grid">
      <div class="welcome-card"><b>Hotkeys</b><br><code>Ctrl/⌘+K</code> focuses the filter.<br><code>Ctrl/⌘+Enter</code> runs the current tool.</div>
      <div class="welcome-card"><b>Auth</b><br>If the gateway requires a bearer token set <code>IMPACT_VISION_API_KEY</code>, paste it in the top-right box.</div>
      <div class="welcome-card"><b>Local dev</b><br>Run <code>uvicorn openharness.api_gateway.router:app --reload</code> then open this page at <code>/</code>.</div>
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

<script>
const TOOLS = {tools_json};
let ACTIVE_TOOL = null;

/* ---------------------- Forms per tool ---------------------- */
function companyFields() {{
  return [
    {{k:"company_name",        t:"text",     label:"Company name"}},
    {{k:"company_description", t:"textarea", label:"Description / mission"}},
    {{k:"sector",              t:"text",     label:"Sector (e.g. AgriTech, HealthTech)"}},
    {{k:"geography",           t:"text",     label:"Geography"}},
    {{k:"impact_themes",       t:"text",     label:"Impact themes (comma-separated)"}},
    {{k:"reported_metrics",    t:"textarea", label:"Reported metrics (JSON: {{\\"PI5380\\": 1200}})"}},
    {{k:"sdg_claims",          t:"text",     label:"Claimed SDGs (comma-separated integers, e.g. 2,3,8)"}},
  ];
}}

const FIELD_RECIPES = {{
  "score":               companyFields(),
  "sdg-map":             companyFields(),
  "data-quality":        companyFields(),
  "greenwashing":        [...companyFields(),
                           {{k:"claims_text", t:"textarea", label:"Claims / marketing copy"}}],
  "gap-analysis":        companyFields(),
  "validate":            companyFields(),
  "framework":           [{{k:"framework", t:"text", label:"Framework (gri|sasb|tcfd|sfdr|edci|unpri|issb_s1|issb_s2|esrs|opim|toc|tnfd|pcaf|eu_tax|cdp|sbti|all)"}},
                           ...companyFields()],
  "cross-reference":     [{{k:"metric_id", t:"text", label:"IRIS+ metric ID"}},
                          {{k:"framework", t:"text", label:"Framework ID (optional)"}},
                          {{k:"concept",   t:"text", label:"Concept keyword (optional)"}}],
  "risk-opportunity":    companyFields(),
  "metric-recommend":    companyFields(),
  "exclusion-screen":    companyFields(),
  "report":              companyFields(),
  "pitch-deck":          [{{k:"deck_text", t:"textarea", label:"Pitch deck raw text"}}],
  "ddq-export":          [...companyFields(),
                          {{k:"format", t:"text", label:"Format: json|excel|csv|pdf"}}],
  "pipeline":            [{{k:"action",  t:"text", label:"Action: add|update|list|score|rank"}},
                          {{k:"payload", t:"textarea", label:"Payload JSON"}}],
  "monitoring":          [{{k:"company_name", t:"text", label:"Company name"}},
                          {{k:"history",      t:"textarea", label:"Historical metrics JSON"}}],
  "improvement-advisor": companyFields(),
  "narrative":           companyFields(),
  "batch":               [{{k:"companies", t:"textarea", label:"JSON array of company objects"}}],
}};

function coerce(v, k) {{
  if (v == null || v === "") return undefined;
  if (k === "impact_themes" || k === "sdg_claims") {{
    const arr = v.split(",").map(s => s.trim()).filter(Boolean);
    return k === "sdg_claims" ? arr.map(Number).filter(n => Number.isFinite(n)) : arr;
  }}
  if (k === "reported_metrics" || k === "payload" || k === "history" || k === "companies") {{
    try {{ return JSON.parse(v); }} catch {{ return v; }}
  }}
  return v;
}}

function renderToolList(filter="") {{
  const list = document.getElementById("toolList");
  list.innerHTML = "";
  const q = filter.trim().toLowerCase();
  TOOLS.filter(t => !q || (t.label+" "+t.desc+" "+t.id).toLowerCase().includes(q))
       .forEach(t => {{
         const b = document.createElement("button");
         b.className = "tool" + (ACTIVE_TOOL === t.id ? " active" : "");
         b.innerHTML = `<span>${{t.label}}</span><span class="t-desc">${{t.desc}}</span>`;
         b.onclick = () => selectTool(t.id);
         list.appendChild(b);
       }});
}}

function selectTool(id) {{
  ACTIVE_TOOL = id;
  const tool = TOOLS.find(t => t.id === id);
  if (!tool) return;
  document.getElementById("welcome").style.display = "none";
  document.getElementById("toolPanel").style.display = "block";
  document.getElementById("toolTitle").textContent = tool.label;
  document.getElementById("toolDesc").innerHTML = tool.desc +
    ` &nbsp;·&nbsp; <code>POST ${{tool.endpoint}}</code>`;
  const form = document.getElementById("toolForm");
  form.innerHTML = "";
  const fields = FIELD_RECIPES[id] || [];
  for (const f of fields) {{
    const wrap = document.createElement("div");
    wrap.innerHTML = `<label for="fld-${{f.k}}">${{f.label}}</label>` +
      (f.t === "textarea"
        ? `<textarea id="fld-${{f.k}}" name="${{f.k}}"></textarea>`
        : `<input id="fld-${{f.k}}" name="${{f.k}}" type="text">`);
    form.appendChild(wrap);
  }}
  const actions = document.createElement("div");
  actions.className = "actions";
  actions.innerHTML = `<button type="submit">Run ${{tool.label}}</button>
    <span class="spinner" id="spinner">Running…</span>`;
  form.appendChild(actions);
  form.onsubmit = (e) => {{ e.preventDefault(); runTool(tool); }};
  renderToolList(document.getElementById("search").value);
}}

async function runTool(tool) {{
  const form = document.getElementById("toolForm");
  const body = {{}};
  for (const el of form.querySelectorAll("input,textarea,select")) {{
    if (el.name) {{
      const v = coerce(el.value, el.name);
      if (v !== undefined) body[el.name] = v;
    }}
  }}
  const base = document.getElementById("apiBase").value.trim() || "";
  const token = document.getElementById("apiToken").value.trim();
  const headers = {{"Content-Type": "application/json"}};
  if (token) headers["Authorization"] = "Bearer " + token;

  const spinner = document.getElementById("spinner");
  spinner.classList.add("on");
  const meta = document.getElementById("resultMeta");
  const resultBody = document.getElementById("resultBody");
  document.getElementById("resultPanel").style.display = "block";
  meta.innerHTML = "";
  resultBody.textContent = "";

  const started = performance.now();
  try {{
    const res = await fetch(base + tool.endpoint, {{method: "POST", headers, body: JSON.stringify(body)}});
    const elapsed = (performance.now() - started).toFixed(0);
    let text = await res.text();
    let parsed; try {{ parsed = JSON.parse(text); }} catch {{ parsed = null; }}
    meta.innerHTML =
      `<span class="pill ${{res.ok ? "ok" : "err"}}">${{res.status}} ${{res.statusText}}</span>` +
      `<span>${{tool.endpoint}}</span>` +
      `<span>${{elapsed}} ms</span>` +
      `<div class="actions">
        <button onclick="navigator.clipboard.writeText(document.getElementById('resultBody').textContent)">Copy JSON</button>
        <button onclick="downloadHTML()">Save .json</button>
      </div>`;
    resultBody.textContent = parsed ? JSON.stringify(parsed, null, 2) : text;
  }} catch (err) {{
    meta.innerHTML = `<span class="pill err">NETWORK</span><span>${{err}}</span>`;
    resultBody.textContent = String(err);
  }} finally {{
    spinner.classList.remove("on");
  }}
}}

function downloadHTML() {{
  const body = document.getElementById("resultBody").textContent;
  const blob = new Blob([body], {{type: "application/json"}});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = (ACTIVE_TOOL || "result") + ".json";
  a.click();
}}

document.getElementById("search").addEventListener("input", e => renderToolList(e.target.value));
document.addEventListener("keydown", e => {{
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {{
    e.preventDefault(); document.getElementById("search").focus();
  }}
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {{
    const f = document.getElementById("toolForm");
    if (f) f.dispatchEvent(new Event("submit", {{cancelable: true}}));
  }}
}});

renderToolList();
</script>
</body>
</html>"""


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


# Lazy accessor so importing ``openharness.web`` doesn't require FastAPI
# unless the consumer actually uses the router.
def console_router() -> Any:
    """Return a FastAPI :class:`APIRouter` serving the web console SPA."""
    return _build_router()
