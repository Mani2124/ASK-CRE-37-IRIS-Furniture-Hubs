# IRIS Windows quick start (existing dashboard)

1. Leave Docker Desktop running. In Command Prompt run `docker ps` and verify `iris-postgis` is Up.
2. Initialize PostGIS locally (ONLY if your local database is empty):
   `docker exec -it iris-postgis psql -U iris -d iris -c "CREATE EXTENSION IF NOT EXISTS postgis;"`
   Then run `sql/01_schema.sql` in psql, or use the `--initialize-db` CLI option. The SQL is a PROPOSED local staging schema, not the company's confirmed DDL.
3. In the extracted project directory, install dependencies: `python -m pip install -r requirements.txt`
4. In CMD, set: `set DB_URI=postgresql://iris:iris_dev_password@localhost:5432/iris`
5. Start: `python -m streamlit run app.py`
6. Search branches; select a small batch first (e.g. 3). Enable 'Save successful polygon results to local PostGIS' after the local table exists.
7. Successful Overpass responses are saved under `data/overpass_cache` and reused on later runs. Failures are not cached. This does NOT fix overloaded Overpass servers or ensure all 122 branches.
8. Check rows: `docker exec -it iris-postgis psql -U iris -d iris -c "SELECT brand, feature_type, count(*) FROM iris_staging.commercial_poi_staging GROUP BY 1,2 ORDER BY 1,2;"`

IMPORTANT: The dashboard only writes polygon records (not store points) to the existing staging table. For full offline Germany coverage, a local PBF ingest is a separate implementation; this patch deliberately preserves your current working Overpass logic.
