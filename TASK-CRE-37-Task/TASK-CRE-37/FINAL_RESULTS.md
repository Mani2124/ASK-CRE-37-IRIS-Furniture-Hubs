# Results at submission

## Live store discovery

The included CSV contains 141 distinct OSM object IDs: XXXLutz 71, Höffner 28, Porta 33, Segmüller 9. These are not verified unique physical branches. Multiple objects can belong to one site; warehouses, outlets and extra buildings require reconciliation. Full branch-level comparison against official directories is incomplete.

## Candidate-reported PostGIS counts

| Brand | Store OSM objects | Polygon association records |
| --- | ---: | ---: |
| Höffner | 16 | 1426 |
| Porta | 4 | 1822 |
| Segmüller | 2 | 840 |
| XXXLutz | 3 | 225 |
| Total | 25 | 4313 |

 Polygon records include nearby_unverified, spatial_candidate and strong_tag_match classes. 

Its compared discovery counts with each brand’s official website as a count-level plausibility check. Limited network bandwidth prevented downloading and loading the remaining data before the submission deadline. The implementation supports all four brands, with partial live database coverage. No artificial records were added to reach the expected 122 branches.

## Validation evidence still to attach

Run sql/validation.sql against the database and save the actual results before submission if time permits. Database geometry validity/SRID checks and repeated-load row-count evidence have not been supplied in this package. 


