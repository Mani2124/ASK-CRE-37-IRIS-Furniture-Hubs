from src.overpass import parse_stores, ENDPOINTS


def test_original_endpoints_without_broken_taiwan_host():
    assert len(ENDPOINTS) == 2
    assert all("nchc" not in endpoint for endpoint in ENDPOINTS)


def test_polygon_only_store_retained():
    raw = {
        "elements": [
            {
                "type": "way",
                "id": 1,
                "tags": {"name": "XXXLutz"},
                "geometry": [
                    {"lon": 10, "lat": 50},
                    {"lon": 10.001, "lat": 50},
                    {"lon": 10.001, "lat": 50.001},
                    {"lon": 10, "lat": 50.001},
                    {"lon": 10, "lat": 50},
                ],
            }
        ]
    }
    assert len(parse_stores(raw)) == 1
