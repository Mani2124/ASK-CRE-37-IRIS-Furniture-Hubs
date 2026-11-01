"""PostGIS access for the IRIS local staging table.

Only iris_staging.commercial_poi_staging is written. Schema setup is an
explicit local-development action; normal writes never change the schema.
"""

import json
import logging
import os
from urllib.parse import urlparse

LOG = logging.getLogger(__name__)
TABLE = "iris_staging.commercial_poi_staging"
REQUIRED_COLUMNS = {
    "record_key",
    "store_osm_id",
    "brand",
    "store_name",
    "feature_type",
    "area_m2",
    "association_status",
    "source",
    "osm_tags",
    "geom",
    "updated_at",
}

DDL = """CREATE SCHEMA IF NOT EXISTS iris_staging;
CREATE TABLE IF NOT EXISTS iris_staging.commercial_poi_staging (
    record_key text PRIMARY KEY,
    store_osm_id text NOT NULL,
    brand text NOT NULL,
    store_name text NOT NULL,
    feature_type text NOT NULL,
    area_m2 double precision,
    association_status text NOT NULL,
    source text NOT NULL,
    osm_tags jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Geometry, 25832),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS commercial_poi_staging_geom_gix_v2
    ON iris_staging.commercial_poi_staging USING gist (geom);"""

UPSERT = """INSERT INTO iris_staging.commercial_poi_staging
    (record_key, store_osm_id, brand, store_name, feature_type, area_m2,
     association_status, source, osm_tags, geom)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
        ST_SetSRID(ST_GeomFromGeoJSON(%s), 25832))
ON CONFLICT (record_key) DO UPDATE SET
    store_osm_id = EXCLUDED.store_osm_id,
    brand = EXCLUDED.brand,
    store_name = EXCLUDED.store_name,
    feature_type = EXCLUDED.feature_type,
    area_m2 = EXCLUDED.area_m2,
    association_status = EXCLUDED.association_status,
    source = EXCLUDED.source,
    osm_tags = EXCLUDED.osm_tags,
    geom = EXCLUDED.geom,
    updated_at = now();"""


def _uri(db_uri=None):
    uri = db_uri or os.getenv("DB_URI")
    if not uri:
        raise ValueError("DB_URI is missing. Set it before starting Streamlit.")
    return uri


def _columns(cur):
    cur.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_schema = 'iris_staging'
                     AND table_name = 'commercial_poi_staging'""")
    return {row[0] for row in cur.fetchall()}


def _validate(cur):
    missing = REQUIRED_COLUMNS - _columns(cur)
    if missing:
        raise RuntimeError(
            "Local PostGIS table has an incompatible schema. Missing: "
            + ", ".join(sorted(missing))
            + ". Use 'Prepare local staging table' in the dashboard."
        )


def check(db_uri=None):
    """Read connection status and count, without modifying the database."""
    import psycopg

    with psycopg.connect(_uri(db_uri), connect_timeout=15) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            database = cur.fetchone()[0]
            cur.execute("SELECT to_regclass('iris_staging.commercial_poi_staging')")
            exists = cur.fetchone()[0] is not None
            columns = _columns(cur) if exists else set()
            count = None
            if exists:
                cur.execute("SELECT COUNT(*) FROM iris_staging.commercial_poi_staging")
                count = cur.fetchone()[0]
    return {
        "database": database,
        "exists": exists,
        "count": count,
        "schema_ok": REQUIRED_COLUMNS.issubset(columns),
        "missing_columns": sorted(REQUIRED_COLUMNS - columns),
    }


def initialize_local(db_uri=None):
    """Create/repair only a local EMPTY staging table, preserving the old one.

    If a previous incompatible table exists, rename it to a backup rather than
    deleting it. Refuse to touch a populated table or remote database.
    """
    import psycopg

    uri = _uri(db_uri)
    parsed = urlparse(uri)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Schema preparation is restricted to localhost.")

    with psycopg.connect(uri, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            cur.execute("CREATE SCHEMA IF NOT EXISTS iris_staging")
            cur.execute("SELECT to_regclass('iris_staging.commercial_poi_staging')")
            exists = cur.fetchone()[0] is not None
            if exists and not REQUIRED_COLUMNS.issubset(_columns(cur)):
                cur.execute("SELECT COUNT(*) FROM iris_staging.commercial_poi_staging")
                if cur.fetchone()[0] != 0:
                    raise RuntimeError(
                        "Existing staging table contains records; no automatic migration performed."
                    )
                cur.execute(
                    "SELECT to_regclass('iris_staging.commercial_poi_staging_legacy_backup')"
                )
                if cur.fetchone()[0] is not None:
                    raise RuntimeError(
                        "Legacy backup table already exists; inspect it before retrying."
                    )
                cur.execute("""ALTER TABLE iris_staging.commercial_poi_staging
                               RENAME TO commercial_poi_staging_legacy_backup""")
            cur.execute(DDL)
            _validate(cur)
    return check(uri)


def load(store, rows, db_uri=None, initialize=False):
    """Upsert projected polygons; return the number of processed records."""
    import psycopg

    uri = _uri(db_uri)
    if initialize:
        initialize_local(uri)
    if not rows:
        return 0

    with psycopg.connect(uri, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            _validate(cur)
            for row in rows:
                key = f"{store['osm_id']}|{row['kind']}|{row['feature_id']}"
                cur.execute(
                    UPSERT,
                    (
                        key,
                        store["osm_id"],
                        store["brand"],
                        store["name"],
                        row["kind"],
                        row["area_m2"],
                        row["association"],
                        row["source"],
                        json.dumps(row["osm_tags"]),
                        json.dumps(row["geometry_25832"]),
                    ),
                )
    LOG.info("Upserted %d polygons into %s", len(rows), TABLE)
    return len(rows)
