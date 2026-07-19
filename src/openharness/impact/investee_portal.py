"""Investee data-collection portal (v5 Track C2).

Generates a **self-contained, offline, single-file HTML** guided questionnaire
that a fund can send to an investee to collect impact / ESG / PAI data. It is
built for the comparability problem LPs flagged (ILPA/Tideline 2026): the form
provides

* **plain-language framing** for every question (especially SFDR PAI
  indicators, which are otherwise jargon-heavy),
* a **"why we need this"** rationale on each field (the feedback loop that
  improves investee response quality),
* **client-side validation** (required, numeric ranges, units), and
* **WCAG 2.2 AA** structure (labels, fieldset/legend, focus states, a skip
  link via the shared chrome) so it is accessible by default.

Submissions are exported as JSON locally in the browser (no server needed),
which the fund can then feed into `investee_collection` / `framework_assess`.
"""

from __future__ import annotations

import html
from typing import Literal

from pydantic import BaseModel, Field

from openharness.impact.report_templates.report_v2 import wrap_document


FieldType = Literal["number", "text", "longtext", "select", "boolean", "percent"]


class PortalQuestion(BaseModel):
    id: str
    label: str
    why_we_need_this: str = ""
    plain_language: str = ""
    field_type: FieldType = "text"
    unit: str = ""
    required: bool = False
    options: list[str] = Field(default_factory=list)
    min: float | None = None
    max: float | None = None
    pai_ref: str = ""
    framework_ref: str = ""


class PortalSection(BaseModel):
    title: str
    description: str = ""
    questions: list[PortalQuestion] = Field(default_factory=list)


def default_portal_sections(include_pai: bool = True) -> list[PortalSection]:
    """A default investee questionnaire: company basics + impact + SFDR PAI."""
    sections: list[PortalSection] = [
        PortalSection(
            title="Company basics",
            description="A few facts so we can tailor the right impact metrics to your business.",
            questions=[
                PortalQuestion(
                    id="company_name",
                    label="Company name",
                    field_type="text",
                    required=True,
                    why_we_need_this="Identifies your submission and links it to our records.",
                ),
                PortalQuestion(
                    id="sector",
                    label="Primary sector",
                    field_type="text",
                    required=True,
                    why_we_need_this="Determines which IRIS+ metrics and benchmarks apply to you.",
                ),
                PortalQuestion(
                    id="geography",
                    label="Main country/region of operation",
                    field_type="text",
                    why_we_need_this="Lets us contextualise impact against local need and regulation.",
                ),
                PortalQuestion(
                    id="employees",
                    label="Total employees (FTE)",
                    field_type="number",
                    unit="people",
                    min=0,
                    why_we_need_this="Used for per-capita intensity metrics and CSRD/VSME scope checks.",
                ),
            ],
        ),
        PortalSection(
            title="Impact thesis & outcomes",
            description="Your intended impact and the outcomes you can already evidence.",
            questions=[
                PortalQuestion(
                    id="impact_thesis",
                    label="What change are you trying to create?",
                    field_type="longtext",
                    required=True,
                    why_we_need_this="The basis of your theory of change — we map it to SDGs and IRIS+ outcomes.",
                ),
                PortalQuestion(
                    id="beneficiaries",
                    label="People meaningfully reached (last 12 months)",
                    field_type="number",
                    unit="people",
                    min=0,
                    why_we_need_this="Breadth of impact — feeds the welfare (QALY) quantifier and SDG-need context.",
                ),
                PortalQuestion(
                    id="underserved_share",
                    label="Share of beneficiaries who are underserved",
                    field_type="percent",
                    unit="%",
                    min=0,
                    max=100,
                    why_we_need_this="Depth/additionality — underserved reach scores higher on the 5 Dimensions.",
                ),
            ],
        ),
    ]
    if include_pai:
        sections.append(_pai_section())
    return sections


