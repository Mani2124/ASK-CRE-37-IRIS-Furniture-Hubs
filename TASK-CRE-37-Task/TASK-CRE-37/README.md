# TASK-CRE-37 — Furniture hub discovery and polygon assessment

Candidate: Manikandan Somu

## Purpose

This Python application discovers XXXLutz, Höffner, Porta and Segmüller records in Germany using OpenStreetMap/Overpass. It retrieves nearby building and parking polygons, validates supported geometry, calculates areas in EPSG:25832 and loads results into iris_staging.commercial_poi_staging. Streamlit provides discovery, inspection, export and explicit database controls.

## Delivery status

User-reported live discovery: 141 OSM objects. Latest user-reported database result: 25 store objects and 4,313 polygon records across all four brands. These figures are a checkpoint, not a fresh database audit; replace them with final counts from sql/validation.sql before submitting if further data has been loaded.

Discovery counts were compared with the brands’ official websites. Limited network bandwidth prevented downloading and loading the remaining data before the submission deadline. This is partial live coverage, not a claim of a complete nationwide branch inventory. The expected 122 branches were supplied separately and were not verified against an authoritative branch registry. Distinct OSM objects may represent the same physical branch.

## Requirements and execution

Python 3.11 or later. From the project directory:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501. To use your existing PostGIS database, set DB_URI in the terminal before launching the app. Use your own connection details and never commit the actual URI or password.

PowerShell example (placeholders):

```powershell
$env:DB_URI="postgresql://USERNAME:PASSWORD@localhost:5432/DATABASE"
python -m streamlit run app.py
```

Docker provides PostgreSQL 16 / PostGIS 3.4 and the dashboard:

```powershell
docker compose up --build
```

The supplied Compose file uses a local demonstration password default. Configure POSTGRES_PASSWORD locally before starting it. DB_URI inside Compose uses the db service host. Compose does not publish the database port by default; use docker compose exec db psql -U iris -d iris to inspect it. The named database volume persists records. Docker execution must be verified on the reviewer's machine; no successful candidate-side Docker run is asserted here.

Offline examples use synthetic fixtures and must not be represented as live output. Run tests from the project directory:

```powershell
python -m pytest -q
```

## Dashboard guide

See DASHBOARD_GUIDE.md for each control and the complete operating sequence.

## Processing and source mapping

Store discovery uses Germany or federal-state boundaries. The submitted baseline query matches the target names in brand tags, or name tags with shop=furniture. The local parser also considers operator tags. Search spelling coverage is limited to the implemented expressions. Do not claim unrestricted operator-based server discovery in this baseline.

Coordinates enter as OSM longitude/latitude (EPSG:4326). Store ways without a centre can use a geometry-derived representative point; relation/bounds centres are approximate. Supported closed polygon geometry is validated and repaired using Shapely make_valid where needed. Complex relations with holes or fragmented rings are skipped by the current conservative polygon parser; this is a known coverage limitation.

Areas are calculated from projected EPSG:25832 geometry in square metres. GeoPackage downloads retain EPSG:25832. GeoJSON is an EPSG:4326 display copy. Store ID/name/brand and feature ID/type/area/evidence are retained in the projected export. Untagged polygon names remain blank.

## Database mapping

| Column | Meaning |
| --- | --- |
| record_key | Stable store ID + feature type + polygon OSM ID |
| store_osm_id | Store OSM type/ID |
| brand / store_name | Store classification and OSM name |
| feature_type | building or parking |
| area_m2 | Projected polygon area in m² |
| association_status | Matching evidence class |
| source | OpenStreetMap / Overpass source |
| osm_tags | Original polygon tags as JSONB |
| geom | Projected geometry, SRID 25832 |
| updated_at | Load/update time, not source observation time |

Writes explicitly target iris_staging.commercial_poi_staging; stable record_key upserts prevent repeated copies of the same store/feature association. Shared polygons may still appear for different stores. Current local DDL is a proposed mapping; compatibility with the coordinator's DDL remains unverified unless separately confirmed. The local preparation tool can back up an incompatible local staging table; review it before use.

## Interpreting results

strong_tag_match means explicit tag evidence; spatial_candidate means a heuristic spatial association; nearby_unverified means proximity without enough evidence. These are screening classifications, not ownership verification. Do not total all nearby polygons as the store's assets. Footprint area is a horizontal roof proxy, not usable PV roof area. Parking geometry does not prove available spaces or development rights. Overlapping polygons and shared facilities require review.

## Validation and limitations

Run sql/validation.sql against your actual database and include the output. Check coverage by brand, geometry validity/emptiness/SRID and record uniqueness. Load the same processed branch twice and compare row counts for idempotency. No live database validation result is invented in this document.

Successful Overpass responses are cached in data/overpass_cache. Repeated downloads can reuse them; failed requests must not be replaced with synthetic data. Network/API failures and unsupported geometry can reduce coverage. Batch failures and partial loading must be reported. Source retrieval timestamps and endpoint provenance are not fully persisted per database row in this version; updated_at is only a load timestamp.

Data: © OpenStreetMap contributors, ODbL. Attribution and licence information: https://www.openstreetmap.org/copyright. No valuation, lease, cadastral ownership, structural roof assessment or energy yield is inferred.

## Submission contents

Include app.py, src/, tests/, fixtures/, sql/, requirements.txt, Dockerfile, docker-compose.yml, README, dashboard guide, final results/validation evidence and one small live or clearly labelled synthetic sample. Exclude .env, credentials, virtual environments, Python caches and unrelated personal files.


## Included samples and review status

The files outputs/features.csv, outputs/features.geojson, outputs/stats.json and outputs/stores.json are supplied synthetic examples, not exports of the reported live database. outputs/TASK-CRE-37-4-store-branches.csv contains 141 live-discovery OSM objects. data/overpass_cache contains successful raw responses; per-response query text, endpoint and retrieval time are not embedded in these raw cache files.

See FINAL_RESULTS.md for user-reported database counts, REVIEW.md for the independent code/package review, and sql/validation.sql for read-only database checks. No claim is made that all technical requirements or nationwide coverage have been fully verified.
