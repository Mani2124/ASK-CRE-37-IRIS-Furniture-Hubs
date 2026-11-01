"""IRIS furniture store explorer and PostGIS polygon staging dashboard."""

import hashlib
import json
import os
import time
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.db import check, initialize_local, load
from src.export import FIELDS, enrich_rows, geopackage_bytes
from src.matching import match_features
from src.overpass import STATES, fetch, parse_stores, query_near, query_stores
from src.spatial import geojson_features, parse_polygons

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "data" / "overpass_cache"
CACHE.mkdir(parents=True, exist_ok=True)
BRANDS = ["XXXLutz", "Höffner", "Porta", "Segmüller"]
COLORS = {
    "strong_tag_match": "#16a34a",
    "spatial_candidate": "#eab308",
    "nearby_unverified": "#94a3b8",
}


def cached_fetch(query, offline=False, fixture=None):
    """Read saved successful responses before requesting the Overpass API."""
    if offline:
        return json.loads((ROOT / "fixtures" / fixture).read_text(encoding="utf-8"))

    key = hashlib.sha256(query.encode("utf-8")).hexdigest()
    cache_file = CACHE / f"{key}.json"
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if isinstance(cached.get("elements"), list):
                return cached
        except (OSError, ValueError, AttributeError):
            pass

    result = fetch(query, retries=0)
    temporary_file = cache_file.with_suffix(".tmp")
    temporary_file.write_text(json.dumps(result), encoding="utf-8")
    temporary_file.replace(cache_file)
    return result


def save_records(records):
    """Save processed polygons without contacting Overpass again."""
    total = 0
    for item in records.values():
        total += load(item["store"], item["rows"])
    return total


st.set_page_config(
    page_title="IRIS | Germany Furniture Hubs", page_icon="🗺️", layout="wide"
)
st.title("IRIS · Germany Furniture Hub Explorer")
st.caption(
    "TASK-CRE-37 | XXXLutz · Höffner · Porta · Segmüller | © OpenStreetMap contributors (ODbL)"
)

