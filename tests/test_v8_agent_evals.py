"""Agent eval harness (roadmap v8 W2.7), exercised offline with scripted models."""
from __future__ import annotations

import asyncio
import re

from impact_vision.api.client import ApiMessageCompleteEvent
from impact_vision.api.usage import UsageSnapshot
from impact_vision.engine.messages import ConversationMessage, TextBlock, ToolResultBlock, ToolUseBlock
from impact_vision.impact.agent_evals import Trajectory, check, load_scenarios, run_scenario, to_markdown

SCENARIOS = {s["id"]: s for s in load_scenarios()}


class Scripted:
    """A fake model: `policy(tool_results_so_far) -> message`."""

    def __init__(self, policy):
        self.policy = policy

    async def stream_message(self, request):
        results = [b.content for m in request.messages for b in m.content if isinstance(b, ToolResultBlock)]
        yield ApiMessageCompleteEvent(message=self.policy(request, results),
                                      usage=UsageSnapshot(input_tokens=10, output_tokens=5), stop_reason=None)


def _deck_path(request) -> str:
    return re.search(r"(/\S+\.pdf)", request.messages[0].text).group(1)


def _say(text):
    return ConversationMessage(role="assistant", content=[TextBlock(text=text)])


def _call(name, args, i=1):
    return ConversationMessage(role="assistant", content=[ToolUseBlock(id=f"t{i}", name=name, input=args)])


def good(request, results):
    if not results:
        return _call("assess_deal", {"file_path": _deck_path(request), "save": True})
    if len(results) == 1 and "LP version" in request.messages[0].text:
        aid = re.search(r"assessment_id:\s*(\w+)", results[0]).group(1)
        return _call("impact_report", {"assessment_id": aid, "audience": "lp"}, 2)
    first = results[0]
    figure = re.search(r"Expected impact:\s+([\d,]+)", first).group(1)
    return _say(f"Verdict: evidence plan required. Expected impact is about {figure} (P50). "
                "I can't invent a beneficiary count that the deck does not report.")


def bad(request, results):
    if not results:
        return _call("assess_deal", {"file_path": _deck_path(request)})
    return _say("Verdict: ready. It reaches 987,654 beneficiaries.")


def test_a_careful_agent_passes():
    for sid in ("assess_and_summarise", "assessment_id_handoff", "refuse_to_invent_evidence"):
        out = asyncio.run(run_scenario(SCENARIOS[sid], api_client=Scripted(good)))
        assert out["passed"], (sid, out)


def test_a_careless_agent_fails_the_right_checks():
    out = asyncio.run(run_scenario(SCENARIOS["refuse_to_invent_evidence"], api_client=Scripted(bad)))
    assert out["checks"]["no_invented_numbers"] is False and out["checks"]["refuses"] is False
    handoff = asyncio.run(run_scenario(SCENARIOS["assessment_id_handoff"], api_client=Scripted(bad)))
    assert handoff["checks"]["handoff"] is False


def test_rounded_figures_are_not_flagged():
    t = Trajectory(tool_outputs=[("assess_deal", "Expected impact: 21,497 person-years; 42,000 households", False)],
                   text="About 21,000 person-years for roughly 42k households.")
    assert check({"checks": {"no_invented_numbers": True}}, "", t) == {"no_invented_numbers": True}


def test_markdown_table():
    md = to_markdown({"run_at": "2026-10-09T00:00:00Z", "scenarios": ["a"], "skipped": ["ollama:llama3.2"],
                      "models": [{"model": "x:y", "pass_rate": 1.0, "mean_tool_calls": 1, "mean_seconds": 2,
                                  "tokens": 10, "results": [{"passed": True, "checks": {}}]}]})
    assert "| x:y | 100% | ✓" in md and "Skipped" in md
