"""Cache plotly.min.js locally so headless screenshots render charts offline."""
import sys
import urllib.request
from pathlib import Path

URL = "https://cdn.plot.ly/plotly-2.27.0.min.js"
OUT = Path(__file__).resolve().parent / ".cache" / "plotly-2.27.0.min.js"

OUT.parent.mkdir(parents=True, exist_ok=True)
try:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=60).read()
    OUT.write_bytes(data)
    print(f"cached {len(data):,} bytes -> {OUT}")
except Exception as e:  # noqa: BLE001
    print("FETCH FAILED:", repr(e))
    sys.exit(1)
