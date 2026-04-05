"""Fetch the current list of hex/map names from the Foxhole WarAPI and report
which ones have a local image cached in the assets/ folder."""

import os
import requests

SHARD_URL = "https://war-service-live.foxholeservices.com/api"
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")


def get_maps() -> list[str]:
    """Return the list of active map names from the WarAPI."""
    response = requests.get(f"{SHARD_URL}/worldconquest/maps", timeout=10)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    print(f"Fetching map names from: {SHARD_URL}")
    maps = get_maps()
    print(f"Found {len(maps)} hexagons:\n")

    missing = []
    for hex_name in maps:
        img_path = os.path.join(ASSETS_DIR, f"{hex_name}.png")
        status = "OK" if os.path.exists(img_path) else "MISSING"
        if status == "MISSING":
            missing.append(hex_name)
        print(f"  [{status}] {hex_name}")

    print(f"\n{len(maps) - len(missing)}/{len(maps)} images available in assets/")
    if missing:
        print(f"Missing local images for: {missing}")
