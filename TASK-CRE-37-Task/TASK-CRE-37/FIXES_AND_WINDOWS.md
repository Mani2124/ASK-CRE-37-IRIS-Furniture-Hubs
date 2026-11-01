


## Start (PowerShell)

```powershell
$env:DB_URI = "postgresql://iris:iris_dev_password@localhost:5432/iris"
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## First run

1. Open **PostGIS database** at the top of the dashboard.
2. Click **Check PostGIS connection and record count**.
3. Click **Prepare local staging table** if the schema is missing or incompatible.
4. Search for stores and extract polygons, or select **Offline demo** to verify the workflow without Overpass.
5. Click **Save selected branch polygons to PostGIS** or **Save ALL processed polygons to PostGIS**.
6. Verify saved data:

```powershell
docker exec -it iris-postgis psql -U iris -d iris -c "SELECT brand, feature_type, count(*) FROM iris_staging.commercial_poi_staging GROUP BY brand, feature_type;"
```


