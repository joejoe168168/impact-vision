# Roadmap intelligence update — July 2026

**Date:** 2026-07-03
**Purpose:** Delta since `roadmap-v6.md` (written 2026-05-29). This is a
watch-list of regulatory / market developments verified by web research in
early July 2026, plus the knowledge-base corrections already applied to the
codebase. Feed these into v6 track prioritisation (or a future v7) — this doc
does not change the v6 plan itself.

**Status (2026-07-03):** the four actionable items below are **shipped**:
SFDR 2.0 category preview (`classify_sfdr2_category` + `framework_assess`
`sfdr2`), AI-estimate provenance flag (`MetricRecord.is_estimate` +
disclosure badge through LP Q&A and evidence chains), EDCI-first collection
scaffold (`edci_core` data-request pack + `sector='edci'` questionnaire
template), and the milestone watch-list (`regulatory_calendar` `watchlist`
action). The ESRS 2.0 datapoint refresh (§1.2) and ISSB nature Practice
Statement mapping (§1.3) stay deferred until the final texts land.

---

## 1. What moved since roadmap-v6 was written

### 1.1 SFDR 2.0 — Council position agreed (2026-06-24)

The Council of the EU settled its negotiating position on the SFDR recast:

- The **three product categories survive** (Sustainable / new Art 7
  Transition / ESG Basics) with the ≥70% portfolio threshold.
- The Council wants a **24-month implementation period** (Commission proposed
  18), pushing likely application to **mid/late 2029**.
- New flexibility relevant to PE/VC: the Commission would be empowered to set
  **phase-in rules for the 70% threshold** (capital deployed over time) and
  **permitted deviations for delayed divestment from illiquid assets** — both
  directly relevant to closed-ended impact funds.
- Trilogue with Parliament expected **late 2026**.

**Roadmap effect:** v6 Track A's Art 8/9 → new-label mapper stays P0, but the
mapper should model the *Council* variant (phase-in + illiquid-asset
deviations) as scenario toggles, since final text is ~2027.
*(Shipped 2026-07-03 as `classify_sfdr2_category` — Council flexibility is
modelled as caveats, never as a pass.)*

### 1.2 ESRS 2.0 — draft delegated act consulted, adoption imminent

- Public feedback on the **revised (simplified) ESRS** and the **new VSME
  standard** ran 2026-05-06 → 2026-06-03; formal adoption expected
  **Q3/Q4 2026**, mandatory from **FY2027** with voluntary early adoption for
  FY2026.
- Mandatory datapoints cut ~60% (total ~70%); the 2 cross-cutting +
  10 topical architecture is retained (our `frameworks/esrs.py` topic
  structure stays valid; datapoint lists will slim).
- **VSME doubles as the value-chain cap**: suppliers under 1,000 employees may
  refuse information requests beyond VSME scope. Our data-room /
  investee-collection flows should respect that ceiling when generating
  requests to small portfolio companies.
- CSRD amendments must be transposed by member states by **2027-03-19**;
  CSDDD transposition remains **2028-07-26**, application **2029-07-26**.

**Roadmap effect:** schedule the `esrs.py` + `csrd_wizard.py` refresh for
right after the delegated act is published (late 2026) rather than now — the
final datapoint list is what matters.

### 1.3 ISSB — IFRS S2 targeted amendments + nature guidance pipeline

- The ISSB issued **targeted amendments to IFRS S2** easing Scope 3 /
  financed-emissions requirements (GICS relief, optionality on certain
  categories).
- **Nature-related disclosure guidance** is coming as an **IFRS Practice
  Statement** — exposure draft due **October 2026**. It layers guidance on
  S1/S2 rather than creating a new standard, and will likely draw on
  TNFD LEAP.

**Roadmap effect:** v6 Track C nature work (SBTN target-setter, biodiversity
credit screen) should anticipate mapping to the Practice Statement once the
ED lands; watch October 2026.

### 1.4 US — SEC rescission proposed, California is the operative regime

- The SEC **formally proposed rescinding** the 2024 climate-disclosure rule
  on **2026-05-29** (it never took effect).
- **California SB 253**: first Scope 1+2 reports due **2026-11-10** (CARB
  deferral); Scope 3 phases in from 2027.
