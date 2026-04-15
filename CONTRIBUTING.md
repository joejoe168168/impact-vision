# Contributing to Impact Vision

Impact Vision is an open-source AI-powered impact measurement engine for VC and impact investment funds. Built on [OpenHarness](https://github.com/HKUDS/OpenHarness).

## Ways to Contribute

- **Standards & Data**: Add new ESG/sustainability framework modules, expand cross-reference mappings, or improve DD checklist questions
- **IRIS+ Coverage**: Improve metric parsing, add new Core Metric Sets, or enhance SDG mappings
- **Tools & Analysis**: Build new agent tools, improve scoring algorithms, or add report templates
- **Visual Output**: Enhance HTML report templates, Plotly charts, or Streamlit dashboard
- **Tests**: Add coverage for edge cases, framework modules, or tool integration
- **Documentation**: Improve guides, add examples, or translate content

## Development Setup

```bash
# Clone and install
git clone <repo-url> impact-vision
cd impact-vision
pip install -e ".[dev]"

# Place the IRIS+ catalog Excel in data/raw/
# Then load it:
python -m openharness catalog load
```

### Prerequisites

- Python 3.11+
- IRIS+ 5.3c Catalog Excel (from [GIIN IRIS+](https://iris.thegiin.org/))
- An LLM API key (Anthropic, OpenAI, or Ollama for local models)

## Running Tests

```bash
# Run all Impact Vision tests
python -m pytest tests/test_impact.py -v

# Run all tests (including OpenHarness core)
python -m pytest tests/ -v

# Lint
ruff check src/
```

## Project Structure

Key directories for contributors:

```
src/openharness/impact/           # Core impact engine (models, scoring, analysis)
src/openharness/impact/frameworks/ # ESG framework modules (add new frameworks here)
src/openharness/tools/impact/     # Agent tools (add new tools here)
src/openharness/dashboard/        # Streamlit dashboard
src/openharness/skills/bundled/content/ # Agent knowledge (markdown)
data/                             # DD checklist YAML, sample data
tests/test_impact.py              # Impact-specific tests
```

## Adding a New Framework

1. Create a module in `src/openharness/impact/frameworks/` (see `edci.py` as a template)
2. Define Pydantic models for the framework's metrics/standards
3. Implement `assess_*` and `get_*` functions
4. Add cross-references in `cross_reference.py` where applicable
5. Register in `frameworks/__init__.py`
6. Add handler in `tools/impact/framework_tool.py`
7. Write tests in `tests/test_impact.py`
8. Update the system prompt in `prompts/system_prompt.py`

## Adding DD Checklist Questions

Edit `data/dd_checklist.yaml` following the existing format:

```yaml
- id: "DD-XX-N"
  question: "Your question here"
  category: "category_name"
  phase: "screening"  # or "deep_diligence"
  dimension: "what"   # optional: what/who/how_much/contribution/risk
  priority: "high"    # high/medium/low
  keywords:
    - keyword1
    - keyword2
  follow_up: "Optional follow-up guidance"
```

## Pull Request Guidelines

- Keep PRs focused: one feature or fix per PR
- Include tests for new functionality
- Update documentation when behavior changes
- Add a changelog entry under `[Unreleased]` in `CHANGELOG.md`
- Ensure all 41+ tests pass before submitting

## Code Style

- Use Pydantic models for structured data
- Type hints on all public functions
- Follow the existing patterns in the codebase (BaseTool, ToolResult, etc.)
- Keep framework modules self-contained with clear public APIs

## Reporting Issues

- Include Python version, OS, and relevant error output
- For framework-related issues, specify which standards/metrics are affected
- For visual output issues, include screenshots if possible

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
