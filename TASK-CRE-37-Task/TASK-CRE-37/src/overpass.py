"""OpenStreetMap Overpass discovery, federal-state scoping and stable OSM IDs."""

import logging, re, time
import requests

LOG = logging.getLogger(__name__)
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
STATES = {
    "All Germany": "DE",
    "Baden-Württemberg": "DE-BW",
    "Bavaria (Bayern)": "DE-BY",
    "Berlin": "DE-BE",
    "Brandenburg": "DE-BB",
    "Bremen": "DE-HB",
    "Hamburg": "DE-HH",
    "Hesse (Hessen)": "DE-HE",
    "Lower Saxony (Niedersachsen)": "DE-NI",
    "Mecklenburg-Vorpommern": "DE-MV",
    "North Rhine-Westphalia (NRW)": "DE-NW",
    "Rhineland-Palatinate": "DE-RP",
    "Saarland": "DE-SL",
    "Saxony (Sachsen)": "DE-SN",
    "Saxony-Anhalt": "DE-ST",
    "Schleswig-Holstein": "DE-SH",
    "Thuringia (Thüringen)": "DE-TH",
}
BRANDS = {
    "XXXLutz": r"XXXLutz|XXXL\s*Lutz",
    "Höffner": r"Höffner|Hoeffner",
    "Porta": r"\bporta\b",
    "Segmüller": r"Segmüller|Segmueller",
}


def query_stores(state="DE"):
    if state not in STATES.values():
        raise ValueError("Unknown German federal-state code")
    area = (
        'area["ISO3166-1"="DE"][admin_level=2]'
        if state == "DE"
        else f'area["ISO3166-2"="{state}"][admin_level=4]'
    )
    regex = "XXXLutz|XXXL Lutz|Höffner|Hoeffner|porta|Porta|Segmüller|Segmueller"
    # Match brands and names independently, including POIs that lack shop=furniture.
    return f"""[out:json][timeout:180];{area}->.region;(nwr["shop"="furniture"]["brand"~"{regex}",i](area.region);nwr["shop"="furniture"]["name"~"{regex}",i](area.region);nwr["brand"~"{regex}",i](area.region););out center;"""


def query_near(lat, lon, radius=350):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180 and 50 <= radius <= 1000):
        raise ValueError("Invalid coordinates or radius")
    return f"""[out:json][timeout:90];(way["building"](around:{radius},{lat:.7f},{lon:.7f});relation["building"](around:{radius},{lat:.7f},{lon:.7f});way["amenity"="parking"](around:{radius},{lat:.7f},{lon:.7f});relation["amenity"="parking"](around:{radius},{lat:.7f},{lon:.7f}););out geom;"""


def fetch(query, session=None, endpoints=None, retries=0, read_timeout=210):
    session = session or requests.Session()
    endpoints = endpoints or ENDPOINTS
    last = None
    for endpoint in endpoints:
        for attempt in range(retries + 1):
            try:
                response = session.post(
                    endpoint,
                    data={"data": query},
                    timeout=(10, read_timeout),
                    headers={
                        "User-Agent": "IRIS-TASK-CRE-37/1.1 (geospatial candidate assessment)"
                    },
                )
                if response.status_code in (429, 502, 503, 504):
                    raise requests.HTTPError(f"Temporary HTTP {response.status_code}")
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or not isinstance(
                    data.get("elements"), list
                ):
                    raise ValueError("Unexpected Overpass response")
                if data.get("remark"):
                    raise ValueError(f'Incomplete Overpass response: {data["remark"]}')
                LOG.info(
                    "Overpass returned %d elements from %s",
                    len(data["elements"]),
                    endpoint,
                )
                return data
            except (requests.RequestException, ValueError) as exc:
                last = exc
                LOG.warning("Overpass %s attempt %d: %s", endpoint, attempt + 1, exc)
                if attempt < retries:
                    time.sleep(2**attempt)
    raise RuntimeError(f"All Overpass endpoints failed: {last}")


def brand_for(tags):
    label = " ".join(str(tags.get(k, "")) for k in ("brand", "name", "operator"))
    for brand, pattern in BRANDS.items():
        if re.search(pattern, label, re.I):
            return brand
    return None


def location_for(element):
    """Retain ways/relations even when out geom has no center field."""
    import math
    from shapely.geometry import Polygon

    def valid(lat, lon):
        try:
            return (
                math.isfinite(float(lat))
                and math.isfinite(float(lon))
                and -90 <= float(lat) <= 90
                and -180 <= float(lon) <= 180
            )
        except (TypeError, ValueError):
            return False

    for label, obj in [
        ("osm_node", element),
        ("overpass_center", element.get("center") or {}),
    ]:
        if valid(obj.get("lat"), obj.get("lon")):
            return float(obj["lat"]), float(obj["lon"]), label
    coords = [
        (p.get("lon"), p.get("lat"))
        for p in element.get("geometry", [])
        if valid(p.get("lat"), p.get("lon"))
    ]
    if len(coords) >= 4 and coords[0] == coords[-1]:
        from shapely import make_valid

        geom = make_valid(Polygon(coords))
        if not geom.is_empty:
            point = geom.representative_point()
            return point.y, point.x, "polygon_representative_point"
    # Relation members carry coordinates when relation has no top-level geometry.
    if not coords:
        coords = [
            (p["lon"], p["lat"])
            for member in element.get("members", [])
            for p in member.get("geometry", [])
            if valid(p.get("lat"), p.get("lon"))
        ]
    if coords:
        xs, ys = zip(*coords)
        return (
            (min(ys) + max(ys)) / 2,
            (min(xs) + max(xs)) / 2,
            "geometry_bounds_center",
        )
    bounds = element.get("bounds") or {}
    if valid(bounds.get("minlat"), bounds.get("minlon")) and valid(
        bounds.get("maxlat"), bounds.get("maxlon")
    ):
        return (
            (bounds["minlat"] + bounds["maxlat"]) / 2,
            (bounds["minlon"] + bounds["maxlon"]) / 2,
            "overpass_bounds_center",
        )
    return None


def parse_stores(data, diagnostics=None):
    found = {}
    counts = {
        "raw_elements": len(data.get("elements", [])),
        "unmatched_brand": 0,
        "missing_location": 0,
        "duplicate_osm_id": 0,
        "kept": 0,
    }
    for element in data.get("elements", []):
        tags = element.get("tags") or {}
        brand = brand_for(tags)
        if not brand:
            counts["unmatched_brand"] += 1
            continue
        location = location_for(element)
        if location is None:
            counts["missing_location"] += 1
            continue
        lat, lon, method = location
        key = f"{element.get('type')}/{element.get('id')}"
        if key in found:
            counts["duplicate_osm_id"] += 1
        found[key] = {
            "osm_id": key,
            "brand": brand,
            "name": tags.get("name") or brand,
            "lat": lat,
            "lon": lon,
            "location_method": method,
            "state_tag": tags.get("addr:state", ""),
            "city": tags.get("addr:city", ""),
            "source": "OpenStreetMap / Overpass API",
            "osm_tags": tags,
            "geometry": [
                (p["lon"], p["lat"])
                for p in element.get("geometry", [])
                if "lon" in p and "lat" in p
            ],
        }
    counts["kept"] = len(found)
    LOG.info("Store parsing audit: %s", counts)
    if diagnostics is not None:
        diagnostics.update(counts)
    return sorted(
        found.values(), key=lambda x: (x["brand"], x["city"], x["name"], x["osm_id"])
    )
