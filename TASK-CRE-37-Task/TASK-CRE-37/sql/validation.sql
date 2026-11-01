-- Read-only validation. Run inside psql: \i validation.sql
\pset pager off
SELECT brand, COUNT(DISTINCT store_osm_id) AS stored_store_objects,
       COUNT(*) AS polygon_records
FROM iris_staging.commercial_poi_staging GROUP BY brand ORDER BY brand;

SELECT COUNT(*) AS total_records,
 COUNT(*) FILTER (WHERE geom IS NULL OR ST_IsEmpty(geom)) AS missing_geometry,
 COUNT(*) FILTER (WHERE geom IS NOT NULL AND NOT ST_IsValid(geom)) AS invalid_geometry,
 COUNT(*) FILTER (WHERE geom IS NOT NULL AND ST_SRID(geom) <> 25832) AS wrong_srid,
 COUNT(*) - COUNT(DISTINCT record_key) AS duplicate_record_keys
FROM iris_staging.commercial_poi_staging;

SELECT brand, feature_type, association_status, COUNT(*) AS polygons
FROM iris_staging.commercial_poi_staging
GROUP BY brand,feature_type,association_status ORDER BY brand,feature_type,association_status;

-- Idempotency evidence: record row count, reload one identical branch using
-- the dashboard, then rerun this count. No increase is expected for unchanged data.
SELECT COUNT(*) AS row_count FROM iris_staging.commercial_poi_staging;
