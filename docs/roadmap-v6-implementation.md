# Impact Vision — v6 Implementation Plan + Pain-Point Extension Tracks (G–J)

**Date:** 2026-07-19
**Status:** Engineering plan — ready for implementation
**Companion to:** `docs/roadmap-v6.md` (strategy) — this file is the *how*, that file is the *why*.
**Audience:** implementing engineers / coding agents (Codex, Claude Code).

This document specifies, at code level, every planned-but-unbuilt feature:

- **Tracks A–F** — the v6 "Comparable, Assured & Connected" wave from `roadmap-v6.md` (all items status *Planned*).
- **Tracks G–J** — four *new* extension tracks derived from July-2026 deep research into practitioner pain points (GIIN State of the Market 2025, BlueMark Making the Mark 2025/2026, Impact Frontiers, 60 Decibels, ILPA/PRI) and a deep study of the OHESG reporting ecosystem (`report.ohesg.com`, `tool.ohesg.com`) whose toolbox snapshots we already bundle in `data/raw/ohesg_toolbox/`.

Research citations are in §2 and §12. Every item names the pain point it resolves.

---

## 0. How to use this document (instructions to the coding agent)

1. Implement items in the build order in §10. Each item is independently shippable.
2. **Extend, never fork.** Every spec names its backing modules. If you find yourself copying a module, stop — wrap or extend it instead. This rule is enforced in review (see `roadmap-v6.md` §4 Codebase Reuse Map).
3. New engine code lives in `src/openharness/impact/` (new modules allowed), `src/openharness/impact/frameworks/`, or `src/openharness/impact/engagements/`. New tool adapters live in `src/openharness/tools/impact/`. Data lives in `data/`.
4. After each item: run `python scripts/check_imports.py --all`, `ruff check src/`, and the relevant `pytest tests/ -q` subset. Update `CHANGELOG.md`. Update the README tool table + count only when a new tool is registered.
5. Do not touch `README.md` changelog-style content (see `CLAUDE.md` documentation conventions).
6. The nested `OpenHarness/` directory at repo root is a vendored copy of the harness — never edit it. The live package is `src/openharness/`.

### 0.1 The three-place tool registration checklist

Every new agent tool must be registered in **all three** places or it will not exist:

1. `src/openharness/tools/__init__.py` — add `("impact.<module>", "<ClassName>")` to the `impact_tools` tuple inside `create_default_tool_registry()` (entries are relative, e.g. `("impact.exit_impact_tool", "ExitImpactTool")`).
2. `src/openharness/tools/impact/__init__.py` — add the class to imports and `__all__`.
3. `src/openharness/impact/tool_advisor.py` — add a routing entry (the file carries the comment "keep in sync with create_default_tool_registry()").

Then: update the README tool table and tool-count reference, and add a CLI subcommand in `src/openharness/cli.py` only if the spec says so.

### 0.2 The canonical tool-adapter pattern

Copy this shape (reference implementations: `tools/impact/exit_impact_tool.py` for a single-domain tool, `tools/impact/engagement_suite_tool.py` for a multi-action dispatcher):

```python
from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class MyToolInput(BaseModel):
    action: Literal["assess", "list", "export"] = "assess"
    company: dict[str, Any] | None = None          # Company payload, validated downstream
    output_format: Literal["json", "text"] = "json"


class MyTool(BaseTool):
    name = "my_tool"
    description = "One-paragraph agent-facing description with action list."
    input_model = MyToolInput

    def is_read_only(self, arguments: dict[str, Any]) -> bool:
        return arguments.get("action") in {"assess", "list", "export"}

    async def execute(self, arguments: dict[str, Any], context: ToolExecutionContext) -> ToolResult:
        try:
            args = MyToolInput.model_validate(arguments)
            # thin adapter: all logic lives in the pure engine module in impact/
            payload = do_engine_work(args)
            return ToolResult(output=json.dumps(payload, default=str), metadata=payload)
        except Exception as e:  # noqa: BLE001 — repo convention
            return ToolResult(output=f"my_tool failed: {e}", is_error=True)
```

Engine modules must be **pure** (no I/O beyond reading `data/` files, no network), synchronous, and fully unit-testable without the tool layer.

### 0.3 Persistence & audit conventions

- State-changing operations append to the audit trail: `impact/audit_trail.py` → `AuditTrail.record_event(event_type, payload, actor, period)` (see `impact/engagements/workspace.py` for the wiring pattern).
- Anything that produces claims/metrics feeds `impact/evidence_graph.py` → `build_evidence_graph(...)` node/link types (`claim|metric|target|evidence|report_section`; `supported_by|measured_by|tracks|appears_in|derived_from`).
- Canonical metric contract is `impact/metric_records.py` → `MetricRecord` (uppercase `metric_id`, non-empty `unit/period/source/owner`, `quality_score` 0–100, `verification_status`, `evidence_refs`). New features that emit metrics emit `MetricRecord`s, never ad-hoc dicts.
- Long-lived workspace state may use the in-memory store pattern (`engagements/workspace.py`) but must expose `to_dict()/from_dict()` round-trips so callers can persist via `impact/storage.py`.

### 0.4 Test conventions

`tests/` mirrors `src/`. New engine module `impact/foo.py` → `tests/test_foo.py`; new tool → a class-level test in `tests/test_tools/`. Use plain `pytest` functions; async tool tests use `pytest.mark.asyncio`. Every item's spec below lists a minimum test set. Wave-level integration tests go in a single `tests/test_v6_wave.py` (create it with item A1).

### 0.5 H0 — housekeeping precondition (do this first)

**Problem:** the tool count disagrees across three sources — `tools/impact/__init__.py` `__all__` lists 47 classes, the README claims 44, and the `impact_tools` registration tuple registers ~44 (three tools commented out as "merged": `narrative_tool`, `verification_prep`, `greenwashing_reviewer`).

**Work:** reconcile before adding new tools. Remove the merged-away classes from `__all__` (keep deprecation aliases if any test imports them), regenerate the README tool table from the registry (add a tiny script `scripts/list_tools.py` that instantiates `create_default_tool_registry()` and prints name+description as a markdown table), and pin the count in one place.

**Tests:** extend `scripts/check_imports.py --registry` (already in CI) to assert `len(__all__) == registered tool count`.

**Effort:** S.

---

## 1. Current-state summary (what already exists — do not rebuild)

For orientation; verified against the tree on 2026-07-19.

- **Engine:** ~100 modules under `impact/` including scoring (`five_dimensions`, `sdg_mapper`, `gap_analysis`), trust infra (`evidence_graph`, `audit_trail`, `signed_feed`, `metric_records`, `standards_registry`), climate (`climate_accounting`, `climate_scenario`, `emission_factors`), valuation (`sroi`, `impact_valuation` (IFVI), `impact_quantifier`, `ecosystem_services`), finance (`blended_finance`, `fund_analytics`, `returns`), causal-ish (`counterfactual`, `causal`, `bayes`, `meta_analysis`, `spillover`), voice (`stakeholder_voice`, `worker_voice`, `surveys`), regulatory (`regulatory_packs`, `regulatory_calendar`, `csrd_wizard`, `hrdd`), plus 21 framework modules in `frameworks/` and the 16-module v4 consultant layer in `engagements/`.
- **Tools:** 50 files in `tools/impact/`, ~44 registered.
- **Data:** IRIS+ 5.3c catalog (Excel + processed JSON), `dd_checklist.yaml` (122 questions), `scoring_config.yaml`, `exclusion_criteria.yaml`, fund-thesis presets, i18n YAML, and 35 OHESG toolbox JSON snapshots in `data/raw/ohesg_toolbox/`.
- **Surfaces:** Typer CLI (`cli.py`), Streamlit dashboard (6 tabs), FastAPI `api_gateway/router.py` (~24 endpoints, bearer auth), single-file HTML investee portal (`impact/investee_portal.py`), React/Ink terminal UI.
- **Known structural gaps** (accepted, not in scope here unless a track says so): no multi-tenant auth/RBAC, SQLite-with-JSON-blobs persistence, in-memory engagement/verification workspaces, no live external connectors.

---

## 2. Research foundation — the pain points each track resolves

Condensed from the July-2026 research memo (full sources in §12).

| # | Pain point (severity-ranked) | Evidence | Resolved by |
|---|---|---|---|
| P1 | Impact washing is the #1 market challenge (62% of investors, GIIN SotM 2025); now an enforcement risk (ESMA priority, UK CMA Green Claims enforcement) | GIIN 2025; KPMG Dec-2025 | C1, C2, C4, I6 (mandatory-gap scan) + existing greenwashing stack |
| P2 | LPs cannot compare impact performance across funds — "most consequential unsolved problem" (BlueMark IQ launched to attack it) | BlueMark MtM 2026; GIIN benchmarks cover only ~5 sectors | B2, B3, B4, F1, F2 |
| P3 | 100%-attribution inflation; contribution rarely monitored post-investment (OPIM P3 reviews); ~12% of deals demonstrably additional | Impact Frontiers IC 2.0; impactprinciples.org | **G1** |
| P4 | Investee reporting fatigue: ~20 h/yr per portfolio company on bespoke investor asks; 56% report data-request burden | UpMetrics; Fundequate | **H1**, H3, B3 |
| P5 | Impact targets set too late: only 42% set targets as a condition of investment | BlueMark MtM 2025 | **G2** |
| P6 | Outputs masquerade as outcomes; shared outcome norms only now converging | 60 Decibels 2025 YiR | H2, G1 |
| P7 | Weakest verified practice areas: impact at exit, impact review, contribution monitoring | BlueMark 8-pillar benchmark | G1 (+ existing `exit_impact`) |
| P8 | Stakeholder voice is becoming a norm but delivery tooling is thin (WhatsApp ≈40% response vs 6% phone; AI voice agents cut collection to days) | Impact Frontiers IPRN; 60dB; IPA/Yazi | **H2** |
| P9 | Regulatory whiplash: SFDR 2.0 (Nov-2025 proposal), Omnibus/CSRD shrink (OJ Feb-2026), simplified ESRS (~430 datapoints, ~Sept 2026), UK SDR entity rules, ISSB in 36 jurisdictions, CA SB 253/261 | Sidley; KPMG; Latham; FCA; IFRS; CARB | A1–A4, E1, **I3** |
| P10 | Impact-linked carry/SAFI wanted but unstructurable without measurement infra | Trowers & Hamlins Oct-2025; New Private Markets; ImpactAlpha | **G3**, C4 |
| P11 | IFVI monetization standardized (~100k value factors) but no fund tooling consumes it live | ifvi.org | v5 `impact_valuation` shipped; G3 consumes it |
| P12 | Impact data doesn't travel between systems; CIDS v3.2 (Jul-2025) exists but no VC/PE platform exports it | Common Approach | **H3** |
| P13 | LP DDQs consolidating and hardening: ILPA DDQ 2.0 ↔ PRI sync, 2025 climate module, PRI 2026 reset (~39–40 mandatory indicators, window May 6–Jul 29 2026) | ILPA; Danesmead; PRI | **J1** |
| P14 | Nature/biodiversity fastest-rising ask with weakest metric tooling (TNFD 733 adopters; ISSB nature ED targeted Oct-2026) | TNFD status report; IFRS | C2, C3 |
| P15 | AI in IMM: rapid adoption, thin assurance; verifiers expect human-in-the-loop provenance | Stanford HAI; PwC | E1, E2, E3 (+ existing `ai_governance`) |
| P16 | China listed-company sustainability reporting (SSE/SZSE Guideline No. 14, FY2025 reports due 2026-04-30) has no open tooling; OHESG demonstrates demand | report.ohesg.com | **I1–I6** |