def _pai_section() -> PortalSection:
    """Plain-language SFDR PAI questions seeded from the PAI indicator list."""
    questions: list[PortalQuestion] = []
    try:
        from openharness.impact.frameworks.sfdr_pai import get_pai_indicators

        indicators = get_pai_indicators()
    except Exception:  # noqa: BLE001
        indicators = []

    # Plain-language rewrites for the headline mandatory PAI indicators.
    plain: dict[int, tuple[str, str, FieldType, str]] = {
        1: (
            "Your total greenhouse-gas emissions",
            "tCO2e",
            "number",
            "Scope 1+2 (and 3 if known) GHG emissions.",
        ),
        3: (
            "How carbon-intensive your revenue is",
            "tCO2e/€M",
            "number",
            "GHG emissions per €M revenue.",
        ),
        4: (
            "Do you operate in fossil fuels?",
            "",
            "boolean",
            "Any revenue from the fossil-fuel sector.",
        ),
        5: (
            "Share of energy from non-renewable sources",
            "%",
            "percent",
            "Non-renewable energy consumption/production share.",
        ),
        10: (
            "Any breaches of UN Global Compact / OECD Guidelines?",
            "",
            "boolean",
            "Violations of responsible-business principles.",
        ),
        13: ("Share of women on your board", "%", "percent", "Board gender diversity."),
    }
    for ind in indicators:
        num = getattr(ind, "number", None)
        if num not in plain:
            continue
        label, unit, ftype, why = plain[num]
        questions.append(
            PortalQuestion(
                id=f"pai_{num}",
                label=label,
                plain_language=f"SFDR PAI {num}: {getattr(ind, 'name', '')}",
                why_we_need_this=why
                + " Required by EU SFDR if we market this fund as Article 8/9.",
                field_type=ftype,
                unit=unit,
                min=0 if ftype in ("number", "percent") else None,
                max=100 if ftype == "percent" else None,
                pai_ref=str(num),
            )
        )
    # Fallback if the PAI catalogue wasn't importable.
    if not questions:
        questions = [
            PortalQuestion(
                id="pai_1",
                label="Your total greenhouse-gas emissions",
                field_type="number",
                unit="tCO2e",
                min=0,
                pai_ref="1",
                why_we_need_this="Scope 1+2 GHG emissions — required for SFDR PAI 1.",
            ),
            PortalQuestion(
                id="pai_13",
                label="Share of women on your board",
                field_type="percent",
                unit="%",
                min=0,
                max=100,
                pai_ref="13",
                why_we_need_this="Board gender diversity — SFDR PAI 13.",
            ),
        ]
    return PortalSection(
        title="SFDR Principal Adverse Impacts (plain language)",
        description=(
            "These map to the EU SFDR mandatory adverse-impact indicators. We've "
            "translated the jargon — answer what you can; leave blanks where data isn't ready."
        ),
        questions=questions,
    )


_PORTAL_CSS = """
.portal-intro{background:var(--primary-light,#e3f2fd);border-left:4px solid var(--primary,#1565c0);
  padding:14px 18px;border-radius:8px;margin:16px 0;}
fieldset.portal-section{border:1px solid var(--border,#d0d7de);border-radius:12px;padding:18px 20px;margin:18px 0;}
fieldset.portal-section>legend{font-weight:700;font-size:1.1rem;padding:0 8px;}
.portal-q{margin:14px 0;padding:12px 0;border-bottom:1px solid var(--border,#eee);}
.portal-q:last-child{border-bottom:none;}
.portal-q label{display:block;font-weight:600;margin-bottom:4px;}
.portal-q .req{color:#c62828;margin-left:3px;}
.portal-q input,.portal-q select,.portal-q textarea{width:100%;max-width:520px;padding:8px 10px;
  border:1px solid var(--border,#c0c7d0);border-radius:8px;font:inherit;}
.portal-q textarea{min-height:80px;}
.portal-q .why{font-size:0.85em;color:var(--text-secondary,#5f6368);margin-top:4px;}
.portal-q .plain{font-size:0.8em;color:var(--text-secondary,#5f6368);font-style:italic;}
.portal-q .unit{font-size:0.8em;color:var(--text-secondary,#5f6368);margin-left:6px;}
.portal-q .field-error{color:#c62828;font-size:0.82em;margin-top:4px;display:none;}
.portal-q.invalid input,.portal-q.invalid select,.portal-q.invalid textarea{border-color:#c62828;}
.portal-actions{margin:24px 0;display:flex;gap:12px;flex-wrap:wrap;align-items:center;}
.portal-btn{background:var(--primary,#1565c0);color:#fff;border:none;padding:10px 20px;border-radius:8px;
  font-weight:600;cursor:pointer;}
.portal-btn.secondary{background:#fff;color:var(--primary,#1565c0);border:1px solid var(--primary,#1565c0);}
#portal-status{font-size:0.9em;}
.portal-progress{height:8px;background:#eceff1;border-radius:99px;overflow:hidden;margin:8px 0 0;}
.portal-progress>span{display:block;height:100%;background:var(--success,#2e7d32);width:0;transition:width .2s;}
"""