- **SB 261** enforcement remains **stayed by a Ninth Circuit injunction** —
  monitor the appeal.

**Codebase state:** `engagements/regulatory.py`, `roadmap_v2.py`, bundle and
tool descriptions now reference California SB 253/261 instead of the SEC rule.

### 1.5 Market signal — ILPA "institutionalisation gap" + AI harmonisation

- ILPA's **"Impact Investing: The State of Market Institutionalization"**
  (Jan 2026) confirms institutional allocators now supply **over half of new
  impact capital**, but flags fragmented / non-comparable IMM data as the top
  structural barrier — LPs fall back on proxies and qualitative diligence.
  LPs converge on **OPIM + IRIS+ + Impact Frontiers Five Dimensions** (all of
  which we implement) but *measurement and reporting* remain non-standard.
- WEF (Apr 2026) frames **AI-driven classification/harmonisation** — matching
  indicators by meaning, flagging double-counting — as the practical answer to
  comparability, rather than forcing metric uniformity.
- PE workflow tooling is consolidating around the **ILPA EDCI metric set** as
  the automation target, with a hard norm: **AI-estimated figures must be
  labelled as estimates with methodology disclosed** (greenwashing exposure
  otherwise).

**Roadmap effect:** strongly validates v6 Track F (comparability engine) and
Track E (governed AI). Two concrete additions worth ticketing:

1. **Estimate provenance flag** *(shipped 2026-07-03)* — `MetricRecord`
   carries `estimation_methodology` + a serialized `is_estimate` flag, and
   the "ESTIMATE — methodology" badge travels through LP Q&A answers and 5D
   evidence chains. Extending the badge to the HTML/XLSX report templates is
   the follow-up.
2. **EDCI-first collection default** *(shipped 2026-07-03)* — the
   `edci_core` data-request pack and the `sector='edci'` questionnaire
   template scaffold collection from the EDCI metric set, with an
   estimate-labelling guardrail on every field.

### 1.6 Dates to watch *(shipped 2026-07-03 — `regulatory_calendar` `watchlist` action)*

| Date | Event |
|---|---|
| 2026-09-27 | ECGT Directive (EU) 2024/825 applies — generic green claims banned |
| 2026-10 | ISSB nature Practice Statement exposure draft |
| ~2026 Q4 | Revised ESRS + VSME delegated acts adopted |
| 2026-11-10 | First California SB 253 Scope 1+2 reports due |
| 2026-12-15 | ISSA 5000 effective (periods beginning on/after) |
| 2026-12-30 | EUDR obligations apply (large/medium operators) |
| 2027-01-01 | Revised ESRS applies (FY2027, early adoption FY2026) |
| 2027-03-19 | CSRD (as amended) member-state transposition deadline |
| 2028-07-26 | CSDDD member-state transposition deadline |
| 2029-07-26 | CSDDD applies to first wave (>5,000 employees + €1.5B) |
| ~2029 | SFDR 2.0 application (Council: 24-month implementation) |

## 2. Knowledge-base corrections applied in this pass (2026-07-03)

- **NGFS scenario catalogue** (`climate_scenario.py`): retired *Divergent Net
  Zero* (dropped by NGFS in Phase IV), added *Low Demand* (Phase V), renamed
  the too-little-too-late scenario to its NGFS name *Fragmented World*.
  Legacy keys still resolve via aliases. Also fixed a weighting bug where
  duplicate holding names corrupted portfolio exposure maths.
- **SFDR status note** (`frameworks/sfdr_pai.py`): documented that Article
  6/8/9 + PAI remain law in force and SFDR 2.0 is pipeline (~2029).
- **ESRS status note** (`frameworks/esrs.py`): documented Omnibus I scope and
  the ESRS 2.0 / VSME value-chain-cap timeline.
- **US profile** (`roadmap_v2.py`, `engagements/regulatory.py`, toolbox
  descriptions): replaced stale SEC-climate-rule references with California
  SB 253/261.
- **ESG toolbox inference** (`toolbox/workflow.py`): word-boundary matching so
  short terms ("eu", "uk", "ev", "mine") no longer false-positive inside words
  like "entrepreneur"; removed dead `_FIELD_SUGGESTION_RULES`.
