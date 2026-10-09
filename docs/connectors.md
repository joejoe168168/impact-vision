# Connectors

Impact Vision can read documents and deals from where your fund keeps them.
Connectors are read-only: they never write back to the source. Tokens are read
from environment variables and are never stored or logged.

```bash
impact-vision connect docs folder --path ~/DataRoom --assess   # data-room export
impact-vision connect docs gdrive --assess                     # Google Drive folder
impact-vision connect docs sharepoint                          # SharePoint / OneDrive
impact-vision connect deals affinity                           # CRM → pipeline
impact-vision connect deals dealcloud
```

`docs` copies new or changed files into the uploads folder, one subfolder per
company, and remembers what it has already copied. Each top-level folder in the
source is treated as one company. With `--assess`, new decks and memos are also
assessed and filed on the company record.

`deals` adds CRM companies to the pipeline at their mapped stage, and records a
stage change as a logged transition.

| Connector | Settings |
|---|---|
| Data-room folder | `IMPACT_VISION_DATAROOM_DIR` (or `--path`) |
| Google Drive | `IMPACT_VISION_GDRIVE_FOLDER` (folder ID), `IMPACT_VISION_GDRIVE_TOKEN` (OAuth access token, `drive.readonly`). Google Docs and Slides are exported as PDF, and Sheets as XLSX. |
| SharePoint / OneDrive | `IMPACT_VISION_SHAREPOINT_DRIVE` (drive ID), `IMPACT_VISION_SHAREPOINT_PATH`, `IMPACT_VISION_GRAPH_TOKEN` (`Files.Read.All` or `Sites.Read.All`) |
| Affinity | `IMPACT_VISION_AFFINITY_KEY` (API v2 key), `IMPACT_VISION_AFFINITY_LIST` (list ID). The key's user needs "Export data from Lists". |
| DealCloud | `IMPACT_VISION_DEALCLOUD_URL` (`https://<tenant>.dealcloud.com`), `IMPACT_VISION_DEALCLOUD_CLIENT_ID`, `IMPACT_VISION_DEALCLOUD_SECRET`, `IMPACT_VISION_DEALCLOUD_ENTRY_TYPE`, optional `IMPACT_VISION_DEALCLOUD_NAME_FIELD` (default `Name`) |

**CRM fields.** The stage, sector, geography and owner are read from fields
named `Status`/`Stage`, `Sector`/`Industry`, `Geography`/`Country`/`Region`
and `Owner`/`Deal lead`. To use other names, set
`IMPACT_VISION_CRM_STAGE_FIELD`, `..._SECTOR_FIELD`, `..._GEOGRAPHY_FIELD` or
`..._OWNER_FIELD`; separate alternatives with `|`. Common stage names
("Due Diligence", "IC", "Term sheet", "Portfolio", "Closed Lost") are mapped
automatically. For other names, set a map like
`IMPACT_VISION_CRM_STAGE_MAP="Deep dive=dd_in_progress,Partner meeting=ic_review"`.

The ILPA Portfolio Company Metrics export will be added once ILPA publishes
the final template (expected January 2027). EDCI and SFDR PAI exports are
already available through `lp_ddq_export`.

The connectors were built against each provider's public API documentation
and tested against mocked responses. Try them on a test folder or list before
pointing them at production data.