---

## 3. Track A — Regulatory Currency & Labelling (P0/P1)

### A1 — SFDR 2.0 category classifier

**Pain point:** P9. Every EU fund spends 2026–28 mapping Art 8/9 products onto the proposed Sustainable / Transition / ESG-Basics categories.

**Backing modules (extend):** `impact/frameworks/sfdr_pai.py` (Art 6/8/9 classifier), `impact/regulatory_packs.py` (`EU-SFDR` pack), `impact/engagements/regulatory.py` (`classify_sfdr`).

**New file:** `src/openharness/impact/frameworks/sfdr_v2.py`

```python
"""SFDR 2.0 (COM proposal 2025-11-20) category classifier.

STATUS: PROPOSED LAW. Every output must carry
`legal_status="proposal"` and `as_of` — trilogue ongoing, application ~2028+.
"""
from enum import Enum
from pydantic import BaseModel, Field

class SFDRv2Category(str, Enum):
    SUSTAINABLE = "sustainable"        # revised Art 9
    TRANSITION = "transition"          # new Art 7
    ESG_BASICS = "esg_basics"          # new Art 8
    UNCATEGORISED = "uncategorised"

class ExclusionBreach(BaseModel):
    exclusion_id: str            # e.g. "controversial_weapons", "tobacco_producer",
                                 # "ungc_oecd_violator", "coal_revenue_gt_threshold"
    category: SFDRv2Category     # which category this exclusion applies to
    holding_name: str
    detail: str

class PortfolioHolding(BaseModel):
    name: str
    weight: float                          # 0..1 of NAV
    follows_esg_strategy: bool = False     # meets the category's binding strategy
    sector_flags: list[str] = []           # feed exclusion screen; reuse
                                           # data/exclusion_criteria.yaml ids

class SFDRv2Result(BaseModel):
    category: SFDRv2Category
    eligible: bool
    strategy_share: float                  # Σ weight where follows_esg_strategy
    threshold: float = 0.70                # member-state variant param (0.70/0.80)
    exclusion_breaches: list[ExclusionBreach]
    migration_note: str                    # from old Art 6/8/9
    legal_status: str = "proposal"
    as_of: str = "2025-11-20"
    citations: list[str]

def classify_sfdr_v2(holdings: list[PortfolioHolding],
                     target_category: SFDRv2Category,
                     threshold: float = 0.70) -> SFDRv2Result: ...

def migrate_from_v1(article: str,           # "6" | "8" | "9"
                    holdings: list[PortfolioHolding]) -> dict:
    """Return {'suggested_category', 'rationale', 'gaps': [...], 'result': SFDRv2Result}."""
```

Mandatory-exclusion tables per category ship as module-level constants with citation strings (source: COM proposal Annexes; reuse ids from `data/exclusion_criteria.yaml` where they overlap — do not duplicate the YAML).

**Tool surface:** extend the existing `framework_assess` tool (`tools/impact/framework_tool.py`) with `framework: "sfdr_v2"` and actions `classify | migrate`. No new tool registration needed. Also add an `engagement_suite` regulatory action `sfdr_v2_migrate` delegating to the same engine.

**CLI:** `impact-vision framework sfdr2 --article 9 --holdings holdings.json`.

**Tests (`tests/test_sfdr_v2.py`):** threshold pass at exactly 0.70; member-state 0.80 variant; each exclusion id triggers a breach; Art 9 → Sustainable happy path; Art 8 with 0.5 strategy share → UNCATEGORISED with gap list; every result has `legal_status == "proposal"`.

**Effort:** M.

### A2 — Simplified ESRS refresh (~430 datapoints)

**Pain point:** P9 (Omnibus). CSRD scope is now >1,000 employees AND >€450m turnover (OJ 2026-02-26, applying 2026-03-18); simplified ESRS delegated act expected ~June 2026.

**Backing modules (extend):** `impact/frameworks/esrs.py`, `impact/csrd_wizard.py`, `impact/standards_registry.py`, `impact/frameworks/eu_taxonomy.py`.

**Work:**
1. Add `data/esrs_simplified_2026.yaml` — datapoint set keyed by ESRS standard (E1–E5, S1–S4, G1, ESRS 2), each entry: `datapoint_id, name, mandatory: bool, phase_in: str|null, removed_in_simplification: bool, source: str`. Seed from the EFRAG simplified-set exposure documents; where the final delegated act is not yet published, mark entries `status: "draft"`.
2. `frameworks/esrs.py`: add `load_simplified_datapoints() -> list[ESRSDatapoint]` and a `regime: Literal["esrs_2023","esrs_simplified_2026"]` parameter to the existing assessment entry points (default stays `esrs_2023` until the delegated act is final).
3. `csrd_wizard.py`: update the scope decision to the new thresholds (>1,000 employees AND >€450m turnover; listed SMEs out; Wave-2 FY2027 / Wave-3 FY2028 stop-the-clock dates) with citations.
4. `standards_registry.py`: register `esrs_simplified_2026` with `as_of` and status.

**Tests (`tests/test_esrs_simplified.py`):** datapoint YAML loads and validates; count is within the expected band (~430); scope wizard: 1,200 employees/€500m in; 800 employees/€600m out; regime switch changes gap-analysis output.

**Effort:** M.

### A3 — California SB 253 / SB 261 pack

**Pain point:** P9 (US). CARB adopted initial regs 2026-02-26; SB 253 Scope 1&2 first reports due 2026-11-10 (postponed from Aug), Scope 3 from 2027; SB 261 enforcement stayed pending Ninth Circuit appeal.

**Backing modules (extend):** `impact/regulatory_packs.py`, `impact/regulatory_calendar.py`, `impact/frameworks/tcfd.py`, `impact/frameworks/issb_ifrs_s2.py`.

**Work:** add a `US-CA-CLIMATE` pack to `regulatory_packs.py` with a scope decision function:

```python
def ca_climate_scope(revenue_usd: float, does_business_in_ca: bool) -> dict:
    """Returns {'sb253': bool (>1e9), 'sb261': bool (>5e8),
    'deadlines': [...], 'assurance': 'limited→reasonable phasing',
    'enforcement_notes': 'SB261 stayed — Ninth Circuit', 'citations': [...]}"""
```

Deadlines go into `regulatory_calendar.py` entries (SB 253: 2026-11-10 Scope 1&2; 2027 Scope 3; SB 261 biennial). Map required disclosure content to the existing TCFD/IFRS-S2 modules (reuse their checklists — no new checklist).

**Tests (`tests/test_ca_climate.py`):** threshold boundaries ($1B/$500M), calendar entries present, disclosure mapping references existing TCFD pillar ids.

**Effort:** M (mostly data + one decision function).

### A4 — ISSB adoption tracker refresh

**Backing modules (extend):** `impact/regulatory_calendar.py`, `impact/standards_registry.py`.

**Work:** `data/issb_adoption.yaml` — one entry per jurisdiction (36+): `jurisdiction, status: adopted|adopting|announced, effective, scope, assurance_posture, source`. Loader + query helper in `regulatory_calendar.py`: `issb_status(jurisdiction: str) -> dict` and `issb_summary() -> list[dict]`. Include Hong Kong (effective 2025-08-01) — relevant to the primary user base. Surface via the existing calendar tool/CLI.

**Tests:** YAML schema validation; HK/Chile/Qatar/Mexico entries effective ≤ 2026-01-01; unknown jurisdiction handled.

**Effort:** S.

---

## 4. Track B — Assurance & Machine-Readable Data (P0/P1)

### B3 — Interoperability / concordance engine *(build before B2 and B4 — they depend on it)*

**Pain point:** P2, P4. "Report once, satisfy many."

**Backing modules (extend):** `impact/frameworks/cross_reference.py` (59 concept mappings — the seed data), `impact/metric_records.py`.

**New file:** `src/openharness/impact/concordance.py`

```python
class DatapointRef(BaseModel):
    framework: Literal["iris", "issb", "esrs", "gri", "edci", "sfdr_pai", "sasb", "tcfd"]
    datapoint_id: str            # e.g. "OI4112", "S2-29a", "E1-6", "GRI 305-1"
    label: str
    unit_hint: str | None = None
    taxonomy_uri: str | None = None   # XBRL element name where known (feeds B2)

class ConcordanceEntry(BaseModel):
    concept_id: str              # stable snake_case, e.g. "ghg_scope1_emissions"
    refs: list[DatapointRef]
    match_quality: Literal["exact", "close", "partial"]
    notes: str = ""

class ConcordanceMap:
    def __init__(self, entries: list[ConcordanceEntry]): ...
    def lookup(self, framework: str, datapoint_id: str) -> ConcordanceEntry | None: ...
    def translate(self, record: MetricRecord,
                  to_framework: str) -> list[tuple[DatapointRef, MetricRecord]]: ...
    def coverage_report(self, records: list[MetricRecord],
                        to_framework: str) -> dict:
        """{'covered': [...], 'gaps': [...], 'coverage_pct': float,
            'partial': [...]} — the LP-facing gap report."""

def load_concordance() -> ConcordanceMap:
    """Seed by converting cross_reference.py's 59 mappings to ConcordanceEntry
    (write a one-off migration in the module, keep cross_reference as the
    lookup API for backwards compat, re-exported over the new store).
    Extend with GRI↔ISSB and ESRS↔ISSB published interoperability mappings."""
```

