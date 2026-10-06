"""Refresh pinned frontend assets and licenses. Runtime pages work without a CDN."""

from pathlib import Path
from urllib.request import urlopen

BASE = Path(__file__).resolve().parents[1] / "app" / "static" / "vendor"
ASSETS = {
    "bootstrap.min.css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
    "bootstrap.bundle.min.js": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
    "chart.umd.min.js": "https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.js",
    "BOOTSTRAP-LICENSE.txt": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/LICENSE",
    "CHARTJS-LICENSE.txt": "https://cdn.jsdelivr.net/npm/chart.js@4.4.8/LICENSE.md",
}


if __name__ == "__main__":
    BASE.mkdir(parents=True, exist_ok=True)
    for filename, url in ASSETS.items():
        with urlopen(url, timeout=30) as response:
            data = response.read()
        (BASE / filename).write_bytes(data)
        print(f"Saved {filename} ({len(data):,} bytes)")
