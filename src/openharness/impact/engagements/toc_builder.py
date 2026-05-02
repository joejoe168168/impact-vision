"""Theory of Change builder + KPI framework generator (roadmap-v4 Track 2).

Wraps the existing :mod:`openharness.impact.toc_graph` (Mermaid renderer)
and the :mod:`openharness.impact.frameworks.cross_reference` crosswalk so
consultants can:

* Assemble an interactive ToC canvas with every GIIN block
  (problem → stakeholders → inputs → activities → outputs → outcomes →
  impact) plus assumptions and risks (Track 2.1).
* Run the logic-chain validator that flags missing assumptions, weak causal
  links, unmeasured outcomes, and risk blind spots (Track 2.2).
* Generate a KPI framework bound to IRIS+ / SDG / GRI / EDCI / ESRS / ISSB /
  TCFD / SFDR PAI (Track 2.3) by reusing the v3 ``metric_recommender``
  scoring logic and then lifting each pick through the cross-reference map
  to every other framework.

The builder deliberately **does not** call an LLM. Track 8 (copilot) is the
home for that. The Sopact counter-response in ``docs/roadmap-v4.md`` §1.3
requires that the consultant's judgement be legible: every outcome,
assumption and KPI pick in this module is either data-driven (rules-based
validator) or explicit consultant input.
"""

from __future__ import annotations

import secrets
from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel, Field, computed_field

from openharness.impact.frameworks.cross_reference import (
    CrossReference,
    lookup_by_iris,
)
from openharness.impact.toc_graph import (
    TheoryOfChangeGraph,
    ToCEdge,
    ToCNode,
    render_markdown,
    render_mermaid,
)


ToCNodeKind = Literal[
    "problem",
    "stakeholder",
    "input",
    "activity",
    "output",
    "outcome",
    "impact",
    "assumption",
    "risk",
]


# ---------------------------------------------------------------- canvas model


class ToCCanvasNode(BaseModel):
    """Node on the consultant-facing ToC canvas (Track 2.1).

    The canvas is a *superset* of :class:`~openharness.impact.toc_graph.ToCNode`:
    it carries metadata the canonical graph doesn't need (stakeholder group,
    AI confidence, consultant override flag) so we can wire into the
    validator and the Sopact-counter audit story.
    """

    model_config = {"validate_assignment": True}

    node_id: str = Field(default_factory=lambda: f"n_{secrets.token_hex(4)}")
    kind: ToCNodeKind
    label: str
    description: str = ""
    stakeholder_group: str = ""
    equity_segment: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    iris_metrics: list[str] = Field(default_factory=list)
    sdg_targets: list[str] = Field(default_factory=list)
    ai_confidence: float = 0.0
    consultant_reviewed: bool = False


class ToCCanvasEdge(BaseModel):
    """Causal link between two ToC nodes."""

    edge_id: str = Field(default_factory=lambda: f"e_{secrets.token_hex(4)}")
    src: str
    dst: str
    label: str = ""
    """Short verb capturing the causal relationship (e.g. 'enables')."""
    causal_strength: Literal["strong", "moderate", "weak", "untested"] = "untested"
    evidence_refs: list[str] = Field(default_factory=list)


class ToCAssumption(BaseModel):
    """Explicit assumption attached to one or more edges / nodes."""

    assumption_id: str = Field(default_factory=lambda: f"as_{secrets.token_hex(4)}")
    statement: str
    attaches_to: list[str] = Field(default_factory=list)
    """IDs of edges / nodes this assumption conditions."""
    evidence_refs: list[str] = Field(default_factory=list)
    tested: bool = False


class ToCRisk(BaseModel):
    """Risk that could break the causal chain."""

    risk_id: str = Field(default_factory=lambda: f"r_{secrets.token_hex(4)}")
    statement: str
    likelihood: Literal["low", "medium", "high"] = "medium"
    severity: Literal["low", "medium", "high"] = "medium"
    mitigation: str = ""


