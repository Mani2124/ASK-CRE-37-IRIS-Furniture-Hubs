from shapely.geometry import box, mapping
from shapely.ops import transform
from src.spatial import PROJECT, parse_polygons
from src.matching import match_features


def test_parking_near_matched_building_is_candidate():
    store = {"brand": "Porta", "lat": 50.79, "lon": 6.09}
    building = transform(PROJECT, box(6.09, 50.79, 6.0901, 50.7901))
    parking = building.buffer(20).difference(building.buffer(5))
    rows = [
        {
            "kind": "building",
            "osm_tags": {"name": "porta Möbel"},
            "geometry_25832": mapping(building),
        },
        {"kind": "parking", "osm_tags": {}, "geometry_25832": mapping(parking)},
    ]
    result = match_features(rows, store)
    assert result[1]["association"] == "spatial_candidate"
    assert result[1]["association_confidence"] == "low"


def test_private_parking_not_auto_matched():
    store = {"brand": "Porta", "lat": 50.79, "lon": 6.09}
    building = transform(PROJECT, box(6.09, 50.79, 6.0901, 50.7901))
    rows = [
        {
            "kind": "building",
            "osm_tags": {"name": "porta"},
            "geometry_25832": mapping(building),
        },
        {
            "kind": "parking",
            "osm_tags": {"access": "private"},
            "geometry_25832": mapping(building.buffer(5)),
        },
    ]
    assert match_features(rows, store)[1]["association"] == "nearby_unverified"


def test_parking_polygon_extraction():
    store = {"osm_id": "way/1"}
    ring = [
        {"lon": 6.09, "lat": 50.79},
        {"lon": 6.091, "lat": 50.79},
        {"lon": 6.091, "lat": 50.791},
        {"lon": 6.09, "lat": 50.791},
        {"lon": 6.09, "lat": 50.79},
    ]
    rows, _ = parse_polygons(
        {
            "elements": [
                {
                    "type": "way",
                    "id": 99,
                    "tags": {"amenity": "parking"},
                    "geometry": ring,
                }
            ]
        },
        store,
    )
    assert len(rows) == 1 and rows[0]["kind"] == "parking" and rows[0]["area_m2"] > 0
