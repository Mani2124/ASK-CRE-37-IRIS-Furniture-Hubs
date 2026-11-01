# Dashboard tools and operating guide

## Recommended order

1. Start the application and configure DB_URI only if database saving is needed.
2. Check the PostGIS connection. Prepare the staging table only in your intended local database if needed.
3. Choose Live OpenStreetMap and All Germany. Search once to discover all four target brands.
4. Review the branch directory and filter a brand. Select an individual store using its OSM ID.
5. Extract one branch as a smoke test. Inspect building and parking polygons and their evidence classes.
6. Run batch extraction if time permits. Set batch size to 0 for all currently filtered store objects.
7. Save the selected branch or all processed results to PostGIS. Extraction alone does not imply database saving unless automatic saving was enabled.
8. Download the EPSG:25832 GeoPackage, attribute CSV and branch directory. Run validation.sql and record final coverage.

## Controls

| Control / display | Description |
| --- | --- |
| Source | Live OpenStreetMap retrieves actual OSM data; Offline demo uses synthetic test fixtures. |
| German federal state | Limits discovery geographically. All Germany searches nationally. |
| Furniture brands | Filters the retrieved directory; selecting fewer brands changes the batch targets. |
| Nearby polygon search radius | Search distance around a store location. Larger values retrieve more surrounding properties, not more certain matches. |
| Search all branches in selected state | Retrieves the store catalogue and reuses an exact-query cache if present. A new successful search resets the current polygon session, so save/download existing work first. |
| Check PostGIS connection and record count | Shows database connection status and stored polygon-row count. This is not a count of unique physical stores. |
| Prepare local staging table | Prepares the proposed table in the allowed local database; may back up an incompatible existing table. |
| Automatically save extracted polygons to PostGIS | When enabled, saves successful branch results during extraction. Requires DB_URI. |
| OSM objects found | All discovered store representations, before brand display filtering. |
| After brand filter | Number of store objects currently visible and eligible for filtered batch processing. |
| Branches with polygons | Processed branch entries in the current application session; check actual polygon rows for empty results. |
| Branch directory | Store brand, name, city, OSM ID and longitude/latitude. Multiple objects can belong to one physical branch. |
| Individual branch selector | Opens one store using a stable OSM type/ID. |
| Extract selected branch polygons | Requests nearby building and parking areas, validates supported polygons, calculates area and assigns evidence labels. |
| Batch size | 0 means all filtered stores. A positive value limits the batch. |
| Extract batch / all branches | Processes the selected batch; inspect failed branches and distinguish extraction success from saving success. |
| Branch map | Shows store location and nearby polygons. Green: strong tag match; yellow: spatial candidate; grey: unverified context. |
| Building / parking area metrics | Sums of retrieved feature areas, including nearby context and possible overlap. Not verified store-owned area. |
| Evidence breakdown | Separates counts and area sums by association status. |
| Save selected branch polygons to PostGIS | Upserts the current branch's processed polygons. |
| Save ALL processed polygons to PostGIS | Writes available processed session results without downloading them again. |
| GeoPackage download | Projected polygon geometry in EPSG:25832 with store/polygon IDs, names, areas and evidence attributes. |
| CSV download | Tabular attributes for review; CSV alone has no polygon geometry. |
| GeoJSON download | WGS84 display/interchange copy; use GeoPackage for required projected delivery. |

## Database inspection

In the PostgreSQL prompt, run the supplied validation.sql. In QGIS, connect to PostgreSQL and load iris_staging.commercial_poi_staging, then style by feature_type or association_status. Use store_osm_id to inspect one branch. Repeated store IDs are expected across that branch's polygon rows; record_key identifies each association uniquely.

## Preserve completed work

Download completed outputs and save processed results before restarting the application or making a new successful discovery request. 
