# Impact Vision — screenshots

Rendered from the `pig_farm_in_malaysia` sample that ships in `examples/output/`. Captured at 1440×900 @ 2× device-pixel-ratio via Playwright against a locally-running `impact-vision serve-web`.

| File | Surface | Description |
|------|---------|-------------|
| `01_web_console_landing.png` | Web Console | Landing page with the auto-discovered 26-tool sidebar + welcome card. |
| `02_web_console_tool_form.png` | Web Console | A tool form auto-generated from `/openapi.json` (OpenAPI-driven inputs + Fill-example button). |
| `03_impact_report_top.png` | Impact Report | Hero banner, KPI strip (5D / top SDG / greenwashing), executive summary, watch-outs. |
| `04_impact_report_charts.png` | Impact Report | 5-Dimension radar + rationale table + "Improve your score" checklist. |
| `05_impact_report_full.png` | Impact Report | Full-page capture for docs / printing. |
| `06_dd_questionnaire_top.png` | DD Questionnaire Helper | Risk-first layout: coverage, high-priority gaps, evidence level, key risk areas. |
| `07_dd_questionnaire_full.png` | DD Questionnaire Helper | Full-page capture incl. priority-sorted information request + evidence gaps. |
| `08_ic_memo_top.png` | IC Memo | Hero + IC-gate verdict (PASS / WARN / FAIL) + thesis-fit fund-weighted scores. |
| `09_ic_memo_full.png` | IC Memo | Full-page capture. |

To regenerate: start the web console (`impact-vision serve-web`) and run the helper script shown in the PR description.
