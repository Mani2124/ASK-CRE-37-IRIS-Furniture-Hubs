import json
from pathlib import Path
from shapely.geometry import shape
from src.overpass import brand_for, parse_stores, query_near, query_stores
from src.spatial import parse_polygons, geojson_features
from src.db import DDL, UPSERT
from src.pipeline import run

ROOT = Path(__file__).resolve().parent.parent


def test_brands():
    assert brand_for({"brand": "Höffner"}) == "Höffner"
    assert brand_for({"name": "Segmüller Möbel"}) == "Segmüller"
    assert brand_for({"name": "unrelated"}) is None


def test_store_parse():
    stores = parse_stores(json.loads((ROOT / "fixtures/stores.json").read_text()))
    assert len(stores) == 2 and stores[0]["osm_id"].startswith("node/")


def test_query():
    assert "shop" in query_stores()
    assert "around:350" in query_near(48.1, 11.5)


def test_bad_query():
    import pytest

    with pytest.raises(ValueError):
        query_near(100, 11.5)


def test_geometry():
    store = parse_stores(json.loads((ROOT / "fixtures/stores.json").read_text()))[0]
    data = json.loads((ROOT / "fixtures/nearby.json").read_text())
    rows, counts = parse_polygons(data, store)
    assert len(rows) == 2 and counts["failed"] == 0
    assert all(shape(r["geometry_25832"]).is_valid and r["area_m2"] > 0 for r in rows)
    assert all(r["association"] == "nearby_unverified" for r in rows)
    assert len(geojson_features(rows)["features"]) == 2


def test_staging_only_sql():
    assert "iris_staging.commercial_poi_staging" in DDL
    assert "iris_staging.commercial_poi_staging" in UPSERT
    assert "ON CONFLICT" in UPSERT
    assert "iris_core" not in DDL + UPSERT


def test_offline_pipeline(tmp_path):
    stats = run(offline=True, max_stores=1, output=str(tmp_path))
    assert stats["stores"] == 1 and stats["processed"] == 2
    assert (tmp_path / "features.geojson").exists()
    assert len(json.loads((tmp_path / "features.geojson").read_text())["features"]) == 2


def test_state_scoped_queries():
    from src.overpass import STATES

    assert len(STATES) == 17
    assert "DE-BY" in query_stores("DE-BY")
    assert "ISO3166-1" in query_stores("DE")


def test_all_branches_have_distinct_osm_keys():
    data = {
        "elements": [
            {
                "type": "node",
                "id": 10,
                "lat": 48,
                "lon": 11,
                "tags": {"name": "XXXLutz"},
            },
            {
                "type": "way",
                "id": 10,
                "center": {"lat": 48.1, "lon": 11.1},
                "tags": {"name": "XXXLutz"},
            },
            {
                "type": "node",
                "id": 11,
                "lat": 49,
                "lon": 12,
                "tags": {"name": "Höffner"},
            },
        ]
    }
    ids = [s["osm_id"] for s in parse_stores(data)]
    assert len(ids) == 3 and len(set(ids)) == 3


def test_offline_all_without_limit(tmp_path):
    stats = run(offline=True, max_stores=0, output=str(tmp_path))
    assert stats["stores"] == 2
