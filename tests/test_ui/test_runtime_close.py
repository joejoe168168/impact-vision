from __future__ import annotations

from pathlib import Path

import pytest

from openharness.ui.runtime import build_runtime, close_runtime


class _ClosableApiClient:
    def __init__(self) -> None:
        self.closed = False

    async def stream_message(self, request):
        del request
        if False:
            yield None

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_close_runtime_closes_api_client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    client = _ClosableApiClient()

    bundle = await build_runtime(cwd=str(tmp_path), api_client=client)
    await close_runtime(bundle)

    assert client.closed is True
