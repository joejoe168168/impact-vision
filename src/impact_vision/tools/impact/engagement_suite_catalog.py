"""Action catalogue for ``engagement_suite`` (v7 W1.5).

The suite takes a free-form ``payload`` per action, so an LLM had no schema
to follow and typos were silently ignored. This module derives, from the
dispatcher's own source, which payload keys each action reads — so the
catalogue can never drift from the implementation — and groups actions by
area for the tool description and the ``describe`` action.
"""

from __future__ import annotations

import ast
import inspect
from functools import lru_cache

# Area → actions (the order shown to users).
ACTION_AREAS: dict[str, tuple[str, ...]] = {
    "Data room (collect investee data)": (
        "build_request_pack", "score_completeness", "rollup_entities", "build_coaching_cards",
        "dedupe_requests", "answer_fanout", "burden_report", "build_lp_dataroom",
    ),
    "Value creation & benchmarks": (
        "benchmark", "list_giin_benchmarks", "giin_kpi_context", "risk_rating", "value_plan",
        "business_case", "run_scenario", "supply_hotspots", "contribution_scorecard",
    ),
    "Reporting studio": (
        "list_report_templates", "build_report", "transition_report", "decide_claim",
        "executive_deck", "public_microsite", "rewrite_audiences", "content_index",
        "completeness", "prepublication_qa", "materiality_assess", "materiality_matrix",
        "materiality_config",
    ),
    "Training & coaching": (
        "training_plan", "list_workshop_packs", "workshop_pack", "coaching_card",
        "learning_loop", "issue_badge",
    ),
    "Website & lead capture": (
        "diagnostic_questions", "score_diagnostic", "gallery", "playbooks", "playbook_page",
        "benchmark_teaser", "capture_lead", "upload_demo", "partner_mode",
    ),
    "AI copilot governance": ("run_challenge", "safe_answer", "extract_meeting_notes"),
    "Regulatory workbench": (
        "list_jurisdictions", "assess_eu_omnibus_scope", "classify_sfdr", "classify_uk_sdr",
        "schedule_deadlines", "regulator_narrative", "sfdr_v2_migrate", "classify_cn",
        "cn_topics",
    ),
    "Assurance (3-pillar verification bundle)": (
        "build_mandate_pack", "build_practice_pack", "build_reporting_pack",
        "build_assurance_bundle", "verify_assurance_bundle", "readiness_badge",
        "issue_verifier_token", "list_verifier_marketplace",
    ),
}


def _actions_in_test(node: ast.AST) -> set[str] | None:
    """Actions named by ``action == "x"`` / ``action in {...}`` tests."""
    if not isinstance(node, ast.Compare) or not isinstance(node.left, ast.Name):
        return None
    if node.left.id != "action" or len(node.ops) != 1:
        return None
    op, right = node.ops[0], node.comparators[0]
    if isinstance(op, ast.Eq) and isinstance(right, ast.Constant) and isinstance(right.value, str):
        return {right.value}
    if isinstance(op, ast.In) and isinstance(right, (ast.Set, ast.Tuple, ast.List)):
        return {e.value for e in right.elts if isinstance(e, ast.Constant)}
    return None


def _returns(stmts: list[ast.stmt]) -> bool:
    return bool(stmts) and isinstance(stmts[-1], (ast.Return, ast.Raise))


