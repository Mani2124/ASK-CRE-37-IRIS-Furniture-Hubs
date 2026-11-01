"""Regression checks for PostGIS and store discovery."""

from src.db import DDL, UPSERT, REQUIRED_COLUMNS
from src.overpass import query_stores


def test_store_search_does_not_request_full_geometry():
    query = query_stores("DE")
    assert "out center;" in query
    assert "out center geom;" not in query


def test_postgis_schema_and_upsert_agree():
    for column in ("record_key", "feature_type", "association_status", "geom"):
        assert column in REQUIRED_COLUMNS
        assert column in DDL
        assert column in UPSERT


def test_no_production_schema_writes():
    assert "iris_core" not in DDL + UPSERT
