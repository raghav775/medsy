"""
Download OpenStreetMap tiles for the Delhi / NCR area and store them in
static/tiles/{z}/{x}/{y}.png so the map works completely offline.

Usage:  python download_tiles.py
"""

import math
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Bounding box: Delhi NCR pharmacy coverage area ──────────────────────────
# Covers all pharmacy locations in the probability engine
MIN_LAT = 28.38
MAX_LAT = 28.75
MIN_LNG = 76.95
MAX_LNG = 77.45

# Zoom levels:
#   10–12 = city/district overview
#   13–14 = neighbourhood / street level (good enough for pharmacy finding)
ZOOM_LEVELS = range(10, 15)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "static", "tiles")

HEADERS = {
    "User-Agent": "Medsy-local-app/1.0 (offline tile cache for development)"
}

MAX_WORKERS = 8          # parallel download threads
DELAY_PER_TILE = 0.02    # seconds between requests per thread


def lat_lng_to_tile(lat: float, lng: float, z: int) -> tuple:
    lat_r = math.radians(lat)
    n = 2 ** z
    x = int((lng + 180) / 360 * n)
    y = int((1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n)
    return x, y


def tile_ranges(z: int) -> tuple:
    x_min, y_max = lat_lng_to_tile(MIN_LAT, MIN_LNG, z)  # SW corner
    x_max, y_min = lat_lng_to_tile(MAX_LAT, MAX_LNG, z)  # NE corner
    return x_min, x_max, y_min, y_max


def all_tiles():
    for z in ZOOM_LEVELS:
        x0, x1, y0, y1 = tile_ranges(z)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                yield z, x, y


def count_tiles() -> int:
    total = 0
    for z in ZOOM_LEVELS:
        x0, x1, y0, y1 = tile_ranges(z)
        total += (x1 - x0 + 1) * (y1 - y0 + 1)
    return total


def download_tile(args) -> str:
    z, x, y = args
    out_path = os.path.join(OUTPUT_DIR, str(z), str(x), f"{y}.png")
    if os.path.exists(out_path):
        return "skip"

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        time.sleep(DELAY_PER_TILE)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        with open(out_path, "wb") as f:
            f.write(data)
        return "ok"
    except Exception as exc:
        return f"err:{exc}"


def main():
    total = count_tiles()
    print(f"Tiles to download (Delhi NCR, zoom {ZOOM_LEVELS.start}-{ZOOM_LEVELS.stop - 1}): {total}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Workers: {MAX_WORKERS}\n")

    for z in ZOOM_LEVELS:
        x0, x1, y0, y1 = tile_ranges(z)
        print(f"  Zoom {z}: x {x0}-{x1}, y {y0}-{y1}  ({(x1-x0+1)*(y1-y0+1)} tiles)")

    print()

    downloaded = skipped = errors = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(download_tile, t): t for t in all_tiles()}
        for i, fut in enumerate(as_completed(futures), 1):
            result = fut.result()
            if result == "ok":
                downloaded += 1
            elif result == "skip":
                skipped += 1
            else:
                errors += 1

            if i % 50 == 0 or i == total:
                elapsed = time.time() - start
                rate = i / elapsed if elapsed else 0
                remaining = (total - i) / rate if rate else 0
                print(
                    f"  {i}/{total}  downloaded={downloaded}  skipped={skipped}"
                    f"  errors={errors}  ~{remaining:.0f}s left"
                )

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.0f}s.  downloaded={downloaded}  skipped={skipped}  errors={errors}")


if __name__ == "__main__":
    main()
