"""Per-GP plug-in hook (Python entry-point discovery).

Allows a GP to ship their own scoring tweaks, custom benchmarks, or
extractor adapters as a separate pip-installable wheel without forking
Impact Vision. Plug-ins register themselves via the standard
``importlib.metadata`` entry-point machinery.

Supported groups (declare in your wheel's ``pyproject.toml``):

  ``impact_vision.extractors``   → ClaimExtractor instances
  ``impact_vision.verifiers``    → SourceVerifier instances
  ``impact_vision.benchmarks``   → SectorBenchmark dicts (additive)
  ``impact_vision.fund_thesis``  → FundThesis loaders
  ``impact_vision.report_renderers`` → custom IC memo / LP report renderers

Example ``pyproject.toml`` for a downstream GP:

    [project.entry-points."impact_vision.extractors"]
    acme_llm = "acme_iv_plugin:AcmeLLMExtractor"

When `discover_plugins()` runs, the entry-point is loaded and — if it's a
class or factory — instantiated. The resulting object is registered with
the matching subsystem (extractors registry, benchmark store, etc.).
"""
from __future__ import annotations

import importlib.metadata as md
import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


PLUGIN_GROUPS = (
    "impact_vision.extractors",
    "impact_vision.verifiers",
    "impact_vision.benchmarks",
    "impact_vision.fund_thesis",
    "impact_vision.report_renderers",
)


@dataclass
class PluginLoadReport:
    loaded: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (f"plugins: loaded={len(self.loaded)} "
                f"failed={len(self.failed)} skipped={len(self.skipped)}")


def _instantiate(obj):
    """If `obj` looks like a class or factory, call it; otherwise return as-is."""
    if isinstance(obj, type) or callable(obj):
        try:
            return obj()
        except TypeError:
            return obj
    return obj


def discover_plugins(*, group_filter: tuple[str, ...] | None = None) -> PluginLoadReport:
    """Walk all configured entry-point groups and register each plug-in."""
    report = PluginLoadReport()
    groups = group_filter or PLUGIN_GROUPS

    for group in groups:
        try:
            entries = md.entry_points(group=group)
        except TypeError:
            entries = md.entry_points().get(group, [])  # py<3.10 fallback

        for ep in entries:
            try:
                target = ep.load()
                instance = _instantiate(target)
                _register(group, ep.name, instance)
                report.loaded.append(f"{group}::{ep.name}")
            except Exception as exc:  # noqa: BLE001
                log.warning("Plugin %s::%s failed: %s", group, ep.name, exc)
                report.failed.append((f"{group}::{ep.name}", str(exc)))
    return report


def _register(group: str, name: str, instance) -> None:
    if group == "impact_vision.extractors":
        from openharness.impact.extractors import register_extractor
        register_extractor(instance)
    elif group == "impact_vision.verifiers":
        from openharness.impact.extractors import register_verifier
        register_verifier(instance)
    elif group == "impact_vision.benchmarks":
        # Benchmark plug-ins return either a dict {sector: SectorBenchmark}
        # or a list of (sector, SectorBenchmark) tuples. We merge in.
        from openharness.impact.benchmarks import SECTOR_BENCHMARKS
        if isinstance(instance, dict):
            SECTOR_BENCHMARKS.update(instance)
        elif isinstance(instance, (list, tuple)):
            for sector, bench in instance:
                SECTOR_BENCHMARKS[sector] = bench
        else:
            log.warning("Benchmark plug-in %s returned unsupported type %s",
                        name, type(instance).__name__)
    elif group == "impact_vision.fund_thesis":
        # Loaders are exposed as callables — we don't auto-call them here, the
        # main thesis loader picks them up by name.
        from openharness.impact import fund_thesis as ft
        registry = getattr(ft, "_PLUGIN_LOADERS", None)
        if registry is None:
            registry = {}
            setattr(ft, "_PLUGIN_LOADERS", registry)
        registry[name] = instance
    elif group == "impact_vision.report_renderers":
        # IC-memo / LP-report custom renderers
        from openharness.impact import ic_memo as im
        registry = getattr(im, "_PLUGIN_RENDERERS", None)
        if registry is None:
            registry = {}
            setattr(im, "_PLUGIN_RENDERERS", registry)
        registry[name] = instance
    else:
        log.warning("Unknown plugin group: %s", group)