class _KeyCollector:
    """Collect ``p.get("k")`` / ``p["k"]`` keys per action.

    Walks the dispatcher statement by statement, narrowing the set of actions
    that can reach each line: inside ``if action == "x"`` only ``x``; after an
    ``if action in {...}: return``, everything but those actions; in an
    ``a if action == "x" else b`` expression, ``x`` for ``a`` and the rest for ``b``.
    """

    def __init__(self, all_actions: set[str]) -> None:
        self.all_actions = all_actions
        self.keys: dict[str, set[str]] = {}
        self.open: set[str] = set()  # actions that pass the whole payload on
        self.sinks: dict[str, str] = {}  # action -> callee receiving the whole payload
        self.imports: dict[str, str] = {}  # local name -> "module:attr"

    def _record(self, scope: set[str], key: str | None) -> None:
        for action in scope:
            if key is None:
                self.open.add(action)
            else:
                self.keys.setdefault(action, set()).add(key)

    def stmts(self, stmts: list[ast.stmt], scope: set[str]) -> None:
        scope = set(scope)
        for stmt in stmts:
            if isinstance(stmt, ast.ImportFrom) and stmt.module:
                for alias in stmt.names:
                    self.imports[alias.asname or alias.name] = f"{stmt.module}:{alias.name}"
            if not scope:
                return
            if isinstance(stmt, ast.If):
                actions = _actions_in_test(stmt.test)
                if actions is not None:
                    inner = scope & actions
                    self.stmts(stmt.body, inner)
                    self.stmts(stmt.orelse, scope - actions)
                    if _returns(stmt.body):
                        scope -= actions
                    continue
                self.expr(stmt.test, scope)
                self.stmts(stmt.body, scope)
                self.stmts(stmt.orelse, scope)
                continue
            for child in ast.iter_child_nodes(stmt):
                if isinstance(child, ast.stmt):
                    self.stmts([child], scope)
                else:
                    self.expr(child, scope)

    def expr(self, node: ast.AST, scope: set[str]) -> None:
        if not scope:
            return
        if isinstance(node, ast.IfExp):
            actions = _actions_in_test(node.test)
            if actions is not None:
                self.expr(node.body, scope & actions)
                self.expr(node.orelse, scope - actions)
                return
        if isinstance(node, ast.Call):
            func = node.func
            passes_payload = any(
                isinstance(a, ast.Name) and a.id == "p" for a in node.args
            ) or any(
                k.arg is None and isinstance(k.value, ast.Name) and k.value.id == "p"
                for k in node.keywords
            )
            callee = func.value if (
                isinstance(func, ast.Attribute) and func.attr == "model_validate"
            ) else func
            if passes_payload and isinstance(callee, ast.Name):
                for action in scope:
                    self.sinks.setdefault(action, callee.id)
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "p"
                and func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                self._record(scope, str(node.args[0].value))
                for arg in node.args[1:]:
                    self.expr(arg, scope)
                return
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "p"
            and isinstance(node.slice, ast.Constant)
        ):
            self._record(scope, str(node.slice.value))
            return
        if isinstance(node, ast.Name) and node.id == "p" and isinstance(node.ctx, ast.Load):
            self._record(scope, None)  # bare payload passed to a model / function
            return
        for child in ast.iter_child_nodes(node):
            self.expr(child, scope)


@lru_cache(maxsize=1)
def payload_catalog() -> tuple[dict[str, tuple[str, ...]], frozenset[str]]:
    """Return ``(action -> payload keys, actions that accept any keys)``."""
    from impact_vision.tools.impact.engagement_suite_tool import EngagementSuiteTool

    import textwrap
    import typing

    from impact_vision.tools.impact.engagement_suite_tool import EngagementSuiteInput

    try:
        source = textwrap.dedent(inspect.getsource(EngagementSuiteTool._dispatch))
        func = ast.parse(source).body[0]
    except (OSError, TypeError, SyntaxError, IndexError):
        return {}, frozenset()
    all_actions = set(typing.get_args(EngagementSuiteInput.model_fields["action"].annotation))
    collector = _KeyCollector(all_actions)
    collector.stmts(func.body, all_actions)  # type: ignore[attr-defined]
    keys = {action: set(found) for action, found in collector.keys.items()}
    open_actions = set(collector.open)
    import impact_vision.tools.impact.engagement_suite_tool as suite_module

    for action, callee in collector.sinks.items():
        target = collector.imports.get(callee)
        if target is None and hasattr(suite_module, callee):
            obj = getattr(suite_module, callee)
            target = f"{getattr(obj, '__module__', '')}:{getattr(obj, '__name__', callee)}"
        fields = _callee_fields(target or "")
        if fields is not None:
            keys.setdefault(action, set()).update(fields)
            open_actions.discard(action)
    return (
        {action: tuple(sorted(found)) for action, found in keys.items()},
        frozenset(open_actions),
    )


def _callee_fields(target: str) -> set[str] | None:
    """Field / parameter names of ``module:attr`` (a pydantic model or function)."""
    if ":" not in target:
        return None
    import importlib

    module_name, attr = target.split(":", 1)
    try:
        obj = getattr(importlib.import_module(module_name), attr)
    except Exception:  # noqa: BLE001 - catalogue must never break the tool
        return None
    fields = getattr(obj, "model_fields", None)
    if isinstance(fields, dict):
        return set(fields)
    try:
        params = inspect.signature(obj).parameters.values()
    except (TypeError, ValueError):
        return None
    if any(p.kind is p.VAR_KEYWORD for p in params):
        return None
    return {p.name for p in params if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)}


def action_area(action: str) -> str:
    for area, actions in ACTION_AREAS.items():
        if action in actions:
            return area
    return "Other"


def describe(action: str | None = None) -> dict:
    """Catalogue for one action or for all, grouped by area."""
    keys, open_actions = payload_catalog()

    def entry(name: str) -> dict:
        return {
            "action": name,
            "area": action_area(name),
            "payload_keys": list(keys.get(name, ())),
            "accepts_other_keys": name in open_actions,
        }

    if action:
        return entry(action)
    return {
        area: [entry(name) for name in actions]
        for area, actions in ACTION_AREAS.items()
    }


def unknown_payload_keys(action: str, payload: dict) -> list[str]:
    """Payload keys the action never reads (likely typos)."""
    keys, open_actions = payload_catalog()
    if action in open_actions or action not in keys:
        return []
    allowed = set(keys[action])
    return sorted(k for k in payload if k not in allowed)
