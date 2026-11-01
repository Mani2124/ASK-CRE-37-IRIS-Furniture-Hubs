"""GeoPackage export with explicit EPSG:25832 and store/feature attributes."""

import json
import sqlite3
import struct
import tempfile
from pathlib import Path
from pyproj import CRS
from shapely.geometry import shape
from shapely import to_wkb
from contextlib import closing

FIELDS = (
    "store_id",
    "store_name",
    "brand",
    "feature_id",
    "feature_name",
    "kind",
    "area_m2",
    "association",
    "source",
)


def enrich_rows(rows, stores):
    lookup = {s["osm_id"]: s for s in stores}
    result = []
    for row in rows:
        store = lookup.get(row["store_id"], {})
        result.append(
            dict(
                row,
                store_name=store.get("name", ""),
                brand=store.get("brand", ""),
                feature_name=row.get("osm_tags", {}).get("name", ""),
            )
        )
    return result


def geopackage_bytes(rows):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "polygons.gpkg"
        with closing(sqlite3.connect(path)) as db, db:
            db.executescript("""
PRAGMA application_id=1196444487;
PRAGMA user_version=10300;
CREATE TABLE gpkg_spatial_ref_sys (srs_name TEXT NOT NULL,srs_id INTEGER NOT NULL PRIMARY KEY,organization TEXT NOT NULL,organization_coordsys_id INTEGER NOT NULL,definition TEXT NOT NULL,description TEXT);
CREATE TABLE gpkg_contents (table_name TEXT NOT NULL PRIMARY KEY,data_type TEXT NOT NULL,identifier TEXT UNIQUE,description TEXT DEFAULT '',last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),min_x DOUBLE,min_y DOUBLE,max_x DOUBLE,max_y DOUBLE,srs_id INTEGER,FOREIGN KEY(srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id));
CREATE TABLE gpkg_geometry_columns (table_name TEXT NOT NULL,column_name TEXT NOT NULL,geometry_type_name TEXT NOT NULL,srs_id INTEGER NOT NULL,z TINYINT NOT NULL,m TINYINT NOT NULL,PRIMARY KEY(table_name,column_name),FOREIGN KEY(table_name) REFERENCES gpkg_contents(table_name),FOREIGN KEY(srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id));
CREATE TABLE polygons (fid INTEGER PRIMARY KEY AUTOINCREMENT,geom GEOMETRY NOT NULL,store_id TEXT,store_name TEXT,brand TEXT,feature_id TEXT,feature_name TEXT,kind TEXT,area_m2 REAL,association TEXT,source TEXT,evidence TEXT);
""")
            db.executemany(
                "INSERT INTO gpkg_spatial_ref_sys VALUES (?,?,?,?,?,?)",
                [
                    ("Undefined Cartesian", -1, "NONE", -1, "undefined", ""),
                    ("Undefined geographic", 0, "NONE", 0, "undefined", ""),
                    (
                        "WGS 84",
                        4326,
                        "EPSG",
                        4326,
                        CRS.from_epsg(4326).to_wkt("WKT1_GDAL"),
                        "",
                    ),
                    (
                        "ETRS89 / UTM zone 32N",
                        25832,
                        "EPSG",
                        25832,
                        CRS.from_epsg(25832).to_wkt("WKT1_GDAL"),
                        "Metres",
                    ),
                ],
            )
            db.execute(
                "INSERT INTO gpkg_contents(table_name,data_type,identifier,description,srs_id) VALUES ('polygons','features','IRIS building and parking candidates','OSM candidate associations; not verified ownership',25832)"
            )
            db.execute(
                "INSERT INTO gpkg_geometry_columns VALUES ('polygons','geom','GEOMETRY',25832,0,0)"
            )
            bounds = []
            for row in rows:
                geom = shape(row["geometry_25832"])
                if (
                    geom.is_empty
                    or not geom.is_valid
                    or geom.geom_type not in ("Polygon", "MultiPolygon")
                ):
                    raise ValueError(
                        "Export requires valid, nonempty EPSG:25832 polygons"
                    )
                bounds.append(geom.bounds)
                blob = (
                    b"GP"
                    + bytes([0, 1])
                    + struct.pack("<i", 25832)
                    + to_wkb(geom, byte_order=1, output_dimension=2)
                )
                db.execute(
                    "INSERT INTO polygons(geom,"
                    + ",".join(FIELDS)
                    + ",evidence) VALUES ("
                    + ",".join("?" for _ in range(11))
                    + ")",
                    [blob]
                    + [row.get(k) for k in FIELDS]
                    + [
                        json.dumps(
                            {
                                k: row.get(k)
                                for k in (
                                    "association_confidence",
                                    "match_evidence",
                                    "distance_to_store_m",
                                )
                            },
                            ensure_ascii=False,
                        )
                    ],
                )
            if bounds:
                db.execute(
                    "UPDATE gpkg_contents SET min_x=?,min_y=?,max_x=?,max_y=? WHERE table_name='polygons'",
                    (
                        min(b[0] for b in bounds),
                        min(b[1] for b in bounds),
                        max(b[2] for b in bounds),
                        max(b[3] for b in bounds),
                    ),
                )
        return path.read_bytes()
