# Fund Manager Quick Reference

A short Python-first walkthrough for fund managers / investment analysts who
want the Impact Vision SDK behind their pipeline or IC workflow. If you are
just exploring the tool, start from the [README](../README.md) — it covers
the CLI, interactive agent, and Web Console.

The SDK (`openharness.impact.sdk.ImpactVision`) wraps every agent tool
behind a single typed Python class so you can embed it in any notebook,
cron job, or internal platform.

## 60-second workflow

```python
from openharness.impact.sdk import ImpactVision

iv = ImpactVision()  # regex extractor + heuristic verifier by default

# 1) Assess a deal from a pitch deck / impact report
asst = iv.assess_company_text(
    "Acme Solar",
    text=pitch_deck_text,
    sector="energy",
    country="KE",
    impact_themes=["climate"],
)

# 2) Run it through your fund's IC gate (uses data/fund_thesis.yaml)
sc = iv.evaluate_deal_against_thesis(
    asst,
    dd_coverage_pct=iv.run_dd_coverage(pitch_deck_text).coverage_pct,
    greenwashing_score=iv.screen_greenwashing(asst.company).overall_score,
)
print(sc.overall_status)  # "pass" / "warn" / "fail"

# 3) IC memo — Markdown, HTML (print-ready), Word, PowerPoint
iv.render_ic_memo(asst, scorecard=sc, output_format="html", path="ic/acme.html")
iv.render_ic_memo(asst, scorecard=sc, output_format="docx", path="ic/acme.docx")

# 4) DD Questionnaire Helper — risk-first HTML the analyst actually works from
iv.render_dd_questionnaire_html(
    pitch_deck_text, company_name="Acme Solar",
    document_label="Pitch deck v3", path="dd/acme.html",
)

# 5) Same questionnaire as an editable Word doc with founder-response slots
iv.render_dd_questionnaire_docx(
    pitch_deck_text, company_name="Acme Solar",
    document_label="Pitch deck v3", path="dd/acme.docx",
)

# 6) Portfolio-level roll-up weighted by capital deployed
roll = iv.rollup([(asst_a, 5.0, 12.0), (asst_b, 8.0, 20.0)])  # (assessment, EUR_m, ownership_%)

# 7) Next 12 months of LP report deliverables
cal = iv.build_lp_calendar(horizon_months=12)
```

## Browser alternative

Prefer a browser? `impact-vision serve-web` launches the **Web Console** plus
REST API in one process at `http://127.0.0.1:8787` and exposes the full tool
surface one click away. Every console invocation is persisted to
`localStorage` so you can re-hydrate old runs without re-typing.

## Configuring your fund

The SDK reads `data/fund_thesis.yaml` by default. Four regional packs ship
out of the box — see `data/fund_thesis.climate_eu.yaml`,
`fund_thesis.inclusive_finance_africa.yaml`,
`fund_thesis.gender_lens_south_asia.yaml`, and
`fund_thesis.indigenous_led_na.yaml`.

To override:

```python
iv = ImpactVision(fund_thesis_path="data/fund_thesis.climate_eu.yaml")
```

Branding (logo, colours, footer) is driven by the `branding:` block in the
same YAML and auto-injected into every HTML surface.

## Where to go next

- [`docs/roadmap-v3-implementation.md`](roadmap-v3-implementation.md) — trust-infrastructure
  modules (evidence review, verification workspace, LP narrative, governed AI).
- [`docs/roadmap-v4.md`](roadmap-v4.md) — consultant-led engagement workspace,
  ToC builder, data room, reporting studio, 3-pillar verification bundle.
- [`CLAUDE.md`](../CLAUDE.md) — codebase map for developers.
- [`CHANGELOG.md`](../CHANGELOG.md) — release history.
