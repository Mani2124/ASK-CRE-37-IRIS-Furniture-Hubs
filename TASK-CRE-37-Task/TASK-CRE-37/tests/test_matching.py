from shapely.geometry import box, mapping
from src.matching import match_features


def test_explicit_brand_match():
    store = {"brand": "Porta", "lat": 50.79, "lon": 6.09}
    rows = [
        {
            "kind": "building",
            "osm_tags": {"name": "porta Möbel"},
            "geometry_25832": mapping(box(300000, 5600000, 300010, 5600010)),
        }
    ]
    assert match_features(rows, store)[0]["association"] == "strong_tag_match"


def test_unrelated_nearby_not_claimed():
    store = {"brand": "Porta", "lat": 50.79, "lon": 6.09}
    rows = [
        {
            "kind": "parking",
            "osm_tags": {"name": "Public parking"},
            "geometry_25832": mapping(box(300000, 5600000, 300010, 5600010)),
        }
    ]
    assert match_features(rows, store)[0]["association"] == "nearby_unverified"


def test_store_polygon_overlap():
    from shapely.ops import transform
    from src.spatial import PROJECT

    store = {
        "brand": "Porta",
        "lat": 50.79,
        "lon": 6.09,
        "geometry": [
            (6.089, 50.789),
            (6.091, 50.789),
            (6.091, 50.791),
            (6.089, 50.791),
            (6.089, 50.789),
        ],
    }
    poly = transform(PROJECT, box(6.0895, 50.7895, 6.0905, 50.7905))
    rows = [{"kind": "building", "osm_tags": {}, "geometry_25832": mapping(poly)}]
    assert match_features(rows, store)[0]["association"] == "spatial_candidate"