class ToCCanvas(BaseModel):
    """The consultant's ToC canvas (Track 2.1).

    The canvas is JSON-serialisable and stable across the engagement. The
    mermaid render goes through :mod:`openharness.impact.toc_graph` so the
    v3 report engine keeps rendering everything.
    """

    canvas_id: str = Field(default_factory=lambda: f"toc_{secrets.token_hex(6)}")
    name: str
    engagement_id: str = ""
    problem_statement: str = ""
    nodes: list[ToCCanvasNode] = Field(default_factory=list)
    edges: list[ToCCanvasEdge] = Field(default_factory=list)
    assumptions: list[ToCAssumption] = Field(default_factory=list)
    risks: list[ToCRisk] = Field(default_factory=list)
    equity_notes: str = ""
    """Free-text equity & inclusion lens (Track 2.6 stub)."""
    created_at: str = Field(default_factory=lambda: _now())
    updated_at: str = Field(default_factory=lambda: _now())
    version: int = 1

    @computed_field  # type: ignore[prop-decorator]
    @property
    def review_coverage_pct(self) -> float:
        """Fraction of nodes the consultant has reviewed."""
        if not self.nodes:
            return 0.0
        reviewed = sum(1 for node in self.nodes if node.consultant_reviewed)
        return round(reviewed / len(self.nodes), 3)

    def node_index(self) -> dict[str, ToCCanvasNode]:
        return {n.node_id: n for n in self.nodes}


# --------------------------------------------------------------- draft helpers


def draft_toc_from_intake(
    *,
    name: str,
    engagement_id: str = "",
    problem_statement: str = "",
    stakeholders: Iterable[str] | None = None,
    inputs: Iterable[str] | None = None,
    activities: Iterable[str] | None = None,
    outputs: Iterable[str] | None = None,
    outcomes: Iterable[str] | None = None,
    impact: Iterable[str] | None = None,
    assumptions: Iterable[str] | None = None,
    risks: Iterable[str] | None = None,
    ai_confidence: float = 0.6,
) -> ToCCanvas:
    """Deterministically draft a ToC canvas from structured intake inputs.

    This is the "AI-draft" hook — Track 8 will later feed this from an LLM,
    but the data path must exist now so the validator has something to
    validate and the override audit trail has something to override.

    Every node generated here carries ``consultant_reviewed=False`` and
    ``ai_confidence=ai_confidence`` so the workspace can require an explicit
    consultant review before the ToC is considered ready.
    """
    canvas = ToCCanvas(
        name=name,
        engagement_id=engagement_id,
        problem_statement=problem_statement,
    )

    def _add_block(kind: ToCNodeKind, items: Iterable[str] | None) -> list[ToCCanvasNode]:
        out: list[ToCCanvasNode] = []
        for label in items or []:
            if not label or not str(label).strip():
                continue
            node = ToCCanvasNode(
                kind=kind,
                label=str(label).strip(),
                ai_confidence=ai_confidence,
            )
            canvas.nodes.append(node)
            out.append(node)
        return out

    stakeholder_nodes = _add_block("stakeholder", stakeholders)
    input_nodes = _add_block("input", inputs)
    activity_nodes = _add_block("activity", activities)
    output_nodes = _add_block("output", outputs)
    outcome_nodes = _add_block("outcome", outcomes)
    impact_nodes = _add_block("impact", impact)

    # Link the layers sequentially (input→activity→output→outcome→impact).
    canvas.edges.extend(_chain_edges(input_nodes, activity_nodes, label="funds"))
    canvas.edges.extend(_chain_edges(activity_nodes, output_nodes, label="produces"))
    canvas.edges.extend(_chain_edges(output_nodes, outcome_nodes, label="drives"))
    canvas.edges.extend(_chain_edges(outcome_nodes, impact_nodes, label="contributes to"))

    # Stakeholders attach to outcomes (who benefits from which outcome).
    if stakeholder_nodes and outcome_nodes:
        for stakeholder in stakeholder_nodes:
            for outcome in outcome_nodes:
                canvas.edges.append(
                    ToCCanvasEdge(
                        src=outcome.node_id,
                        dst=stakeholder.node_id,
                        label="benefits",
                        causal_strength="untested",
                    )
                )

    for statement in assumptions or []:
        if str(statement).strip():
            canvas.assumptions.append(ToCAssumption(statement=str(statement).strip()))
    for statement in risks or []:
        if str(statement).strip():
            canvas.risks.append(ToCRisk(statement=str(statement).strip()))

    canvas.updated_at = _now()
    return canvas


