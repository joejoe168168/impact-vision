"""CLI entry point using typer."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer


def _resolve_version() -> str:
    """Read the canonical version from package metadata.

    Hardcoding ``__version__`` here is a perpetual source of doc-drift: the
    last few releases shipped with a stale literal because the bump on
    ``pyproject.toml`` was not mirrored in the CLI. ``importlib.metadata``
    keeps a single source of truth.
    """
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("impact-vision")
    except (PackageNotFoundError, Exception):  # noqa: BLE001 - defensive
        return "0.0.0+unknown"


__version__ = _resolve_version()


def _resolve_tool_count() -> int:
    """Count of impact agent tools currently registered.

    Single source of truth for ``serve-mcp`` / banner messaging.
    """
    try:
        from openharness.tools.impact import __all__ as _impact_all

        return len(_impact_all)
    except Exception:  # noqa: BLE001 - defensive
        return 0


def _version_callback(value: bool) -> None:
    if value:
        print(f"impact-vision {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="impact-vision",
    help=(
        "Impact Vision: AI-powered impact measurement and SDG alignment agent.\n\n"
        "Built on OpenHarness for VC/impact investment funds.\n"
        "Starts an interactive session by default, use -p/--print for non-interactive output."
    ),
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True,
)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

mcp_app = typer.Typer(name="mcp", help="Manage MCP servers")
plugin_app = typer.Typer(name="plugin", help="Manage plugins")
auth_app = typer.Typer(name="auth", help="Manage authentication")
provider_app = typer.Typer(name="provider", help="Manage provider profiles")
cron_app = typer.Typer(name="cron", help="Manage cron scheduler and jobs")
catalog_app = typer.Typer(name="catalog", help="Manage the IRIS+ metric catalog")
framework_app = typer.Typer(name="framework", help="ESG/sustainability framework tools")
dd_app = typer.Typer(name="dd", help="Impact due diligence checklist tools")

app.add_typer(mcp_app)
app.add_typer(plugin_app)
app.add_typer(auth_app)
app.add_typer(provider_app)
app.add_typer(cron_app)
app.add_typer(catalog_app)
app.add_typer(framework_app)
app.add_typer(dd_app)


# ---- serve-mcp command (Impact Vision MCP server) ----

@app.command("serve-mcp")
def serve_mcp(
    transport: str = typer.Option("stdio", help="Transport: stdio or sse"),
    host: str = typer.Option(
        "127.0.0.1",
        help=(
            "Host for SSE transport. Defaults to 127.0.0.1 to avoid binding "
            "to all interfaces; pass '0.0.0.0' explicitly to expose."
        ),
    ),
    port: int = typer.Option(8765, help="Port for SSE transport"),
) -> None:
    """Start the Impact Vision MCP server.

    The server exposes the full impact-tool surface registered in
    ``openharness.tools.impact``. The exact tool count is sourced at runtime
    from ``len(openharness.tools.impact.__all__)`` so this docstring never
    drifts from reality.
    """
    from openharness.impact.mcp_server import mcp as mcp_server  # noqa: F811

    print(
        f"impact-vision serve-mcp: exposing {_resolve_tool_count()} impact tools "
        f"over {transport}",
        file=sys.stderr,
    )
    if transport == "sse":
        mcp_server.settings.host = host
        mcp_server.settings.port = port
    mcp_server.run(transport=transport)


# ---- serve-web command (Web console + REST gateway) ----

@app.command("serve-web")
def serve_web(
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    port: int = typer.Option(8787, help="Port to bind"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes (dev)"),
) -> None:
    """Start the Impact Vision web console — UI + REST gateway in one process.

    The console is mounted at ``/`` and proxies every /api/v1/* endpoint of
    the FastAPI gateway. Think of it as the Impact Vision equivalent of
    ``sst/opencode`` or ``siteboon/claudecodeui``: a browser UI for the
    same tool surface the CLI / MCP server exposes.
    """
    try:
        import uvicorn  # type: ignore
    except ImportError as exc:  # pragma: no cover
        print(
            "uvicorn is required to run the web console. "
            "Install with: pip install 'impact-vision[web]' or "
            "'pip install uvicorn fastapi'.",
            file=sys.stderr,
        )
        raise typer.Exit(1) from exc

    print(f"Impact Vision web console → http://{host}:{port}")
    print(f"  · REST API: http://{host}:{port}/api/v1/*")
    print(f"  · OpenAPI:  http://{host}:{port}/docs")
    uvicorn.run(
        "openharness.web.app:app",
        host=host,
        port=port,
        reload=reload,
    )


# ---- mcp subcommands ----

@mcp_app.command("list")
def mcp_list() -> None:
    """List configured MCP servers."""
    from openharness.config import load_settings
    from openharness.mcp.config import load_mcp_server_configs
    from openharness.plugins import load_plugins

    settings = load_settings()
    plugins = load_plugins(settings, str(Path.cwd()))
    configs = load_mcp_server_configs(settings, plugins)
    if not configs:
        print("No MCP servers configured.")
        return
    for name, cfg in configs.items():
        transport = cfg.get("transport", cfg.get("command", "unknown"))
        print(f"  {name}: {transport}")


@mcp_app.command("add")
def mcp_add(
    name: str = typer.Argument(..., help="Server name"),
    config_json: str = typer.Argument(..., help="Server config as JSON string"),
) -> None:
    """Add an MCP server configuration."""
    from openharness.config import load_settings, save_settings

    settings = load_settings()
    try:
        cfg = json.loads(config_json)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        raise typer.Exit(1)
    if not isinstance(settings.mcp_servers, dict):
        settings.mcp_servers = {}
    settings.mcp_servers[name] = cfg
    save_settings(settings)
    print(f"Added MCP server: {name}")


@mcp_app.command("remove")
def mcp_remove(
    name: str = typer.Argument(..., help="Server name to remove"),
) -> None:
    """Remove an MCP server configuration."""
    from openharness.config import load_settings, save_settings

    settings = load_settings()
    if not isinstance(settings.mcp_servers, dict) or name not in settings.mcp_servers:
        print(f"MCP server not found: {name}", file=sys.stderr)
        raise typer.Exit(1)
    del settings.mcp_servers[name]
    save_settings(settings)
    print(f"Removed MCP server: {name}")


# ---- plugin subcommands ----

@plugin_app.command("list")
def plugin_list() -> None:
    """List installed plugins."""
    from openharness.config import load_settings
    from openharness.plugins import load_plugins

    settings = load_settings()
    plugins = load_plugins(settings, str(Path.cwd()))
    if not plugins:
        print("No plugins installed.")
        return
    for plugin in plugins:
        status = "enabled" if plugin.enabled else "disabled"
        print(f"  {plugin.name} [{status}] - {plugin.description or ''}")


@plugin_app.command("install")
def plugin_install(
    source: str = typer.Argument(..., help="Plugin source (path or URL)"),
) -> None:
    """Install a plugin from a source path."""
    from openharness.plugins.installer import install_plugin_from_path

    result = install_plugin_from_path(source)
    print(f"Installed plugin: {result}")


@plugin_app.command("uninstall")
def plugin_uninstall(
    name: str = typer.Argument(..., help="Plugin name to uninstall"),
) -> None:
    """Uninstall a plugin."""
    from openharness.plugins.installer import uninstall_plugin

    uninstall_plugin(name)
    print(f"Uninstalled plugin: {name}")


# ---- cron subcommands ----

@cron_app.command("start")
def cron_start() -> None:
    """Start the cron scheduler daemon."""
    from openharness.services.cron_scheduler import is_scheduler_running, start_daemon

    if is_scheduler_running():
        print("Cron scheduler is already running.")
        return
    pid = start_daemon()
    print(f"Cron scheduler started (pid={pid})")


@cron_app.command("stop")
def cron_stop() -> None:
    """Stop the cron scheduler daemon."""
    from openharness.services.cron_scheduler import stop_scheduler

    if stop_scheduler():
        print("Cron scheduler stopped.")
    else:
        print("Cron scheduler is not running.")


@cron_app.command("status")
def cron_status_cmd() -> None:
    """Show cron scheduler status and job summary."""
    from openharness.services.cron_scheduler import scheduler_status

    status = scheduler_status()
    state = "running" if status["running"] else "stopped"
    print(f"Scheduler: {state}" + (f" (pid={status['pid']})" if status["pid"] else ""))
    print(f"Jobs:      {status['enabled_jobs']} enabled / {status['total_jobs']} total")
    print(f"Log:       {status['log_file']}")


@cron_app.command("list")
def cron_list_cmd() -> None:
    """List all registered cron jobs with schedule and status."""
    from openharness.services.cron import load_cron_jobs

    jobs = load_cron_jobs()
    if not jobs:
        print("No cron jobs configured.")
        return
    for job in jobs:
        enabled = "on " if job.get("enabled", True) else "off"
        last = job.get("last_run", "never")
        if last != "never":
            last = last[:19]  # trim to readable datetime
        last_status = job.get("last_status", "")
        status_indicator = f" [{last_status}]" if last_status else ""
        print(f"  [{enabled}] {job['name']}  {job.get('schedule', '?')}")
        print(f"        cmd: {job['command']}")
        print(f"        last: {last}{status_indicator}  next: {job.get('next_run', 'n/a')[:19]}")


@cron_app.command("toggle")
def cron_toggle_cmd(
    name: str = typer.Argument(..., help="Cron job name"),
    enabled: bool = typer.Argument(..., help="true to enable, false to disable"),
) -> None:
    """Enable or disable a cron job."""
    from openharness.services.cron import set_job_enabled

    if not set_job_enabled(name, enabled):
        print(f"Cron job not found: {name}")
        raise typer.Exit(1)
    state = "enabled" if enabled else "disabled"
    print(f"Cron job '{name}' is now {state}")


@cron_app.command("history")
def cron_history_cmd(
    name: str | None = typer.Argument(None, help="Filter by job name"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of entries"),
) -> None:
    """Show cron execution history."""
    from openharness.services.cron_scheduler import load_history

    entries = load_history(limit=limit, job_name=name)
    if not entries:
        print("No execution history.")
        return
    for entry in entries:
        ts = entry.get("started_at", "?")[:19]
        status = entry.get("status", "?")
        rc = entry.get("returncode", "?")
        print(f"  {ts}  {entry.get('name', '?')}  {status} (rc={rc})")
        stderr = entry.get("stderr", "").strip()
        if stderr and status != "success":
            for line in stderr.splitlines()[:3]:
                print(f"    stderr: {line}")


@cron_app.command("logs")
def cron_logs_cmd(
    lines: int = typer.Option(30, "--lines", "-n", help="Number of lines to show"),
) -> None:
    """Show recent cron scheduler log output."""
    from openharness.config.paths import get_logs_dir

    log_path = get_logs_dir() / "cron_scheduler.log"
    if not log_path.exists():
        print("No scheduler log found. Start the scheduler with: oh cron start")
        return
    content = log_path.read_text(encoding="utf-8", errors="replace")
    tail = content.splitlines()[-lines:]
    for line in tail:
        print(line)


# ---- catalog subcommands ----


@catalog_app.command("load")
def catalog_load(
    excel_path: str | None = typer.Argument(None, help="Path to IRIS+ 5.3c Excel file"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reload from Excel even if JSON cache exists"),
) -> None:
    """Load the IRIS+ 5.3c catalog from Excel into the processed JSON cache."""
    from openharness.impact.catalog import (
        get_default_excel_path,
        get_default_json_path,
        load_catalog_from_excel,
        save_catalog_json,
    )

    path = Path(excel_path) if excel_path else get_default_excel_path()
    if not path.exists():
        print(f"IRIS+ catalog Excel not found: {path}", file=sys.stderr)
        print(f"Place the file at: {get_default_excel_path()}", file=sys.stderr)
        raise typer.Exit(1)

    json_path = get_default_json_path()
    if json_path.exists() and not force:
        print(f"JSON cache already exists: {json_path}")
        print("Use --force to reload from Excel.")
        return

    print(f"Loading IRIS+ catalog from: {path}")
    metrics = load_catalog_from_excel(path)
    save_catalog_json(metrics, json_path)
    print(f"Loaded {len(metrics)} metrics -> {json_path}")


@catalog_app.command("stats")
def catalog_stats() -> None:
    """Show summary statistics for the loaded IRIS+ catalog."""
    from openharness.impact.database import get_metric_store

    try:
        store = get_metric_store()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)

    if store.count == 0:
        print("No catalog loaded. Run: impact-vision catalog load")
        raise typer.Exit(1)

    stats = store.stats()
    print("IRIS+ 5.3c Catalog Statistics")
    print(f"{'=' * 50}")
    print(f"Total metrics:             {stats['total_metrics']}")
    print(f"With SDG mapping:          {stats['metrics_with_sdg_mapping']}")
    print(f"With dimension tags:       {stats['metrics_with_dimension_tags']}")
    print()
    print("SDG Coverage (metrics per goal):")
    for goal, count in stats["sdg_coverage"].items():
        print(f"  SDG {goal:>2}: {count} metrics")
    print()
    print("Top Impact Themes:")
    for theme, count in list(stats["top_themes"].items())[:10]:
        print(f"  {theme}: {count}")
    print()
    print("Categories:")
    for cat, count in stats["categories"].items():
        print(f"  {cat}: {count}")


@catalog_app.command("search")
def catalog_search(
    query: str = typer.Argument(..., help="Search query for metrics"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max results"),
) -> None:
    """Search the IRIS+ catalog by keyword."""
    from openharness.impact.database import get_metric_store

    store = get_metric_store()
    if store.count == 0:
        print("No catalog loaded. Run: impact-vision catalog load")
        raise typer.Exit(1)

    results = store.search(query, limit=limit)
    if not results:
        print(f"No metrics found for: {query}")
        return

    print(f"Found {len(results)} metrics for '{query}':\n")
    for m in results:
        sdgs = ", ".join(f"SDG {g}" for g in m.sdg_goals[:3]) if m.sdg_goals else "No SDG"
        print(f"  {m.id}: {m.name}")
        print(f"    {m.primary_impact_category} | {sdgs}")
        if m.definition:
            print(f"    {m.definition[:100]}...")
        print()


# ---- framework subcommands ----


@framework_app.command("list")
def framework_list_cmd() -> None:
    """List all supported ESG/sustainability frameworks."""
    frameworks = [
        ("sasb", "SASB Industry-Specific Materiality", "17 industries, 77+ topics"),
        ("gri", "GRI Universal + Topic Standards", "30+ standards, 120+ disclosures"),
        ("tcfd", "TCFD / IFRS S2 Climate Disclosure", "4 pillars, 11 disclosures"),
        ("sfdr_pai", "SFDR PAI Indicators", "14 mandatory EU indicators"),
        ("edci", "EDCI PE/VC Metrics", "2026 KPI fields incl. non-core"),
        ("unpri", "UN PRI Self-Assessment", "6 principles, 27 actions"),
        ("toc", "Theory of Change", "RS Group + GIIN ToC Checklist"),
    ]
    print("Supported ESG / Sustainability Frameworks:")
    print(f"{'=' * 60}")
    for key, name, detail in frameworks:
        print(f"  {key:<12} {name}")
        print(f"  {'':12} {detail}")


@framework_app.command("scan")
def framework_scan_cmd(
    description: str = typer.Argument(..., help="Company description for assessment"),
    sector: str = typer.Option("", "--sector", "-s", help="Company sector"),
) -> None:
    """Quick scan a company against all ESG frameworks."""
    from openharness.impact.frameworks.edci import assess_edci_coverage
    from openharness.impact.frameworks.sasb import match_sasb_industry
    from openharness.impact.frameworks.sfdr_pai import assess_sfdr_compliance
    from openharness.impact.frameworks.tcfd import assess_tcfd_alignment
    from openharness.impact.frameworks.theory_of_change import assess_toc_alignment
    from openharness.impact.frameworks.unpri import assess_unpri_alignment

    print("MULTI-FRAMEWORK ESG SCAN")
    print(f"{'=' * 50}")

    sasb = match_sasb_industry(sector, description)
    if sasb:
        top = sasb[0]
        print(f"SASB: Best match = {top[0].industry} ({top[0].sector}), {len(top[0].topics)} topics")
    else:
        print("SASB: No industry match")

    tcfd = assess_tcfd_alignment(description)
    print(f"TCFD: {tcfd['overall_coverage']}% coverage ({tcfd['addressed_disclosures']}/{tcfd['total_disclosures']})")

    sfdr = assess_sfdr_compliance(company_description=description)
    print(f"SFDR PAI: {sfdr['coverage_pct']}% coverage ({sfdr['addressed']}/{sfdr['total']})")

    edci = assess_edci_coverage(company_description=description)
    print(f"EDCI: {edci['coverage_pct']}% coverage ({edci['addressed']}/{edci['total']})")

    unpri = assess_unpri_alignment(description)
    print(f"UNPRI: {unpri['overall_coverage']}% alignment ({unpri['addressed_actions']}/{unpri['total_actions']})")

    toc = assess_toc_alignment(description)
    print(f"ToC: {toc['coverage_pct']}% alignment ({toc['addressed']}/{toc['total_principles']})")


@framework_app.command("xref")
def framework_xref_cmd(
    metric_id: str = typer.Argument(..., help="Metric ID to look up cross-references for"),
) -> None:
    """Look up cross-references for a metric across all frameworks."""
    from openharness.impact.frameworks.cross_reference import (
        format_cross_reference,
        lookup_by_edci,
        lookup_by_gri,
        lookup_by_iris,
        lookup_by_sfdr,
        search_cross_references,
    )

    results = []
    results.extend(lookup_by_iris(metric_id))
    results.extend(lookup_by_gri(metric_id))
    results.extend(lookup_by_edci(metric_id))
    try:
        results.extend(lookup_by_sfdr(int(metric_id)))
    except ValueError:
        pass
    if not results:
        results = search_cross_references(metric_id)

    seen = set()
    for r in results:
        if r.concept not in seen:
            seen.add(r.concept)
            print(format_cross_reference(r))
            print()

    if not seen:
        print(f"No cross-references found for: {metric_id}")


# ---- dd subcommands ----


@dd_app.command("list")
def dd_list_cmd(
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
    priority: str | None = typer.Option(None, "--priority", "-p", help="Filter by priority (high/medium/low)"),
) -> None:
    """List DD checklist questions."""
    from openharness.impact.dd_checklist import load_checklist

    questions = load_checklist()
    if category:
        questions = [q for q in questions if q.category == category]
    if priority:
        questions = [q for q in questions if q.priority == priority]

    print(f"DD Checklist ({len(questions)} questions):")
    for q in questions:
        icon = {"high": "!!!", "medium": "..", "low": "."}.get(q.priority, "")
        dim = f" [{q.dimension}]" if q.dimension else ""
        print(f"  {q.id} {icon} {q.question}{dim}")
        print(f"    Category: {q.category} | Phase: {q.phase}")


@dd_app.command("categories")
def dd_categories_cmd() -> None:
    """List all DD checklist categories with question counts."""
    from openharness.impact.dd_checklist import load_checklist

    questions = load_checklist()
    cats: dict[str, int] = {}
    for q in questions:
        cats[q.category] = cats.get(q.category, 0) + 1
    print(f"DD Checklist Categories ({len(cats)} categories, {len(questions)} questions):")
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count} questions")


@dd_app.command("analyze")
def dd_analyze_cmd(
    text: str = typer.Argument(..., help="Document text to analyze (or file path)"),
) -> None:
    """Analyze document text against the DD checklist."""
    from openharness.impact.dd_checklist import analyze_document_coverage

    doc_text = text
    if Path(text).exists():
        doc_text = Path(text).read_text(encoding="utf-8")

    result = analyze_document_coverage(doc_text)
    print(f"DD Checklist Coverage: {result.coverage_pct}%")
    print(f"Addressed: {len(result.addressed)}/{result.total_questions}")
    print(f"High-Priority Gaps: {len(result.high_priority_gaps)}")
    print(f"Average Evidence Level: {result.avg_evidence_level:.1f}/5")
    if result.high_priority_gaps:
        print("\nHigh-Priority Gaps:")
        for q in result.high_priority_gaps:
            print(f"  {q.id}: {q.question}")


# ---- local LLM / ollama setup ----


@app.command("ollama-setup")
def ollama_setup_cmd(
    base_url: str = typer.Option("http://localhost:11434/v1", "--base-url", help="Ollama API base URL"),
    model: str = typer.Option("llama3.2", "--model", "-m", help="Model name available in Ollama"),
) -> None:
    """Configure Impact Vision to use Ollama (or any local OpenAI-compatible LLM).

    Prerequisites:
      1. Install Ollama: https://ollama.com
      2. Pull a model: ollama pull llama3.2
      3. Start the server: ollama serve

    This command configures the 'ollama' provider profile with the given base URL and model.
    """
    from openharness.auth.manager import AuthManager
    from openharness.config.settings import ProviderProfile

    manager = AuthManager()
    profile = ProviderProfile(
        label=f"Ollama ({model})",
        provider="openai",
        api_format="openai",
        auth_source="openai_api_key",
        default_model=model,
        last_model=model,
        base_url=base_url,
        credential_slot="ollama",
        allowed_models=[model],
    )
    manager.upsert_profile("ollama", profile)
    manager.store_profile_credential("ollama", "api_key", "ollama")
    manager.use_profile("ollama")

    print("Ollama configured:")
    print(f"  Base URL: {base_url}")
    print(f"  Model:    {model}")
    print("  Profile:  ollama (now active)")
    print()
    print("Make sure Ollama is running: ollama serve")
    print("To switch back: impact-vision provider use <other-profile>")


# ---- auth subcommands ----

# Mapping from provider name to human-readable label for interactive prompts.
_PROVIDER_LABELS: dict[str, str] = {
    "anthropic": "Anthropic (Claude API)",
    "anthropic_claude": "Claude subscription (Claude CLI)",
    "openai": "OpenAI / compatible",
    "openai_codex": "OpenAI Codex subscription (Codex CLI)",
    "copilot": "GitHub Copilot",
    "dashscope": "Alibaba DashScope",
    "bedrock": "AWS Bedrock",
    "vertex": "Google Vertex AI",
    "moonshot": "Moonshot (Kimi)",
    "gemini": "Google Gemini",
}

_AUTH_SOURCE_LABELS: dict[str, str] = {
    "anthropic_api_key": "Anthropic API key",
    "openai_api_key": "OpenAI API key",
    "codex_subscription": "Codex subscription",
    "claude_subscription": "Claude subscription",
    "copilot_oauth": "GitHub Copilot OAuth",
    "dashscope_api_key": "DashScope API key",
    "bedrock_api_key": "Bedrock credentials",
    "vertex_api_key": "Vertex credentials",
    "moonshot_api_key": "Moonshot API key",
    "gemini_api_key": "Gemini API key",
}


def _can_use_questionary() -> bool:
    """Return True when a real interactive terminal is available."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    if sys.stdin is not sys.__stdin__ or sys.stdout is not sys.__stdout__:
        return False
    try:
        import questionary  # noqa: F401
    except ImportError:
        return False
    return True


def _select_with_questionary(
    title: str,
    options: list[tuple[str, str]],
    *,
    default_value: str | None = None,
) -> str:
    import questionary

    choices = [
        questionary.Choice(
            title=label,
            value=value,
            checked=(value == default_value),
        )
        for value, label in options
    ]
    result = questionary.select(title, choices=choices, default=default_value).ask()
    if result is None:
        raise typer.Abort()
    return str(result)


def _text_prompt(message: str, *, default: str = "") -> str:
    """Prompt for text input, preferring questionary in a real TTY."""
    if _can_use_questionary():
        import questionary

        result = questionary.text(message, default=default).ask()
        if result is None:
            raise typer.Abort()
        return str(result)
    return typer.prompt(message, default=default)


def _secret_prompt(message: str) -> str:
    """Prompt for secret text, preferring questionary in a real TTY."""
    if _can_use_questionary():
        import questionary

        result = questionary.password(message).ask()
        if result is None:
            raise typer.Abort()
        return str(result)
    return typer.prompt(message, hide_input=True)


def _select_from_menu(
    title: str,
    options: list[tuple[str, str]],
    *,
    default_value: str | None = None,
) -> str:
    """Render a simple numbered picker and return the selected value."""
    if _can_use_questionary():
        return _select_with_questionary(title, options, default_value=default_value)
    print(title, flush=True)
    default_index = 1
    for index, (value, label) in enumerate(options, 1):
        marker = " (default)" if value == default_value else ""
        if value == default_value:
            default_index = index
        print(f"  {index}. {label}{marker}", flush=True)
    raw = typer.prompt("Choose", default=str(default_index))
    try:
        selected = options[int(raw) - 1]
    except (ValueError, IndexError):
        raise typer.BadParameter(f"Invalid selection: {raw}") from None
    return selected[0]


def _prompt_model_for_profile(profile) -> str:
    from openharness.config.settings import (
        CLAUDE_MODEL_ALIAS_OPTIONS,
        display_model_setting,
        is_claude_family_provider,
    )

    current = display_model_setting(profile)
    if profile.allowed_models:
        if len(profile.allowed_models) == 1:
            return profile.allowed_models[0]
        options = [(value, value) for value in profile.allowed_models]
        return _select_from_menu("Choose a model setting:", options, default_value=current if current in profile.allowed_models else profile.allowed_models[0])
    if is_claude_family_provider(profile.provider):
        options = [(value, f"{label} - {description}") for value, label, description in CLAUDE_MODEL_ALIAS_OPTIONS]
        options.append(("__custom__", "Custom model ID"))
        selection = _select_from_menu(
            "Choose a model setting:",
            options,
            default_value=current if any(value == current for value, _, _ in CLAUDE_MODEL_ALIAS_OPTIONS) else "__custom__",
        )
        if selection != "__custom__":
            return selection
    return _text_prompt("Model", default=current).strip() or current


def _format_profile_choice_label(info: dict[str, object]) -> str:
    """Render a user-facing workflow label without leaking internal provider ids."""
    label = str(info["label"])
    state = "" if bool(info["configured"]) else f" ({info['auth_state']})"
    return f"{label}{state}"


def _styled_missing_suffix(info: dict[str, object]) -> tuple[str, str] | None:
    """Return a soft red missing-auth suffix for questionary titles."""
    if bool(info["configured"]):
        return None
    return (f" ({info['auth_state']})", "fg:#d3869b")


def _select_setup_workflow(
    statuses: dict[str, dict[str, object]],
    *,
    default_value: str | None = None,
) -> str:
    """Render the top-level `oh setup` workflow picker with richer hints."""
    hints = {
        "claude-api": ("Claude / Kimi / GLM / MiniMax", "fg:#7aa2f7"),
        "openai-compatible": ("OpenAI / OpenRouter", "fg:#9ece6a"),
    }

    if _can_use_questionary():
        import questionary

        choices = []
        for name, info in statuses.items():
            label = str(info["label"])
            hint = hints.get(name)
            missing = _styled_missing_suffix(info)
            if hint is None:
                if missing is None:
                    title = label
                else:
                    suffix, suffix_style = missing
                    title = [("", label), (suffix_style, suffix)]
            else:
                hint_text, hint_style = hint
                if missing is None:
                    title = [
                        ("", f"{label}  "),
                        (hint_style, hint_text),
                    ]
                else:
                    suffix, suffix_style = missing
                    title = [
                        ("", f"{label}  "),
                        (hint_style, hint_text),
                        ("", "  "),
                        (suffix_style, suffix.strip()),
                    ]
            choices.append(questionary.Choice(title=title, value=name, checked=(name == default_value)))

        result = questionary.select("Choose a provider workflow:", choices=choices, default=default_value).ask()
        if result is None:
            raise typer.Abort()
        return str(result)

    options: list[tuple[str, str]] = []
    for name, info in statuses.items():
        label = _format_profile_choice_label(info)
        hint = hints.get(name)
        if hint is not None:
            label = f"{label} ({hint[0]})"
        options.append((name, label))
    return _select_from_menu("Choose a provider workflow:", options, default_value=default_value)


def _default_credential_slot_for_profile(name: str, auth_source: str) -> str | None:
    from openharness.config.settings import auth_source_uses_api_key, builtin_provider_profile_names

    if name in builtin_provider_profile_names():
        return None
    if not auth_source_uses_api_key(auth_source):
        return None
    return name


def _prompt_api_key_for_profile(label: str) -> str:
    key = _secret_prompt(f"Enter API key for {label}").strip()
    if not key:
        raise typer.BadParameter("API key cannot be empty.")
    return key


def _configure_custom_profile_via_setup(manager) -> str:
    from openharness.config.settings import ProviderProfile, default_auth_source_for_provider

    family = _select_from_menu(
        "Choose a compatible API family:",
        [
            ("anthropic", "Anthropic-compatible"),
            ("openai", "OpenAI-compatible"),
        ],
        default_value="anthropic",
    )
    default_name = f"custom-{family}"
    name = _text_prompt("Profile name", default=default_name).strip()
    if not name:
        raise typer.BadParameter("Profile name cannot be empty.")
    label = _text_prompt("Display label", default=name).strip() or name
    base_url = _text_prompt("Base URL", default="").strip()
    if not base_url:
        raise typer.BadParameter("Base URL cannot be empty.")

    auth_source = default_auth_source_for_provider(family, family)
    model = _text_prompt("Default model", default="").strip()
    if not model:
        raise typer.BadParameter("Default model cannot be empty.")

    profile = ProviderProfile(
        label=label,
        provider=family,
        api_format=family,
        auth_source=auth_source,
        default_model=model,
        last_model=model,
        base_url=base_url,
        credential_slot=_default_credential_slot_for_profile(name, auth_source),
        allowed_models=[model],
    )
    manager.upsert_profile(name, profile)
    manager.store_profile_credential(name, "api_key", _prompt_api_key_for_profile(label))
    return name


def _ensure_preset_profile(
    manager,
    *,
    name: str,
    label: str,
    provider: str,
    api_format: str,
    auth_source: str,
    base_url: str | None,
    model: str,
    lock_model: bool,
) -> str:
    from openharness.config.settings import ProviderProfile

    existing = manager.list_profiles().get(name)
    profile = ProviderProfile(
        label=label,
        provider=provider,
        api_format=api_format,
        auth_source=auth_source,
        default_model=model,
        last_model=model,
        base_url=base_url,
        credential_slot=_default_credential_slot_for_profile(name, auth_source),
        allowed_models=[model] if lock_model else (existing.allowed_models if existing else []),
    )
    manager.upsert_profile(name, profile)
    return name


def _specialize_setup_target(manager, target: str) -> str:
    """Expand a top-level family choice into a concrete workflow profile."""
    from openharness.config.settings import default_auth_source_for_provider

    if target == "claude-api":
        choice = _select_from_menu(
            "Choose an Anthropic-compatible provider:",
            [
                ("claude-api", "Claude official"),
                ("kimi-anthropic", "Moonshot Kimi"),
                ("glm-anthropic", "Zhipu GLM"),
                ("minimax-anthropic", "MiniMax"),
            ],
            default_value="claude-api",
        )
        if choice == "claude-api":
            return choice
        defaults = {
            "kimi-anthropic": ("Kimi (Anthropic-compatible)", "https://api.moonshot.cn/anthropic", "kimi-k2.5"),
            "glm-anthropic": ("GLM (Anthropic-compatible)", "", "glm-4.5"),
            "minimax-anthropic": ("MiniMax (Anthropic-compatible)", "", "minimax-m1"),
        }
        label, suggested_base_url, suggested_model = defaults[choice]
        base_url = _text_prompt("Base URL", default=suggested_base_url).strip()
        if not base_url:
            raise typer.BadParameter("Base URL cannot be empty.")
        model = _text_prompt("Model", default=suggested_model).strip()
        if not model:
            raise typer.BadParameter("Model cannot be empty.")
        return _ensure_preset_profile(
            manager,
            name=choice,
            label=label,
            provider="anthropic",
            api_format="anthropic",
            auth_source=default_auth_source_for_provider("anthropic", "anthropic"),
            base_url=base_url,
            model=model,
            lock_model=True,
        )

    if target == "openai-compatible":
        choice = _select_from_menu(
            "Choose an OpenAI-compatible provider:",
            [
                ("openai-compatible", "OpenAI official"),
                ("openrouter", "OpenRouter"),
                ("custom-openai", "Custom endpoint (any OpenAI-compatible API)"),
            ],
            default_value="openai-compatible",
        )
        if choice == "openai-compatible":
            return choice
        if choice == "openrouter":
            default_url = "https://openrouter.ai/api/v1"
            profile_name = "openrouter"
            profile_label = "OpenRouter"
        else:
            default_url = ""
            profile_label = _text_prompt("Display name", default="Custom OpenAI").strip() or "Custom OpenAI"
            profile_name = profile_label.lower().replace(" ", "-")
        base_url = _text_prompt("Base URL", default=default_url).strip()
        if not base_url:
            raise typer.BadParameter("Base URL cannot be empty.")
        model = _text_prompt("Default model", default="").strip()
        if not model:
            raise typer.BadParameter("Default model cannot be empty.")
        return _ensure_preset_profile(
            manager,
            name=profile_name,
            label=profile_label,
            provider="openai",
            api_format="openai",
            auth_source=default_auth_source_for_provider("openai", "openai"),
            base_url=base_url,
            model=model,
            lock_model=False,
        )

    return target


def _ensure_profile_auth(manager, profile_name: str) -> None:
    from openharness.auth.flows import ApiKeyFlow
    from openharness.config.settings import auth_source_provider_name, auth_source_uses_api_key

    profile = manager.list_profiles()[profile_name]
    if not auth_source_uses_api_key(profile.auth_source):
        _login_provider(auth_source_provider_name(profile.auth_source))
        return

    flow = ApiKeyFlow(
        provider=profile.provider,
        prompt_text=f"Enter API key for {profile.label}",
    )
    try:
        key = flow.run()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(1)
    manager.store_profile_credential(profile_name, "api_key", key)
    print(f"{profile.label} API key saved.", flush=True)


def _maybe_update_default_model_for_provider(provider: str) -> None:
    """Keep the active model in-family after switching auth providers."""
    from openharness.auth.manager import AuthManager

    manager = AuthManager()
    profile_name = {
        "openai_codex": "codex",
        "anthropic_claude": "claude-subscription",
    }.get(provider)
    if profile_name is None:
        return
    profile = manager.list_profiles()[profile_name]
    model = profile.resolved_model.lower()
    target_model = None
    if provider == "openai_codex" and not model.startswith(("gpt-", "o1", "o3", "o4")):
        target_model = "gpt-5.4"
    elif provider == "anthropic_claude" and not model.startswith("claude-"):
        target_model = "sonnet"
    if not target_model:
        return
    manager.update_profile(profile_name, default_model=target_model, last_model=target_model)


def _bind_external_provider(provider: str) -> None:
    """Bind a provider to credentials managed by an external CLI."""
    from openharness.auth.external import default_binding_for_provider, load_external_credential
    from openharness.auth.storage import store_external_binding

    binding = default_binding_for_provider(provider)
    try:
        credential = load_external_credential(
            binding,
            refresh_if_needed=(provider == "anthropic_claude"),
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr, flush=True)
        raise typer.Exit(1)

    profile_label = credential.profile_label or binding.profile_label
    store_external_binding(
        binding.__class__(
            provider=binding.provider,
            source_path=binding.source_path,
            source_kind=binding.source_kind,
            managed_by=binding.managed_by,
            profile_label=profile_label,
        )
    )

    _maybe_update_default_model_for_provider(provider)
    label = _PROVIDER_LABELS.get(provider, provider)
    profile_name = {
        "openai_codex": "codex",
        "anthropic_claude": "claude-subscription",
    }[provider]
    print(f"{label} bound from {credential.source_path}.", flush=True)
    print(f"Use `oh provider use {profile_name}` to activate it.", flush=True)


def _login_provider(provider: str) -> None:
    """Authenticate or bind the given provider."""
    from openharness.auth.flows import ApiKeyFlow
    from openharness.auth.manager import AuthManager
    from openharness.auth.storage import store_credential

    manager = AuthManager()

    if provider == "copilot":
        _run_copilot_login()
        return

    if provider in ("openai_codex", "anthropic_claude"):
        _bind_external_provider(provider)
        return

    if provider in ("anthropic", "openai", "dashscope", "bedrock", "vertex", "moonshot", "gemini"):
        label = _PROVIDER_LABELS.get(provider, provider)
        flow = ApiKeyFlow(provider=provider, prompt_text=f"Enter your {label} API key")
        try:
            key = flow.run()
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            raise typer.Exit(1)
        store_credential(provider, "api_key", key)
        try:
            manager.store_credential(provider, "api_key", key)
        except Exception:
            pass
        print(f"{label} API key saved.", flush=True)
        return

    print(f"Unknown provider: {provider!r}. Known: {', '.join(_PROVIDER_LABELS)}", file=sys.stderr)
    raise typer.Exit(1)


def _test_api_connection(manager, profile_name: str, model: str) -> None:
    """Send a minimal API request to verify the key and endpoint work."""
    import httpx

    from openharness.auth.storage import load_credential
    from openharness.config.settings import credential_storage_provider_name

    profile = manager.list_profiles()[profile_name]
    storage_ns = credential_storage_provider_name(profile_name, profile)
    cred = load_credential(storage_ns, "api_key")
    if not cred:
        cred = getattr(manager.settings, "api_key", "")
    if not cred:
        print("  No API key stored -- skipping test.", flush=True)
        return

    base_url = profile.base_url or ""
    if profile.provider == "anthropic" or profile.api_format == "anthropic":
        url = (base_url.rstrip("/") if base_url else "https://api.anthropic.com") + "/v1/messages"
        headers = {"x-api-key": cred, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        body = {"model": model, "max_tokens": 10, "messages": [{"role": "user", "content": "Hi"}]}
    else:
        if base_url:
            normalized = base_url.rstrip("/")
            if not normalized.endswith("/v1"):
                normalized += "/v1"
        else:
            normalized = "https://api.openai.com/v1"
        url = normalized + "/chat/completions"
        headers = {"Authorization": f"Bearer {cred}", "Content-Type": "application/json"}
        body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 10}

    try:
        r = httpx.post(url, headers=headers, json=body, timeout=30)
        if r.status_code == 200:
            print("  API key is valid. Connection successful!", flush=True)
        elif r.status_code == 401:
            print("  API key rejected (401 Unauthorized). Please check your key.", flush=True)
            print("  Run 'impact-vision setup' again to enter a new key.", flush=True)
        elif r.status_code == 403:
            print("  Access denied (403 Forbidden). Your key may lack permissions.", flush=True)
        else:
            print(f"  API returned status {r.status_code}. Response: {r.text[:200]}", flush=True)
    except httpx.ConnectError:
        print(f"  Could not connect to {url}. Check the base URL.", flush=True)
    except httpx.TimeoutException:
        print("  Connection timed out. The server may be down or slow.", flush=True)
    except Exception as e:
        print(f"  Test failed: {e}", flush=True)


@app.command("setup")
def setup_cmd(
    profile: str | None = typer.Argument(None, help="Provider profile name to configure"),
) -> None:
    """Unified setup flow: choose workflow, authenticate if needed, then set the model."""
    from openharness.auth.manager import AuthManager
    from openharness.config.settings import display_model_setting

    manager = AuthManager()
    statuses = manager.get_profile_statuses()
    if not statuses:
        print("No provider profiles available.", file=sys.stderr)
        raise typer.Exit(1)

    target = profile
    if target is None:
        target = _select_setup_workflow(
            statuses,
            default_value=manager.get_active_profile(),
        )

    target = _specialize_setup_target(manager, target)
    manager = AuthManager()
    statuses = manager.get_profile_statuses()

    if target not in statuses:
        print(f"Unknown provider profile: {target!r}", file=sys.stderr)
        raise typer.Exit(1)

    info = statuses[target]
    if not info["configured"]:
        source_label = _AUTH_SOURCE_LABELS.get(info["auth_source"], info["auth_source"])
        print(f"{info['label']} requires {source_label}.", flush=True)
        _ensure_profile_auth(manager, target)
        manager = AuthManager()
    else:
        reauth = _select_from_menu(
            f"{info['label']} is already configured. Update API key?",
            [("no", "No, keep current key"), ("yes", "Yes, enter a new key")],
            default_value="no",
        )
        if reauth == "yes":
            _ensure_profile_auth(manager, target)
            manager = AuthManager()

    profile_obj = manager.list_profiles()[target]
    model_setting = _prompt_model_for_profile(profile_obj)
    if model_setting.lower() == "default":
        manager.update_profile(target, last_model="")
    else:
        manager.update_profile(target, last_model=model_setting)
    manager.use_profile(target)

    updated = manager.list_profiles()[target]
    print(
        "Setup complete:\n"
        f"- profile: {target}\n"
        f"- provider: {updated.provider}\n"
        f"- auth_source: {updated.auth_source}\n"
        f"- model: {display_model_setting(updated)}",
        flush=True,
    )

    print("\nTesting API connection...", flush=True)
    _test_api_connection(manager, target, display_model_setting(updated))


@auth_app.command("login")
def auth_login(
    provider: Optional[str] = typer.Argument(None, help="Provider name (anthropic, openai, copilot, …)"),
) -> None:
    """Interactively authenticate with a provider.

    Run without arguments to choose a provider from a menu.
    Supported providers: anthropic, anthropic_claude, openai, openai_codex, copilot, dashscope, bedrock, vertex, moonshot.
    """
    if provider is None:
        print("Select a provider to authenticate:", flush=True)
        labels = list(_PROVIDER_LABELS.items())
        for i, (name, label) in enumerate(labels, 1):
            print(f"  {i}. {label} [{name}]", flush=True)
        raw = typer.prompt("Enter number or provider name", default="1")
        try:
            idx = int(raw.strip()) - 1
            if 0 <= idx < len(labels):
                provider = labels[idx][0]
            else:
                print("Invalid selection.", file=sys.stderr)
                raise typer.Exit(1)
        except ValueError:
            provider = raw.strip()

    provider = provider.lower()
    _login_provider(provider)


@auth_app.command("status")
def auth_status_cmd() -> None:
    """Show authentication source and provider profile status."""
    from openharness.auth.manager import AuthManager

    manager = AuthManager()
    auth_sources = manager.get_auth_source_statuses()
    profiles = manager.get_profile_statuses()

    print("Auth sources:")
    print(f"{'Source':<24} {'State':<14} {'Origin':<10} Active")
    print("-" * 60)
    for name, info in auth_sources.items():
        label = _AUTH_SOURCE_LABELS.get(name, name)
        active_str = "<-- active" if info["active"] else ""
        print(f"{label:<24} {info['state']:<14} {info['source']:<10} {active_str}")
        if info.get("detail"):
            print(f"  detail: {info['detail']}")

    print()
    print("Provider profiles:")
    print(f"{'Profile':<20} {'Provider':<18} {'Auth source':<22} {'State':<12} Active")
    print("-" * 92)
    for name, info in profiles.items():
        status_str = "ready" if info["configured"] else info.get("auth_state", "missing auth")
        active_str = "<-- active" if info["active"] else ""
        print(f"{name:<20} {info['provider']:<18} {info['auth_source']:<22} {status_str:<12} {active_str}")


@auth_app.command("logout")
def auth_logout(
    provider: Optional[str] = typer.Argument(None, help="Provider to log out (default: active provider)"),
) -> None:
    """Clear stored authentication for a provider."""
    from openharness.auth.manager import AuthManager

    manager = AuthManager()
    if provider is None:
        target = manager.get_active_profile()
        manager.clear_profile_credential(target)
        print(f"Authentication cleared for profile: {target}", flush=True)
        return
    manager.clear_credential(provider)
    print(f"Authentication cleared for provider: {provider}", flush=True)


@auth_app.command("switch")
def auth_switch(
    provider: str = typer.Argument(..., help="Auth source or profile to activate"),
) -> None:
    """Switch the auth source for the active profile, or use a profile by name."""
    from openharness.auth.manager import AuthManager

    manager = AuthManager()
    try:
        manager.switch_provider(provider)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(1)
    print(f"Switched auth/profile to: {provider}", flush=True)


# ---------------------------------------------------------------------------
# Copilot login helper (kept as a named function for reuse and backward compat)
# ---------------------------------------------------------------------------


def _run_copilot_login() -> None:
    """Run the GitHub Copilot device-code flow and persist the result."""
    from openharness.api.copilot_auth import save_copilot_auth
    from openharness.auth.flows import DeviceCodeFlow

    print("Select GitHub deployment type:", flush=True)
    print("  1. GitHub.com (public)", flush=True)
    print("  2. GitHub Enterprise (data residency / self-hosted)", flush=True)
    choice = typer.prompt("Enter choice", default="1")

    enterprise_url: str | None = None
    github_domain = "github.com"

    if choice.strip() == "2":
        raw_url = typer.prompt("Enter your GitHub Enterprise URL or domain (e.g. company.ghe.com)")
        domain = raw_url.replace("https://", "").replace("http://", "").rstrip("/")
        if not domain:
            print("Error: domain cannot be empty.", file=sys.stderr, flush=True)
            raise typer.Exit(1)
        enterprise_url = domain
        github_domain = domain

    print(flush=True)
    flow = DeviceCodeFlow(github_domain=github_domain, enterprise_url=enterprise_url)
    try:
        token = flow.run()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr, flush=True)
        raise typer.Exit(1)

    save_copilot_auth(token, enterprise_url=enterprise_url)
    print("GitHub Copilot authenticated successfully.", flush=True)
    if enterprise_url:
        print(f"  Enterprise domain: {enterprise_url}", flush=True)
    print(flush=True)
    print("To use Copilot as the provider, run:", flush=True)
    print("  oh provider use copilot", flush=True)


@auth_app.command("copilot-login")
def auth_copilot_login() -> None:
    """Authenticate with GitHub Copilot via device flow (alias for 'oh auth login copilot')."""
    _run_copilot_login()


@auth_app.command("codex-login")
def auth_codex_login() -> None:
    """Bind OpenHarness to a local Codex CLI subscription session."""
    _bind_external_provider("openai_codex")


@auth_app.command("claude-login")
def auth_claude_login() -> None:
    """Bind OpenHarness to a local Claude CLI subscription session."""
    _bind_external_provider("anthropic_claude")


@auth_app.command("copilot-logout")
def auth_copilot_logout() -> None:
    """Remove stored GitHub Copilot authentication."""
    from openharness.api.copilot_auth import clear_github_token

    clear_github_token()
    print("Copilot authentication cleared.")


# ---- provider subcommands ----


@provider_app.command("list")
def provider_list() -> None:
    """List configured provider profiles."""
    from openharness.auth.manager import AuthManager

    statuses = AuthManager().get_profile_statuses()
    for name, info in statuses.items():
        marker = "*" if info["active"] else " "
        configured = "ready" if info["configured"] else "missing auth"
        base = info["base_url"] or "(default)"
        print(f"{marker} {name}: {info['label']} [{configured}]")
        print(f"    auth={info['auth_source']} model={info['model']} base_url={base}")


@provider_app.command("use")
def provider_use(
    name: str = typer.Argument(..., help="Provider profile name"),
) -> None:
    """Activate a provider profile."""
    from openharness.auth.manager import AuthManager

    manager = AuthManager()
    try:
        manager.use_profile(name)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(1)
    print(f"Activated provider profile: {name}", flush=True)


@provider_app.command("add")
def provider_add(
    name: str = typer.Argument(..., help="Provider profile name"),
    label: str = typer.Option(..., "--label", help="Display label"),
    provider: str = typer.Option(..., "--provider", help="Runtime provider id"),
    api_format: str = typer.Option(..., "--api-format", help="API format"),
    auth_source: str = typer.Option(..., "--auth-source", help="Auth source name"),
    model: str = typer.Option(..., "--model", help="Default model"),
    base_url: str | None = typer.Option(None, "--base-url", help="Optional base URL"),
    credential_slot: str | None = typer.Option(None, "--credential-slot", help="Optional profile-specific credential slot"),
    allowed_models: list[str] | None = typer.Option(None, "--allowed-model", help="Allowed model values for this profile"),
    context_window_tokens: int | None = typer.Option(None, "--context-window-tokens", help="Optional context window override for auto-compact"),
    auto_compact_threshold_tokens: int | None = typer.Option(None, "--auto-compact-threshold-tokens", help="Optional explicit auto-compact threshold override"),
) -> None:
    """Create a provider profile."""
    from openharness.auth.manager import AuthManager
    from openharness.config.settings import ProviderProfile

    manager = AuthManager()
    manager.upsert_profile(
        name,
        ProviderProfile(
            label=label,
            provider=provider,
            api_format=api_format,
            auth_source=auth_source,
            default_model=model,
            last_model=model,
            base_url=base_url,
            credential_slot=credential_slot or _default_credential_slot_for_profile(name, auth_source),
            allowed_models=allowed_models or ([model] if credential_slot or _default_credential_slot_for_profile(name, auth_source) else []),
            context_window_tokens=context_window_tokens,
            auto_compact_threshold_tokens=auto_compact_threshold_tokens,
        ),
    )
    print(f"Saved provider profile: {name}", flush=True)


@provider_app.command("edit")
def provider_edit(
    name: str = typer.Argument(..., help="Provider profile name"),
    label: str | None = typer.Option(None, "--label", help="Display label"),
    provider: str | None = typer.Option(None, "--provider", help="Runtime provider id"),
    api_format: str | None = typer.Option(None, "--api-format", help="API format"),
    auth_source: str | None = typer.Option(None, "--auth-source", help="Auth source name"),
    model: str | None = typer.Option(None, "--model", help="Default model"),
    base_url: str | None = typer.Option(None, "--base-url", help="Optional base URL"),
    credential_slot: str | None = typer.Option(None, "--credential-slot", help="Optional profile-specific credential slot"),
    allowed_models: list[str] | None = typer.Option(None, "--allowed-model", help="Allowed model values for this profile"),
    context_window_tokens: int | None = typer.Option(None, "--context-window-tokens", help="Optional context window override for auto-compact"),
    auto_compact_threshold_tokens: int | None = typer.Option(None, "--auto-compact-threshold-tokens", help="Optional explicit auto-compact threshold override"),
) -> None:
    """Edit a provider profile."""
    from openharness.auth.manager import AuthManager

    manager = AuthManager()
    try:
        manager.update_profile(
            name,
            label=label,
            provider=provider,
            api_format=api_format,
            auth_source=auth_source,
            default_model=model,
            last_model=model,
            base_url=base_url,
            credential_slot=credential_slot,
            allowed_models=allowed_models,
            context_window_tokens=context_window_tokens,
            auto_compact_threshold_tokens=auto_compact_threshold_tokens,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(1)
    print(f"Updated provider profile: {name}", flush=True)


@provider_app.command("remove")
def provider_remove(
    name: str = typer.Argument(..., help="Provider profile name"),
) -> None:
    """Remove a provider profile."""
    from openharness.auth.manager import AuthManager

    manager = AuthManager()
    try:
        manager.remove_profile(name)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(1)
    print(f"Removed provider profile: {name}", flush=True)

# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        callback=_version_callback,
        is_eager=True,
    ),
    # --- Session ---
    continue_session: bool = typer.Option(
        False,
        "--continue",
        "-c",
        help="Continue the most recent conversation in the current directory",
        rich_help_panel="Session",
    ),
    resume: str | None = typer.Option(
        None,
        "--resume",
        "-r",
        help="Resume a conversation by session ID, or open picker",
        rich_help_panel="Session",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Set a display name for this session",
        rich_help_panel="Session",
    ),
    # --- Model & Effort ---
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Model alias (e.g. 'sonnet', 'opus') or full model ID",
        rich_help_panel="Model & Effort",
    ),
    effort: str | None = typer.Option(
        None,
        "--effort",
        help="Effort level for the session (low, medium, high, max)",
        rich_help_panel="Model & Effort",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Override verbose mode setting from config",
        rich_help_panel="Model & Effort",
    ),
    max_turns: int | None = typer.Option(
        None,
        "--max-turns",
        help="Maximum number of agentic turns (enforced by default in --print; optional cap for interactive mode)",
        rich_help_panel="Model & Effort",
    ),
    # --- Output ---
    print_mode: str | None = typer.Option(
        None,
        "--print",
        "-p",
        help="Print response and exit. Pass your prompt as the value: -p 'your prompt'",
        rich_help_panel="Output",
    ),
    output_format: str | None = typer.Option(
        None,
        "--output-format",
        help="Output format with --print: text (default), json, or stream-json",
        rich_help_panel="Output",
    ),
    # --- Permissions ---
    permission_mode: str | None = typer.Option(
        None,
        "--permission-mode",
        help="Permission mode: default, plan, or full_auto",
        rich_help_panel="Permissions",
    ),
    dangerously_skip_permissions: bool = typer.Option(
        False,
        "--dangerously-skip-permissions",
        help="Bypass all permission checks (only for sandboxed environments)",
        rich_help_panel="Permissions",
    ),
    allowed_tools: Optional[list[str]] = typer.Option(
        None,
        "--allowed-tools",
        help="Comma or space-separated list of tool names to allow",
        rich_help_panel="Permissions",
    ),
    disallowed_tools: Optional[list[str]] = typer.Option(
        None,
        "--disallowed-tools",
        help="Comma or space-separated list of tool names to deny",
        rich_help_panel="Permissions",
    ),
    # --- System & Context ---
    system_prompt: str | None = typer.Option(
        None,
        "--system-prompt",
        "-s",
        help="Override the default system prompt",
        rich_help_panel="System & Context",
    ),
    append_system_prompt: str | None = typer.Option(
        None,
        "--append-system-prompt",
        help="Append text to the default system prompt",
        rich_help_panel="System & Context",
    ),
    settings_file: str | None = typer.Option(
        None,
        "--settings",
        help="Path to a JSON settings file or inline JSON string",
        rich_help_panel="System & Context",
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help="Anthropic-compatible API base URL",
        rich_help_panel="System & Context",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key (overrides config and environment)",
        rich_help_panel="System & Context",
    ),
    bare: bool = typer.Option(
        False,
        "--bare",
        help="Minimal mode: skip hooks, plugins, MCP, and auto-discovery",
        rich_help_panel="System & Context",
    ),
    api_format: str | None = typer.Option(
        None,
        "--api-format",
        help="API format: 'anthropic' (default), 'openai' (DashScope, GitHub Models, etc.), or 'copilot' (GitHub Copilot)",
        rich_help_panel="System & Context",
    ),
    theme: str | None = typer.Option(
        None,
        "--theme",
        help="TUI theme: default, dark, minimal, cyberpunk, solarized, or custom name",
        rich_help_panel="System & Context",
    ),
    # --- Advanced ---
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug logging",
        rich_help_panel="Advanced",
    ),
    mcp_config: Optional[list[str]] = typer.Option(
        None,
        "--mcp-config",
        help="Load MCP servers from JSON files or strings",
        rich_help_panel="Advanced",
    ),
    cwd: str = typer.Option(
        str(Path.cwd()),
        "--cwd",
        help="Working directory for the session",
        hidden=True,
    ),
    backend_only: bool = typer.Option(
        False,
        "--backend-only",
        help="Run the structured backend host for the React terminal UI",
        hidden=True,
    ),
    task_worker: bool = typer.Option(
        False,
        "--task-worker",
        help="Run the stdin-driven headless worker loop used for background agent tasks",
        hidden=True,
    ),
) -> None:
    """Start an interactive session or run a single prompt."""
    if ctx.invoked_subcommand is not None:
        return

    import asyncio
    import logging

    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
            stream=sys.stderr,
        )
        logging.getLogger("openharness").setLevel(logging.DEBUG)
    elif os.environ.get("OPENHARNESS_LOG_LEVEL"):
        lvl = getattr(logging, os.environ["OPENHARNESS_LOG_LEVEL"].upper(), logging.WARNING)
        logging.basicConfig(level=lvl, format="%(asctime)s [%(name)s] %(levelname)s %(message)s", stream=sys.stderr)

    if dangerously_skip_permissions:
        permission_mode = "full_auto"

    # Apply --theme override to settings
    if theme:
        from openharness.config.settings import load_settings, save_settings

        settings = load_settings()
        settings.theme = theme
        save_settings(settings)

    from openharness.ui.app import run_print_mode, run_repl, run_task_worker

    # Handle --continue and --resume flags
    if continue_session or resume is not None:
        from openharness.services.session_storage import (
            list_session_snapshots,
            load_session_by_id,
            load_session_snapshot,
        )

        session_data = None
        if continue_session:
            session_data = load_session_snapshot(cwd)
            if session_data is None:
                print("No previous session found in this directory.", file=sys.stderr)
                raise typer.Exit(1)
            print(f"Continuing session: {session_data.get('summary', '(untitled)')[:60]}")
        elif resume == "" or resume is None:
            # --resume with no value: show session picker
            sessions = list_session_snapshots(cwd, limit=10)
            if not sessions:
                print("No saved sessions found.", file=sys.stderr)
                raise typer.Exit(1)
            print("Saved sessions:")
            for i, s in enumerate(sessions, 1):
                print(f"  {i}. [{s['session_id']}] {s.get('summary', '?')[:50]} ({s['message_count']} msgs)")
            choice = typer.prompt("Enter session number or ID")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(sessions):
                    session_data = load_session_by_id(cwd, sessions[idx]["session_id"])
                else:
                    print("Invalid selection.", file=sys.stderr)
                    raise typer.Exit(1)
            except ValueError:
                session_data = load_session_by_id(cwd, choice)
            if session_data is None:
                print(f"Session not found: {choice}", file=sys.stderr)
                raise typer.Exit(1)
        else:
            session_data = load_session_by_id(cwd, resume)
            if session_data is None:
                print(f"Session not found: {resume}", file=sys.stderr)
                raise typer.Exit(1)

        # Pass restored session to the REPL
        asyncio.run(
            run_repl(
                prompt=None,
                cwd=cwd,
                model=session_data.get("model") or model,
                backend_only=backend_only,
                base_url=base_url,
                system_prompt=system_prompt,
                api_key=api_key,
                restore_messages=session_data.get("messages"),
                restore_tool_metadata=session_data.get("tool_metadata"),
                permission_mode=permission_mode,
                api_format=api_format,
            )
        )
        return

    if print_mode is not None:
        prompt = print_mode.strip()
        if not prompt:
            print("Error: -p/--print requires a prompt value, e.g. -p 'your prompt'", file=sys.stderr)
            raise typer.Exit(1)
        asyncio.run(
            run_print_mode(
                prompt=prompt,
                output_format=output_format or "text",
                cwd=cwd,
                model=model,
                base_url=base_url,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
                api_key=api_key,
                api_format=api_format,
                permission_mode=permission_mode,
                max_turns=max_turns,
            )
        )
        return

    if task_worker:
        asyncio.run(
            run_task_worker(
                cwd=cwd,
                model=model,
                max_turns=max_turns,
                base_url=base_url,
                system_prompt=system_prompt,
                api_key=api_key,
                api_format=api_format,
                permission_mode=permission_mode,
            )
        )
        return

    asyncio.run(
        run_repl(
            prompt=None,
            cwd=cwd,
            model=model,
            max_turns=max_turns,
            backend_only=backend_only,
            base_url=base_url,
            system_prompt=system_prompt,
            api_key=api_key,
            api_format=api_format,
            permission_mode=permission_mode,
        )
    )
