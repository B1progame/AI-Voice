from __future__ import annotations

import httpx
from backend.services.tools.context import ToolContext
from backend.services.tools.errors import ToolError

# Wir nutzen Open-Meteo fürs Geocoding (haben wir schon, ist stabil)
def _geocode(address: str) -> tuple[float, float, str]:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": address, "count": 1, "language": "de", "format": "json"}
    
    with httpx.Client(timeout=5.0) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    
    results = data.get("results") or []
    if not results:
        raise ToolError(f"Adresse nicht gefunden: {address}")
    
    top = results[0]
    return float(top["latitude"]), float(top["longitude"]), top["name"]

def run(args: dict, ctx: ToolContext) -> dict:
    start = args.get("start")
    end = args.get("end")
    mode = args.get("mode", "driving") # driving, cycling, walking

    if not start or not end:
        raise ToolError("Start und Ziel werden benötigt.")

    # 1. Geocoding
    try:
        lat1, lon1, name1 = _geocode(start)
        lat2, lon2, name2 = _geocode(end)
    except Exception as e:
        raise ToolError(f"Konnte Adressen nicht finden: {e}")

    # 2. OSRM Profil wählen
    # OSRM unterstützt: 'driving' (Auto), 'cycling' (Fahrrad), 'walking' (Fuß)
    osrm_mode = "driving"
    if "bike" in mode or "rad" in mode or "cycling" in mode:
        osrm_mode = "bike" # OSRM Public API nutzt oft 'bike' oder 'cycling', wir mappen unten
    elif "walk" in mode or "fuß" in mode or "walking" in mode:
        osrm_mode = "foot"
    
    # Mapping für den öffentlichen Server
    # Server URLs: http://router.project-osrm.org/route/v1/driving/...
    profile_map = {
        "driving": "driving",
        "bike": "cycling",  # OSRM nutzt 'cycling' in der URL (manchmal 'bike' je nach Server, Standard ist cycling)
        "cycling": "cycling",
        "foot": "walking",
        "walking": "walking"
    }
    
    final_profile = profile_map.get(osrm_mode, "driving")

    # 3. Routing Anfrage (Kostenloser Public Server)
    # Format: /route/v1/{profile}/{lon1},{lat1};{lon2},{lat2}
    url = f"http://router.project-osrm.org/route/v1/{final_profile}/{lon1},{lat1};{lon2},{lat2}"
    
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url, params={"overview": "false"})
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        raise ToolError("Routing-Server nicht erreichbar.")

    routes = data.get("routes") or []
    if not routes:
        raise ToolError("Keine Route gefunden.")

    summary = routes[0]
    duration_seconds = summary.get("duration", 0)
    distance_meters = summary.get("distance", 0)

    minutes = round(duration_seconds / 60)
    km = round(distance_meters / 1000, 2)

    return {
        "start": name1,
        "end": name2,
        "mode": final_profile,
        "duration_minutes": minutes,
        "distance_km": km
    }