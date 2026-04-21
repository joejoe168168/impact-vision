"""Theory-of-Change graph builder.

Renders a `TheoryOfChange` (defined in `frameworks.theory_of_change`) as a
Mermaid diagram so it can be embedded directly into Markdown reports, IC
memos, and the LP letter pack.

The flow follows the GIIN ToC convention:

    Inputs → Activities → Outputs → Outcomes → Impact

with optional cross-references to SDG targets and IRIS+ metric IDs as
node-level annotations.
"""
from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, Field


class ToCNode(BaseModel):
    """Generic node — kept lightweight so any caller can populate it."""
    id: str
    label: str
    kind: str   # "input" | "activity" | "output" | "outcome" | "impact" | "assumption" | "risk"
    iris_metrics: list[str] = Field(default_factory=list)
    sdg_targets: list[str] = Field(default_factory=list)


class ToCEdge(BaseModel):
    src: str
    dst: str
    label: str = ""


class TheoryOfChangeGraph(BaseModel):
    name: str
    nodes: list[ToCNode]
    edges: list[ToCEdge]
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


_KIND_STYLE: dict[str, tuple[str, str]] = {
    # (mermaid shape open/close, css class for theming)
    "input":     ("([", "])"),
    "activity":  ("[",  "]"),
    "output":    ("[/", "/]"),
    "outcome":   ("[\\", "\\]"),
    "impact":    ("{{", "}}"),
    "assumption":(">", "]"),
    "risk":      ("[(",  ")]"),
}


def _mermaid_node(node: ToCNode) -> str:
    open_, close_ = _KIND_STYLE.get(node.kind, ("[", "]"))
    label = node.label.replace('"', "'")
    annotation_parts: list[str] = []
    if node.iris_metrics:
        annotation_parts.append("IRIS+ " + ", ".join(node.iris_metrics[:3]))
    if node.sdg_targets:
        annotation_parts.append("SDG " + ", ".join(node.sdg_targets[:3]))
    if annotation_parts:
        label = f"{label}<br/><i>{' | '.join(annotation_parts)}</i>"
    return f'    {node.id}{open_}"{label}"{close_}'


def render_mermaid(graph: TheoryOfChangeGraph, *, direction: str = "LR") -> str:
    """Render the ToC graph as a Mermaid `flowchart` block."""
    lines = [f"flowchart {direction}"]
    by_kind: dict[str, list[ToCNode]] = {}
    for n in graph.nodes:
        by_kind.setdefault(n.kind, []).append(n)

    # Render nodes grouped by kind for readability
    for kind in ("input", "activity", "output", "outcome", "impact", "assumption", "risk"):
        nodes = by_kind.get(kind, [])
        if not nodes:
            continue
        lines.append(f"    %% {kind.upper()}")
        for n in nodes:
            lines.append(_mermaid_node(n))

    for e in graph.edges:
        if e.label:
            lines.append(f'    {e.src} -->|{e.label}| {e.dst}')
        else:
            lines.append(f"    {e.src} --> {e.dst}")

    if graph.assumptions:
        lines.append("    %% Assumptions")
        for i, a in enumerate(graph.assumptions):
            lines.append(f'    A{i}>"Assumption: {a}"]')
    if graph.risks:
        lines.append("    %% Risks")
        for i, r in enumerate(graph.risks):
            lines.append(f'    R{i}[("Risk: {r}")]')

    return "\n".join(lines)


def render_markdown(graph: TheoryOfChangeGraph, *, direction: str = "LR") -> str:
    """Wrap the Mermaid render in a fenced Markdown block."""
    body = render_mermaid(graph, direction=direction)
    return f"### Theory of Change — {graph.name}\n\n```mermaid\n{body}\n```\n"


def build_simple_chain(
    name: str,
    chain: Iterable[tuple[str, str]],
    assumptions: list[str] | None = None,
    risks: list[str] | None = None,
) -> TheoryOfChangeGraph:
    """Helper: build a linear ToC from a `[(kind, label), ...]` sequence.

    Example::

        build_simple_chain("Off-grid solar", [
            ("input",   "EUR 5M growth equity"),
            ("activity","Deploy 50,000 home solar kits in East Africa"),
            ("output",  "50,000 households connected"),
            ("outcome", "Reduced kerosene usage; 4h/day extra study time"),
            ("impact",  "Improved health, education, climate (SDG 7, 13)"),
        ])
    """
    nodes: list[ToCNode] = []
    edges: list[ToCEdge] = []
    last_id: str | None = None
    for i, (kind, label) in enumerate(chain):
        node_id = f"N{i}"
        nodes.append(ToCNode(id=node_id, label=label, kind=kind))
        if last_id:
            edges.append(ToCEdge(src=last_id, dst=node_id))
        last_id = node_id
    return TheoryOfChangeGraph(
        name=name, nodes=nodes, edges=edges,
        assumptions=assumptions or [], risks=risks or [],
    )