with st.sidebar:
    st.header("Discover branches")
    mode = st.radio("Source", ["Live OpenStreetMap", "Offline demo"])
    state_name = st.selectbox("German federal state", list(STATES))
    brands = st.multiselect("Furniture brands", BRANDS, default=BRANDS)
    radius = st.slider("Nearby polygon search radius (m)", 100, 750, 350, 50)
    db_enabled = bool(os.getenv("DB_URI"))
    auto_db = st.checkbox(
        "Automatically save extracted polygons to PostGIS",
        value=False,
        disabled=not db_enabled,
    )
    st.caption(
        "Successful Overpass responses are cached. The offline demo uses synthetic fixtures."
    )

    if st.button(
        "Search all branches in selected state",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner("Searching OpenStreetMap for furniture stores…"):
                raw = cached_fetch(
                    query_stores(STATES[state_name]),
                    offline=mode == "Offline demo",
                    fixture="stores.json",
                )
            catalog = parse_stores(raw)
            st.session_state.catalog = catalog
            st.session_state.scope = (state_name, mode)
            st.session_state.polygons = {}
            st.success(f"Found {len(catalog)} OSM objects before brand filtering.")
        except Exception as exc:
            st.error(f"Store search failed: {exc}")
            st.info(
                "This is an Overpass request failure, not a PostGIS connection failure."
            )

    st.caption(
        "Live searches use OSM state boundaries. OSM objects are not always unique physical stores."
    )

# Database controls are always visible, even when Overpass has failed.
st.subheader("PostGIS database")
if not os.getenv("DB_URI"):
    st.warning(
        "DB_URI is not configured. Set it in PowerShell before starting Streamlit."
    )
else:
    db_col1, db_col2 = st.columns(2)
    with db_col1:
        if st.button("Check PostGIS connection and record count"):
            try:
                info = check()
                st.success(f"Connected to database: {info['database']}")
                st.write(
                    f"Stored polygon records: {info['count'] if info['count'] is not None else 'Table missing'}"
                )
                if not info["schema_ok"]:
                    st.warning(
                        "The staging table needs local preparation before saving polygons."
                    )
            except Exception as exc:
                st.error(f"PostGIS check failed: {exc}")
    with db_col2:
        if st.button("Prepare local staging table"):
            try:
                info = initialize_local()
                st.success(
                    f"Local staging table ready. Stored records: {info['count']}"
                )
            except Exception as exc:
                st.error(f"Could not prepare local table: {exc}")

catalog = st.session_state.get("catalog", [])
records = st.session_state.get("polygons", {})
stores = [store for store in catalog if store["brand"] in brands]

if not catalog:
    st.info(
        "Select a state and search for stores. You can check PostGIS above before searching."
    )
    st.stop()

metric1, metric2, metric3 = st.columns(3)
metric1.metric("OSM objects found", len(catalog))
metric2.metric("After brand filter", len(stores))
metric3.metric("Branches with polygons", len(records))

if not stores:
    st.warning("No stores match the selected brands.")
    st.stop()

st.subheader("Branch directory")
directory = pd.DataFrame(
    [
        {
            "Brand": store["brand"],
            "Branch / name": store["name"],
            "City (OSM)": store["city"] or "Not tagged",
            "OSM ID": store["osm_id"],
            "Latitude": store["lat"],
            "Longitude": store["lon"],
        }
        for store in stores
    ]
)
st.dataframe(directory, use_container_width=True, hide_index=True)
st.download_button(
    "Download branch directory (CSV)",
    directory.to_csv(index=False).encode("utf-8-sig"),
    file_name="TASK-CRE-37-branches.csv",
    mime="text/csv",
)

labels = {
    store[
        "osm_id"
    ]: f"{store['brand']} | {store['city'] or store['name']} | {store['osm_id']}"
    for store in stores
}
selected_id = st.selectbox(
    "Choose branch (OSM ID)", list(labels), format_func=labels.get
)
selected = next(store for store in stores if store["osm_id"] == selected_id)
st.write(f"**Selected:** {selected['brand']} · {selected['name']} · `{selected_id}`")

extract_col, batch_col = st.columns(2)
with extract_col:
    extract_one = st.button(
        "Extract selected branch polygons", type="primary", use_container_width=True
    )
with batch_col:
    batch_count = st.number_input(
        "Batch size (0 = all filtered branches)",
        min_value=0,
        max_value=len(stores),
        value=0,
        step=1,
    )
    extract_batch = st.button("Extract batch / all branches", use_container_width=True)

if extract_one or extract_batch:
    targets = (
        [selected]
        if extract_one
        else stores[: int(batch_count)] if batch_count else stores
    )
    progress = st.progress(0)
    failures = []
    saved = 0

    for index, store in enumerate(targets):
        store_id = store["osm_id"]
        if store_id not in records:
            try:
                raw = cached_fetch(
                    query_near(store["lat"], store["lon"], radius),
                    offline=st.session_state.get("scope", ("", ""))[1]
                    == "Offline demo",
                    fixture="nearby.json",
                )
                rows, counts = parse_polygons(raw, store)
                rows = match_features(rows, store)
                records[store_id] = {"rows": rows, "counts": counts, "store": store}
            except Exception as exc:
                failures.append(f"{store_id}: {exc}")

        if auto_db and store_id in records and records[store_id]["rows"]:
            try:
                saved += load(store, records[store_id]["rows"])
            except Exception as exc:
                st.error(f"PostGIS save failed for {store_id}: {exc}")

        progress.progress((index + 1) / len(targets))
        if len(targets) > 1 and index < len(targets) - 1 and mode != "Offline demo":
            time.sleep(1)

    st.success(
        f"Extraction completed: {len(targets) - len(failures)} processed/cached, {len(failures)} failed."
    )
    if auto_db:
        st.info(f"Polygon records written to PostGIS: {saved}")
    if failures:
        st.error("Failed branches: " + "; ".join(failures[:10]))
        st.download_button(
            "Download failed branch IDs",
            "\n".join(failures),
            file_name="failed-branches.txt",
        )
    if len(targets) > 20:
        st.warning("Large batches may overload public Overpass servers.")

entry = records.get(selected_id)
map_obj = folium.Map(location=[selected["lat"], selected["lon"]], zoom_start=14)
folium.Marker(
    [selected["lat"], selected["lon"]],
    tooltip=labels[selected_id],
    popup=selected_id,
).add_to(map_obj)

if entry:
    for row in entry["rows"]:
        color = COLORS.get(row["association"], "#94a3b8")
        folium.GeoJson(
            row["geometry_wgs84"],
            style_function=lambda feature, color=color: {
                "color": color,
                "weight": 2,
                "fillOpacity": 0.25,
            },
            tooltip=(
                f"{row['feature_id']} | {row['kind']} | "
                f"{row['area_m2']:,.0f} m² | {row['association']}"
            ),
        ).add_to(map_obj)

st_folium(map_obj, height=510, width=None, returned_objects=[])

if entry:
    rows = entry["rows"]
    building_rows = [row for row in rows if row["kind"] == "building"]
    parking_rows = [row for row in rows if row["kind"] == "parking"]

    area_col1, area_col2, area_col3 = st.columns(3)
    area_col1.metric("Candidate polygons", len(rows))
    area_col2.metric(
        "Nearby building area (m²)", f"{sum(r['area_m2'] for r in building_rows):,.0f}"
    )
    area_col3.metric(
        "Nearby parking area (m²)", f"{sum(r['area_m2'] for r in parking_rows):,.0f}"
    )

    count_col1, count_col2, count_col3 = st.columns(3)
    count_col1.metric("Building polygons", len(building_rows))
    count_col2.metric("Parking polygons", len(parking_rows))
    count_col3.metric(
        "Parking spatial/tag candidates",
        sum(row["association"] != "nearby_unverified" for row in parking_rows),
    )

    if not parking_rows:
        st.warning(
            "No parking polygons returned. This does not prove that parking is absent."
        )
    elif not any(row["association"] != "nearby_unverified" for row in parking_rows):
        st.info(
            "Parking polygons exist, but their association with this store is unverified."
        )

    st.caption("Green: tag match · Yellow: spatial candidate · Grey: nearby unverified")
    summary = pd.DataFrame(
        [
            {
                "Association": association,
                "Polygons": sum(row["association"] == association for row in rows),
                "Building m²": round(
                    sum(
                        row["area_m2"]
                        for row in building_rows
                        if row["association"] == association
                    ),
                    2,
                ),
                "Parking m²": round(
                    sum(
                        row["area_m2"]
                        for row in parking_rows
                        if row["association"] == association
                    ),
                    2,
                ),
            }
            for association in COLORS
        ]
    )
    st.subheader("Evidence-based association breakdown")
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Feature OSM ID": row["feature_id"],
                    "Type": row["kind"],
                    "Area m²": row["area_m2"],
                    "Association": row["association"],
                    "Confidence": row.get("association_confidence", "unverified"),
                    "Evidence": row.get("match_evidence", ""),
                    "Distance m": row.get("distance_to_store_m"),
                }
                for row in rows
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    export_rows = enrich_rows(rows, catalog)
    st.download_button(
        "Download selected branch GeoPackage — EPSG:25832",
        geopackage_bytes(export_rows),
        file_name=f"{selected_id.replace('/', '-')}-EPSG25832.gpkg",
        mime="application/geopackage+sqlite3",
    )
    st.download_button(
        "Download selected branch GeoJSON (WGS84)",
        json.dumps(geojson_features(rows), indent=2),
        file_name=f"{selected_id.replace('/', '-')}-polygons.geojson",
        mime="application/geo+json",
    )
    if db_enabled and st.button("Save selected branch polygons to PostGIS"):
        try:
            st.success(f"Upserted {load(selected, rows)} polygon records")
        except Exception as exc:
            st.error(f"PostGIS write failed: {exc}")

if records:
    combined = [row for item in records.values() for row in item["rows"]]
    export_all = enrich_rows(combined, catalog)
    st.download_button(
        "Download ALL polygons — GeoPackage EPSG:25832",
        geopackage_bytes(export_all),
        file_name="TASK-CRE-37-all-EPSG25832.gpkg",
        mime="application/geopackage+sqlite3",
    )
    attributes = pd.DataFrame(
        [{field: row.get(field) for field in FIELDS} for row in export_all]
    )
    st.download_button(
        "Download ALL polygon attributes (CSV)",
        attributes.to_csv(index=False).encode("utf-8-sig"),
        file_name="TASK-CRE-37-polygon-attributes.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download all processed polygons (GeoJSON — WGS84)",
        json.dumps(geojson_features(combined), indent=2),
        file_name="TASK-CRE-37-all-polygons.geojson",
        mime="application/geo+json",
    )
    if db_enabled and st.button("Save ALL processed polygons to PostGIS"):
        try:
            saved = save_records(records)
            st.success(f"Upserted {saved} polygon records")
        except Exception as exc:
            st.error(f"PostGIS write failed: {exc}")

st.divider()
st.caption(
    "OSM association is screening evidence, not proof of ownership or PV suitability."
)
