# Fund Manager Guide — task recipes

Short, web-first recipes for fund managers, analysts and impact consultants.
Every recipe starts in the browser; the command-line and Python equivalents
follow where they exist. Terms are defined in the [glossary](glossary.md) and
at the end of every report.

**Start the web app once:**

```bash
pip install "impact-vision[web]"
impact-vision serve-web --open        # http://127.0.0.1:8787
```

No API key is needed for deck screening, reports, the portfolio home or the
console. Connect a model (chat settings, or `OPENAI_API_KEY`) only when you
want the conversational agent, or LLM claim extraction, which is then used
automatically.

---

## 1. Screen a pitch deck

1. In the chat, click **Analyze a pitch deck** and drop a PDF, TXT or MD file.
2. The report opens in the side panel: the verdict card, KPIs, *what would
   change our mind*, 5D, SDGs, the evidence ledger, risks and an action plan.
3. Read the gate: **INSUFFICIENT EVIDENCE** means the deck lacks data (send
   the questions), **FAIL** means a negative finding.

CLI: `impact-vision assess deck.pdf --open`. Agent: "screen this deck" runs
`assess_deal` and returns an `assessment_id` that other tools accept.

## 2. Send a report to someone

1. In the report viewer, pick the **audience** (IC, LP, public, regulator),
   **language** (English, 繁體中文, 简体中文) and theme.
2. Click **Share** to create a signed, read-only link. Revoke it from the
   **Reports** tab at any time.
3. For an offline copy, download the HTML, PDF (with the `[pdf]` extra),
   IC memo `.docx`, or the XLSX / CSV / JSON data export.

Every output carries an **AI & automation disclosure** (EU AI Act Art 50)
and the **methodology version + config hash**. Two reports are directly
comparable only when the methodology stamps match.

## 3. Prepare the IC

- Use the **IC memo** (HTML / Word) from the report's file list. It is built
  on your fund thesis (§8) and lists the evidence warnings.
- The **DD questionnaire** (`.docx`) holds the open questions, risk-first,
  with founder-response slots. Send it to the company.
- Several deals: ask the agent to "compare these two deals"
  (`decision_workflow`).

## 4. See the whole portfolio

Open **/portfolio/view**: pipeline by IC-gate status, the 5D / SDG heat-map,
the evidence-review queue, stale assessments, and regulatory deadlines for
EU, US, UK and Hong Kong. Statutory dates inside 60 days appear under **Needs
attention** (for example California SB 253, first report due 2026-11-10).

## 5. Check regulatory exposure

Ask the agent, or use the console form for `regulatory_calendar`:

- *"What is due in the next 90 days for an EU and Hong Kong fund?"*
  gives a per-jurisdiction calendar with live alerts.
- *"Show the regulatory watch-list"* gives market-wide dates (revised ESRS,
  VSME, ISSA 5000 / HKSSA 5000, UK SRS, AI Act, SFDR 2.0), each with its
  source link.
- *"Can this fund call itself an impact fund under SFDR 2.0?"* runs the
  Commission / Council / Parliament category preview and the "impact"
  wording check (Art 7/9, theory of change, measured outcomes) via
  `framework_assess`.
- *"Screen this company against the Hong Kong Taxonomy"* gives eligibility
  candidates, plus alignment % once you supply the revenue split.

## 6. Collect data from investees

- **SME investees:** use the VSME template (`sector="vsme"`). It is the most
  a CSRD reporter may require from a partner with ≤1,000 employees, and the
  data-request packs enforce that cap automatically.
- **LP reporting:** use the EDCI-first pack (`bundle_id="edci_core"`).
- **Offline portal:** `investee_portal` produces a self-contained HTML form
  with plain-language SFDR PAI guidance.

## 7. Run a consultant engagement

`engagement_workspace` and `engagement_suite` cover proposal → data room →
ToC / KPI framework → reporting studio → assurance bundle. Engagements, the
audit trail and review queues are saved to `~/.impact-vision/state.db`
(override with `IMPACT_VISION_STATE_DB`, or use Postgres with
`IMPACT_VISION_STATE_STORE=postgres` + `IMPACT_VISION_STATE_DSN`), so work
survives a restart.

## 8. Configure your fund

The IC gate reads `data/fund_thesis.yaml`. Four regional packs ship as
examples: `fund_thesis.climate_eu.yaml`,
`fund_thesis.inclusive_finance_africa.yaml`,
`fund_thesis.gender_lens_south_asia.yaml` and `fund_thesis.indigenous_led_na.yaml`.
The `branding:` block (fund name, logo, colour, footer) is applied to every
HTML deliverable.

---

## For developers: the same flows in Python

```python
from impact_vision import ImpactVision
from impact_vision.pipeline import assess_file, write_deliverables

bundle = assess_file("deck.pdf", sector="energy")        # one deck → everything
write_deliverables(bundle, "reports/", lang="zh-HK")      # HTML, memo, DD, docx, data
print(bundle.summary()["gate"], bundle.summary()["methodology"])

iv = ImpactVision()                                       # LLM extractor if a key is set
thesis = iv.load_thesis("data/fund_thesis.climate_eu.yaml")
asst = iv.assess_company_text("Acme Solar", text=deck_text, sector="energy")
sc = iv.evaluate_deal_against_thesis(asst, thesis=thesis)
iv.render_ic_memo(asst, scorecard=sc, output_format="docx", path="ic/acme.docx")
reg = iv.build_regulatory_calendar(jurisdiction="HK", fiscal_year_end="2026-12-31")
print(reg.alerts)
```

REST: every tool is `POST /api/v1/tools/{name}` (schemas at
`GET /api/v1/tools?schemas=true`). MCP: `impact-vision serve-mcp` exposes the same
48 tools plus playbook prompts. The full list is in
[reference/tools.md](reference/tools.md).

## Survey delivery channels

`survey_delivery` renders WhatsApp, SMS, voice, or self-contained web content
without coupling the engine to a vendor SDK. Deployments configure Twilio/Meta
or another provider to forward signed inbound payloads to
`POST /api/v1/surveys/webhook/{channel_id}`. Each dispatch and response must
carry an active `ConsentRecord`; respondent references should be pseudonymous,
PII stays in the delivery provider, and `STOP`/`退订` immediately opts out the
dispatch. Keep the API bearer-authenticated and validate provider signatures at
the reverse proxy before forwarding the normalized payload.

## Where to go next

- [Web chat guide](web-chat-guide.md) — the chat UI in detail.
- [Roadmap v7](roadmap-v7.md) — current direction; [CHANGELOG](../CHANGELOG.md) — release history.
- [CLAUDE.md](../CLAUDE.md) — codebase map for developers.
