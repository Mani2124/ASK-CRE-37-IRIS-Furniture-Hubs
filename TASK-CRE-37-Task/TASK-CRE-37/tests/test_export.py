import sqlite3, struct
from shapely.geometry import mapping, box
from shapely import from_wkb
from src.export import enrich_rows, geopackage_bytes


def test_projected_export_and_names(tmp_path):
    rows = [
        {
            "store_id": "node/1",
            "feature_id": "way/2",
            "kind": "building",
            "area_m2": 100,
            "geometry_25832": mapping(box(500000, 5600000, 500010, 5600010)),
            "osm_tags": {"name": "Main building"},
            "association": "spatial_candidate",
            "source": "OSM",
        }
    ]
    enriched = enrich_rows(
        rows, [{"osm_id": "node/1", "name": "Porta Test", "brand": "Porta"}]
    )
    path = tmp_path / "test.gpkg"
    path.write_bytes(geopackage_bytes(enriched))
    with sqlite3.connect(path) as db:
        assert (
            db.execute("SELECT srs_id FROM gpkg_geometry_columns").fetchone()[0]
            == 25832
        )
        name, fid, blob = db.execute(
            "SELECT store_name,feature_id,geom FROM polygons"
        ).fetchone()
        assert name == "Porta Test" and fid == "way/2"
        assert struct.unpack("<i", blob[4:8])[0] == 25832
        assert from_wkb(blob[8:]).bounds == (500000, 5600000, 500010, 5600010)