def _chain_edges(
    sources: list[ToCCanvasNode],
    targets: list[ToCCanvasNode],
    *,
    label: str = "",
) -> list[ToCCanvasEdge]:
    """Connect every source to every target (fan-out) when both sets exist."""
    if not sources or not targets:
        return []
    edges: list[ToCCanvasEdge] = []
    for src in sources:
        for dst in targets:
            edges.append(
                ToCCanvasEdge(
                    src=src.node_id,
                    dst=dst.node_id,
                    label=label,
                    causal_strength="untested",
                )
            )
    return edges


# ---------------------------------------------------------------- render hooks


def to_graph(canvas: ToCCanvas) -> TheoryOfChangeGraph:
    """Convert a canvas into a v3 :class:`TheoryOfChangeGraph` for Mermaid."""
    nodes: list[ToCNode] = []
    # toc_graph recognises a fixed set of kinds; map canvas-only kinds onto
    # the closest supported one.
    kind_map: dict[ToCNodeKind, str] = {
        "problem": "activity",  # problems render as an activity-shaped box
        "stakeholder": "activity",
        "input": "input",
        "activity": "activity",
        "output": "output",
        "outcome": "outcome",
        "impact": "impact",
        "assumption": "assumption",
        "risk": "risk",
    }
    for n in canvas.nodes:
        nodes.append(
            ToCNode(
                id=n.node_id,
                label=n.label,
                kind=kind_map.get(n.kind, "activity"),
                iris_metrics=list(n.iris_metrics),
                sdg_targets=list(n.sdg_targets),
            )
        )
    edges = [ToCEdge(src=e.src, dst=e.dst, label=e.label) for e in canvas.edges]
    return TheoryOfChangeGraph(
        name=canvas.name,
        nodes=nodes,
        edges=edges,
        assumptions=[a.statement for a in canvas.assumptions],
        risks=[r.statement for r in canvas.risks],
    )


def render_canvas_mermaid(canvas: ToCCanvas, *, direction: str = "LR") -> str:
    """Render the canvas as a Mermaid flowchart (reuses toc_graph)."""
    return render_mermaid(to_graph(canvas), direction=direction)


def render_canvas_markdown(canvas: ToCCanvas, *, direction: str = "LR") -> str:
    """Render the canvas as a Markdown+Mermaid block (reuses toc_graph)."""
    return render_markdown(to_graph(canvas), direction=direction)


# ------------------------------------------------------------- logic validator


class ToCValidationFinding(BaseModel):
    """One validator finding."""

    finding_id: str = Field(default_factory=lambda: f"f_{secrets.token_hex(4)}")
    code: str
    severity: Literal["info", "low", "medium", "high", "critical"] = "medium"
    message: str
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    suggestion: str = ""


