"""CLI pipeline and testable offline mode."""

import argparse, csv, json, logging, os
from pathlib import Path
from .overpass import fetch, query_stores, query_near, parse_stores, STATES
from .spatial import parse_polygons, geojson_features
from .matching import match_features
from .db import load

LOG = logging.getLogger(__name__)


def run(
    offline=False,
    brand=None,
    max_stores=0,
    radius=350,
    state="DE",
    write_db=False,
    output="outputs",
    initialize_db=False,
):
    if not 0 <= max_stores <= 10000:
        raise ValueError("max-stores must be 0 (all) or 1..10000")
    if state not in STATES.values():
        raise ValueError("Unknown state")
    if not 50 <= radius <= 1000:
        raise ValueError("radius must be 50..1000")
    fixture = Path(__file__).resolve().parent.parent / "fixtures"
    raw = (
        json.loads((fixture / "stores.json").read_text())
        if offline
        else fetch(query_stores(state))
    )
    stores = parse_stores(raw)
    if brand:
        stores = [s for s in stores if s["brand"].casefold() == brand.casefold()]
    if max_stores:
        stores = stores[:max_stores]
    if not stores:
        LOG.warning("No stores matched")
    rows = []
    stats = {
        "stores": len(stores),
        "processed": 0,
        "failed": 0,
        "skipped": 0,
        "upserted": 0,
    }
    for store in stores:
        try:
            data = (
                json.loads((fixture / "nearby.json").read_text())
                if offline
                else fetch(query_near(store["lat"], store["lon"], radius))
            )
            features, c = parse_polygons(data, store)
            features = match_features(features, store)
            rows.extend(features)
            for k in ("processed", "failed", "skipped"):
                stats[k] += c[k]
            if write_db:
                stats["upserted"] += load(store, features, initialize=initialize_db)
        except Exception:
            stats["failed"] += 1
            LOG.exception("Store processing failed: %s", store["osm_id"])
            if write_db:
                raise
    dest = Path(output)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "features.geojson").write_text(
        json.dumps(geojson_features(rows), indent=2), encoding="utf-8"
    )
    (dest / "stores.json").write_text(json.dumps(stores, indent=2), encoding="utf-8")
    (dest / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    with (dest / "features.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "store_id",
                "feature_id",
                "kind",
                "area_m2",
                "association",
                "source",
            ],
        )
        writer.writeheader()
        writer.writerows([{k: r[k] for k in writer.fieldnames} for r in rows])
    LOG.info("Pipeline complete: %s", stats)
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--brand")
    parser.add_argument("--max-stores", type=int, default=0)
    parser.add_argument("--state", choices=list(STATES.values()), default="DE")
    parser.add_argument("--radius", type=int, default=350)
    parser.add_argument("--write-db", action="store_true")
    parser.add_argument("--initialize-db", action="store_true")
    parser.add_argument("--output", default="outputs")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    print(json.dumps(run(**vars(args)), indent=2))
