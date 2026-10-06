# Impact Vision — sample deliverables

Every file here is **real, unedited output** from Impact Vision. It was generated
offline, with no API key, from the three fictional pitch decks in
[`data/sample_decks/`](../data/sample_decks/). Open **[`index.html`](index.html)**
for the gallery.

| Company (fictional) | Sector | What it shows |
|---|---|---|
| [Kampung Makmur Sdn Bhd](kampung_makmur_sdn_bhd/) | Integrated pig farm + biogas, Malaysia | Evidence-rich pitch with a randomized pilot and SIRIM verification. Includes all variants. |
| [SunPath Energy Ltd](sunpath_energy_ltd/) | Pay-as-you-go solar, Kenya | Quantified outcomes mapped to IRIS+ (households connected, tCO2e avoided). |
| [BrightPath Finance](brightpath_finance/) | Digital microfinance, Sub-Saharan Africa | A memo that cites IRIS+ IDs explicitly. |

Each company folder has:

| File | Deliverable |
|---|---|
| `*_impact_report.html` / `.pdf` | **Decision-first impact report**. It opens with the verdict, headline tiles and "what would change our mind", then shows impact at a glance (SDG wheel + impact pathway), the 5 Dimensions against the sector benchmark, material SDGs, the evidence ledger, the greenwashing review, risks, the action plan, and the methodology and glossary. |
| `*_ic_memo.html` / `.pdf` / `.docx` | **Investment-committee memo**: IC gate, thesis fit, 5D, SDGs, DD and greenwashing. |
| `*_dd_report.html` | **DD questionnaire helper**: risk-ranked areas and the questions to send. |
| `*_dd_questionnaire.docx` | The DD questionnaire as an editable Word file. |
| `*_summary.json` | The headline numbers, for pipelines. |

The pig farm also has the **LP** and **public** editions, a forced **dark**
theme, a **white-label** edition, **繁體中文 (zh-HK)** and **简体中文
(zh-CN)** reports, and the offline **investee data portal**.

Regenerate everything (PDFs need the `[pdf]` extra or `IMPACT_VISION_CHROMIUM`):

```bash
python demo/generate_demo.py
python scripts/capture_screenshots.py   # refresh docs/images and demo/screenshots
```

`pig_farm_profile.json` is the input profile used by the regression tests.

![Report overview](screenshots/report-overview.png)