Data file: `data/concordance.yaml` (the migrated 59 + new entries; target ≥120 concepts covering the full GHG/energy/water/workforce/governance core). `cross_reference.py` becomes a thin shim over `concordance.py` — **do not** leave two sources of truth.

**Tool surface:** extend `cross_reference_tool.py` with actions `translate` (record → target framework) and `coverage` (records list → gap report).

**Tests (`tests/test_concordance.py`):** all 59 legacy mappings survive migration byte-for-byte (regression fixture); `translate` GHG Scope-1 IRIS→GRI 305-1; `coverage_report` math; round-trip A→B→A returns the same concept.

**Effort:** M.

### B2 — XBRL / iXBRL digital tagging export

**Pain point:** P2/P9. CSRD digital tagging (iXBRL vs EFRAG ESRS taxonomy) mandatory for FYs starting 2026-01-01; ISSB has its own taxonomy.

**Backing modules (extend):** `impact/issb_reporting.py`, `impact/frameworks/esrs.py`, `impact/metric_records.py`, `tools/impact/impact_report_tool.py`, `impact/concordance.py` (B3).

**New file:** `src/openharness/impact/xbrl_export.py`

```python
class XBRLTag(BaseModel):
    element: str                # taxonomy element qname, e.g. "esrs:GrossScope1GHGEmissions"
    taxonomy: Literal["esrs_set1", "issb"]
    context_ref: str            # period + entity context id
    unit_ref: str | None        # e.g. "tCO2e", "EUR"
    value: str
    decimals: str = "0"
    metric_record_id: str       # provenance link back to MetricRecord

def build_context(entity_id: str, period: str) -> dict: ...
def tag_records(records: list[MetricRecord], taxonomy: str,
                concordance: ConcordanceMap) -> tuple[list[XBRLTag], list[dict]]:
    """Returns (tags, untaggable) — untaggable carries the reason
    (no taxonomy_uri in concordance, missing unit, missing period)."""
def render_ixbrl(html: str, tags: list[XBRLTag], entity_id: str, period: str) -> str:
    """Wrap the existing HTML report: inject <ix:header> (contexts, units)
    and wrap tagged values in <ix:nonFraction>/<ix:nonNumeric>."""
def render_xbrl_json(tags: list[XBRLTag], ...) -> dict:
    """xBRL-JSON (OIM) sibling output."""
```

Implementation notes:
- **No heavyweight dependency.** Emit iXBRL via string/`jinja2` templating in `impact/report_templates/` (new `ixbrl_template.py`), consistent with the existing report pipeline. Do not add Arelle as a runtime dependency; add it as an optional dev-dependency used only in tests to validate output (guard with `pytest.importorskip("arelle")`, plus schema-free structural assertions that always run).
- Taxonomy element names ship as the `taxonomy_uri` column in `data/concordance.yaml` (B3), sourced from the EFRAG ESRS Set-1 XBRL taxonomy and the IFRS ISSB taxonomy. Seed the ~40 highest-traffic elements (GHG scopes, energy, water, workforce, governance); mark the rest `taxonomy_uri: null` → they surface in `untaggable`.
- Wire into `impact_report_tool.py` as a new `output_format: "ixbrl"` and `"xbrl-json"`.

**Tests (`tests/test_xbrl_export.py`):** tag GHG Scope 1 record → correct element/unit/context; untaggable reasons; iXBRL output parses as XML and contains `ix:nonFraction` per tag; xBRL-JSON structure; optional Arelle validation test.

**Effort:** L.

### B1 — ISSA 5000 engagement-readiness

**Pain point:** P2/assurance. ISSA 5000 effective for periods beginning on/after 2026-12-15.

**Backing modules (extend):** `impact/assurance.py` (ISAE 3000/AA1000 packs), `impact/verification_workspace.py`, `impact/engagements/verification_bundle.py`, `impact/evidence_graph.py`, `impact/audit_trail.py`.

**Work — extend `impact/assurance.py`** (no new module):

```python
class Assertion(BaseModel):
    assertion_id: str
    statement: str                       # management assertion text
    subject_matter: str                  # metric/claim ids in scope
    criteria: str                        # e.g. "GHG Protocol", "IRIS+ 5.3c"
    evidence_node_ids: list[str]         # evidence-graph node ids

class EvidenceSufficiency(BaseModel):
    assertion_id: str
    evidence_count: int
    independent_evidence: bool           # any evidence not self-reported
    quality_band: Literal["high", "medium", "low"]
    sufficient_for: Literal["reasonable", "limited", "neither"]
    gaps: list[str]

def build_issa5000_pack(assessment, graph: EvidenceGraph, trail: AuditTrail,
                        level: Literal["limited", "reasonable"]) -> dict:
    """{'assertions': [...], 'sufficiency': [...],
        'limited_vs_reasonable_gap': [...],   # what more 'reasonable' needs
        'engagement_acceptance': {...},        # preconditions checklist
        'audit_trail_head': trail.head, 'manifest': signed}"""
```

Sufficiency scoring rules (deterministic, documented in the module docstring): reasonable requires ≥2 evidence nodes per assertion with ≥1 independent + quality high; limited requires ≥1 with quality ≥ medium. The **limited-vs-reasonable gap report** lists, per assertion, exactly which rule fails. Wire the pack into `engagements/verification_bundle.py` as a fourth pillar section and expose through the existing `verification_workspace` tool (`action: "issa5000_pack"`).

**Tests (`tests/test_issa5000.py`):** sufficiency rule table (parametrized); gap report names failing rules; pack is HMAC-signed via `signed_feed`; verification-workspace action round-trip.

**Effort:** L.

### B4 — Data comparability score

**Pain point:** P2 — LP-facing "can I actually compare this?"

**Backing modules (extend):** `impact/metric_records.py`, `impact/portfolio_rollup.py`, `impact/concordance.py` (B3).

**Work — add to `impact/metric_records.py`:**

```python
COMPARABILITY_WEIGHTS = {"unit": 0.25, "period": 0.20, "boundary": 0.15,
                         "taxonomy_id": 0.25, "methodology": 0.15}

def comparability_score(record: MetricRecord, concordance: ConcordanceMap) -> dict:
    """0-100 + per-component breakdown. taxonomy_id component = record maps to
    a concordance concept with an XBRL taxonomy_uri."""

def portfolio_comparability_index(records_by_company: dict[str, list[MetricRecord]],
                                  concordance: ConcordanceMap) -> dict:
    """{'index': float, 'per_company': {...}, 'weakest_components': [...],
        'shared_concepts': [...]}  # concepts every company reports — the
        actually-comparable core, for F1."""
```

Add `boundary: str | None = None` field to `MetricRecord` if absent (organizational/operational boundary) — additive, defaulted, so existing callers are untouched. Surface via `portfolio_tool.py` action `comparability` and in the F1 report.

**Tests:** score component math; index over a 3-company fixture; missing-boundary degrades score; shared-concept extraction.

**Effort:** M.

---

## 5. Track C — Frontier Instruments & Integrity (P1/P2)

### C1 — Carbon-credit integrity screen

**Pain point:** P1. ICVCM CCPs are the supply-side benchmark (8 programs, 38 methodologies CCP-eligible); VCMI Claims Code requires CCP-labelled or Article 6.4 credits for credible claims; ICROA winding down 2026.

**Backing modules (extend):** `impact/greenwashing.py`, `impact/greenwashing_reviewer.py`, `impact/climate_accounting.py`, `impact/emission_factors.py`.

**New file:** `src/openharness/impact/carbon_credit_integrity.py`

```python
class CarbonCredit(BaseModel):
    program: str                  # "verra_vcs", "gold_standard", "acr", ...
    methodology_id: str
    vintage: int
    volume_tco2e: float
    ccp_labelled: bool | None = None      # if None, infer from program/methodology tables
    article_6_authorized: bool = False
    corresponding_adjustment: bool | None = None
    project_type: str                     # "redd+", "cookstoves", "dac", ...

CCP_ELIGIBLE_PROGRAMS: dict[str, dict]      # program -> {status, as_of, source}
CCP_APPROVED_METHODOLOGIES: dict[str, dict] # methodology -> {status, as_of, source}

class CreditIntegrityResult(BaseModel):
    credit_score: int              # 0-100
    ccp_status: Literal["ccp_labelled", "ccp_eligible_program", "not_eligible", "unknown"]
    vcmi_claim_tier: Literal["compliant", "at_risk", "non_compliant"]
    flags: list[str]               # e.g. "pre-2016 vintage", "non-CCP methodology",
                                   # "claim wording implies offsetting neutrality"
    citations: list[str]

def screen_credits(credits: list[CarbonCredit],
                   claim_text: str | None = None) -> CreditIntegrityResult
```

When `claim_text` is provided, delegate wording analysis to the existing greenwashing engine (`greenwashing.py` detector + `greenwashing_reviewer` severity model) and merge flags — do not reimplement claim NLP. Program/methodology tables live as module constants with `as_of: "2026-06"` and source URLs; they are small (~50 rows).

**Tool surface:** new registered tool `carbon_credit_integrity` (module `tools/impact/carbon_credit_tool.py`, actions `screen | list_programs`). Register per §0.1.

**Tests (`tests/test_carbon_credit_integrity.py`):** CCP-labelled high score; unknown program → "unknown" not crash; old vintage flag; neutrality-claim wording escalates via greenwashing engine (mock); VCMI tier mapping.

**Effort:** M.

### C2 — Biodiversity-credit integrity screen

**Backing modules (extend):** `impact/ecosystem_services.py`, `impact/greenwashing_reviewer.py`.

**Work:** add to `impact/ecosystem_services.py` (it already owns natural-capital logic): `BIODIVERSITY_CREDIT_PRINCIPLES` — the IAPB/BCA/WEF 21 High-Level Principles as structured records `{id, pillar: outcomes|equity|governance, principle, assessment_question, scoring_guidance}`; `screen_biodiversity_credit(answers: dict[str, int]) -> dict` returning per-pillar scores, quality band (high/medium/low integrity), and unanswered-principle gaps. Expose via the C1 tool (`action: "screen_biodiversity"`) rather than a separate tool.

**Tests:** 21 principles load; banding thresholds; partial answers produce gaps.

