# Agent evals

These evals check what the agent does, not just its answer. For each scenario
in `scenarios.yaml` they check:
- which tools the agent called and how many times;
- whether it passed `assessment_id` on to the next tool;
- whether every figure in its answer came from a tool result;
- whether it refuses to invent evidence.

```bash
export ANTHROPIC_API_KEY=… OPENAI_API_KEY=… DEEPSEEK_API_KEY=… DASHSCOPE_API_KEY=…
impact-vision eval agents                                    # every provider with a key set
impact-vision eval agents --model claude-api:claude-sonnet-5-5 --scenario refuse_to_invent_evidence
```

Each run uses a temporary working folder, database and state store, so your
own records are never touched. Results are written to `results/<date>.md` and
`.json`. The models each provider preset recommends should follow the
pass-rate table. Providers without a key (or Ollama without a running server)
are skipped and listed.

The harness itself is tested offline with scripted models
(`tests/test_v8_agent_evals.py`). Live runs cost API credits, so they are
not part of CI.
