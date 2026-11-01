# Project structure and execution

## Run the dashboard on Windows

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```



## Files and responsibilities

| File | Responsibility |
| --- | --- |
| app.py | Streamlit controls, cached retrieval, maps, batch processing, downloads and explicit database actions |
| src/overpass.py | Original state-scoped store search, nearby polygon queries, HTTP handling and store-location parsing |
| src/spatial.py | Polygon validation, EPSG:25832 transformation and area calculation |
| src/matching.py | Building and parking association evidence |
| src/export.py | Projected GeoPackage and attribute export |
| src/db.py | PostGIS connection checks and staging-only persistence |
| src/pipeline.py | Command-line execution and offline processing |
| sql/01_schema.sql | Proposed local staging schema |
| tests/ | Automated fixture and mock tests |
| fixtures/ | Synthetic offline examples |
| requirements.txt | Python dependencies |
| Dockerfile / docker-compose.yml | Reproducible application and database setup |

## Processing order

Discover store records, select branches, retrieve nearby geometries, validate and project polygons, calculate area and association evidence, then export or explicitly load staging records. Database checks do not supply or replace Overpass data.