class ToCValidationReport(BaseModel):
    """Output of :func:`validate_toc_canvas`."""

    canvas_id: str
    findings: list[ToCValidationFinding] = Field(default_factory=list)
    checked_rules: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def severity_counts(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for f in self.findings:
            counts[f.severity] += 1
        return dict(counts)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_passing(self) -> bool:
        """True when there are no high/critical findings."""
        return not any(f.severity in {"high", "critical"} for f in self.findings)


_VALIDATION_RULES = [
    "has_problem_statement",
    "has_outcomes",
    "has_impact",
    "outcomes_have_inputs",
    "outcomes_have_indicators",
    "outcomes_have_assumptions",
    "causal_strength",
    "stakeholders_identified",
    "equity_lens",
    "risks_have_mitigations",
    "assumption_tested",
]


def validate_toc_canvas(canvas: ToCCanvas) -> ToCValidationReport:
    """Run the rules-based logic-chain validator (Track 2.2).

    Rules implemented (all deterministic):

    * **has_problem_statement** — problem is described.
    * **has_outcomes / has_impact** — the ToC actually goes past outputs.
    * **outcomes_have_inputs** — every outcome traces back to an input
      through the edge graph (weak causal link finder).
    * **outcomes_have_indicators** — every outcome has at least one IRIS+
      metric mapped (roadmap §1 "unmeasured outcomes" flag).
    * **outcomes_have_assumptions** — every outcome is conditioned by at
      least one explicit assumption.
    * **causal_strength** — edges still marked ``untested`` are surfaced
      as low-severity findings the consultant should validate.
    * **stakeholders_identified** — at least one stakeholder node exists.
    * **equity_lens** — equity_notes or equity_segment fields are populated.
    * **risks_have_mitigations** — every risk carries a mitigation plan.
    * **assumption_tested** — flags assumptions where ``tested=False``.
    """
    findings: list[ToCValidationFinding] = []
    index = canvas.node_index()

    if not canvas.problem_statement.strip():
        findings.append(
            ToCValidationFinding(
                code="has_problem_statement",
                severity="high",
                message="ToC has no problem statement.",
                suggestion="Capture the root problem the intervention is trying to solve.",
            )
        )

    outcomes = [n for n in canvas.nodes if n.kind == "outcome"]
    impacts = [n for n in canvas.nodes if n.kind == "impact"]
    inputs = [n for n in canvas.nodes if n.kind == "input"]
    stakeholders = [n for n in canvas.nodes if n.kind == "stakeholder"]

    if not outcomes:
        findings.append(
            ToCValidationFinding(
                code="has_outcomes",
                severity="critical",
                message="ToC has no outcomes — only outputs or activities.",
                suggestion="Describe the behavioural / systemic change the outputs are meant to drive.",
            )
        )
    if not impacts:
        findings.append(
            ToCValidationFinding(
                code="has_impact",
                severity="high",
                message="ToC has no long-term impact statement.",
                suggestion="State the long-term systemic or beneficiary-level change being targeted.",
            )
        )

    # Build a reverse graph for backwards reachability (outcome → input).
    predecessors: dict[str, set[str]] = defaultdict(set)
    for edge in canvas.edges:
        predecessors[edge.dst].add(edge.src)

    def _reaches_input(start_id: str) -> bool:
        if not inputs:
            return False
        input_ids = {n.node_id for n in inputs}
        visited: set[str] = set()
        stack = [start_id]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            if cur in input_ids:
                return True
            stack.extend(predecessors.get(cur, set()))
        return False

    assumption_attach_index: dict[str, list[ToCAssumption]] = defaultdict(list)
    for assumption in canvas.assumptions:
        for target in assumption.attaches_to:
            assumption_attach_index[target].append(assumption)

    for outcome in outcomes:
        if not _reaches_input(outcome.node_id):
            findings.append(
                ToCValidationFinding(
                    code="outcomes_have_inputs",
                    severity="high",
                    message=f"Outcome '{outcome.label}' does not trace back to any input.",
                    node_ids=[outcome.node_id],
                    suggestion="Add the causal edges back through outputs → activities → inputs.",
                )
            )
        if not outcome.iris_metrics:
            findings.append(
                ToCValidationFinding(
                    code="outcomes_have_indicators",
                    severity="medium",
                    message=f"Outcome '{outcome.label}' has no IRIS+ metric mapped.",
                    node_ids=[outcome.node_id],
                    suggestion="Run generate_kpi_framework and attach at least one metric.",
                )
            )
        if not assumption_attach_index.get(outcome.node_id):
            findings.append(
                ToCValidationFinding(
                    code="outcomes_have_assumptions",
                    severity="medium",
                    message=f"Outcome '{outcome.label}' is not conditioned by any assumption.",
                    node_ids=[outcome.node_id],
                    suggestion="Add at least one explicit assumption (behavioural, contextual, or counterfactual).",
                )
            )

    for edge in canvas.edges:
        if edge.causal_strength == "untested":
            findings.append(
                ToCValidationFinding(
                    code="causal_strength",
                    severity="low",
                    message=(
                        f"Causal link between '{index[edge.src].label if edge.src in index else edge.src}'"
                        f" and '{index[edge.dst].label if edge.dst in index else edge.dst}' is untested."
                    ),
                    edge_ids=[edge.edge_id],
                    suggestion="Mark as strong/moderate/weak after the workshop, or add evidence_refs.",
                )
            )

    if not stakeholders:
        findings.append(
            ToCValidationFinding(
                code="stakeholders_identified",
                severity="medium",
                message="No stakeholder groups captured in the ToC.",
                suggestion="Add at least one stakeholder node covering beneficiaries and decision-makers.",
            )
        )

    equity_signal = bool(canvas.equity_notes.strip()) or any(
        n.equity_segment.strip() for n in canvas.nodes
    )
    if not equity_signal:
        findings.append(
            ToCValidationFinding(
                code="equity_lens",
                severity="medium",
                message="Equity & inclusion lens not applied (no equity_notes or equity_segment set).",
                suggestion="Identify excluded groups and whose voice is missing from the data.",
            )
        )

    for risk in canvas.risks:
        if not risk.mitigation.strip():
            findings.append(
                ToCValidationFinding(
                    code="risks_have_mitigations",
                    severity="medium" if risk.severity != "high" else "high",
                    message=f"Risk '{risk.statement}' has no mitigation plan.",
                    suggestion="Document the planned mitigation and owner.",
                )
            )

    for assumption in canvas.assumptions:
        if not assumption.tested and not assumption.evidence_refs:
            findings.append(
                ToCValidationFinding(
                    code="assumption_tested",
                    severity="low",
                    message=f"Assumption '{assumption.statement}' is untested and has no evidence.",
                    suggestion="Link to an evidence source or mark it as a research question.",
                )
            )

    return ToCValidationReport(
        canvas_id=canvas.canvas_id,
        findings=findings,
        checked_rules=list(_VALIDATION_RULES),
    )


# --------------------------------------------------------- KPI framework build


class KPIFrameworkEntry(BaseModel):
    """One KPI mapped across frameworks (Track 2.3)."""

    kpi_id: str = Field(default_factory=lambda: f"kpi_{secrets.token_hex(4)}")
    outcome_node_id: str = ""
    outcome_label: str = ""
    iris_metric_id: str
    iris_metric_name: str
    score: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    sdg_goals: list[int] = Field(default_factory=list)
    frameworks: dict[str, list[str]] = Field(default_factory=dict)
    """Mapping ``framework -> list of codes`` pulled from cross_reference."""
    concept: str = ""
    """Human-readable cross-reference concept name."""


class KPIFramework(BaseModel):
    """Engagement-scoped KPI framework (Track 2.3)."""

    framework_id: str = Field(default_factory=lambda: f"kf_{secrets.token_hex(6)}")
    engagement_id: str = ""
    canvas_id: str = ""
    sector: str = ""
    geography: str = ""
    impact_themes: list[str] = Field(default_factory=list)
    sdg_goals: list[int] = Field(default_factory=list)
    entries: list[KPIFrameworkEntry] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: _now())
    version: int = 1
    locked: bool = False
    """Once locked, downstream consumers treat the framework as immutable."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def metric_count(self) -> int:
        return len(self.entries)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def framework_coverage(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for entry in self.entries:
            for name, codes in entry.frameworks.items():
                if codes:
                    counts[name] += 1
        return dict(counts)


def generate_kpi_framework(
    *,
    canvas: ToCCanvas,
    sector: str = "",
    geography: str = "",
    impact_themes: Iterable[str] | None = None,
    sdg_goals: Iterable[int] | None = None,
    per_outcome_limit: int = 3,
    include_core_set: bool = True,
    engagement_id: str = "",
) -> KPIFramework:
    """Map every ToC outcome to IRIS+ metrics + cross-framework codes.

    This function is graceful when the IRIS+ catalog has not been loaded
    (common in CI / test envs): it falls back to the outcome's existing
    ``iris_metrics`` list so the generator is always deterministic.
    Framework expansion uses
    :func:`openharness.impact.frameworks.cross_reference.lookup_by_iris`,
    which is always available (pure Python, no external data).
    """
    themes = [t.strip() for t in (impact_themes or []) if str(t).strip()]
    goals = list(sdg_goals or [])

    outcomes = [n for n in canvas.nodes if n.kind == "outcome"]
    framework = KPIFramework(
        engagement_id=engagement_id or canvas.engagement_id,
        canvas_id=canvas.canvas_id,
        sector=sector,
        geography=geography,
        impact_themes=themes,
        sdg_goals=goals,
    )

    catalog_store = _try_load_metric_store()

    for outcome in outcomes:
        chosen: list[tuple[str, str, float, list[str], list[int]]] = []
        # Outcome-level explicit picks from the canvas take priority — they
        # represent consultant-curated choices.
        for metric_id in outcome.iris_metrics[:per_outcome_limit]:
            chosen.append(
                (metric_id, metric_id, 4.0, ["canvas:explicit"], [])
            )

        if catalog_store is not None and len(chosen) < per_outcome_limit:
            recs = _rank_metrics(
                store=catalog_store,
                outcome_text=f"{outcome.label} {outcome.description}",
                themes=themes,
                goals=goals,
                include_core_set=include_core_set,
            )
            for metric, score, reasons in recs[: per_outcome_limit - len(chosen)]:
                chosen.append(
                    (
                        metric.id,
                        metric.name,
                        score,
                        reasons,
                        list(metric.sdg_goals[:5]),
                    )
                )

        for metric_id, metric_name, score, reasons, sdgs in chosen:
            xrefs: list[CrossReference] = lookup_by_iris(metric_id)
            frameworks_map: dict[str, list[str]] = {}
            concept = ""
            for xref in xrefs:
                concept = concept or xref.concept
                for name, codes in (
                    ("gri", xref.gri),
                    ("edci", xref.edci),
                    ("sasb", xref.sasb_codes),
                    ("tcfd", xref.tcfd),
                    ("issb", xref.issb),
                    ("esrs", list(getattr(xref, "esrs", []) or [])),
                    ("tnfd", xref.tnfd),
                    ("pcaf", xref.pcaf),
                    ("eu_taxonomy", xref.eu_taxonomy),
                    ("cdp", xref.cdp),
                    ("sbti", xref.sbti),
                ):
                    if codes:
                        frameworks_map.setdefault(name, [])
                        for code in codes:
                            if code not in frameworks_map[name]:
                                frameworks_map[name].append(code)
                if xref.sfdr_pai:
                    frameworks_map.setdefault("sfdr_pai", [])
                    for num in xref.sfdr_pai:
                        code = f"PAI#{num}"
                        if code not in frameworks_map["sfdr_pai"]:
                            frameworks_map["sfdr_pai"].append(code)

            framework.entries.append(
                KPIFrameworkEntry(
                    outcome_node_id=outcome.node_id,
                    outcome_label=outcome.label,
                    iris_metric_id=metric_id,
                    iris_metric_name=metric_name,
                    score=round(score, 2),
                    reasons=list(reasons),
                    sdg_goals=list(sdgs),
                    frameworks=frameworks_map,
                    concept=concept,
                )
            )

    return framework


def lock_kpi_framework(framework: KPIFramework) -> KPIFramework:
    """Return a copy of the framework with ``locked=True`` and a bumped version."""
    return framework.model_copy(update={"locked": True, "version": framework.version + 1})


def _try_load_metric_store():  # type: ignore[no-untyped-def]
    """Attempt to load the IRIS+ catalog; swallow errors for CI / offline use."""
    try:
        from openharness.impact.database import get_metric_store

        store = get_metric_store()
        if store.count == 0:
            return None
        return store
    except Exception:  # noqa: BLE001 - validator must remain deterministic
        return None


def _rank_metrics(*, store, outcome_text: str, themes, goals, include_core_set):  # type: ignore[no-untyped-def]
    from openharness.impact.gap_analysis import CORE_METRIC_SET_IDS

    scores: dict[str, float] = defaultdict(float)
    reasons: dict[str, list[str]] = defaultdict(list)
    metric_map: dict[str, object] = {}

    if include_core_set:
        for metric_id in CORE_METRIC_SET_IDS:
            metric = store.get(metric_id)
            if metric is None:
                continue
            scores[metric.id] += 2.0
            reasons[metric.id].append("core-set")
            metric_map[metric.id] = metric

    for theme in themes:
        for metric in store.filter_by_theme(theme):
            scores[metric.id] += 3.0
            reasons[metric.id].append(f"theme:{theme}")
            metric_map[metric.id] = metric

    for goal in goals:
        for metric in store.filter_by_sdg(goal):
            scores[metric.id] += 2.5
            reasons[metric.id].append(f"sdg:{goal}")
            metric_map[metric.id] = metric

    if outcome_text.strip():
        for metric in store.search(outcome_text, limit=40):
            scores[metric.id] += 1.5
            reasons[metric.id].append("outcome-keyword")
            metric_map[metric.id] = metric

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        (metric_map[metric_id], score, list(dict.fromkeys(reasons[metric_id])))
        for metric_id, score in ranked
    ]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "KPIFramework",
    "KPIFrameworkEntry",
    "ToCAssumption",
    "ToCCanvas",
    "ToCCanvasEdge",
    "ToCCanvasNode",
    "ToCNodeKind",
    "ToCRisk",
    "ToCValidationFinding",
    "ToCValidationReport",
    "draft_toc_from_intake",
    "generate_kpi_framework",
    "lock_kpi_framework",
    "render_canvas_markdown",
    "render_canvas_mermaid",
    "to_graph",
    "validate_toc_canvas",
]
