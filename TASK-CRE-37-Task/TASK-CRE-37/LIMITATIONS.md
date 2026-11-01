# Limitations and integrity notes

- OpenStreetMap is community maintained, incomplete, and not authoritative cadastral or ownership data.
- Nearby features are **unverified spatial candidates**; proximity is not proof of building ownership, roof availability, or parking access. Overlapping polygons may double count. Never sum them as verified property totals.
- Geometry from OSM may be a ground footprint, **not usable rooftop surface area**. No PV/BESS/HPC income, GRZ/GFZ, WALT, ImmoWertV, or HBU valuation is computed.
- Complex OSM multipolygon relations with inner rings or fragmented outer members are skipped rather than incorrectly reconstructed. Some buildings and parking areas will be missed.
- Germany-wide Overpass queries can be slow, throttled or unavailable; use small `--max-stores` values for demonstrations. Respect OSM API usage policies.
- Store identification relies on names/brand tags; missing tags, misspellings and franchise naming variations reduce coverage.
- Offline fixtures are **synthetic examples**, not client records or actual German retail properties.
- Database schema in this repository is a proposed staging-only DDL; confirm with Tariq before writing to any shared IRIS database. No credentials or production data included.
- The pipeline logs counts; errors in live services are surfaced, not replaced with invented values.
- OSM attribution: © OpenStreetMap contributors; data under Open Database License (ODbL). Check downstream share-alike/attribution obligations before redistributing derived databases.
- Docker and live PostgreSQL service require local runtime verification; local tests alone do not validate external services.

## Evidence-based association update
`strong_tag_match` indicates an OSM name/brand/operator match, `spatial_candidate` indicates overlap/proximity, and `nearby_unverified` indicates no supporting association. None proves ownership, lease rights, roof usability, or available parking. A single mapped OSM object may represent a POI, a building, or part of a multi-tenant site. Building-to-store matching should be reviewed manually for high-value cases. Confidence is a heuristic label, not a calibrated probability.
