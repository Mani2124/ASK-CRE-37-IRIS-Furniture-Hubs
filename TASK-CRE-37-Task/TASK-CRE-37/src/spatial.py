"""Build valid projected polygon records; no fabricated roof or parking areas."""

import logging
from shapely.geometry import Polygon, MultiPolygon, shape, mapping
from shapely.ops import transform, unary_union
from shapely.validation import explain_validity
from shapely import make_valid
from pyproj import Transformer

LOG = logging.getLogger(__name__)
PROJECT = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True).transform
TO_WGS = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True).transform


def rings_from_element(e):
    if e.get("type") == "way":
        coords = [
            (p["lon"], p["lat"])
            for p in e.get("geometry", [])
            if "lon" in p and "lat" in p
        ]
        return [coords] if len(coords) >= 4 and coords[0] == coords[-1] else []
    # Relation geometry: only accept complete closed outer member rings. Never bridge missing segments.
    if e.get("type") == "relation":
        return [
            [(p["lon"], p["lat"]) for p in m["geometry"]]
            for m in e.get("members", [])
            if m.get("role") == "outer"
            and m.get("geometry")
            and len(m["geometry"]) >= 4
            and m["geometry"][0] == m["geometry"][-1]
        ]
    return []


def parse_polygons(data, store):
    out = []
    counts = {"processed": 0, "failed": 0, "skipped": 0}
    for e in data.get("elements", []):
        tags = e.get("tags") or {}
        kind = (
            "parking"
            if tags.get("amenity") == "parking"
            else "building" if "building" in tags else None
        )
        if kind is None:
            continue
        counts["processed"] += 1
        try:
            rings = rings_from_element(e)
            if not rings:
                counts["skipped"] += 1
                continue
            # Multipolygon relations with holes/fragmented outer rings need a topology-aware assembler.
            # Skip incomplete/complex relations rather than misreport area.
            if e.get("type") == "relation" and (
                len(rings) != 1
                or any(m.get("role") == "inner" for m in e.get("members", []))
            ):
                counts["skipped"] += 1
                continue
            geom = (
                Polygon(rings[0])
                if len(rings) == 1
                else MultiPolygon([Polygon(r) for r in rings])
            )
            if not geom.is_valid:
                geom = make_valid(geom)
            if geom.is_empty:
                counts["skipped"] += 1
                continue
            if geom.geom_type == "GeometryCollection":
                polys = [
                    g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")
                ]
                geom = unary_union(polys) if polys else Polygon()
            if geom.is_empty or geom.geom_type not in ("Polygon", "MultiPolygon"):
                counts["skipped"] += 1
                continue
            projected = transform(PROJECT, geom)
            if projected.is_empty or projected.area <= 0:
                counts["skipped"] += 1
                continue
            out.append(
                {
                    "feature_id": f"{e['type']}/{e['id']}",
                    "store_id": store["osm_id"],
                    "kind": kind,
                    "area_m2": round(projected.area, 2),
                    "geometry_25832": mapping(projected),
                    "geometry_wgs84": mapping(geom),
                    "association": "nearby_unverified",
                    "source": "OpenStreetMap / Overpass API",
                    "osm_tags": tags,
                }
            )
        except (ValueError, TypeError, KeyError) as ex:
            counts["failed"] += 1
            LOG.warning("Skipped feature %s/%s: %s", e.get("type"), e.get("id"), ex)
    return out, counts


def geojson_features(rows):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": r["feature_id"],
                "geometry": r["geometry_wgs84"],
                "properties": {
                    k: r[k]
                    for k in (
                        "store_id",
                        "feature_id",
                        "kind",
                        "area_m2",
                        "association",
                        "source",
                        "association_confidence",
                        "match_evidence",
                        "distance_to_store_m",
                    )
                    if k in r
                },
            }
            for r in rows
        ],
    }
