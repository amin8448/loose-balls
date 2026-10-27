# Audit log

## Step 1, loose-ball audit

Brief: docs/step1_audit_brief.md. Exploration matches only: 1886347, 1959846, 1996436, 1996435, 2007448.

### Setup (2026-10-27)

Data and specifications. data/ is not committed.

| item | value |
|:--|:--|
| data/opendata | link to ../../analytics-cup-football/data/opendata |
| open-data commit | 4340d274572876239c154c90bc507a9b3250a656 (clean working tree) |
| data/specs/dynamic_events_spec.pdf | Dynamic Events CSV Specifications, 2025/02/16, 89 pages, md5 2413c3cef606a1b156a13a2b60107496 |
| data/specs/phases_of_play_spec.pdf | Phases of Play CSV Specifications, 2025/02/16, 8 pages, md5 c54922a0b9331bbbfba1b8344499abc2 |
| specs copied from | ~/projects/analytics-cup-football/data/specs (competition_analytics-cup-2-football has no data/specs folder) |

Guard. tests/test_guard.py was run before any match data was read.

| test | result |
|:--|:--|
| test match 1874553 raises TestSetLocked before any file of that match is opened | pass |
| exploration match 1886347 loads (metadata id matches) | pass |
| all 15 test ids refused for raw and cache paths; an id in neither set refused | pass |
| a marker in the working copy of AUDIT.md does not unlock; the same marker committed does (temporary repository) | pass |

Frame class rule (tracking.py): empty when player_data is empty; camera when player_data is present and all eight image_corners_projection values are set; no camera otherwise. The tracking possession field is dropped on read.

Setup check: frames per match by frame class (frames inside a period only; frames outside a period are pre-match frames with no data) and player_possession rows in the dynamic events.

| match   |   frames |   outside periods |   in periods |   camera |   no camera |   empty |   camera share |   player_possession rows |
|:--------|---------:|------------------:|-------------:|---------:|------------:|--------:|---------------:|-------------------------:|
| 1886347 |    59061 |                19 |        59042 |    37530 |        5928 |   15584 |          0.636 |                      990 |
| 1959846 |    58541 |                 9 |        58532 |    36259 |        6480 |   15793 |          0.619 |                      946 |
| 1996436 |    60280 |                19 |        60261 |    34882 |        8184 |   17195 |          0.579 |                      786 |
| 1996435 |    57621 |                19 |        57602 |    38255 |        5276 |   14071 |          0.664 |                     1005 |
| 2007448 |    58081 |                19 |        58062 |    37329 |        6954 |   13779 |          0.643 |                      863 |
| total   |   293584 |                85 |       293499 |   184255 |       32822 |   76422 |          0.628 |                     4590 |