**Effort:** M (mostly content).

### C3 — SBTN science-based targets for nature

**Backing modules (extend):** `impact/frameworks/tnfd.py`, `impact/ecosystem_services.py`, `impact/geospatial.py`, `impact/impact_target_setter.py`.

**Work:** new file `src/openharness/impact/frameworks/sbtn.py` implementing the 5-step readiness flow (Assess → Prioritise → Measure → Act → Track), mirroring the structure of `impact_target_setter.py`:

```python
class SBTNStep(BaseModel):
    step: Literal["assess", "prioritise", "measure", "act", "track"]
    questions: list[dict]          # {id, text, evidence_ask}
    complete: bool

def sbtn_readiness(company: Company, answers: dict) -> dict:
    """Per-step completion, overall readiness band, next actions,
    GBF Target 15 linkage note, and V2-methods 'beta' label."""

def nature_target_ranges(pressure: Literal["land", "freshwater", "ocean", ...],
                         sector: str) -> dict:
    """Pressure-based indicative target ranges with source citations;
    values marked status='indicative' until SBTN V2 finalises (mid-2026)."""
```

Materiality of pressures by sector: reuse the sector normalization from `tools/impact/common.py` and TNFD sector guidance already encoded in `frameworks/tnfd.py` — reference, don't copy.

**Tool surface:** extend `framework_assess` with `framework: "sbtn"`.

**Tests:** 5 steps present; readiness math; target ranges carry `status` + citations; unknown sector falls back gracefully.

**Effort:** L.

### C4 — Outcomes / impact-linked finance verification

**Pain point:** P10, P1. SLBs subdued because of weak KPIs and immaterial step-ups; credibility question = KPI quality + payment verification.

**Backing modules (extend):** `impact/blended_finance.py` (`ILLoanTerms`, `RateStep`, `SOCTerms`, impact carry), the monitoring models in `impact/models.py` (`MonitoringSchedule`, `MonitoringAlert`, persisted via `impact/storage.py` — there is no separate `monitoring.py`), plus `impact/metric_records.py`.

**Work — extend `impact/blended_finance.py`:**

```python
class KPICredibility(BaseModel):
    kpi_id: str
    core_impact_relevance: int      # 1-5: does the KPI capture the core impact of the ToC?
    ambition: int                   # 1-5: vs baseline/benchmark trajectory
    penalty_materiality: float      # step-up bps / coupon, or forfeited carry %
    penalty_material: bool          # rule: >= 25bps or >= 10% of carry at risk
    verification: Literal["third_party", "internal", "none"]
    score: int                      # 0-100 composite
    flags: list[str]

def score_kpi_credibility(kpi: dict, toc_outcomes: list[str],
                          benchmark: dict | None) -> KPICredibility

class PbRMilestone(BaseModel):
    milestone_id: str
    metric_id: str                  # MetricRecord metric id
    threshold: float
    due: str                        # ISO date
    payment: float
    status: Literal["pending", "achieved", "missed", "disputed", "verified"]
    evidence_refs: list[str]

def track_payment_by_results(deal_terms, milestones: list[PbRMilestone],
                             records: list[MetricRecord]) -> dict:
    """Evaluate milestones against MetricRecords (only 'verified' records can
    move status to 'verified'), compute payments due, emit audit events."""
```

