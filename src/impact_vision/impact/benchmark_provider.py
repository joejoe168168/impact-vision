"""One benchmark provider over ``data/benchmarks.yaml`` (v7 W5.1).

Before W5.1 four modules each held their own benchmark data:
:mod:`~impact_vision.impact.benchmarks` (sector 5D averages, GIIN survey),
:mod:`~impact_vision.impact.giin_benchmarks` (KPI distributions),
:mod:`~impact_vision.impact.external_benchmarks` (5D peer percentiles) and
:mod:`~impact_vision.impact.engagements.value_creation` (sample observations).
The data now lives in one YAML file. :class:`ImpactBenchmarkProvider` is the
single object that answers every benchmark question, and it satisfies both
provider protocols:

* ``ExternalBenchmarkProvider`` — ``id`` + ``percentiles(sector, dimension)``
* engagement-suite ``BenchmarkProvider`` — ``name`` + ``fetch(query)``

A licensed feed replaces it by implementing the same two methods and
registering through ``external_benchmarks.register_benchmark_provider`` /
``value_creation.set_default_benchmark_provider``.
"""

from __future__ import annotations

from typing import Any

from impact_vision.impact.knowledge import effective_provenance, load_knowledge


class ImpactBenchmarkProvider:
    """Offline provider for every benchmark set in ``data/benchmarks.yaml``."""

    id = "impact_vision"
    name = "impact_vision"

    # -- 5D peer percentiles (ExternalBenchmarkProvider protocol) ----------
    def percentiles(self, sector: str, dimension: str):  # noqa: ANN201
        from impact_vision.impact.external_benchmarks import OfflineBenchmarkProvider

        return OfflineBenchmarkProvider().percentiles(sector, dimension)  # type: ignore[arg-type]

    # -- metric observations (engagement BenchmarkProvider protocol) -------
    def fetch(self, query):  # noqa: ANN001, ANN201
        """GIIN KPI distribution when one matches, else the sample observations."""
        from impact_vision.impact.engagements.value_creation import get_default_benchmark_provider
        from impact_vision.impact.giin_benchmarks import GIINImpactBenchmarkProvider

        result = GIINImpactBenchmarkProvider().fetch(query)
        if result.sample_size:
            return result.model_copy(update={"provider": self.name})
        fallback = get_default_benchmark_provider().fetch(query)
        return fallback.model_copy(update={"provider": self.name})

    # -- direct accessors -------------------------------------------------
    def sector_profile(self, sector: str):  # noqa: ANN201
        from impact_vision.impact.benchmarks import get_benchmark

        return get_benchmark(sector)

    def kpi(self, sector: str, metric_id: str):  # noqa: ANN201
        from impact_vision.impact.giin_benchmarks import get_giin_benchmark

        return get_giin_benchmark(sector, metric_id)

    def survey(self) -> dict[str, Any]:
        from impact_vision.impact.benchmarks import GIIN_SURVEY_BENCHMARKS

        return dict(GIIN_SURVEY_BENCHMARKS)

    def provenance(self, section: str) -> dict[str, Any]:
        """Provenance for one section (``sector_5d``, ``kpi``, ``peer_percentiles`` …)."""
        payload = load_knowledge("benchmarks.yaml")
        block = payload.get(section)
        meta = block if isinstance(block, dict) else {}
        return effective_provenance({k: v for k, v in meta.items() if k != "rows"}, payload)


_PROVIDER = ImpactBenchmarkProvider()


def get_impact_benchmark_provider() -> ImpactBenchmarkProvider:
    return _PROVIDER


def _register() -> None:
    from impact_vision.impact.external_benchmarks import register_benchmark_provider

    register_benchmark_provider(_PROVIDER)  # type: ignore[arg-type]


_register()


__all__ = ["ImpactBenchmarkProvider", "get_impact_benchmark_provider"]
