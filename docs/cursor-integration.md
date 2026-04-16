# Cursor / VS Code MCP Integration Guide

Impact Vision exposes **25 impact measurement tools** as an MCP (Model Context Protocol) server that can be used directly within Cursor, VS Code, Claude Desktop, or any MCP-compatible AI client.

## Quick Setup

### Option 1: Cursor IDE (`.cursor/mcp.json`)

Add to your workspace or user MCP configuration:

```json
{
  "mcpServers": {
    "impact-vision": {
      "command": "impact-vision",
      "args": ["serve-mcp"]
    }
  }
}
```

### Option 2: Claude Desktop (`claude_desktop_config.json`)

Copy `examples/claude_desktop_config.json` into your Claude Desktop config directory:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### Option 3: Remote / SSE Transport

Start the server on a network port:

```bash
impact-vision serve-mcp --transport sse --port 8765
```

Then configure your client to connect via `http://localhost:8765/sse`.

### Option 4: Direct Python Module

```bash
python -m openharness.impact.mcp_server
```

## Prerequisites

1. Install Impact Vision:
   ```bash
   pip install -e .
   # or
   uv pip install -e .
   ```

2. (Optional) Load the IRIS+ catalog for full metric lookup:
   ```bash
   impact-vision catalog load
   ```

## Available Tools

| Tool | Description |
|------|-------------|
| `five_dimension_assess` | 5-Dimension Impact scoring (What/Who/How Much/Contribution/Risk) |
| `sdg_mapper` | SDG alignment mapping with evidence chains |
| `greenwashing_detect` | Greenwashing risk detection (5 sub-scores) |
| `gap_analysis` | Core Metric Set gap analysis |
| `iris_catalog` | IRIS+ metric catalog search/browse |
| `dd_checklist` | 96-question DD checklist |
| `framework_assess` | Multi-framework ESG assessment (11 frameworks) |
| `cross_reference` | Cross-framework metric lookup |
| `impact_report` | Full report generation (HTML/PDF/CSV/JSON/XLSX) |
| `impact_data_quality` | Metric data quality assessment |
| `exclusion_screening` | Exclusion criteria screening |
| `pitch_deck_analyze` | Pitch deck / investment memo analysis |
| `lp_ddq_export` | LP DDQ export (ILPA/GIIN/EDCI) |
| `portfolio_analyze` | Portfolio batch analysis and attribution |
| `impact_risk_opportunity` | Risk/opportunity assessment |
| `impact_metric_recommender` | IRIS+ metric recommendations |
| `trend_analysis` | Time-series metric trend analysis |
| `beneficiary_feedback` | Beneficiary feedback integration |
| `verification_prep` | Third-party verification preparation |
| `product_passport` | EU Digital Product Passport |
| `pipeline` | Investment pipeline management |
| `monitoring` | Continuous monitoring and alerts |
| `improvement_advisor` | LLM-guided improvement recommendations |
| `narrative` | Impact narrative generation |
| `document_analysis` | Multi-document comparison and verification |
| `guided_assessment` | Step-by-step assessment workflow |

## Available Resources

| Resource URI | Description |
|-------------|-------------|
| `impact://catalog/stats` | IRIS+ catalog statistics |
| `impact://dd-checklist/categories` | DD checklist categories |
| `impact://frameworks/list` | Available ESG frameworks |
| `impact://cross-reference/{metric_id}` | Cross-reference lookup |
| `impact://sdg/goals` | UN SDG 17 goals reference |

## Example Usage in Cursor

Once configured, you can ask Cursor's AI agent to:

- *"Analyze this pitch deck for impact claims and SDG alignment"*
- *"Score EcoFinance on the 5 Dimensions of Impact given these metrics..."*
- *"Check our portfolio for greenwashing risks"*
- *"Generate an LP DDQ report for our fund"*
- *"What IRIS+ metrics should a fintech company in Kenya track?"*

## Agent-to-Agent Protocol

Impact Vision tools follow a consistent input/output contract:

**Input**: Each tool accepts JSON arguments with typed fields (see tool descriptions for details). All tools accept `company_name` as the primary identifier.

**Output**: All tools return plain text by default. Use `output_format` parameter (where available) for structured output (json, csv, html).

**Error Handling**: Errors are returned as text with `is_error=true` in the MCP response.

**Idempotency**: All read operations are idempotent. Write operations (pipeline, monitoring) modify the SQLite store.

## Troubleshooting

1. **"IRIS+ catalog not loaded"**: Run `impact-vision catalog load` to load the IRIS+ Excel file.
2. **Import errors**: Ensure all dependencies are installed: `pip install -e ".[all]"`
3. **Connection refused (SSE)**: Check that port 8765 is not in use: `impact-vision serve-mcp --transport sse --port 8766`