**Tool surface:** **no blended-finance tool exists today** (verified — `impact/blended_finance.py` has no adapter in `tools/impact/`). Create and register a new tool `impact_linked_finance` (module `tools/impact/impact_linked_finance_tool.py`) exposing the existing blended-finance builders plus new actions `score_kpi | track_pbr` (and later G3's `simulate_carry | simulate_safi`). Register per §0.1.

**Tests:** penalty-materiality rule; unverified record cannot verify a milestone; payment computation; dispute path; audit events appended.

**Effort:** M.

---

## 6. Track D — Social Frontier (P2)

### D1 — Just Transition assessment

**Backing modules (extend):** `impact/worker_voice.py`, `impact/stakeholder_voice.py`, `impact/frameworks/tisfd.py`, `impact/hrdd.py`, `impact/climate_scenario.py`.

**Work:** new file `src/openharness/impact/just_transition.py` encoding the Shift/Council for Inclusive Capitalism/WBA/WBCSD/LSE **19 sector-agnostic Just Transition metrics** as data:

```python
JT_METRICS: list[dict]  # {id, stakeholder_group: own_workforce|communities|value_chain,
                        #  pillar: governance|strategy|risk_impact|metrics_targets,
                        #  metric, outcome_focus, gri_ref, tisfd_ref, source}

def assess_just_transition(company: Company,
                           records: list[MetricRecord],
                           transition_plan: dict | None) -> dict:
    """Coverage per stakeholder group + pillar, linkage check
    (does the climate transition plan reference people outcomes?),
    worker-voice signal (reuse worker_voice scoring), gap list."""
```

**Tool surface:** extend `framework_assess` with `framework: "just_transition"`.

**Tests:** 19 metrics load with valid group/pillar enums; coverage math; plan-linkage flag; GRI/TISFD refs resolve against existing framework modules.

**Effort:** M.

### D2 — Living-wage gap analyser

**Backing modules (extend):** `impact/hrdd.py`, `impact/benchmarks.py`, D1.

**Work:** new file `src/openharness/impact/living_wage.py` + data file `data/living_wage_benchmarks.yaml` (country/region → annual living-wage estimate, currency, source (Anker methodology / WageIndicator), `as_of`). Seed ~40 geographies including HK, mainland China tiers, SEA, Sub-Saharan Africa.

```python
def living_wage_gap(geography: str, wages: list[dict],  # {role, headcount, annual_wage, currency}
                    fx=None) -> dict:
    """Per-role and weighted gap %, headcount below living wage, remediation
    cost estimate, benchmark provenance. Currency conversion via impact/fx.py."""
```

Feeds D1 (metric jt-lw), 2X (`frameworks/two_x.py`) and HRDD outputs — expose a small helper each module can call.

**Tests:** gap math incl. currency conversion; missing geography → explicit "no benchmark" not zero; remediation cost.

**Effort:** M.

### D3 — TISFD disclosure builder

**Backing modules (extend):** `impact/frameworks/tisfd.py` (v5 readiness), `impact/engagements/reporting_studio.py`, `impact/concordance.py`.

**Work:** add `build_tisfd_disclosure(readiness_result, records) -> dict` to `frameworks/tisfd.py` producing a drafted four-pillar disclosure skeleton (governance/strategy/risk/metrics) with per-section text scaffolds, GRI/ESRS crosswalk (via concordance), and a persistent `"beta — TISFD framework still stabilising"` banner. Register the output as a reporting-studio template so the claim-review state machine applies to it.

**Tests:** four pillars present; crosswalk refs valid; beta banner present; reporting-studio template registration.

**Effort:** S.

---

## 7. Track E — Governed, Self-Updating AI (P1/P2)

### E1 — Regulatory radar

**Pain point:** P9, P15. A static knowledge base rots; funds need "what changed and who in my portfolio is affected".

**Backing modules (extend):** `impact/standards_registry.py`, `impact/regulatory_calendar.py`, `impact/ai_governance.py`, `impact/evidence_workflow.py`.

**New file:** `src/openharness/impact/regulatory_radar.py`

```python
class TrackedStandard(BaseModel):
    standard_id: str              # must exist in standards_registry
    watch_urls: list[str]         # official source pages
    last_seen_hash: str | None
    last_checked: str | None

class RadarFinding(BaseModel):
    standard_id: str
    change_kind: Literal["content_changed", "new_version", "deadline_changed", "manual_note"]
    summary: str
    detected_at: str
    affected_companies: list[str] # portfolio impact
    review_status: Literal["pending", "confirmed", "dismissed"]

def check_tracked_standards(tracked: list[TrackedStandard],
                            fetcher: Callable[[str], str]) -> list[RadarFinding]:
    """Pure logic: hash-compare fetched content, diff-summarize headings.
    `fetcher` is injected — the engine module does no network I/O itself;
    the tool layer supplies the fetch (and tests supply a stub)."""

def portfolio_impact(finding: RadarFinding, companies: list[Company],
                     packs) -> list[str]:
    """Which companies' jurisdictions/sectors are touched (reuse
    regulatory_packs applicability logic)."""
```

Findings enter the **existing** `evidence_workflow` review queue (AI-produced → human-confirmed) — never auto-update `standards_registry`; a confirmed finding produces a suggested registry patch the user applies. Seed `data/tracked_standards.yaml` with: SFDR 2.0 trilogue page, EFRAG simplified-ESRS page, FCA SDR page, IFRS ISSB adoption page, CARB SB253 page, SSE Guideline No. 14 page (Track I), IRIS+ updates page.

**Tool surface:** new registered tool `regulatory_radar` (actions `check | list_findings | confirm | dismiss | impact`). The tool layer may use the harness's HTTP capability for `fetcher`; keep timeouts and per-URL error isolation.

**Tests (`tests/test_regulatory_radar.py`):** hash-change detection with stub fetcher; no-change → no finding; finding enters review queue; portfolio-impact matching; registry never mutated without confirmation.

**Effort:** M.

### E2 — Extraction eval / benchmark harness

**Backing modules (extend):** `impact/extractors/`, `impact/ai_governance.py` (v5 model card), `impact/evidence_workflow.py`.

**New file:** `src/openharness/impact/extraction_eval.py` + gold set `data/eval/extraction_gold.jsonl` (each line: `{doc_id, source_text, expected_claims: [...], expected_metrics: [...], expected_sdgs: [...]}` — seed with ≥25 hand-labelled excerpts from the existing test fixtures/pitch-deck samples).

```python
class EvalResult(BaseModel):
    precision: float; recall: float; f1: float
    per_field: dict[str, dict]      # claims/metrics/sdgs breakdown
    failures: list[dict]            # doc_id + diff for regression triage
    extractor_version: str
    run_at: str

def run_eval(extract_fn: Callable[[str], dict], gold_path: str) -> EvalResult
def update_model_card(result: EvalResult) -> dict   # auto-populate v5 ai_governance model card
```

Matching rules: claims match on normalized-text Jaccard ≥ 0.6; metrics on metric_id; SDGs on goal number. Add a CI-friendly entry `python -m openharness.impact.extraction_eval --gate 0.75` returning non-zero exit if F1 drops below the gate; wire as an optional CI step (do not block existing CI initially — add as `continue-on-error: true` first wave).

**Tests:** matcher rules; perfect extractor → 1.0; regression fixture; model-card population.

**Effort:** M.

### E3 — dMRV evidence ingestion + anchoring

**Backing modules (extend):** `impact/signed_feed.py`, `impact/geospatial.py`, `impact/evidence_graph.py`, `impact/metric_records.py`.

**New file:** `src/openharness/impact/dmrv.py`

```python
class TimeSeriesEvidence(BaseModel):
    series_id: str
    source_kind: Literal["remote_sensing", "iot_sensor", "meter", "survey_wave", "registry_api"]
    metric_id: str
    points: list[dict]            # {t: ISO ts, value: float, unit: str, quality: str|None}
    provider: str
    methodology: str
    content_hash: str = ""        # sha256 of canonical JSON, computed on ingest

def ingest_time_series(evidence: TimeSeriesEvidence, graph, trail) -> dict:
    """Canonicalise → hash → add evidence node to graph, link measured_by to
    the metric, append audit event, return node id + hash."""

def anchor_claim(claim_id: str, evidence_ids: list[str], graph, signer) -> dict:
    """Build a verifiable-claim envelope {claim, evidence hashes, graph proof
    path, HMAC signature via signed_feed} — NOT a blockchain; see roadmap-v6 §8."""

def summarise_series(evidence: TimeSeriesEvidence) -> MetricRecord:
    """Derive a period MetricRecord (mean/sum per methodology) with
    source_type='dmrv', evidence_refs=[series hash]."""
```

**Tool surface:** new registered tool `dmrv_evidence` (actions `ingest | anchor | summarise | verify`). `verify` re-hashes and checks the signature — pairs with the verifier-token flow in `engagements/verification_bundle.py`.

**Tests:** hash determinism; tamper detection; graph node/link creation; MetricRecord derivation respects the canonical contract; anchor→verify round-trip.

**Effort:** L.

---

## 8. Track F — Comparability & Portfolio Intelligence (P1)

### F1 — Multi-company interactive portfolio report

**Backing modules (extend):** `impact/portfolio_rollup.py`, `impact/portfolio_nlq.py`, `impact/external_benchmarks.py`, `impact/giin_benchmarks.py`, `impact/report_templates/` (reuse v5 report chrome: audience filter, dark mode, print/PDF), B4 comparability index.

**Work:** new template `impact/report_templates/portfolio_report.py` + assembly function in `portfolio_rollup.py`:

```python
def build_portfolio_report(companies: list[Company],
                           records_by_company: dict[str, list[MetricRecord]],
                           benchmarks=None) -> dict:
    """Sections: portfolio KPIs, comparability index (B4), shared-concept
    comparison table (only actually-comparable metrics), per-company 5D/SDG
    heatmap, peer benchmarking, gaps. Returns section dict consumed by the
    template; single-file HTML with Plotly, no external assets."""
```

Expose via `impact_report_tool.py` (`report_type: "portfolio"`) and `portfolio_tool.py`. Add a dashboard Portfolio-tab download button.

**Tests:** 3-company fixture renders; comparability section present; only shared concepts in the comparison table; HTML is self-contained (no http(s) asset refs except CDN plotly consistent with existing reports).

**Effort:** L.

### F2 — LP data-room export

**Backing modules (extend):** `tools/impact/lp_ddq_export_tool.py`, `impact/engagements/data_room.py`, B2 (xBRL-JSON), B3.

**Work:** add `build_lp_dataroom(fund, companies, records) -> dict` to `engagements/data_room.py` producing a zip-able bundle manifest: `portfolio.xbrl.json` (B2), `metrics.csv` (flat MetricRecords), `concordance_coverage.json` (B3 gap report per framework), `comparability.json` (B4), `ddq_answers.xlsx` (existing lp_ddq_export), `manifest.json` (hashes of every file, signed via `signed_feed`). Writer helper in the tool layer assembles actual files to a target dir.

**Tests:** manifest hashes match files; bundle contains all six artifacts; signature verifies.

**Effort:** M.

### F3 — Emerging-market / SDG-need context layer

**Backing modules (extend):** `impact/giin_benchmarks.py`, `impact/sdg_taxonomy.py`, `impact/benchmarks.py`.

**Work:** `data/sdg_need_context.yaml` (country → per-SDG need intensity band with source: UN SDG index tiers) + `sdg_need_context(geography, sdg_goals) -> dict` helper in `sdg_taxonomy.py`; render as a context ribbon in reports ("this outcome is delivered where SDG-6 need is high"). Feeds F1 and the flagship report.

**Tests:** lookup; unknown country neutral band; report section render.

**Effort:** S.

---

## 9. NEW extension tracks (G–J) — pain-point wave

These four tracks come from the July-2026 research (§2) and the OHESG deep-dive. They follow the same rules: extend, never fork; three-place tool registration; audit-trail integration.

### Track G — Contribution, Targets & Impact-Linked Economics (P0/P1)

#### G1 — Investor Contribution 2.0 evidence engine

**Pain point:** P3/P7 — the field's weakest verified practice. Most investors claim 100% of investee impact; OPIM Principle 3 reviews find contribution narratives are written once and never evidenced. Impact Frontiers is consulting on "Investor Contribution 2.0". **No commercial tool ships this — clear whitespace.**

**Backing modules (extend):** `impact/evidence_graph.py`, `impact/audit_trail.py`, `impact/counterfactual.py`, `impact/causal.py`, `impact/exit_impact.py` (OPIM P8 pattern to mirror), `impact/metric_records.py`.

**New file:** `src/openharness/impact/contribution.py`

```python
class ContributionChannel(str, Enum):
    CAPITAL_ADDITIONALITY = "capital_additionality"   # capital otherwise unavailable
    NON_FINANCIAL_SUPPORT = "non_financial_support"   # active engagement/ta
    MARKET_SIGNAL = "market_signal"
    FLEXIBLE_TERMS = "flexible_terms"
    NEW_MARKET_CATALYSED = "new_market_catalysed"

class ContributionClaim(BaseModel):
    claim_id: str
    company: str
    channel: ContributionChannel
    narrative: str
    stated_at: str                 # investment date — claims must be pre-registered
    planned_activities: list[dict] # {activity_id, description, cadence, owner}
    attribution_pct: float | None  # None = contribution-only language (preferred)
    evidence_node_ids: list[str] = []

class ContributionEvidence(BaseModel):
    activity_id: str
    occurred_at: str
    description: str
    artifact_refs: list[str]       # board minutes, TA reports, term sheets
    outcome_link: str | None       # metric_id the activity plausibly moved

def register_contribution_claim(claim, graph, trail) -> dict
def log_contribution_activity(claim_id, evidence, graph, trail) -> dict
def contribution_scorecard(claims: list[ContributionClaim],
                           evidence: list[ContributionEvidence],
                           records: list[MetricRecord]) -> dict:
    """Per-claim: evidence coverage of planned activities, staleness
    (days since last evidence), attribution-inflation flag
    (attribution_pct set with < 2 evidence items, or Σ across co-investors > 100%),
    contribution-monitoring grade A–E. Portfolio view: % of claims monitored
    in last 12m — the number a BlueMark practice review asks for."""

def attribution_sanity_check(company: str, investor_claims: list[dict]) -> dict:
    """Flag Σ attribution_pct > 100% across investors; suggest
    contribution-language rewrite (delegates phrasing check to
    greenwashing_reviewer)."""
```

Deterministic grade rules documented in the docstring (A = all planned activities evidenced ≤ 90 days stale; E = no evidence post-investment). Counterfactual helpers: where a baseline exists, call `impact/counterfactual.py` for a "with/without" delta annotation — annotation only, never a causal certificate.

**Tool surface:** new registered tool `contribution_tracker` (module `tools/impact/contribution_tool.py`; actions `register_claim | log_activity | scorecard | attribution_check`). Also expose `scorecard` inside `engagement_suite` (value_creation track) for consultants.

**Tests (`tests/test_contribution.py`):** claim pre-registration timestamps immutable via audit trail; grade rule table (parametrized A–E); inflation flag at Σ>100%; staleness math; evidence links appear in the evidence graph; greenwashing delegation mocked.

**Effort:** L. **This is the highest-differentiation item in the plan.**

#### G2 — Investment-time impact target setting (term-sheet gate)

**Pain point:** P5 — only 42% of investors set impact targets as a condition of investment (BlueMark). We have `impact_target_setter.py` (v5) and `deal_gate.py` but nothing binds targets to the deal decision.

**Backing modules (extend):** `impact/impact_target_setter.py`, `impact/deal_gate.py`, `impact/ic_memo.py`, `impact/engagements/toc_builder.py` (KPI lock), G1.

**Work — extend `impact/deal_gate.py`:**

```python
class TargetCondition(BaseModel):
    target_id: str                # from impact_target_setter output
    metric_id: str
    baseline: float | None
    target_value: float
    by_period: str
    condition_kind: Literal["condition_precedent", "covenant", "aspiration"]
    linked_incentive: str | None  # G3 instrument id, if any

def gate_with_targets(deal, targets: list[TargetCondition]) -> dict:
    """Deal-gate verdict extension: block 'pass' when zero
    condition_precedent/covenant targets exist; emit the BlueMark-style
    'targets set at investment: yes/no' flag; write targets into the
    evidence graph as target nodes and register a monitoring schedule."""
```

`ic_memo.py`: add a "Impact targets as investment conditions" section to the IC memo template rendering the `TargetCondition` table. `toc_builder`: locked KPI frameworks can be promoted to `TargetCondition`s (`promote_kpis_to_conditions(framework_id) -> list[TargetCondition]`).

**Tool surface:** extend the existing deal-gate/target-setter tools with `action: "gate_with_targets"` and `"promote_kpis"`. No new tool.

**Tests:** gate blocks without binding targets; aspiration-only → warning not pass; monitoring schedule created; IC memo section renders; ToC promotion round-trip.

**Effort:** M.

#### G3 — Impact-linked carry / SAFI structuring calculator

**Pain point:** P10 — impact-linked carry (Apollo/Apax/EQT-style) and SAFI instruments lack measurement-backed underwriting.

**Backing modules (extend):** `impact/blended_finance.py` (C4's `KPICredibility` is the underwriting input), `impact/fund_analytics.py`, `impact/impact_valuation.py` (IFVI factors for monetized triggers), G2.

**Work — extend `impact/blended_finance.py`:**

```python
class CarryStructure(BaseModel):
    model: Literal["reward", "forfeiture_escrow"]
    base_carry_pct: float               # e.g. 0.20
    at_risk_pct: float                  # share of carry tied to impact
    triggers: list[dict]                # {target_id (G2), weight, measurement: str,
                                        #  verifier: third_party|internal}
    charity_fallback: str | None        # forfeited carry destination

def simulate_carry(structure: CarryStructure,
                   scenarios: list[dict]) -> dict:
    """Per scenario (target achievement vector): carry paid, forfeited,
    LP economics delta; credibility annotations from score_kpi_credibility
    (C4) per trigger; flags: 'trigger not third-party verified',
    'at_risk_pct < 0.1 — likely immaterial to LPs'."""

class SAFITerms(BaseModel):
    principal: float
    max_discount_pct: float
    outcome_schedule: list[PbRMilestone]   # reuse C4 model

def simulate_safi(terms: SAFITerms, records: list[MetricRecord]) -> dict
```

**Tool surface:** add actions `simulate_carry | simulate_safi` to the `impact_linked_finance` tool created in C4.

**Tests:** carry math both models; materiality flag at <10% at-risk; SAFI discount accrual against verified records only; scenario table.

**Effort:** M.

### Track H — Investee Burden Reduction & Data Delivery (P1)

#### H1 — "Ask once" data-request deduplication

**Pain point:** P4 — portfolio companies spend ~20 h/yr answering near-duplicate asks from multiple investors in different formats.

**Backing modules (extend):** `impact/engagements/data_room.py` (data request packs), `impact/investee_collection.py` (questionnaire schema + submission lifecycle), `impact/questionnaire_v2.py`, `impact/concordance.py` (B3).

**Work — extend `impact/engagements/data_room.py`:**

```python
def dedupe_requests(packs: list[dict]) -> dict:
    """Given N investor request packs, map every requested field to a
    concordance concept_id; cluster duplicates; emit ONE consolidated
    request list + a routing table {concept_id -> [(pack_id, field_id, format)]}
    so one answer fans out to every asker in their format."""

def answer_fanout(consolidated_answers: dict[str, MetricRecord],
                  routing: dict) -> dict[str, dict]:
    """pack_id -> filled pack. Unit conversion via existing helpers;
    period alignment noted, never silently re-based."""

def burden_report(packs: list[dict], consolidated: dict) -> dict:
    """{'fields_before': int, 'fields_after': int, 'estimated_hours_saved': float}
    — the number that sells this feature (assume 5 min/field, cite UpMetrics)."""
```

**Tool surface:** `engagement_suite` data_room actions `dedupe_requests | answer_fanout | burden_report`. Also surface in the investee portal (`impact/investee_portal.py`): render the consolidated list instead of per-investor lists when routing exists.

**Tests:** two packs asking GHG Scope 1 under different names dedupe to one concept via concordance; fan-out preserves format ids; unmappable fields pass through un-deduped (never dropped); burden math.

**Effort:** M.

#### H2 — Survey delivery channel abstraction (WhatsApp / SMS / voice / web)

**Pain point:** P6/P8 — stakeholder-voice models exist (`stakeholder_voice`, `surveys`, `worker_voice`) but there is **no delivery/collection channel**. Field evidence: WhatsApp ≈40% response vs 6% phone, 15–25% email; AI voice agents cut collection from weeks to days (60dB "Beto").

**Backing modules (extend):** `impact/surveys.py`, `impact/stakeholder_voice.py` (Lean Data templates + `ConsentRecord`), `impact/evidence_workflow.py`.

**New file:** `src/openharness/impact/survey_delivery.py`

```python
class DeliveryChannel(Protocol):
    channel_id: str                       # "whatsapp" | "sms" | "voice" | "web_link"
    def render(self, survey, language: str) -> list[dict]: ...
        # channel-appropriate message sequence (WhatsApp: ≤ 4096-char messages,
        # numbered-reply choice questions; SMS: 160-char segments; voice: SSML-ish
        # prompt script; web: single-file HTML form reusing investee_portal chrome)
    def parse_response(self, raw: dict) -> dict: ...

class SurveyDispatch(BaseModel):
    dispatch_id: str
    survey_id: str
    channel_id: str
    respondent_ref: str            # pseudonymous — PII stays out; consent_id required
    consent_id: str                # must reference a valid ConsentRecord
    status: Literal["draft", "sent", "responded", "expired", "opted_out"]
    sent_at: str | None; responded_at: str | None

class InMemoryDispatchStore: ...   # workspace.py pattern; to_dict()/from_dict()

def build_webhook_payload_parser(channel_id: str) -> Callable[[dict], dict]:
    """Normalise inbound webhook payloads (Twilio-style WhatsApp/SMS shapes,
    generic voice-transcript shape) to {respondent_ref, answers, meta}.
    Pure parsing — no vendor SDK dependency; vendors are integrated at the
    api_gateway layer."""

def ingest_response(dispatch: SurveyDispatch, parsed: dict,
                    graph, trail) -> dict:
    """Validate against survey schema → feedback record via stakeholder_voice
    quality scoring → evidence node → audit event. Refuse ingest without
    valid consent; honour opt-out keywords (STOP/退出) by voiding the dispatch."""
```

**Gateway:** add `POST /api/v1/surveys/webhook/{channel_id}` to `api_gateway/router.py` (bearer-authed per existing pattern) calling the parser + `ingest_response`. **No vendor SDKs in core** — the engine renders channel-native content and parses normalized payloads; actual Twilio/Meta wiring is deployment configuration documented in `docs/fund-manager-guide.md`.

**Consent is non-negotiable:** every dispatch requires a `ConsentRecord` id; GDPR/PDPA fields already exist in `stakeholder_voice.py` — reuse.

**Tool surface:** new registered tool `survey_delivery` (actions `render | dispatch | ingest | status | response_rates`). `response_rates` reports per-channel response % against the published benchmarks table (cited constants).

**Tests (`tests/test_survey_delivery.py`):** WhatsApp render respects message-length and numbered-choice format; SMS segmentation; consent enforcement (no consent → error); opt-out voids dispatch; webhook parser fixtures per channel; ingest creates feedback + evidence + audit entries; response-rate math.

**Effort:** L.

#### H3 — CIDS v3.2 export (Common Impact Data Standard)

**Pain point:** P12 — impact data doesn't travel; CIDS v3.2 (2025-07-28) is the only open interoperability ontology (OWL/SHACL; ToC, outcomes, indicators, ISO 21972 units) and **no VC/PE platform exports it**.

**Backing modules (extend):** `impact/engagements/toc_builder.py` (ToC canvas), `impact/metric_records.py`, `impact/models.py` (`ImpactTarget`), `impact/concordance.py`.

**New file:** `src/openharness/impact/cids_export.py`

```python
CIDS_CONTEXT = {...}   # JSON-LD @context pinned to CIDS v3.2 namespace URIs

def export_cids(company: Company, toc: dict | None,
                records: list[MetricRecord],
                targets: list[ImpactTarget]) -> dict:
    """JSON-LD document: cids:Organization, cids:Theme, cids:Outcome (from ToC
    outcomes), cids:Indicator (from MetricRecords; unit via ISO 21972 mapping
    table), cids:IndicatorReport (values+periods), cids:ImpactModel linking the
    chain. Basic-tier conformance first (the standard defines tiers); document
    which SHACL shapes we satisfy in the module docstring."""

def validate_cids(doc: dict) -> list[str]:
    """Structural validation against bundled shape summaries (no pyshacl
    runtime dep; add pyshacl as optional dev-dep for a skipped-if-absent test)."""
```

Data: `data/cids_unit_map.yaml` — our unit strings → ISO 21972 unit URIs (~60 rows).

**Tool surface:** `impact_report_tool.py` gains `output_format: "cids"`; also an F2 data-room artifact (`portfolio.cids.json`).

**Tests:** export fixture validates; ToC-less company still exports org+indicators; unit mapping fallback marks `unmapped_unit`; JSON-LD `@context` pinned.

**Effort:** M.

### Track I — OHESG-Derived Reporting Suite (P1) — China disclosure + interactive reporting logic

Source: deep study of `report.ohesg.com` (SSE Guideline No. 14 visualization: 63 articles, 21 topics, calculators, double-materiality workflow) and `tool.ohesg.com` (34-tool ESG toolbox whose metadata we already ingest via `impact/toolbox/ingest.py` + `tools/impact/esg_toolbox_tool.py`). We replicate the *interactive reporting logic* (with our own data files and provenance), not the site content wholesale.

#### I1 — Double-materiality assessment wizard (scored, quadrant, exportable)

**Pain point:** P16/P9 — we have ESRS double materiality conceptually (`frameworks/esrs.py`) but not the quantified workflow OHESG demonstrates and Guide No. 1 codifies.

**Backing modules (extend):** `impact/frameworks/esrs.py`, `impact/engagements/` (module style of `toc_builder.py`), `impact/report_templates/`.

**New file:** `src/openharness/impact/engagements/materiality.py`

```python
class ImpactMaterialityScore(BaseModel):
    topic_id: str
    scale: int; scope: int; irremediability: int; likelihood: int   # each 0-5,
    # anchor descriptions per level loaded from data (Guide-1 Table-7 style anchors)
    @property
    def severity(self) -> float: ...        # documented formula: mean(scale,scope,irremediability)
    @property
    def impact_material(self) -> bool: ...  # severity*likelihood normalised >= threshold

class FinancialMaterialityInput(BaseModel):
    topic_id: str
    qualitative_band: Literal["none", "low", "medium", "high"] | None
    absolute_amount: float | None           # reporting currency
    pct_net_profit: float | None

class MaterialityConfig(BaseModel):
    impact_threshold_detail: float = 7.0    # >= detailed disclosure
    impact_threshold_optional: float = 5.0  # 5..7 optional
    financial_abs_bands: list[dict]         # configurable currency bands
    financial_pct_bands: list[dict]         # e.g. >=5% net profit => material

class MaterialityResult(BaseModel):
    topic_id: str
    quadrant: Literal["dual", "financial_only", "impact_only", "neither"]
    disclosure_consequence: str   # "four_pillar_plus_topic" | "topic_rules" |
                                  # "explain_omission"
    scores: dict

def assess_materiality(topics: list[str], impact_scores, financial_inputs,
                       config: MaterialityConfig) -> list[MaterialityResult]
def materiality_matrix_payload(results) -> dict   # Plotly quadrant chart for reports
```

Topic universes are pluggable: ESRS topical standards (from `frameworks/esrs.py`), the 21 SSE topics (I3 data), or a custom list. The **union rule** (disclose if impact-material OR financially material) and per-quadrant consequences are explicit outputs.

**Tool surface:** `engagement_suite` new action group `materiality` (`assess | matrix | config`). Dashboard: add the matrix to the Company Assessment tab.

**Tests (`tests/test_materiality.py`):** threshold boundaries (7.0 / 5.0); quadrant classification truth table; union rule; config overrides; matrix payload shape.

**Effort:** M.

#### I2 — Four-pillar disclosure checklist engine (data-driven)

**Pain point:** P16/P9 — the Governance/Strategy/IRO-management/Metrics-&-Targets checklist structure is shared by ISSB S1/S2, TCFD, CSRD, and SSE Guide No. 2; we have no per-topic, pillar-organised requirement checker.

**Backing modules (extend):** `impact/dd_checklist.py` (the engine pattern to mirror: YAML → analyze → suggest), `impact/frameworks/issb_ifrs_s2.py`, `impact/frameworks/tcfd.py`.

**New files:** `src/openharness/impact/disclosure_checklist.py` + `data/disclosure_checklists/climate.yaml` (seed topic; schema below), later `data/disclosure_checklists/<topic>.yaml`.

```yaml
# data/disclosure_checklists/climate.yaml
topic_id: climate
frameworks: {sse_g14: "art. 21-28, Guide No. 2", issb: "IFRS S2", tcfd: "all pillars"}
pillars:
  - pillar: governance
    items:
      - id: clim-gov-01
        requirement: "Board oversight of climate-related risks and opportunities"
        bullets: ["oversight body and charter", "reporting cadence", "competence"]
        modality: shall          # shall | encouraged
        legal_basis: ["SSE G14 art.22", "IFRS S2 ¶6"]
  - pillar: strategy ...
  - pillar: iro_management ...
  - pillar: metrics_targets ...
```

```python
class DisclosureChecklist(BaseModel): ...   # loads/validates the YAML
def load_checklist(topic_id: str) -> DisclosureChecklist
def analyze_disclosure(topic_id: str, report_text: str) -> dict:
    """Keyword+section heuristic coverage per item (mirror dd_checklist.analyze),
    coverage % per pillar, mandatory-item gaps ranked first."""
def checklist_gap_report(topic_id: str, covered_ids: list[str]) -> dict
```

Seed the climate checklist with ~22 items (four pillars) synthesised from IFRS S2 + TCFD + SSE Guide No. 2 with legal_basis citations per item.

**Tool surface:** extend `dd_checklist_tool.py` with `checklist_kind: "disclosure"` + `topic_id`, or a `framework_assess` action — pick `dd_checklist_tool` (closest surface). CLI: `impact-vision dd disclosure climate --report report.txt`.

**Tests:** YAML schema validation; pillar enum; analyze finds seeded phrases; mandatory-first ranking; unknown topic error.

**Effort:** M.

#### I3 — China SSE/SZSE jurisdiction pack + disclosure-obligation determiner

**Pain point:** P16 — FY2025 sustainability reports for mandated issuers were due 2026-04-30; no open tooling exists; directly relevant to the HK/Greater-China user base.

**Backing modules (extend):** `impact/engagements/regulatory.py` (8 jurisdiction profiles + SFDR/UK SDR classifier pattern), `impact/regulatory_calendar.py`, `impact/standards_registry.py`.

**Work:**
1. Add a 9th jurisdiction profile `CN` to `engagements/regulatory.py` covering SSE Self-Regulatory Guideline No. 14 (6 chapters / 63 articles, effective 2024-05-01) + Preparation Guides No. 1–5 (Feb 2025, revised Jan 2026) + the SZSE twin.
2. Obligation determiner:

```python
def classify_cn_disclosure(listing_venue: Literal["sse_main", "star", "szse_main", "chinext", "bse"],
                           index_membership: list[str],   # "sse180","star50","szse100","chinext_index"
                           dual_listed_overseas: bool) -> dict:
    """mandatory | voluntary + deadline (FY reports due Apr 30 following year)
    + Article 7 exemption note + citations."""
```

3. Data file `data/cn_sse_topics.yaml`: the **21 topics** with `topic_id, name_zh, name_en, dimension (E/S/G), articles, mandatory: bool, preparation_guide: int|null` — feeds I1 (topic universe), I2 (checklists), I4 (content index).
4. `regulatory_calendar.py`: CN deadlines (Apr-30 annual cycle).
5. i18n: add zh strings via the existing `data/i18n/` convention.

**Tool surface:** `engagement_suite` regulatory actions `classify_cn | cn_topics`. CLI parity with existing `framework` subcommands.

**Tests:** determiner truth table (index member → mandatory; dual-listed → mandatory; plain ChiNext → voluntary); 21 topics load; calendar entries; zh i18n keys resolve.

**Effort:** M.

#### I4 — Content-index generator + report completeness + pre-publication QA

**Pain point:** P16/P2 — regulators and readers want a topic→article→chapter index ("对标索引", SSE art. 57; same shape as a GRI content index / ESRS index); reports ship without a completeness check.

**Backing modules (extend):** `impact/engagements/reporting_studio.py`, `impact/concordance.py`, I2, I3.

**Work — extend `engagements/reporting_studio.py`:**

```python
def build_content_index(framework: Literal["sse_g14", "gri", "esrs", "issb"],
                        covered: dict[str, str]   # topic/standard id -> report chapter
                        ) -> dict:
    """Rows: {topic, requirement ref (article/disclosure id), chapter, status:
    disclosed|partially|omitted(reason required)}. Sources: I3 topic data for
    sse_g14; frameworks/gri.py standards for gri; esrs datapoints for esrs;
    concordance for cross-framework 'also satisfies' column."""

def completeness_check(framework: str, covered: dict) -> dict:
    """% complete, mandatory gaps (blocking), encouraged gaps (advisory)."""

def prepublication_qa(report_sections: dict) -> list[dict]:
    """Checklist items {item, basis, priority: blocker|high|advisory}:
    mandatory topics covered, every quantitative claim has a MetricRecord,
    every claim passed greenwashing review (delegate to greenwashing_reviewer),
    comparative period present, methodology stated, content index present.
    Reuse the reporting-studio approval state machine: QA blockers prevent
    transition to 'approved'."""
```

**Tool surface:** `engagement_suite` reporting actions `content_index | completeness | prepublication_qa`.

**Tests:** index rows for each framework source; omission requires reason; blocker prevents approval transition (state-machine test); GRI index golden fixture.

**Effort:** M.

#### I5 — Calculator extensions with versioned factors (Scope-1 mass balance, 15 Scope-3 categories, energy tce, water)

**Pain point:** P16 — our `climate_accounting.py` covers Scope 1/2 (emission-factor method); OHESG's calculators encode additional regulator-published formulas worth having, each with factor provenance.

**Backing modules (extend):** `impact/climate_accounting.py`, `impact/emission_factors.py` (multi-revision factors + uncertainty — put ALL new constants here as revisions, never inline).

**Work:**
1. `climate_accounting.py` additions:

```python
def scope1_mass_balance(inputs: list[dict], outputs: list[dict], gwp: str = "AR6") -> dict:
    """E = [Σ(M_in×CC_in) − Σ(M_out×CC_out)] × 44/12 × GWP; per-stream table."""
def scope3_estimate(categories: dict[int, dict]) -> dict:
    """All 15 GHG-Protocol Scope-3 categories (1-8 upstream, 9-15 downstream),
    activity×factor per category, roll-up with per-category method note."""
def energy_to_tce(energy_lines: list[dict]) -> dict:
    """GB/T 2589-2020: k_i = NCV_i / 29307.6 kJ/kgce; clean-energy share;
    intensity per revenue/output."""
def water_balance(withdrawals: list[dict], discharge: float) -> dict:
    """withdrawal=Σsources; consumption=withdrawal−discharge; conventional vs
    non-conventional split (reclaimed/rain/desalinated/mine); reuse rate; intensity."""
```

2. `emission_factors.py`: new factor revisions with citations — IPCC AR6 GWPs (CO2=1, CH4=28, N2O=273, SF6=23,500), purchased-heat default 0.11 tCO2/GJ, MEE China grid factors (latest published year), GB/T 2589-2020 NCV table (~25 fuels). Every calculator output embeds `formula`, `factors_used` (id+revision), `sources` — consistent with the audit-trail ethos.

**Tool surface:** the existing climate tool surface gains actions `scope1_mass_balance | scope3 | energy_tce | water`.

**Tests (`tests/test_climate_calculators.py`):** worked examples per formula (hand-computed fixtures); factor-revision pinning (changing a revision changes output + provenance string); Scope-3 category enum completeness (15); clean-energy share; water non-conventional rule.

**Effort:** M.

#### I6 — Standard-article modality model + mandatory-gap scan

**Pain point:** P16/P1 — storing standards at article level tagged shall/encouraged/neutral enables automated "mandatory gap" scans (SSE: 49 of 63 articles binding); generalises to any standard.

**Backing modules (extend):** `impact/standards_registry.py`.

**Work:** add to `standards_registry.py`:

```python
class StandardArticle(BaseModel):
    standard_id: str; article_id: str; chapter: str
    text_summary: str                    # our own summary — do not embed full
                                         # regulation text verbatim
    modality: Literal["shall", "encouraged", "neutral"]
    topics: list[str]

def load_articles(standard_id: str) -> list[StandardArticle]   # data/standard_articles/<id>.yaml
def mandatory_gap_scan(standard_id: str, covered_article_ids: list[str]) -> dict
```

Seed `data/standard_articles/sse_g14.yaml` (63 article summaries with modality; write summaries, not verbatim text). CLI: `impact-vision framework scan --mandatory-only`.

**Tests:** modality counts (49/7/7 for sse_g14); gap scan; registry linkage.

**Effort:** S.

### Track J — LP DDQ Auto-Responder (P1)

#### J1 — ILPA DDQ 2.0 + PRI 2026 auto-responder

**Pain point:** P13 — 87% of PE funds receive ILPA-framework DDQs; ILPA ESG section now syncs with the PRI LP RI DDQ; 2025 added the PRI/ILPA/iCI Climate Module; PRI's 2026 reset (~39–40 mandatory indicators, reporting window May 6 – Jul 29 2026) ended partial reporting.

**Backing modules (extend):** `tools/impact/lp_ddq_export_tool.py` (ILPA/GIIN/EDCI/SFDR export exists), `impact/lp_narrative.py` (audit-friendly narrative + Q&A constrained to verified data), `impact/portfolio_nlq.py` (`ApprovedDataPolicy`), `impact/concordance.py`.

**New file:** `src/openharness/impact/ddq_responder.py`

```python
class DDQQuestion(BaseModel):
    qid: str; framework: Literal["ilpa_ddq2", "pri_2026", "ilpa_climate_module"]
    section: str; text: str
    answer_kind: Literal["narrative", "metric", "boolean", "attachment"]
    maps_to: list[str]           # concept_ids / module outputs that can answer it

def load_ddq_bank() -> list[DDQQuestion]     # data/ddq_bank.yaml — question texts
                                             # paraphrased/summarised, with source refs
def draft_answers(questions: list[DDQQuestion], fund_profile: dict,
                  records: list[MetricRecord], policy: ApprovedDataPolicy) -> list[dict]:
    """Per question: drafted answer + evidence citations (ONLY approved/verified
    data via ApprovedDataPolicy — same constraint as portfolio_nlq),
    confidence, 'needs_human' flag for narrative answers. Narrative drafting
    delegates to lp_narrative generators; metric answers come from
    concordance-mapped MetricRecords. Every draft enters the evidence_workflow
    review queue — nothing ships unreviewed (AI-governance rule)."""

def export_ddq(answers, format: Literal["xlsx", "docx_outline", "json"]) -> ...
    # xlsx via the existing lp_ddq_export writer
```

Seed `data/ddq_bank.yaml` with ~80 questions: ILPA DDQ 2.0 ESG section, PRI 2026 mandatory indicator set (~40), climate module (~15) — paraphrase question intents with `source` refs rather than reproducing proprietary text verbatim.

**Tool surface:** new registered tool `ddq_responder` (actions `list_questions | draft | export | review_status`). Register per §0.1.

**Tests (`tests/test_ddq_responder.py`):** bank loads/validates; metric question answered only from approved records (policy violation → refusal); narrative flagged `needs_human`; drafts enter review queue; xlsx export reuses existing writer; unanswered questions surface as gaps not fabrications.

**Effort:** L. **Second-highest differentiation after G1 — directly converts existing trust infrastructure into hours saved per fundraise.**

---

## 10. Build order & dependency graph

Dependencies: **B3 → {B2, B4, F2, H1, H3, I4, J1}** (concordance underpins everything comparable); **C4 → G3**; **G2 → G3**; **I3 → {I1 topics, I2 seeds, I4, I6 data}**; **B2 → F2**.

| Phase | Items | Rationale |
|---|---|---|
| 0 | **H0** tool-count reconciliation | Precondition for adding tools cleanly |
| 1 | **A1** SFDR 2.0 · **B3** concordance | Highest-demand currency item + the unlock for everything comparable |
| 2 | **G1** contribution engine · **G2** term-sheet targets | The two highest-differentiation practice-gap items (P3, P5); no external deps |
| 3 | **B2** iXBRL export · **B4** comparability score | Machine-readable deliverable + LP-facing index (need B3) |
| 4 | **I3** CN pack · **I1** materiality wizard · **I2** disclosure checklists | OHESG wave core — China deadline cycle recurs every April |
| 5 | **B1** ISSA 5000 readiness | Assurance goes global 2026-12-15 |
| 6 | **J1** DDQ auto-responder · **H1** ask-once dedup | Burden-reduction pair (P4, P13); need B3 |
| 7 | **A2 / A3 / A4** currency batch · **I4 / I5 / I6** reporting-suite completion | Low-risk data-heavy batch |
| 8 | **C1** carbon-credit integrity · **C4** KPI credibility · **G3** carry/SAFI | Integrity + impact-linked economics chain |
| 9 | **H2** survey delivery · **E1** regulatory radar · **E2** eval harness | Delivery channel + governed-AI pair |
| 10 | **F1** portfolio report · **F2** LP data-room · **H3** CIDS export | Comparability payoff (needs B2/B3/B4) |
| 11 | **D1 / D2 / D3** social frontier · **C2 / C3** nature · **E3** dMRV · **F3** context layer | Frontier / polish |

Each phase ends with: tool registration checklist (§0.1), `scripts/check_imports.py --all`, `ruff check src/`, full `pytest tests/ -q`, README tool-table update (if tools added), `CHANGELOG.md` entry. Version bumps: one minor version per phase (0.16.0 onward), stories in `CHANGELOG.md` only (per `CLAUDE.md` doc conventions).

## 11. Wave-level acceptance criteria

- **Comparability:** a 3-company portfolio exports to ISSB and ESRS from one input set; comparability index reported; ≥120 concordance concepts.
- **Machine-readable:** flagship assessment emits structurally valid iXBRL (ESRS + ISSB elements) and xBRL-JSON; CIDS JSON-LD export validates.
- **Practice gaps:** a fund can (a) pre-register contribution claims and get a monitored-in-last-12m percentage, (b) block a deal gate on missing impact-target conditions, (c) draft an ILPA/PRI DDQ from approved data only.
- **Currency:** SFDR 2.0, simplified ESRS, CA SB 253/261, ISSB tracker, CN SSE/SZSE all carry `as_of ≥ 2026` + citations; every proposed-law output is labelled.
- **Integrity:** carbon credits, biodiversity credits, and SLB/SLL KPIs receive credibility scores, never counts.
- **Burden:** ask-once dedup demonstrably reduces field count on the 2-pack fixture and reports estimated hours saved.
- **Governed AI:** DDQ drafts and radar findings pass through the evidence-workflow review queue; the model card is populated from a reproducible eval run; consent gates all survey dispatches.
- **No regressions:** import smoke + ruff + full pytest green; zero forked modules; tool count consistent across `__all__`, registry, README.

## 12. Sources

**Practitioner pain points:** GIIN State of the Market 2025 (<https://thegiin.org/publication/research/state-of-the-market-2025-trends-performance-and-allocations/>); BlueMark Making the Mark 2025 + 2026 (<https://bluemark.co/making-the-mark-2025/>, <https://bluemark.co/making-the-mark-2026/>); Impact Frontiers Investor Contribution 2.0 (<https://impactfrontiers.org/discussion-ic-20>) and Impact Performance Reporting Norms (<https://impactfrontiers.org/norms/>); OPIM Principle 3 practices (<https://www.impactprinciples.org/common-and-emerging-practices/principle3/>); 60 Decibels 2025 Year in Review (<https://60decibels.com/insights/2025-year-in-review/>); UpMetrics portfolio data-collection playbook (<https://blog.upmetrics.com/portfolio-company-data-collection-playbook>); IPA WhatsApp surveys (<https://poverty-action.org/whatsapp-surveys-public-good-remote-low-cost-and-scalable-research>).

**Regulatory (dated facts):** SFDR 2.0 proposal 2025-11-20 (Sidley <https://www.sidley.com/en/insights/newsupdates/2025/11/sfdr--five-key-takeaways-from-the-european-commissions-proposal>; Morgan Lewis <https://www.morganlewis.com/pubs/2025/12/sfdr-2-0-eu-commission-proposes-overhaul-of-sfdr-regime>); Omnibus I in OJ 2026-02-26 (Latham <https://www.lw.com/en/insights/eu-sustainability-state-of-play-the-conclusion-of-the-sustainability-omnibus-process>; KPMG <https://kpmg.com/xx/en/our-insights/ifrg/2025/esrs-eu-omnibus.html>); UK SDR (<https://www.fca.org.uk/firms/climate-change-and-sustainable-finance/sustainability-disclosure-requirements-sdr-regime>); ISSB adoption (<https://www.ifrs.org/news-and-events/news/2025/06/ifrs-foundation-publishes-jurisdictional-profiles-issb-standards/>); ISSB↔TNFD nature standard (<https://www.ifrs.org/news-and-events/news/2025/11/issb-welcomes-tnfd-support-nature-related-disclosure/>); CA SB 253/261 CARB regs 2026-02-26 (<https://www.gtlaw.com/en/insights/2026/3/carb-adopts-initial-climate-disclosure-reporting-regulations-to-implement-sb-253-and-sb-261>); TNFD Status Report 2025 (<https://tnfd.global/wp-content/uploads/2025/09/250918_TNFD-Status-Report_DIGITAL.pdf>).

**Methods & standards:** IFVI value factors (<https://ifvi.org/>); Common Impact Data Standard v3.2 (<https://www.commonapproach.org/common-impact-data-standard-version-3-2/>); ILPA DDQ (<https://ilpa.org/resources-tools/resource-library/due-diligence-questionnaire/>); PRI 2026 reporting framework (<https://www.danesmeadadvisory.com/news/pri-2026-reporting-framework>); impact-linked carry (<https://www.trowers.com/insights/2025/october/impact-linked-carried-interest>); SAFI (<https://impactalpha.com/the-brief-meet-safi-the-newest-tool-in-impact-linked-finance/>); ICVCM CCPs (<https://icvcm.org/>); IAPB/BCA biodiversity-credit principles; SBTN (<https://sciencebasedtargetsnetwork.org/>); Shift 19 Just Transition metrics.

**OHESG ecosystem (Track I inspiration):** report.ohesg.com — rules browser, 21-topic atlas, 6 interactive calculators, double-materiality drag-and-drop method, framework/content-index pages, power-generation carbon-market digest (<https://report.ohesg.com/>, /rules/, /topics/climate/, /tools/, /method/, /framework/); tool.ohesg.com 34-tool toolbox incl. double-materiality app (<https://tool.ohesg.com/>, </material/>); underlying regulation: SSE Self-Regulatory Guideline No. 14 — Sustainability Report (Trial) + Preparation Guides No. 1–5 (sse.com.cn), MEE 2026 power-generation GHG accounting/verification specs (mee.gov.cn). Repo assets already present: `data/raw/ohesg_toolbox/*.json`, `src/openharness/impact/toolbox/ingest.py`, `src/openharness/tools/impact/esg_toolbox_tool.py`, `docs/esg-toolbox-implementation-plan.md`.

---

*End of implementation plan. Strategy context: `docs/roadmap-v6.md`. Engineering conventions: `CLAUDE.md`.*
