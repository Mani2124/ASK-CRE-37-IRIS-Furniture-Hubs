"""Conservative, explainable OSM feature association. Never asserts ownership."""

import re
from shapely.geometry import Point, Polygon, shape
from shapely.ops import transform
from shapely import make_valid
from src.spatial import PROJECT

BRAND_PATTERNS = {
    "XXXLutz": r"xxx\s*lutz",
    "Höffner": r"h[oö]ffner|hoeffner",
    "Porta": r"\bporta\b",
    "Segmüller": r"segm[uü]ller|segmueller",
}


def _store_geometry(store):
    coords = store.get("geometry") or []
    if len(coords) >= 4 and coords[0] == coords[-1]:
        geom = Polygon(coords)
        if not geom.is_valid:
            geom = make_valid(geom)
        if not geom.is_empty and geom.geom_type in ("Polygon", "MultiPolygon"):
            return transform(PROJECT, geom)
    return None


def match_features(rows, store):
    """Label evidence without claiming legal ownership or PV suitability.

    strong_tag_match: feature's own name/brand/operator explicitly matches brand.
    spatial_candidate: building overlaps a mapped store-area polygon.
    nearby_unverified: only geographic proximity is known.
    """
    store_geom = _store_geometry(store)
    center = transform(PROJECT, Point(store["lon"], store["lat"]))
    brand_pattern = BRAND_PATTERNS.get(store["brand"], r"(?!)")
    for row in rows:
        tags = row.get("osm_tags") or {}
        geom = shape(row["geometry_25832"])
        labels = " ".join(str(tags.get(k, "")) for k in ("name", "brand", "operator"))
        distance = round(center.distance(geom), 1)
        row["distance_to_store_m"] = distance
        row["match_evidence"] = "No explicit association; within search radius"
        row["association"] = "nearby_unverified"
        row["association_confidence"] = "unverified"
        if re.search(brand_pattern, labels, re.I):
            row["association"] = "strong_tag_match"
            row["association_confidence"] = "high"
            row["match_evidence"] = (
                "Feature name/brand/operator matches store brand; ownership unverified"
            )
        elif (
            store_geom is not None
            and row["kind"] == "building"
            and store_geom.intersects(geom)
        ):
            intersection = store_geom.intersection(geom).area
            fraction = intersection / geom.area if geom.area else 0
            if fraction >= 0.5:
                row["association"] = "spatial_candidate"
                row["association_confidence"] = "medium"
                row["match_evidence"] = (
                    f"Building overlaps mapped store polygon by {fraction:.0%}; ownership unverified"
                )
        elif row["kind"] == "building" and distance <= 15:
            row["association"] = "spatial_candidate"
            row["association_confidence"] = "low"
            row["match_evidence"] = (
                "Building within 15 m of store POI; ownership unverified"
            )
    # Parking is usually mapped without furniture-brand tags. Spatial association
    # is a *candidate*, not ownership evidence. First compare with the mapped
    # store polygon; then with strongly supported building footprints.
    supported_buildings = [
        shape(r["geometry_25832"])
        for r in rows
        if r["kind"] == "building"
        and r["association"] in ("strong_tag_match", "spatial_candidate")
    ]
    for row in rows:
        if row["kind"] != "parking" or row["association"] != "nearby_unverified":
            continue
        geom = shape(row["geometry_25832"])
        tags = row.get("osm_tags") or {}
        if tags.get("access") in ("private", "no"):
            row["match_evidence"] = (
                "Parking access restricted; no store association established"
            )
            continue
        if store_geom is not None and store_geom.intersects(geom):
            row["association"] = "spatial_candidate"
            row["association_confidence"] = "medium"
            row["match_evidence"] = (
                "Parking intersects mapped store polygon; ownership unverified"
            )
        elif supported_buildings:
            d = min(geom.distance(b) for b in supported_buildings)
            if d <= 40:
                row["association"] = "spatial_candidate"
                row["association_confidence"] = "low"
                row["match_evidence"] = (
                    f"Parking within {d:.1f} m of matched building; ownership unverified"
                )
    return rows