def _q_html(q: PortalQuestion) -> str:
    qid = html.escape(q.id)
    label = html.escape(q.label)
    req = '<span class="req" aria-hidden="true">*</span>' if q.required else ""
    req_attr = ' aria-required="true" required' if q.required else ""
    unit = f'<span class="unit">{html.escape(q.unit)}</span>' if q.unit else ""
    plain = f'<div class="plain">{html.escape(q.plain_language)}</div>' if q.plain_language else ""
    why = (
        f'<div class="why" id="{qid}-why">Why we ask: {html.escape(q.why_we_need_this)}</div>'
        if q.why_we_need_this
        else ""
    )
    describedby = f"{qid}-why" if q.why_we_need_this else ""
    aria_db = f' aria-describedby="{describedby}"' if describedby else ""

    if q.field_type in ("number", "percent"):
        rng = ""
        if q.min is not None:
            rng += f' min="{q.min}"'
        if q.max is not None:
            rng += f' max="{q.max}"'
        control = (
            f'<input type="number" step="any" id="{qid}" name="{qid}"{rng}{req_attr}{aria_db}>'
        )
    elif q.field_type == "boolean":
        control = (
            f'<select id="{qid}" name="{qid}"{req_attr}{aria_db}>'
            '<option value="">—</option><option value="yes">Yes</option><option value="no">No</option></select>'
        )
    elif q.field_type == "select":
        opts = "".join(
            f'<option value="{html.escape(o)}">{html.escape(o)}</option>' for o in q.options
        )
        control = f'<select id="{qid}" name="{qid}"{req_attr}{aria_db}><option value="">—</option>{opts}</select>'
    elif q.field_type == "longtext":
        control = f'<textarea id="{qid}" name="{qid}"{req_attr}{aria_db}></textarea>'
    else:
        control = f'<input type="text" id="{qid}" name="{qid}"{req_attr}{aria_db}>'

    return (
        f'<div class="portal-q" data-qid="{qid}" data-required="{str(q.required).lower()}" '
        f'data-type="{q.field_type}">'
        f'<label for="{qid}">{label}{req}{unit}</label>'
        f"{plain}{control}"
        f'<div class="field-error" id="{qid}-error" role="alert">This field is required.</div>'
        f"{why}</div>"
    )


_PORTAL_JS = """
(function(){
  var form = document.getElementById('investee-form');
  var status = document.getElementById('portal-status');
  var bar = document.getElementById('portal-bar');
  if(!form) return;
  function updateProgress(){
    var qs = form.querySelectorAll('.portal-q');
    var filled = 0;
    qs.forEach(function(q){
      var c = q.querySelector('input,select,textarea');
      if(c && String(c.value).trim() !== '') filled++;
    });
    var pct = qs.length ? Math.round(filled/qs.length*100) : 0;
    if(bar) bar.style.width = pct + '%';
    if(status) status.textContent = filled + ' of ' + qs.length + ' answered (' + pct + '%)';
  }
  function validate(){
    var ok = true;
    form.querySelectorAll('.portal-q').forEach(function(q){
      var c = q.querySelector('input,select,textarea');
      var err = q.querySelector('.field-error');
      var bad = false, msg = 'This field is required.';
      if(!c) return;
      var v = String(c.value).trim();
      if(q.dataset.required === 'true' && v === ''){ bad = true; }
      if(v !== '' && (q.dataset.type === 'number' || q.dataset.type === 'percent')){
        var num = parseFloat(v);
        if(isNaN(num)){ bad = true; msg = 'Enter a number.'; }
        else if(c.min !== '' && num < parseFloat(c.min)){ bad = true; msg = 'Must be ≥ ' + c.min + '.'; }
        else if(c.max !== '' && num > parseFloat(c.max)){ bad = true; msg = 'Must be ≤ ' + c.max + '.'; }
      }
      q.classList.toggle('invalid', bad);
      if(err){ err.style.display = bad ? 'block' : 'none'; if(bad) err.textContent = msg; }
      if(bad) ok = false;
    });
    return ok;
  }
  form.addEventListener('input', updateProgress);
  document.getElementById('portal-export').addEventListener('click', function(){
    if(!validate()){ if(status) status.textContent = 'Please fix the highlighted fields.'; return; }
    var data = {};
    form.querySelectorAll('.portal-q').forEach(function(q){
      var c = q.querySelector('input,select,textarea');
      if(c && String(c.value).trim() !== '') data[q.dataset.qid] = c.value;
    });
    var blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'investee_submission.json';
    a.click();
    if(status) status.textContent = 'Saved investee_submission.json — send this file back to your investor.';
  });
  updateProgress();
})();
"""


