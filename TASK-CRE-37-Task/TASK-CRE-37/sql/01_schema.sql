-- DDL is a proposed staging-only schema; confirm with Tariq before shared database use.
CREATE SCHEMA IF NOT EXISTS iris_staging;
CREATE TABLE IF NOT EXISTS iris_staging.commercial_poi_staging (
 record_key text PRIMARY KEY, store_osm_id text NOT NULL, brand text NOT NULL,
 store_name text NOT NULL, feature_type text NOT NULL,
 area_m2 double precision, association_status text NOT NULL,
 source text NOT NULL, osm_tags jsonb NOT NULL DEFAULT '{}'::jsonb,
 geom geometry(Geometry,25832), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS commercial_poi_staging_geom_gix ON iris_staging.commercial_poi_staging USING gist(geom);
