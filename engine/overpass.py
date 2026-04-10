"""
Fetch real pharmacies near a location from the OpenStreetMap Overpass API.
Results are cached to disk (24 h TTL) so repeated searches are instant.
Falls back to None if the API is unreachable (caller uses hardcoded data).
"""

import json
import math
import os
import time

import requests

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "pharmacy_cache")
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_CACHE_TTL = 86400  # 24 hours


def _cache_path(lat: float, lng: float, radius_m: int) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{lat:.3f}_{lng:.3f}_{radius_m}.json")


def fetch_pharmacies(lat: float, lng: float, radius_m: int = 5000) -> list | None:
    """
    Return a list of pharmacy dicts from Overpass, or None on failure.

    Each dict has: id, name, lat, lng, address, phone, operating_hours,
                   reliability, is_24h, specialties, inventory (empty — uses
                   tier defaults in the scoring engine).
    """
    path = _cache_path(lat, lng, radius_m)
    if os.path.exists(path):
        age = time.time() - os.path.getmtime(path)
        if age < _CACHE_TTL:
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    query = f"""
[out:json][timeout:15];
(
  node["amenity"="pharmacy"](around:{radius_m},{lat},{lng});
  way["amenity"="pharmacy"](around:{radius_m},{lat},{lng});
);
out center body;
"""
    try:
        resp = requests.post(_OVERPASS_URL, data={"data": query}, timeout=15)
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
    except Exception:
        return None

    pharmacies = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en") or "Pharmacy"
        if name.lower() in ("pharmacy", "medical store", "chemist"):
            name = tags.get("operator", name)

        # lat/lng: nodes have it directly; ways have a "center" key
        p_lat = el.get("lat") or el.get("center", {}).get("lat")
        p_lng = el.get("lon") or el.get("center", {}).get("lon")
        if not p_lat or not p_lng:
            continue

        address_parts = [
            tags.get("addr:housenumber", ""),
            tags.get("addr:street", ""),
            tags.get("addr:suburb", ""),
            tags.get("addr:city", ""),
        ]
        address = ", ".join(p for p in address_parts if p) or tags.get("addr:full", "")

        hours = tags.get("opening_hours", "")
        is_24h = "24/7" in hours or "24 hours" in hours.lower()

        pharmacies.append({
            "id": f"osm_{el['id']}",
            "name": name,
            "lat": float(p_lat),
            "lng": float(p_lng),
            "address": address,
            "phone": tags.get("phone") or tags.get("contact:phone") or "",
            "operating_hours": hours or "Hours not listed",
            "reliability": 0.80,   # conservative default for unknown pharmacies
            "is_24h": is_24h,
            "specialties": ["general"],
            "inventory": {},       # scoring engine uses tier defaults
        })

    if not pharmacies:
        return None

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(pharmacies, f, ensure_ascii=False)
    except Exception:
        pass

    return pharmacies
