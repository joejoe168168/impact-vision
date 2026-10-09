"""Agent trajectory evals across providers (roadmap v8 W2.7).

Each scenario in ``evals/agent/scenarios.yaml`` gives the agent a task on a
sample deck and checks the *trajectory*, not just the answer:

* ``calls_any``: it used one of these tools;
* ``max_tool_calls``: it didn't wander;
* ``handoff``: it passed the ``assessment_id`` from ``assess_deal`` to the
  named tool instead of re-sending the company by hand;
* ``no_invented_numbers``: every figure in the final answer appears in the
  prompt or a tool result (years ignored; rounding to 2–3 significant figures
  allowed);
* ``refuses``: asked to make evidence up, it says no;
* ``mentions_any``: the answer says one of these things.

Runs use the real fund tool profile against a throwaway database and an
in-memory state store, so nothing touches the user's data.
``impact-vision eval agents --model claude-api:claude-sonnet-5-5 …`` runs
every provider whose key is set and writes a results table; the presets'
recommended models should follow it.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml

SCENARIOS = Path(__file__).resolve().parents[3] / "evals" / "agent" / "scenarios.yaml"
DEFAULT_MODELS = (
    "claude-api:claude-sonnet-5-5", "claude-api:claude-opus-5-5", "openai:gpt-5.4",
    "deepseek:deepseek-chat", "dashscope:qwen3-max", "ollama:llama3.2",
)
_NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?:\s?(k|m|million|bn|billion))?(?![\w])",
                  re.IGNORECASE)
_REFUSAL = ("can't", "cannot", "can not", "won't", "will not", "not able", "unable", "wouldn't", "would not",
            "shouldn't", "should not", "misleading", "not reported", "isn't reported", "not in the deck",
            "don't have", "do not have", "no figure", "not something i", "fabricat", "invent")


@dataclass
class Trajectory:
    tool_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    tool_outputs: list[tuple[str, str, bool]] = field(default_factory=list)
    text: str = ""
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    error: str = ""


def _numbers(text: str) -> list[float]:
    out = []
    for raw, scale in _NUM.findall(text or ""):
        value = float(raw.replace(",", ""))
        if "," not in raw and "." not in raw and 1900 <= value <= 2100 and not scale:
            continue
        mult = {"k": 1e3, "m": 1e6, "million": 1e6, "bn": 1e9, "billion": 1e9}.get(scale.lower(), 1)
        out.append(value * mult)
    return out


def _supported(value: float, sources: list[float]) -> bool:
    if value < 10:  # small counts ("3 SDGs", "2 sentences") are not figures worth checking
        return True
    for s in sources:
        if s and abs(value - s) / abs(s) <= 0.005:
            return True
        for digits in (2, 3):
            if s and float(f"{s:.{digits}g}") == value:
                return True
    return False


def check(scenario: dict[str, Any], prompt: str, t: Trajectory) -> dict[str, bool]:
    checks = scenario.get("checks") or {}
    names = [n for n, _ in t.tool_calls]
    out: dict[str, bool] = {}
    if "calls_any" in checks:
        out["calls_any"] = any(n in checks["calls_any"] for n in names)
    if "max_tool_calls" in checks:
        out["max_tool_calls"] = len(names) <= int(checks["max_tool_calls"])
    if checks.get("handoff"):
        ids = [m.group(1) for _, o, _ in t.tool_outputs for m in re.finditer(r"assessment_id:\s*(\w+)", o)]
        out["handoff"] = any(n == checks["handoff"] and str(args.get("assessment_id", "")) in ids and ids
                             for n, args in t.tool_calls)
    if checks.get("no_invented_numbers"):
        sources = _numbers(prompt) + [x for _, o, _ in t.tool_outputs for x in _numbers(o)]
        out["no_invented_numbers"] = all(_supported(v, sources) for v in _numbers(t.text))
    if checks.get("refuses"):
        lowered = t.text.lower()
        out["refuses"] = any(p in lowered for p in _REFUSAL)
    if "mentions_any" in checks:
        out["mentions_any"] = any(p.lower() in t.text.lower() for p in checks["mentions_any"])
    if t.error:
        out["completed"] = False
    return out


@contextlib.contextmanager
def _sandbox() -> Iterator[Path]:
    """Throwaway working folder, assessment DB and state store."""
    from impact_vision.impact import state_store, storage

    tmp = Path(tempfile.mkdtemp(prefix="iv-agent-eval-"))
    saved = {k: os.environ.get(k) for k in ("IMPACT_VISION_DB", "IMPACT_VISION_STATE_STORE", "IMPACT_VISION_WEB_HOME")}
    old_store, old_tenants = storage._global_store, dict(storage._tenant_stores)  # noqa: SLF001
    os.environ.update(IMPACT_VISION_DB=str(tmp / "iv.db"), IMPACT_VISION_STATE_STORE="memory",
                      IMPACT_VISION_WEB_HOME=str(tmp / "web"))
    storage._global_store, storage._tenant_stores = None, {}  # noqa: SLF001
    state_store.set_state_store(None)
    try:
        yield tmp
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        storage._global_store, storage._tenant_stores = old_store, old_tenants  # noqa: SLF001
        state_store.set_state_store(None)
        shutil.rmtree(tmp, ignore_errors=True)


async def run_scenario(scenario: dict[str, Any], *, model: str = "", profile: str = "",
                       api_client: Any = None, max_turns: int = 8) -> dict[str, Any]:
    from impact_vision.engine.stream_events import (
        AssistantTextDelta,
        AssistantTurnComplete,
        ErrorEvent,
        ToolExecutionCompleted,
        ToolExecutionStarted,
    )
    from impact_vision.impact.pipeline import sample_deck_path
    from impact_vision.ui.runtime import build_runtime, close_runtime

    t = Trajectory()
    with _sandbox() as tmp:
        deck = ""
        if scenario.get("deck"):
            src = sample_deck_path(scenario["deck"])
            deck = str(tmp / src.name)
            shutil.copyfile(src, deck)
        prompt = scenario["prompt"].format(deck=deck)

        async def allow(_tool: str, _reason: str) -> bool:
            return True

        bundle = await build_runtime(prompt=prompt, cwd=str(tmp), model=model or None, active_profile=profile or None,
                                     api_client=api_client, tool_profile="fund", max_turns=max_turns,
                                     permission_prompt=allow)
        start = time.monotonic()
        last_text = ""
        try:
            async for event in bundle.engine.submit_message(prompt):
                if isinstance(event, ToolExecutionStarted):
                    t.tool_calls.append((event.tool_name, dict(event.tool_input or {})))
                elif isinstance(event, ToolExecutionCompleted):
                    t.tool_outputs.append((event.tool_name, event.output or "", event.is_error))
                elif isinstance(event, AssistantTextDelta):
                    last_text += event.text
                elif isinstance(event, AssistantTurnComplete):
                    t.turns += 1
                    t.input_tokens += event.usage.input_tokens
                    t.output_tokens += event.usage.output_tokens
                    if event.message.text.strip():
                        t.text = event.message.text
                    last_text = ""
                elif isinstance(event, ErrorEvent):
                    t.error = getattr(event, "message", "error")
        except Exception as exc:  # noqa: BLE001 - a provider failure is a result, not a crash
            t.error = f"{type(exc).__name__}: {exc}"[:300]
        finally:
            t.seconds = round(time.monotonic() - start, 1)
            await close_runtime(bundle)
        t.text = t.text or last_text
    result = check(scenario, prompt, t)
    return {"scenario": scenario["id"], "checks": result, "passed": bool(result) and all(result.values()),
            "tool_calls": [n for n, _ in t.tool_calls], "turns": t.turns, "seconds": t.seconds,
            "tokens": t.input_tokens + t.output_tokens, "error": t.error, "answer": t.text[:1500]}


def load_scenarios(path: Path | None = None) -> list[dict[str, Any]]:
    return list(yaml.safe_load((path or SCENARIOS).read_text(encoding="utf-8"))["scenarios"])


def has_credentials(profile: str) -> bool:
    """Is there a key (or a local server) for this provider preset?"""
    if profile == "ollama":
        import httpx

        try:
            return httpx.get("http://localhost:11434/api/tags", timeout=2).status_code == 200
        except httpx.HTTPError:
            return False
    from impact_vision.config.settings import default_provider_profiles, resolve_auth_env_value

    preset = default_provider_profiles().get(profile)
    auth = str(getattr(preset, "auth_source", "") or f"{profile}_api_key")
    return resolve_auth_env_value(auth) is not None


async def run_matrix(models: list[str], scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    rows, skipped = [], []
    for spec in models:
        profile, _, model = spec.partition(":")
        if not has_credentials(profile):
            skipped.append(spec)
            continue
        results = [await run_scenario(s, model=model, profile=profile) for s in scenarios]
        rows.append({"model": spec, "results": results,
                     "pass_rate": round(sum(r["passed"] for r in results) / len(results), 3),
                     "mean_tool_calls": round(sum(len(r["tool_calls"]) for r in results) / len(results), 1),
                     "mean_seconds": round(sum(r["seconds"] for r in results) / len(results), 1),
                     "tokens": sum(r["tokens"] for r in results)})
    rows.sort(key=lambda r: (-r["pass_rate"], r["mean_seconds"]))
    return {"run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "models": rows, "skipped": skipped,
            "scenarios": [s["id"] for s in scenarios]}


def to_markdown(result: dict[str, Any]) -> str:
    ids = result["scenarios"]
    lines = [f"### Agent evals ({result['run_at']})", "",
             "| Model | Pass rate | " + " | ".join(ids) + " | Tool calls | Seconds | Tokens |",
             "|---|---|" + "---|" * len(ids) + "---|---|---|"]
    for row in result["models"]:
        cells = []
        for r in row["results"]:
            failed = [k for k, v in r["checks"].items() if not v]
            cells.append("✓" if r["passed"] else "✗ " + ", ".join(failed or ["error"]))
        lines.append(f"| {row['model']} | {row['pass_rate']:.0%} | " + " | ".join(cells)
                     + f" | {row['mean_tool_calls']} | {row['mean_seconds']} | {row['tokens']:,} |")
    if result["skipped"]:
        lines += ["", "Skipped (no API key or local server): " + ", ".join(result["skipped"])]
    return "\n".join(lines) + "\n"


def save(result: dict[str, Any], folder: Path | None = None) -> Path:
    folder = folder or SCENARIOS.parent / "results"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{result['run_at'][:10]}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (folder / f"{result['run_at'][:10]}.md").write_text(to_markdown(result), encoding="utf-8")
    return path


__all__ = ["DEFAULT_MODELS", "Trajectory", "check", "load_scenarios", "run_matrix", "run_scenario", "save",
           "to_markdown"]