def build_investee_portal(
    *,
    fund_name: str = "",
    company_name: str = "",
    sections: list[PortalSection] | None = None,
    consolidated_request: dict | None = None,
    routing: dict | None = None,
    theme: str = "",
) -> str:
    """Render the guided investee data-collection portal as a single HTML file."""
    if routing:
        rows = (consolidated_request or {}).get("consolidated", [])
        if not rows:
            rows = [
                {"concept_id": concept, "label": concept.replace("_", " ").title()}
                for concept in routing
            ]
        secs = [
            PortalSection(
                title="Consolidated investor data request",
                description=(
                    "Answer each concept once. The routing table fans the answer out "
                    "to every investor request without silently changing its period."
                ),
                questions=[
                    PortalQuestion(
                        id=str(row["concept_id"]),
                        label=str(row.get("label", row["concept_id"])),
                        why_we_need_this=(
                            f"One answer satisfies {len(routing.get(row['concept_id'], []))} "
                            "mapped investor field(s)."
                        ),
                        framework_ref="concordance",
                    )
                    for row in rows
                ],
            )
        ]
    else:
        secs = sections if sections is not None else default_portal_sections()
    fund = html.escape(fund_name or "your investor")
    title = (
        f"Impact data request — {html.escape(company_name)}"
        if company_name
        else "Impact data request"
    )

    body_parts: list[str] = [
        '<div class="report-hero"><h1>Impact &amp; ESG data request</h1>'
        f"<p>Prepared for {html.escape(company_name) or 'your company'} by {fund}.</p></div>",
        '<div class="portal-intro">'
        "<strong>Why this matters:</strong> consistent, comparable impact data is what lets your "
        "investor tell your story credibly to their own LPs and regulators. Every question explains "
        "<em>why we need it</em>. Answer what you can — leave blanks where data isn't ready yet. "
        "Your answers stay in your browser until you export and send them."
        "</div>",
        '<div class="portal-progress" aria-hidden="true"><span id="portal-bar"></span></div>',
        '<p id="portal-status" role="status" aria-live="polite"></p>',
        '<form id="investee-form" novalidate>',
    ]
    for s in secs:
        body_parts.append('<fieldset class="portal-section">')
        body_parts.append(f"<legend>{html.escape(s.title)}</legend>")
        if s.description:
            body_parts.append(f'<p class="why">{html.escape(s.description)}</p>')
        for q in s.questions:
            body_parts.append(_q_html(q))
        body_parts.append("</fieldset>")
    body_parts.append(
        '<div class="portal-actions">'
        '<button type="button" id="portal-export" class="portal-btn">Save &amp; export my answers</button>'
        '<span class="why">No data is uploaded — export creates a JSON file you send back.</span>'
        "</div>"
    )
    body_parts.append("</form>")

    extra_head = f"<style>{_PORTAL_CSS}</style><script defer>{_PORTAL_JS}</script>"
    return wrap_document(
        title=title,
        body_html="".join(body_parts),
        extra_head=extra_head,
        theme=theme,
    )


def portal_schema(sections: list[PortalSection] | None = None) -> dict:
    """Return the questionnaire as a machine-readable schema (for analysts)."""
    secs = sections if sections is not None else default_portal_sections()
    return {
        "sections": [s.model_dump() for s in secs],
        "question_count": sum(len(s.questions) for s in secs),
    }


__all__ = [
    "FieldType",
    "PortalQuestion",
    "PortalSection",
    "default_portal_sections",
    "build_investee_portal",
    "portal_schema",
]
