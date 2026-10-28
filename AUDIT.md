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

### A0. Specification wording (2026-10-27)

Source: data/specs/dynamic_events_spec.pdf (Dynamic Events CSV Specifications, 2025/02/16). Text extracted with pypdf; whitespace collapsed and the "ﬁ" ligature written as "fi". Otherwise verbatim, including the original typo "but one player".

| field | page | description (verbatim) | values (verbatim) |
|:--|:--|:--|:--|
| start_type | 40 | How the player got in possession of the ball. Keep possession corresponds to when the player possession does not start with a pass reception but the team in possession is still the same. For instance - if a player attempts a pass that is intercepted by an opponent and the ball bounces back to the player's own team. - if a player shoots to the goal and the ball is saved or hits the post to be recovered but one player from the same team as the player who shot the ball. | pass_reception / pass_interception / keep_possession / recovery / free_kick_reception / free_kick_interception / throw_in_reception / throw_in_interception / goal_kick_reception / goal_kick_interception / corner_reception / corner_interception / unknown |
| end_type | 41 | How the possession ended. | pass / shot / clearance / foul_suffered / possession_loss / unknown / direct_regain / indirect_regain / direct_disruption / indirect_disruption / foul_committed / None |
| is_header | 76 | TRUE if the possession was a header. Else FALSE. | TRUE / FALSE |

Wording for each value the brief asks about. The whole 89-page document was searched for each term.

| field | value | wording in the specification |
|:--|:--|:--|
| start_type | recovery | none; listed as a value only (p. 40) |
| start_type | pass_interception | none; listed as a value only (p. 40) |
| start_type | keep_possession | defined in the start_type description (p. 40), quoted above |
| start_type | unknown | none; listed as a value only (p. 40) |
| end_type | clearance | none; listed as a value only (p. 41) |
| end_type | possession_loss | none; listed as a value only (p. 41) |
| end_type | unknown | none; listed as a value only (p. 41) |
| is_header | TRUE / FALSE | p. 76, quoted above |

Related wording elsewhere in the same document.

| page | section | wording (verbatim) |
|:--|:--|:--|
| 6 | Event Definitions, Player Possession | For an activity to be detected as a Player Possession (PP) the player needs to be in control of the ball , i.e. able to do a pass, shot or carry. A player possession starts from the first touch of the player up to the last touch. A one-touch is a player possession that lasts only one frame. If a player is not in control of the ball then it does not qualify as a player possession. Typically, if a player intercepts the ball without controlling it afterward, like for blocks, it does not count as a player possession. |
| 19 | Phases of play, Chaotic | A chaotic phase is marked by a short contested possession. For a phase to avoid being labelled chaotic, it must meet one of these criteria: Include at least three passes with no more than one header, or Involve at least 5 seconds of possession. Clearances under pressure are always considered chaotic. |
| 19 | Phases of play, How It Works, rule 3 | If possession transitions between two teams (Team A and Team B), possession shifts to Team B at the start of their player possession event. |

Reading. The specification does not say whether recovery is a loose-ball pickup or includes a clean tackle. From the value list, recovery is what remains for a possession that starts without a pass reception, a pass interception, a restart, or the same team keeping the ball (keep_possession). That would cover both a tackle on a dribbler and a pickup of a free ball. This is an inference from the value list, not wording in the specification; A1 (gap by trigger and continuity) is the evidence for separating the two. The p. 6 definition means a block or a touch without control is not a possession, so such touches fall inside a gap.

### A1 implementation choices, logged before the A1 tables (2026-10-27)

Points where the brief does not fix the implementation. The pair builder (src/looseball/episodes.py) was run once before this entry to check that the trigger classes cover all retained pairs; the two items marked "after the coverage check" were set from that run, before any A1 table was produced.

| item | choice | reason |
|:--|:--|:--|
| sort ties | possessions sorted by frame_start, ties broken by the CSV field index | no ties occur in the five matches |
| restart interception types | throw_in_interception, free_kick_interception, goal_kick_interception, corner_interception | the four restart values of start_type ending in _interception |
| stoppage between i and i+1 | dropped when game_interruption_after of i or game_interruption_before of i+1 is set (any value) | both fields describe an interruption at the boundary between the two |
| order of the trigger rules (after the coverage check) | T5 is tested first, then T1, T2, T3, T4, T6, T0 | every header with end_type outside (pass, shot) is also clearance or possession_loss, so in the listed order T5 would always be empty. At pair level this concerns 10 retained headed clearances. Testing T1 first instead moves these 10 pairs from T5 to T1 and does not change the candidate set |
| end_type foul_suffered (after the coverage check) | trigger class "other" | not covered by T0 to T6. 60 of 61 such pairs are dropped by the stoppage rule; 1 retained pair remains |
| quantiles | linear interpolation (numpy default), gap in seconds = frames / 10 | |

### A1. Gap cross-tab (2026-10-27)

Script: scripts/a1_gap_crosstab.py. Pairs and classes from src/looseball/episodes.py with the choices logged above. "Retained" means after the period, restart, offside and stoppage drops. Gap quantiles in seconds; shares are of pairs with gap >= 3 frames. Candidate = provisional definition from the brief (trigger T1 to T6 or resolution recovery or unknown, gap >= 1 frame, not same player).

Drop reasons (a pair can carry more than one):

| match_id   |   pairs |   period |   restart |   offside |   stoppage |   retained |   dropped |
|:-----------|--------:|---------:|----------:|----------:|-----------:|-----------:|----------:|
| 1886347    |     989 |        1 |        90 |         2 |        100 |        889 |       100 |
| 1959846    |     945 |        1 |        77 |         2 |         96 |        848 |        97 |
| 1996436    |     785 |        1 |        83 |         2 |        107 |        678 |       107 |
| 1996435    |    1004 |        1 |        68 |         4 |         89 |        914 |        90 |
| 2007448    |     862 |        1 |        68 |         3 |         85 |        775 |        87 |
| total      |    4585 |        5 |       386 |        13 |        477 |       4104 |       481 |

A1a. Retained pairs, trigger by resolution, counts:

| trigger   |   pass_reception |   pass_interception |   recovery |   keep_possession |   unknown |   all |
|:----------|-----------------:|--------------------:|-----------:|------------------:|----------:|------:|
| T0        |             3137 |                   2 |         69 |                59 |         0 |  3267 |
| T1        |                0 |                   0 |         22 |                 4 |         0 |    26 |
| T2        |                1 |                 355 |         67 |                79 |         2 |   504 |
| T3        |                0 |                   0 |         30 |                19 |         2 |    51 |
| T4        |                0 |                   1 |        157 |                75 |         3 |   236 |
| T5        |                1 |                   0 |          8 |                 1 |         0 |    10 |
| T6        |                0 |                   0 |          2 |                 4 |         3 |     9 |
| other     |                0 |                   0 |          1 |                 0 |         0 |     1 |
| all       |             3139 |                 358 |        356 |               241 |        10 |  4104 |

A1b. Retained pairs, gap quantiles (seconds) and share with gap >= 3 frames, by cell:

| trigger   | resolution        |    n |   p10 s |   p50 s |   p90 s |   share gap >= 3 fr |
|:----------|:------------------|-----:|--------:|--------:|--------:|--------------------:|
| T0        | pass_reception    | 3137 |    0.80 |    1.30 |    2.10 |               0.995 |
| T0        | pass_interception |    2 |    6.02 |    6.10 |    6.18 |               1.000 |
| T0        | recovery          |   69 |    1.38 |    2.60 |    4.82 |               1.000 |
| T0        | keep_possession   |   59 |    1.60 |    2.90 |    4.74 |               1.000 |
| T0        | all               | 3267 |    0.80 |    1.30 |    2.20 |               0.995 |
| T1        | recovery          |   22 |    1.93 |    2.85 |    4.98 |               1.000 |
| T1        | keep_possession   |    4 |    2.05 |    2.55 |    4.94 |               1.000 |
| T1        | all               |   26 |    1.90 |    2.75 |    5.25 |               1.000 |
| T2        | pass_reception    |    1 |    4.10 |    4.10 |    4.10 |               1.000 |
| T2        | pass_interception |  355 |    0.70 |    1.70 |    3.10 |               0.980 |
| T2        | recovery          |   67 |    1.50 |    3.60 |    5.40 |               1.000 |
| T2        | keep_possession   |   79 |    1.18 |    3.50 |    5.90 |               1.000 |
| T2        | unknown           |    2 |   33.73 |   42.25 |   50.77 |               1.000 |
| T2        | all               |  504 |    0.80 |    2.10 |    4.40 |               0.986 |
| T3        | recovery          |   30 |    0.30 |    0.95 |    2.35 |               0.933 |
| T3        | keep_possession   |   19 |    0.80 |    2.10 |    3.62 |               1.000 |
| T3        | unknown           |    2 |   36.68 |   88.60 |  140.52 |               1.000 |
| T3        | all               |   51 |    0.40 |    1.50 |    3.70 |               0.961 |
| T4        | pass_interception |    1 |    7.20 |    7.20 |    7.20 |               1.000 |
| T4        | recovery          |  157 |    0.10 |    0.20 |    1.60 |               0.471 |
| T4        | keep_possession   |   75 |    0.20 |    1.30 |    3.66 |               0.867 |
| T4        | unknown           |    3 |   10.12 |   10.60 |   89.80 |               1.000 |
| T4        | all               |  236 |    0.10 |    0.60 |    2.40 |               0.606 |
| T5        | pass_reception    |    1 |    2.80 |    2.80 |    2.80 |               1.000 |
| T5        | recovery          |    8 |    1.54 |    2.65 |    3.72 |               1.000 |
| T5        | keep_possession   |    1 |    0.20 |    0.20 |    0.20 |               0.000 |
| T5        | all               |   10 |    1.28 |    2.65 |    3.64 |               0.900 |
| T6        | recovery          |    2 |    0.65 |    1.25 |    1.85 |               1.000 |
| T6        | keep_possession   |    4 |    2.66 |    3.15 |    4.48 |               1.000 |
| T6        | unknown           |    3 |   11.34 |   11.50 |   12.62 |               1.000 |
| T6        | all               |    9 |    1.70 |    3.50 |   11.78 |               1.000 |
| other     | recovery          |    1 |    1.30 |    1.30 |    1.30 |               1.000 |
| other     | all               |    1 |    1.30 |    1.30 |    1.30 |               1.000 |
| all       | all               | 4104 |    0.70 |    1.30 |    2.70 |               0.971 |

A1c. Counts by continuity and trigger:

| trigger   |   same player |   same team |   change of team |   all |
|:----------|--------------:|------------:|-----------------:|------:|
| T0        |             5 |        3191 |               71 |  3267 |
| T1        |             0 |           4 |               22 |    26 |
| T2        |            11 |          74 |              419 |   504 |
| T3        |             1 |          19 |               31 |    51 |
| T4        |             2 |          76 |              158 |   236 |
| T5        |             0 |           1 |                9 |    10 |
| T6        |             1 |           6 |                2 |     9 |
| other     |             0 |           0 |                1 |     1 |
| all       |            20 |        3371 |              713 |  4104 |

A1d. Continuity = same player: gap quantiles (seconds) and share with gap >= 3 frames, by cell:

| trigger   | resolution      |   n |   p10 s |   p50 s |   p90 s |   share gap >= 3 fr |
|:----------|:----------------|----:|--------:|--------:|--------:|--------------------:|
| T0        | keep_possession |   5 |    2.24 |    2.60 |    4.46 |               1.000 |
| T0        | all             |   5 |    2.24 |    2.60 |    4.46 |               1.000 |
| T2        | keep_possession |  11 |    0.40 |    1.30 |    5.60 |               1.000 |
| T2        | all             |  11 |    0.40 |    1.30 |    5.60 |               1.000 |
| T3        | keep_possession |   1 |    3.60 |    3.60 |    3.60 |               1.000 |
| T3        | all             |   1 |    3.60 |    3.60 |    3.60 |               1.000 |
| T4        | keep_possession |   2 |    7.50 |    8.30 |    9.10 |               1.000 |
| T4        | all             |   2 |    7.50 |    8.30 |    9.10 |               1.000 |
| T6        | keep_possession |   1 |    4.90 |    4.90 |    4.90 |               1.000 |
| T6        | all             |   1 |    4.90 |    4.90 |    4.90 |               1.000 |
| all       | all             |  20 |    0.58 |    2.80 |    6.58 |               1.000 |

A1d. Continuity = same team: gap quantiles (seconds) and share with gap >= 3 frames, by cell:

| trigger   | resolution        |    n |   p10 s |   p50 s |   p90 s |   share gap >= 3 fr |
|:----------|:------------------|-----:|--------:|--------:|--------:|--------------------:|
| T0        | pass_reception    | 3137 |    0.80 |    1.30 |    2.10 |               0.995 |
| T0        | keep_possession   |   54 |    1.60 |    2.95 |    4.64 |               1.000 |
| T0        | all               | 3191 |    0.80 |    1.30 |    2.20 |               0.995 |
| T1        | keep_possession   |    4 |    2.05 |    2.55 |    4.94 |               1.000 |
| T1        | all               |    4 |    2.05 |    2.55 |    4.94 |               1.000 |
| T2        | pass_interception |    2 |    2.00 |    2.40 |    2.80 |               1.000 |
| T2        | recovery          |    3 |    4.74 |    5.70 |    6.90 |               1.000 |
| T2        | keep_possession   |   67 |    1.54 |    3.50 |    5.66 |               1.000 |
| T2        | unknown           |    2 |   33.73 |   42.25 |   50.77 |               1.000 |
| T2        | all               |   74 |    1.70 |    3.70 |    5.97 |               1.000 |
| T3        | keep_possession   |   18 |    0.80 |    2.10 |    3.63 |               1.000 |
| T3        | unknown           |    1 |   23.70 |   23.70 |   23.70 |               1.000 |
| T3        | all               |   19 |    0.80 |    2.10 |    3.92 |               1.000 |
| T4        | pass_interception |    1 |    7.20 |    7.20 |    7.20 |               1.000 |
| T4        | keep_possession   |   73 |    0.20 |    1.30 |    3.50 |               0.863 |
| T4        | unknown           |    2 |   10.06 |   10.30 |   10.54 |               1.000 |
| T4        | all               |   76 |    0.20 |    1.35 |    4.15 |               0.868 |
| T5        | keep_possession   |    1 |    0.20 |    0.20 |    0.20 |               0.000 |
| T5        | all               |    1 |    0.20 |    0.20 |    0.20 |               0.000 |
| T6        | keep_possession   |    3 |    2.64 |    2.80 |    3.36 |               1.000 |
| T6        | unknown           |    3 |   11.34 |   11.50 |   12.62 |               1.000 |
| T6        | all               |    6 |    2.70 |    7.40 |   12.20 |               1.000 |
| all       | all               | 3371 |    0.80 |    1.30 |    2.30 |               0.992 |

A1d. Continuity = change of team: gap quantiles (seconds) and share with gap >= 3 frames, by cell:

| trigger   | resolution        |   n |   p10 s |   p50 s |   p90 s |   share gap >= 3 fr |
|:----------|:------------------|----:|--------:|--------:|--------:|--------------------:|
| T0        | pass_interception |   2 |    6.02 |    6.10 |    6.18 |               1.000 |
| T0        | recovery          |  69 |    1.38 |    2.60 |    4.82 |               1.000 |
| T0        | all               |  71 |    1.40 |    2.90 |    5.00 |               1.000 |
| T1        | recovery          |  22 |    1.93 |    2.85 |    4.98 |               1.000 |
| T1        | all               |  22 |    1.93 |    2.85 |    4.98 |               1.000 |
| T2        | pass_reception    |   1 |    4.10 |    4.10 |    4.10 |               1.000 |
| T2        | pass_interception | 353 |    0.70 |    1.70 |    3.10 |               0.980 |
| T2        | recovery          |  64 |    1.50 |    3.45 |    5.27 |               1.000 |
| T2        | keep_possession   |   1 |    9.80 |    9.80 |    9.80 |               1.000 |
| T2        | all               | 419 |    0.80 |    1.90 |    3.80 |               0.983 |
| T3        | recovery          |  30 |    0.30 |    0.95 |    2.35 |               0.933 |
| T3        | unknown           |   1 |  153.50 |  153.50 |  153.50 |               1.000 |
| T3        | all               |  31 |    0.30 |    1.10 |    2.80 |               0.935 |
| T4        | recovery          | 157 |    0.10 |    0.20 |    1.60 |               0.471 |
| T4        | unknown           |   1 |  109.60 |  109.60 |  109.60 |               1.000 |
| T4        | all               | 158 |    0.10 |    0.20 |    1.63 |               0.475 |
| T5        | pass_reception    |   1 |    2.80 |    2.80 |    2.80 |               1.000 |
| T5        | recovery          |   8 |    1.54 |    2.65 |    3.72 |               1.000 |
| T5        | all               |   9 |    1.56 |    2.70 |    3.68 |               1.000 |
| T6        | recovery          |   2 |    0.65 |    1.25 |    1.85 |               1.000 |
| T6        | all               |   2 |    0.65 |    1.25 |    1.85 |               1.000 |
| other     | recovery          |   1 |    1.30 |    1.30 |    1.30 |               1.000 |
| other     | all               |   1 |    1.30 |    1.30 |    1.30 |               1.000 |
| all       | all               | 713 |    0.20 |    1.60 |    3.80 |               0.871 |

A1e. Candidate episodes under the provisional definition:

| route                               |   pairs |
|:------------------------------------|--------:|
| trigger T1 to T6 only               |     525 |
| resolution recovery or unknown only |      70 |
| both                                |     296 |
| all candidates                      |     891 |

|   retained pairs meeting the trigger or resolution rule |   excluded as same player |   excluded for gap < 1 frame |   candidates |
|--------------------------------------------------------:|--------------------------:|-----------------------------:|-------------:|
|                                                     906 |                        15 |                            0 |          891 |

A1f. Candidates, gap in frames by bucket, by trigger and resolution (cells with n >= 5):

| trigger   | resolution        |   gap 1 fr |   gap 2 fr |   gap 3-5 fr |   gap 6-10 fr |   gap 11-30 fr |   gap >30 fr |
|:----------|:------------------|-----------:|-----------:|-------------:|--------------:|---------------:|-------------:|
| T0        | recovery          |          0 |          0 |            0 |             4 |             34 |           31 |
| T1        | recovery          |          0 |          0 |            0 |             0 |             13 |            9 |
| T2        | keep_possession   |          0 |          0 |            0 |             3 |             24 |           41 |
| T2        | pass_interception |          1 |          6 |           14 |            52 |            243 |           39 |
| T2        | recovery          |          0 |          0 |            0 |             4 |             20 |           43 |
| T3        | keep_possession   |          0 |          0 |            0 |             3 |              9 |            6 |
| T3        | recovery          |          1 |          1 |            6 |             7 |             13 |            2 |
| T4        | keep_possession   |          6 |          4 |            8 |            10 |             34 |           11 |
| T4        | recovery          |         68 |         15 |           15 |            25 |             31 |            3 |
| T5        | recovery          |          0 |          0 |            0 |             0 |              5 |            3 |

A1g. Candidates where the player of possession i+1 is the goalkeeper (player_position GK):

| trigger   | resolution        |   candidates |   goalkeeper |
|:----------|:------------------|-------------:|-------------:|
| T0        | recovery          |           69 |            4 |
| T2        | keep_possession   |           68 |            1 |
| T2        | pass_interception |          355 |           28 |
| T2        | recovery          |           67 |            8 |
| T3        | recovery          |           30 |           14 |
| T3        | unknown           |            2 |            1 |
| T4        | keep_possession   |           73 |            1 |
| T4        | recovery          |          157 |            2 |

Candidates by match:

|   match_id |   candidates |
|-----------:|-------------:|
|    1886347 |          178 |
|    1959846 |          187 |
|    1996435 |          192 |
|    1996436 |          174 |
|    2007448 |          160 |

Long gaps among retained pairs, by trigger:

| trigger   |   gap > 5 s |   gap > 10 s |   gap > 30 s |   max gap s |
|:----------|------------:|-------------:|-------------:|------------:|
| T0        |          13 |            0 |            0 |         8.2 |
| T1        |           3 |            0 |            0 |         9.4 |
| T2        |          33 |            2 |            2 |        52.9 |
| T3        |           2 |            2 |            1 |       153.5 |
| T4        |           8 |            2 |            1 |       109.6 |
| T5        |           0 |            0 |            0 |         4.0 |
| T6        |           3 |            3 |            0 |        12.9 |
| other     |           0 |            0 |            0 |         1.3 |
| all       |          62 |            9 |            4 |       153.5 |


Figure: audit/figures/a1_gap_histogram.png (retained pairs, gap 0 to 50 frames, one panel per trigger class; no random draw, so no seed).

A1h. All retained pairs with resolution unknown (seq_i is the position of possession i in the sorted possession sequence of the match). No retained pair with any other resolution has a gap above 98 frames.

|   match_id |   seq_i | trigger   | continuity     |   gap (frames) | candidate   |   gap s |
|-----------:|--------:|:----------|:---------------|------:|:------------|--------:|
|    1959846 |     234 | T4        | same team      |   100 | True        |    10.0 |
|    1959846 |     644 | T4        | same team      |   106 | True        |    10.6 |
|    1886347 |     258 | T6        | same team      |   113 | True        |    11.3 |
|    2007448 |     528 | T6        | same team      |   115 | True        |    11.5 |
|    1996435 |     593 | T6        | same team      |   129 | True        |    12.9 |
|    1886347 |     272 | T3        | same team      |   237 | True        |    23.7 |
|    1996436 |      57 | T2        | same team      |   316 | True        |    31.6 |
|    1959846 |     584 | T2        | same team      |   529 | True        |    52.9 |
|    1996436 |     659 | T4        | change of team |  1096 | True        |   109.6 |
|    1886347 |     929 | T3        | change of team |  1535 | True        |   153.5 |

A1 reading. Facts from the tables above; no definition is changed here.

| item | finding |
|:--|:--|
| gap 0 | never occurs; the smallest retained gap is 1 frame, so the gap >= 1 rule removes nothing and the only exclusion among in-scope pairs is same player (15 pairs) |
| candidate volume | 891 candidate pairs, 160 to 192 per match |
| T2 to pass_interception | the largest candidate cell, 355 of 891 (39.8%), 353 of them change of team; median gap 1.7 s, 243 with gaps of 11 to 30 frames. This matches the flight of a pass to an opponent. The brief's idea text names "an unsuccessful pass that nobody intercepts cleanly"; the provisional definition includes the clean interceptions |
| T4 to recovery | 157 candidates, median gap 0.2 s; 68 at 1 frame and 15 at 2 frames (83, 52.9%). A dispossession followed one or two frames later by the opponent's possession reads as a tackle with the ball kept. The other 74 spread over several seconds |
| T3 to recovery | 30 candidates, median gap 0.95 s, 14 won by the goalkeeper |
| T0 to recovery | 69 candidates, all change of team, all gaps >= 6 frames, median 2.6 s; they enter through the resolution rule only |
| resolution unknown | all 10 retained pairs have gap >= 100 frames (10 s) and all 10 are candidates. This looks like the start being marked unknown after a stoppage that carries no game_interruption value. Inference only; not checked against video or the specification |
| clearances | 36 retained pairs end in a clearance (26 T1, 10 T5) |

A1 tables above were produced at commit 67b1fb3 with the provisional definition. Table A1i below was added to scripts/a1_gap_crosstab.py afterwards and run on the same code before any revision.

A1i. Retained pairs, resolution by continuity:

| resolution        |   same player |   same team |   change of team |   all |
|:------------------|--------------:|------------:|-----------------:|------:|
| pass_reception    |             0 |        3137 |                2 |  3139 |
| pass_interception |             0 |           3 |              355 |   358 |
| recovery          |             0 |           3 |              353 |   356 |
| keep_possession   |            20 |         220 |                1 |   241 |
| unknown           |             0 |           8 |                2 |    10 |
| all               |            20 |        3371 |              713 |  4104 |

### Post hoc revisions after A0 and A1 (2026-10-27)

Decided by the project lead after seeing A0 and A1. Every item here is post hoc. Reasons are as given by the project lead unless marked otherwise. Pair counts are retained pairs from A1 (gap >= 1).

Principle, as given: a loose ball is a release after which nobody controls the ball directly. A clean reception (pass_reception) and a clean interception (pass_interception) are the same mechanism from opposite sides, so both are excluded. The winner of a loose ball never enters its definition.

| # | revision | reason | pairs affected |
|:--|:--|:--|:--|
| 1 | drop every pair whose resolution is pass_interception | a clean interception is direct control | 355 after T2 (context); 356 among triggers T1 to T7 (355 T2, 1 T4); 358 among all retained pairs (2 more after T0, never candidates) |
| 1a | drop pairs whose resolution is pass_reception | the stated principle excludes clean receptions with clean interceptions; decision 1 names only pass_interception, so applying it to pass_reception is my reading of the principle, flagged for confirmation | 2 (1 after T2, 1 after T5) |
| 2 | minimum gap of 3 frames for every candidate in A2 to A6, G1, G3 and G4; G2 stays on the gap >= 1 candidate set, as in the brief | removes tackles where the tackler controls the ball directly (A1f: 68 T4 to recovery pairs at 1 frame, 15 at 2) | reported in A5 |
| 3 | drop T3 pairs won by a player whose player_position is GK | a save held by the goalkeeper is direct control. Known selection on the winner, limited to T3; goalkeepers winning loose balls after other triggers stay | 14 (T3 to recovery); 1 more T3 pair won by a goalkeeper has resolution unknown and falls under 4 |
| 4 | drop pairs whose resolution is unknown; no gap cap for now | all 10 have gap >= 10 s (A1h). A6 reports the gap tail; the seeded figure draw adds three pairs from the top 5% of gaps | 10 |
| 5 | T5 tested before T1, confirmed. Drop pairs whose possession i has end_type foul_suffered; there is no "other" class | a foul is followed by a restart | 1 |
| 6 | candidates are defined by trigger class only: the clause "or whose resolution is recovery or unknown" is removed. New trigger T7: end_type pass and pass_outcome successful (T0), followed by a possession whose start_type is recovery or keep_possession | a completed pass that nobody controlled directly. The old rule kept T0 to recovery (69) and dropped T0 to keep_possession (59), which selected on the winner | T7: 128 retained pairs, 5 of them same player |
| 7 | report whether recovery always means a change of team and keep_possession always the same team | requested | see below |

Item 7, from A1i: neither holds strictly. recovery is a change of team in 353 of 356 retained pairs; the other 3 are same team, all after a T2 failed pass (A1d). keep_possession is same team in 220 of 241, same player in 20 and change of team in 1, after a T2 failed pass (A1d).

### Revised candidate definition (2026-10-27)

Implemented in src/looseball/episodes.py (pairs, scrambles, window_measures).

| element | definition |
|:--|:--|
| retained pair | consecutive player_possession rows i, i+1 sorted by frame_start; dropped when they span a period boundary, when i+1 starts from a restart (start_type throw_in, free_kick, goal_kick or corner, reception or interception), when pass_outcome of i is offside, when game_interruption_after of i or game_interruption_before of i+1 is set, or when end_type of i is foul_suffered |
| trigger, tested in this order | T5 header non-pass (is_header TRUE, end_type not pass or shot); T1 clearance; T2 failed pass (pass, unsuccessful); T3 shot; T4 dispossession (possession_loss); T6 unknown end_type; T7 completed pass not controlled (pass, successful, start_type of i+1 recovery or keep_possession); T0 completed pass (reference, not a candidate) |
| candidate pair (G2 set) | retained; trigger T1 to T7; resolution (start_type of i+1) recovery or keep_possession; not a T3 pair won by player_position GK; not the same player; gap >= 1 frame |
| main set (A2 to A6, G1, G3, G4) | candidate pairs with gap >= 3 frames |
| scramble | main pairs are merged when the winning possession of one is the releasing possession of the next main pair, lasts fewer than 5 frames (frame_end minus frame_start < 5, equal to the CSV duration < 0.5 s) and ends in possession_loss, clearance or unknown. Scramble trigger: that of its first pair. Scramble winner: team of possession i+1 of its last pair. Aerial if any link is aerial |
| window | frames strictly after the release frame (frame_end of i) up to and including the pickup frame (frame_start of i+1) |
| aerial | ball_data.z > 1.8 m on any window frame with ball_data.is_detected TRUE; an episode with no detected window frame is ground (counted in A6) |

### A2 to A6 implementation choices, logged before the run (2026-10-27)

| item | choice |
|:--|:--|
| unit (set by the project lead before the run) | raw main pairs for A2, A3, A4, A6, G3 and G4; merged scrambles of main pairs for G1; A5 reports both |
| rotation of event coordinates (A2) | specification p. 11: event coordinates assume the team in possession attacks left to right, mirrored for the team attacking right to left, origin at the centre. Rotation used: (x, y) to (-x, -y) when attacking_side of possession i+1 is right_to_left. As a check, A2 also reports the x-only mirror and no rotation |
| missing pickup point | when the pickup frame has no ball position (an empty frame), the episode is left out of the A2 distances and the A4 player counts, and counted. Winner detection counts it as not detected |
| window ball detection (A3, G3) | denominator: all window frames; a frame without ball data counts as not detected |
| teams in A4 | the releasing team (team of possession i) and the other team; the winner does not label players |
| detection shares in A4 and G4 (set by the project lead before the run) | pooled over player instances, separately for the release frame and the pickup frame |
| phases (A5) | an episode lies in the phase of the phases of play CSV whose frame_start to frame_end contains its release frame; on a shared boundary frame, the earlier phase. Phase type: team_in_possession_phase_type |
| horizontal distance (A6) | straight-line distance between the tracking ball on the release frame and on the pickup frame; not path length, since nothing is smoothed in step 1 and a path on raw positions adds noise |
| seeded figures | seed 20261027, numpy default_rng. Order of draws without replacement: 6 from all main pairs, then 3 from main pairs with gap >= the 95th percentile of main-pair gaps, then 2 from T7 main pairs. 11 figures (set by the project lead before the run) |

### Gate thresholds, logged before the gate code runs (2026-10-27)

Thresholds are those of the brief. The two procedural points the brief leaves open (small margin in G3, pooling in G4) were set by the project lead before any revised result was computed.

| gate | set | pass condition | on failure |
|:--|:--|:--|:--|
| G1 volume | merged scrambles of main pairs, per match | >= 50 in each of the five exploration matches | stop: too thin for team-level work |
| G2 window exists | candidate pairs, gap >= 1, before merging or further filtering | median gap >= 5 frames (0.5 s) and share of pairs with gap >= 3 frames >= 0.60 | stop: no loose window; the 1v1 approach idea is next |
| G3 ball seen | main pairs | ball_data.is_detected TRUE on >= 0.85 of window frames, pooled; and share of pairs with at least one no-camera or empty window frame <= 0.25 (also reported by trigger class) | small margin, defined as every failing criterion within 5 percentage points of its threshold (>= 0.80; <= 0.30): recheck once on main pairs with gap <= 20 frames (2 s), same thresholds. Larger miss, or second failure: stop |
| G4 players seen | main pairs | pooled share of detected players within 15 m of the pickup point >= 0.85 on the release frame and >= 0.85 on the pickup frame; and winner detected on the pickup frame in >= 0.90 of pairs | recheck once with a 10 m radius (the winner criterion does not depend on the radius); second failure: stop |

### A2 to A6 and T7, revised candidate set (2026-10-27)

Script: scripts/a2_a6.py, run after the thresholds commit 1f0b65c. "Main pairs" are candidate pairs with gap >= 3 frames. CSV: audit/loose_episodes_exploration.csv, one row per candidate pair (gap >= 1, 562 rows); column main marks gap >= 3; scramble fields are set on main pairs only; winner_team_id is the team of possession i+1.

A2a. Pickup point agreement: tracking ball on the pickup frame vs rotated event x_start, y_start of i+1:

| trigger   |   pairs |   no pickup point |   p10 m |   p50 m |   p90 m |   p95 m |   share <= 2 m |   share <= 5 m |
|:----------|--------:|------------------:|--------:|--------:|--------:|--------:|---------------:|---------------:|
| T1        |      26 |                 0 |   0.819 |   1.640 |   2.459 |   2.617 |          0.731 |          1.000 |
| T2        |     135 |                 0 |   0.729 |   1.463 |   2.647 |   3.239 |          0.763 |          0.978 |
| T3        |      32 |                 0 |   0.859 |   1.556 |   3.099 |   3.277 |          0.656 |          1.000 |
| T4        |     137 |                 0 |   0.608 |   1.253 |   2.142 |   2.599 |          0.883 |          1.000 |
| T5        |       8 |                 0 |   0.736 |   1.383 |   2.182 |   2.374 |          0.750 |          1.000 |
| T6        |       5 |                 0 |   1.567 |   2.053 |   7.766 |   9.604 |          0.400 |          0.800 |
| T7        |     123 |                 0 |   0.792 |   1.527 |   2.945 |   4.047 |          0.707 |          0.976 |
| all       |     466 |                 0 |   0.698 |   1.426 |   2.644 |   3.196 |          0.770 |          0.985 |

A2b. Same, by frame class of the pickup frame:

| pickup frame class   |   pairs |   no pickup point |   p10 m |   p50 m |   p90 m |   p95 m |   share <= 2 m |   share <= 5 m |
|:---------------------|--------:|------------------:|--------:|--------:|--------:|--------:|---------------:|---------------:|
| camera               |     456 |                 0 |   0.708 |   1.426 |   2.619 |   3.117 |          0.774 |          0.987 |
| no_camera            |      10 |                 0 |   0.516 |   1.669 |   4.349 |   7.896 |          0.600 |          0.900 |
| empty                |       0 |                 0 | nan     | nan     | nan     | nan     |        nan     |        nan     |

A2c. Rotation check, all main pairs with a pickup point:

| event frame to tracking frame                |   median m |   share <= 2 m |   share <= 5 m |
|:---------------------------------------------|-----------:|---------------:|---------------:|
| (x, y) to (-x, -y) when right_to_left (used) |      1.426 |          0.770 |          0.985 |
| x only mirrored when right_to_left           |      3.584 |          0.369 |          0.519 |
| no rotation                                  |     19.150 |          0.358 |          0.483 |

A3. Ball visibility in the window, main pairs:

| trigger   |   pairs |   window frames |   share of window frames ball detected |   share of pairs with a no-camera or empty window frame |   with a no-camera frame |   with an empty frame |   share release or pickup frame not camera |
|:----------|--------:|----------------:|---------------------------------------:|--------------------------------------------------------:|-------------------------:|----------------------:|-------------------------------------------:|
| T1        |      26 |             874 |                                  0.879 |                                                   0.038 |                    0.038 |                 0.000 |                                      0.000 |
| T2        |     135 |            4933 |                                  0.928 |                                                   0.030 |                    0.030 |                 0.000 |                                      0.030 |
| T3        |      32 |             625 |                                  0.974 |                                                   0.000 |                    0.000 |                 0.000 |                                      0.000 |
| T4        |     137 |            2086 |                                  0.819 |                                                   0.124 |                    0.124 |                 0.007 |                                      0.117 |
| T5        |       8 |             213 |                                  1.000 |                                                   0.000 |                    0.000 |                 0.000 |                                      0.000 |
| T6        |       5 |             114 |                                  0.447 |                                                   0.600 |                    0.600 |                 0.000 |                                      0.600 |
| T7        |     123 |            3726 |                                  0.973 |                                                   0.049 |                    0.049 |                 0.000 |                                      0.033 |
| all       |     466 |           12571 |                                  0.919 |                                                   0.067 |                    0.067 |                 0.002 |                                      0.058 |

A4a. Players within radius of the pickup point, main pairs with a pickup point (466 of 466). Mean count per pair by team; detected shares pooled over players:

| frame   |   radius m | trigger   |   pairs |   mean n releasing team |   mean n other team |   detected share releasing |   detected share other |   detected share all |
|:--------|-----------:|:----------|--------:|------------------------:|--------------------:|---------------------------:|-----------------------:|---------------------:|
| release |         10 | T1        |      26 |                    0.65 |                0.92 |                       0.82 |                   0.38 |                 0.56 |
| release |         10 | T2        |     135 |                    1.53 |                1.80 |                       0.82 |                   0.82 |                 0.82 |
| release |         10 | T3        |      32 |                    2.16 |                3.09 |                       0.88 |                   0.96 |                 0.93 |
| release |         10 | T4        |     137 |                    2.12 |                2.55 |                       0.89 |                   0.90 |                 0.90 |
| release |         10 | T5        |       8 |                    1.25 |                1.00 |                       1.00 |                   0.62 |                 0.83 |
| release |         10 | T6        |       5 |                    0.60 |                0.80 |                       1.00 |                   0.75 |                 0.86 |
| release |         10 | T7        |     123 |                    1.54 |                1.99 |                       0.79 |                   0.78 |                 0.78 |
| release |         10 | all       |     466 |                    1.68 |                2.09 |                       0.85 |                   0.84 |                 0.84 |
| release |         15 | T1        |      26 |                    1.42 |                2.08 |                       0.73 |                   0.41 |                 0.54 |
| release |         15 | T2        |     135 |                    2.71 |                3.30 |                       0.83 |                   0.81 |                 0.82 |
| release |         15 | T3        |      32 |                    3.28 |                5.12 |                       0.87 |                   0.95 |                 0.92 |
| release |         15 | T4        |     137 |                    3.55 |                4.28 |                       0.89 |                   0.89 |                 0.89 |
| release |         15 | T5        |       8 |                    2.88 |                2.62 |                       1.00 |                   0.76 |                 0.89 |
| release |         15 | T6        |       5 |                    2.40 |                1.80 |                       0.83 |                   0.78 |                 0.81 |
| release |         15 | T7        |     123 |                    2.76 |                3.70 |                       0.81 |                   0.78 |                 0.79 |
| release |         15 | all       |     466 |                    2.94 |                3.73 |                       0.85 |                   0.83 |                 0.84 |
| pickup  |         10 | T1        |      26 |                    1.35 |                1.85 |                       0.97 |                   1.00 |                 0.99 |
| pickup  |         10 | T2        |     135 |                    2.36 |                2.77 |                       0.98 |                   0.98 |                 0.98 |
| pickup  |         10 | T3        |      32 |                    2.66 |                3.72 |                       0.96 |                   0.97 |                 0.97 |
| pickup  |         10 | T4        |     137 |                    2.51 |                3.26 |                       0.94 |                   0.94 |                 0.94 |
| pickup  |         10 | T5        |       8 |                    2.25 |                2.38 |                       1.00 |                   0.95 |                 0.97 |
| pickup  |         10 | T6        |       5 |                    1.40 |                1.60 |                       0.71 |                   0.75 |                 0.73 |
| pickup  |         10 | T7        |     123 |                    2.33 |                3.26 |                       0.98 |                   0.98 |                 0.98 |
| pickup  |         10 | all       |     466 |                    2.35 |                3.04 |                       0.96 |                   0.96 |                 0.96 |
| pickup  |         15 | T1        |      26 |                    2.19 |                2.88 |                       0.98 |                   0.95 |                 0.96 |
| pickup  |         15 | T2        |     135 |                    3.90 |                4.61 |                       0.96 |                   0.96 |                 0.96 |
| pickup  |         15 | T3        |      32 |                    4.06 |                6.16 |                       0.93 |                   0.96 |                 0.95 |
| pickup  |         15 | T4        |     137 |                    3.94 |                4.72 |                       0.92 |                   0.92 |                 0.92 |
| pickup  |         15 | T5        |       8 |                    4.00 |                3.75 |                       1.00 |                   0.93 |                 0.97 |
| pickup  |         15 | T6        |       5 |                    3.00 |                2.40 |                       0.60 |                   0.67 |                 0.63 |
| pickup  |         15 | T7        |     123 |                    3.74 |                5.20 |                       0.97 |                   0.96 |                 0.97 |
| pickup  |         15 | all       |     466 |                    3.78 |                4.77 |                       0.95 |                   0.95 |                 0.95 |

A4b. Winner detected on the pickup frame and fully_extrapolated of possession i+1, all main pairs:

| trigger   |   pairs |   winner detected on pickup frame |   i+1 fully_extrapolated TRUE |
|:----------|--------:|----------------------------------:|------------------------------:|
| T1        |      26 |                             0.962 |                         0.000 |
| T2        |     135 |                             0.993 |                         0.000 |
| T3        |      32 |                             1.000 |                         0.000 |
| T4        |     137 |                             0.927 |                         0.015 |
| T5        |       8 |                             1.000 |                         0.000 |
| T6        |       5 |                             0.800 |                         0.200 |
| T7        |     123 |                             1.000 |                         0.000 |
| all       |     466 |                             0.972 |                         0.006 |

A5a. Exclusion flow, all five matches (each row applies its rule to the row above):

| step                                     |   pairs |
|:-----------------------------------------|--------:|
| retained pairs                           |    4103 |
| trigger T1 to T7                         |     964 |
| resolution recovery or keep_possession   |     596 |
| not a T3 pair won by GK                  |     582 |
| not the same player                      |     562 |
| gap >= 1 frame (candidate pairs, G2 set) |     562 |
| gap >= 3 frames (main pairs)             |     466 |

A5b. Volume per match:

| match_id   |   candidate pairs (gap >= 1) |   main pairs (gap >= 3) |   merged scrambles |
|:-----------|-----------------------------:|------------------------:|-------------------:|
| 1886347    |                          114 |                      96 |                 91 |
| 1959846    |                          126 |                     104 |                101 |
| 1996435    |                          113 |                      94 |                 92 |
| 1996436    |                          119 |                      97 |                 93 |
| 2007448    |                           90 |                      75 |                 74 |
| total      |                          562 |                     466 |                451 |

A5c. Main pairs per match by trigger class:

| match_id   |   T1 |   T2 |   T3 |   T4 |   T5 |   T6 |   T7 |   total |
|:-----------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|--------:|
| 1886347    |    5 |   26 |    7 |   32 |    4 |    1 |   21 |      96 |
| 1959846    |    5 |   28 |    8 |   31 |    2 |    2 |   28 |     104 |
| 1996435    |    6 |   27 |    7 |   30 |    1 |    2 |   21 |      94 |
| 1996436    |    7 |   30 |    6 |   22 |    1 |    0 |   31 |      97 |
| 2007448    |    3 |   24 |    4 |   22 |    0 |    0 |   22 |      75 |
| total      |   26 |  135 |   32 |  137 |    8 |    5 |  123 |     466 |

A5d. Merged scrambles per match by trigger class of the first link:

| match_id   |   T1 |   T2 |   T3 |   T4 |   T5 |   T6 |   T7 |   total |
|:-----------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|--------:|
| 1886347    |    3 |   26 |    7 |   32 |    1 |    1 |   21 |      91 |
| 1959846    |    2 |   28 |    8 |   31 |    2 |    2 |   28 |     101 |
| 1996435    |    4 |   27 |    7 |   30 |    1 |    2 |   21 |      92 |
| 1996436    |    4 |   30 |    6 |   22 |    0 |    0 |   31 |      93 |
| 2007448    |    2 |   24 |    4 |   22 |    0 |    0 |   22 |      74 |
| total      |   15 |  135 |   32 |  137 |    4 |    5 |  123 |     451 |

A5e. Aerial or ground per match, main pairs and merged scrambles:

| match_id   |   main pairs aerial |   main pairs ground |   scrambles aerial |   scrambles ground |
|:-----------|--------------------:|--------------------:|-------------------:|-------------------:|
| 1886347    |                  39 |                  57 |                 35 |                 56 |
| 1959846    |                  45 |                  59 |                 43 |                 58 |
| 1996435    |                  39 |                  55 |                 39 |                 53 |
| 1996436    |                  50 |                  47 |                 48 |                 45 |
| 2007448    |                  38 |                  37 |                 38 |                 36 |
| total      |                 211 |                 255 |                203 |                248 |

A5f. Scramble size (links = main pairs merged):

|   links |   scrambles |
|--------:|------------:|
|       1 |         437 |
|       2 |          13 |
|       3 |           1 |

A5g. Phases of play (team_in_possession_phase_type) and main pairs by release frame:

| type        |   phases |   phases with an episode |   main pairs released in it |   share of phases with an episode |   share of main pairs |
|:------------|---------:|-------------------------:|----------------------------:|----------------------------------:|----------------------:|
| build_up    |      308 |                       49 |                          51 |                             0.159 |                 0.109 |
| chaotic     |      414 |                       80 |                          83 |                             0.193 |                 0.178 |
| create      |      699 |                      109 |                         118 |                             0.156 |                 0.253 |
| direct      |      141 |                       10 |                          10 |                             0.071 |                 0.021 |
| finish      |      433 |                      115 |                         142 |                             0.266 |                 0.305 |
| quick_break |       19 |                       10 |                          12 |                             0.526 |                 0.026 |
| set_play    |      104 |                       26 |                          36 |                             0.250 |                 0.077 |
| transition  |       41 |                       12 |                          14 |                             0.293 |                 0.030 |

A5h. Winner counts by match and team (plain counts; no predictor is related to them):

|   match_id |   team_id | team            |   main pairs won |   scrambles won |
|-----------:|----------:|:----------------|-----------------:|----------------:|
|    1886347 |      1805 | Newcastle       |               44 |              41 |
|    1886347 |      4177 | Auckland FC     |               52 |              50 |
|    1959846 |       868 | Melbourne V FC  |               51 |              51 |
|    1959846 |      1803 | Western United  |               53 |              50 |
|    1996435 |       866 | Adelaide United |               47 |              46 |
|    1996435 |       869 | Sydney FC       |               47 |              46 |
|    1996436 |      1804 | Macarthur FC    |               44 |              40 |
|    1996436 |      4177 | Auckland FC     |               53 |              53 |
|    2007448 |       871 | Perth Glory     |               37 |              37 |
|    2007448 |      1802 | Brisbane FC     |               38 |              37 |

A6a. Flight geometry, main pairs (quantiles p10, p50, p90):

| trigger   |   pairs |   window s p10 |   window s p50 |   window s p90 |   pairs with a detected window frame |   max z m p10 |   max z m p50 |   max z m p90 |   share aerial |   pairs with ball at both ends |   ball distance m p10 |   ball distance m p50 |   ball distance m p90 |
|:----------|--------:|---------------:|---------------:|---------------:|-------------------------------------:|--------------:|--------------:|--------------:|---------------:|-------------------------------:|----------------------:|----------------------:|----------------------:|
| T1        |      26 |           1.90 |           2.75 |           5.25 |                                   26 |          1.36 |          4.90 |          8.18 |           0.81 |                             26 |                 14.45 |                 28.01 |                 48.21 |
| T2        |     135 |           1.50 |           3.60 |           5.56 |                                  135 |          0.39 |          3.99 |          8.68 |           0.71 |                            135 |                  7.72 |                 20.22 |                 49.86 |
| T3        |      32 |           0.70 |           1.95 |           3.59 |                                   32 |          0.26 |          1.08 |          3.09 |           0.31 |                             32 |                  4.32 |                  9.71 |                 20.79 |
| T4        |     137 |           0.40 |           1.20 |           3.02 |                                  129 |          0.09 |          0.24 |          1.41 |           0.07 |                            137 |                  1.33 |                  5.10 |                 15.90 |
| T5        |       8 |           1.54 |           2.65 |           3.72 |                                    8 |          1.52 |          4.29 |          5.63 |           0.75 |                              8 |                  6.47 |                 17.78 |                 29.66 |
| T6        |       5 |           1.10 |           2.60 |           3.22 |                                    4 |          0.22 |          0.43 |          1.15 |           0.00 |                              5 |                  7.56 |                 19.64 |                 26.43 |
| T7        |     123 |           1.50 |           2.90 |           4.78 |                                  123 |          0.18 |          2.47 |          7.49 |           0.55 |                            123 |                  7.38 |                 19.35 |                 44.85 |
| all       |     466 |           0.70 |           2.30 |           4.90 |                                  457 |          0.16 |          1.53 |          7.32 |           0.45 |                            466 |                  2.84 |                 13.75 |                 42.07 |

A6b. Gap tail, main pairs (seconds):

| trigger   |   pairs |   p90 s |   p95 s |   p99 s |   max s |   gap > 5 s |   gap > 10 s |
|:----------|--------:|--------:|--------:|--------:|--------:|------------:|-------------:|
| T1        |      26 |    5.25 |    5.80 |    8.53 |    9.40 |           3 |            0 |
| T2        |     135 |    5.56 |    6.86 |    9.60 |    9.80 |          29 |            0 |
| T3        |      32 |    3.59 |    3.70 |    4.46 |    4.80 |           0 |            0 |
| T4        |     137 |    3.02 |    3.84 |    5.08 |    9.70 |           2 |            0 |
| T5        |       8 |    3.72 |    3.86 |    3.97 |    4.00 |           0 |            0 |
| T6        |       5 |    3.22 |    3.36 |    3.47 |    3.50 |           0 |            0 |
| T7        |     123 |    4.78 |    5.65 |    6.71 |    8.20 |           9 |            0 |
| all       |     466 |    4.90 |    5.57 |    8.55 |    9.80 |          43 |            0 |

T7a. T7 candidate pairs (gap >= 1), gap quantiles (seconds) by resolution and continuity:

| resolution      | continuity     |   pairs |   p10 |   p50 |   p90 |   share gap >= 3 fr |
|:----------------|:---------------|--------:|------:|------:|------:|--------------------:|
| keep_possession | same team      |      54 |  1.60 |  2.95 |  4.64 |                1.00 |
| recovery        | change of team |      69 |  1.38 |  2.60 |  4.82 |                1.00 |
| all             | all            |     123 |  1.50 |  2.90 |  4.78 |                1.00 |

T7b. T7 candidate pairs, gap in frames by bucket:

| gap frames   |   pairs |
|:-------------|--------:|
| 1-2          |       0 |
| 3-5          |       0 |
| 6-10         |       4 |
| 11-20        |      37 |
| 21-30        |      25 |
| 31-50        |      48 |
| >50          |       9 |


A2 to A6 reading. Facts from the tables above.

| item | finding |
|:--|:--|
| A2 | 98.5% of pickup points agree within 5 m and 77.0% within 2 m (median 1.43 m), above the 90% check, so no rotation or alignment problem. The x-only mirror gives 51.9% within 5 m and no rotation 48.3%, which confirms the 180 degree rotation. No main pair has an empty pickup frame |
| A3 | the ball is detected on 91.9% of window frames; 6.7% of main pairs have a no-camera or empty window frame, almost all no-camera (empty 0.2%). T4 is the weakest large class (81.9% detected, 12.4% camera loss); T6 (5 pairs) is poor (44.7%, 60.0%) |
| A4 | detection around the pickup point is high on the pickup frame (95% within 15 m) and lower on the release frame (84%), lowest for T1 (54%) and T7 (79%) at release. The winner is detected on the pickup frame in 97.2% of main pairs; fully_extrapolated is TRUE for possession i+1 in 0.6% |
| A5 | 466 main pairs, 75 to 104 per match; 451 merged scrambles. Merging is rare: 13 scrambles of 2 links and 1 of 3. 45% of main pairs are aerial. 19.3% of chaotic phases and 7.1% of direct phases contain a main pair; 17.8% of main pairs are released in a chaotic phase; every main pair's release frame lies in some phase |
| A6 | median window 2.3 s (p10 0.7, p90 4.9); median max detected ball height 1.53 m; median ball distance release to pickup 13.8 m. Gap tail: p95 5.57 s, p99 8.55 s, maximum 9.8 s; no main pair above 10 s after resolution unknown was dropped |
| T7 | 123 candidate pairs, all with gap >= 6 frames, so all are main pairs. keep_possession pairs (54) are all same team and recovery pairs (69) all change of team; median gaps 2.95 s and 2.60 s. T7 has the second lowest release-frame detection within 15 m (0.791, after T1) and its winner is detected on the pickup frame in all 123 pairs |

### Gates G1 to G4 (2026-10-27)

Script: scripts/gates.py, written and run after the thresholds were committed (1f0b65c). Thresholds and recheck rules as logged above; nothing was changed after the result.

G1 per match (merged scrambles of main pairs):

|   match_id |   merged scrambles |
|-----------:|-------------------:|
|    1886347 |                 91 |
|    1959846 |                101 |
|    1996435 |                 92 |
|    1996436 |                 93 |
|    2007448 |                 74 |

Gate verdicts:

| gate       | criterion                                                   | value                | threshold   | result   |
|:-----------|:------------------------------------------------------------|:---------------------|:------------|:---------|
| G1         | merged scrambles, minimum over matches                      | 74 (match 2007448)   | >= 50       | pass     |
| G2         | median gap, candidate pairs gap >= 1 (n = 562)              | 19.0 frames (1.90 s) | >= 5 frames | pass     |
| G2         | share with gap >= 3 frames                                  | 0.829                | >= 0.60     | pass     |
| G2         | verdict                                                     |                      |             | pass     |
| G3         | ball detected, share of window frames, main pairs (n = 466) | 0.919                | >= 0.85     | pass     |
| G3         | pairs with a no-camera or empty window frame                | 0.067                | <= 0.25     | pass     |
| G3         | verdict                                                     |                      |             | pass     |
| G4         | players within 15 m detected, release frame (n = 466)       | 0.8371               | >= 0.85     | fail     |
| G4         | players within 15 m detected, pickup frame                  | 0.9483               | >= 0.85     | pass     |
| G4         | winner detected on pickup frame                             | 0.9721               | >= 0.90     | pass     |
| G4 recheck | players within 10 m detected, release frame                 | 0.8434               | >= 0.85     | fail     |
| G4 recheck | players within 10 m detected, pickup frame                  | 0.9641               | >= 0.85     | pass     |
| G4 recheck | winner detected on pickup frame (radius-free)               | 0.9721               | >= 0.90     | pass     |
| G4         | verdict                                                     |                      |             | fail     |

G3 by trigger class, main pairs:

| trigger   |   pairs |   ball detected share |   camera loss share |
|:----------|--------:|----------------------:|--------------------:|
| T1        |      26 |                 0.879 |               0.038 |
| T2        |     135 |                 0.928 |               0.030 |
| T3        |      32 |                 0.974 |               0.000 |
| T4        |     137 |                 0.819 |               0.124 |
| T5        |       8 |                 1.000 |               0.000 |
| T6        |       5 |                 0.447 |               0.600 |
| T7        |     123 |                 0.973 |               0.049 |
| all       |     466 |                 0.919 |               0.067 |

G4 by trigger class, main pairs:

| trigger   |   pairs |   release 15 m |   pickup 15 m |   release 10 m |   pickup 10 m |   winner detected |
|:----------|--------:|---------------:|--------------:|---------------:|--------------:|------------------:|
| T1        |      26 |          0.538 |         0.962 |          0.561 |         0.988 |             0.962 |
| T2        |     135 |          0.820 |         0.961 |          0.822 |         0.980 |             0.993 |
| T3        |      32 |          0.918 |         0.951 |          0.929 |         0.966 |             1.000 |
| T4        |     137 |          0.887 |         0.923 |          0.897 |         0.938 |             0.927 |
| T5        |       8 |          0.886 |         0.968 |          0.833 |         0.973 |             1.000 |
| T6        |       5 |          0.810 |         0.630 |          0.857 |         0.733 |             0.800 |
| T7        |     123 |          0.791 |         0.966 |          0.781 |         0.980 |             1.000 |
| all       |     466 |          0.837 |         0.948 |          0.843 |         0.964 |             0.972 |

Gate verdicts, summary.

| gate | number | threshold | result |
|:--|:--|:--|:--|
| G1 volume | fewest merged scrambles in a match: 74 (2007448); range 74 to 101 | >= 50 per match | pass |
| G2 window exists | median gap 19 frames (1.90 s); share gap >= 3 frames 0.829 (n = 562) | >= 5 frames; >= 0.60 | pass |
| G3 ball seen | window frames ball detected 0.919; pairs with camera loss 0.067 (n = 466) | >= 0.85; <= 0.25 | pass |
| G4 players seen | within 15 m detected: release frame 0.8371, pickup frame 0.9483; winner detected 0.9721 | >= 0.85; >= 0.85; >= 0.90 | fail on the release frame |
| G4 recheck, 10 m | release frame 0.8434, pickup frame 0.9641; winner detected 0.9721 | same | fail on the release frame |

Under the brief, G4 failing twice means stop. Not all gates pass, so the episode definition is not frozen in DESIGN.md.

### Diagnostic after G4 (2026-10-27)

Not a gate and not a recheck; no threshold applies. Script: scripts/g4_diagnostic.py. Release-frame detection of players within the radius of the pickup point, split by whether the pickup point lies inside the camera view (the image_corners_projection polygon) on the release frame. The "all" rows reproduce the G4 values.

| pickup point at release   |   radius m |   pairs |   players |   detected share |
|:--------------------------|-----------:|--------:|----------:|-----------------:|
| inside                    |         15 |     302 |      2560 |            0.945 |
| inside                    |         10 |     302 |      1475 |            0.963 |
| outside or no camera view |         15 |     164 |       546 |            0.330 |
| outside or no camera view |         10 |     164 |       281 |            0.217 |
| all                       |         15 |     466 |      3106 |            0.837 |
| all                       |         10 |     466 |      1756 |            0.843 |

| trigger   |   pairs |   share with pickup point in view at release |
|:----------|--------:|---------------------------------------------:|
| T1        |      26 |                                        0.192 |
| T2        |     135 |                                        0.622 |
| T3        |      32 |                                        0.844 |
| T4        |     137 |                                        0.810 |
| T5        |       8 |                                        0.375 |
| T6        |       5 |                                        0.600 |
| T7        |     123 |                                        0.561 |

Reading. The release-frame shortfall in G4 comes from pairs whose pickup point is outside the camera view at release (164 of 466): 33.0% of players within 15 m are detected there, against 94.5% when the pickup point is in view. Long flights are most affected: the pickup point is in view at release for 19.2% of T1 pairs and 56.1% of T7 pairs, against 81.0% of T4 and 84.4% of T3 pairs.

### Seeded episode figures (2026-10-27)

Script: scripts/episode_figures.py. Seed 20261027 (numpy default_rng). Draw order as logged: 6 from all main pairs, 3 from main pairs with gap >= 55.8 frames (95th percentile of main-pair gaps), 2 from T7 main pairs, without replacement.

|   figure | draw     |   match_id |   seq_i | trigger   | resolution      |   gap | file                                                           |
|---------:|:---------|-----------:|--------:|:----------|:----------------|------:|:---------------------------------------------------------------|
|        1 | general  |    1996435 |     868 | T4        | keep_possession |    46 | audit/figures/episode_seed20261027_01_general_1996435_868.png  |
|        2 | general  |    1886347 |      99 | T2        | keep_possession |    51 | audit/figures/episode_seed20261027_02_general_1886347_99.png   |
|        3 | general  |    2007448 |     732 | T1        | recovery        |    38 | audit/figures/episode_seed20261027_03_general_2007448_732.png  |
|        4 | general  |    2007448 |     609 | T7        | recovery        |    14 | audit/figures/episode_seed20261027_04_general_2007448_609.png  |
|        5 | general  |    1959846 |      25 | T7        | keep_possession |    18 | audit/figures/episode_seed20261027_05_general_1959846_25.png   |
|        6 | general  |    1996436 |     378 | T3        | keep_possession |     7 | audit/figures/episode_seed20261027_06_general_1996436_378.png  |
|        7 | gap tail |    1996435 |     872 | T7        | recovery        |    64 | audit/figures/episode_seed20261027_07_gap_tail_1996435_872.png |
|        8 | gap tail |    1959846 |     468 | T7        | recovery        |    60 | audit/figures/episode_seed20261027_08_gap_tail_1959846_468.png |
|        9 | gap tail |    1959846 |     559 | T2        | recovery        |    68 | audit/figures/episode_seed20261027_09_gap_tail_1959846_559.png |
|       10 | T7       |    1996436 |     191 | T7        | recovery        |    18 | audit/figures/episode_seed20261027_10_T7_1996436_191.png       |
|       11 | T7       |    1959846 |     631 | T7        | recovery        |    38 | audit/figures/episode_seed20261027_11_T7_1959846_631.png       |

Figure reading (all 11 inspected). No bug found: the event and tracking pickup points agree within 2.7 m in all 11, and ball paths are continuous. Figures 3 and 10 show the G4 mechanism: at release the camera view covers the release area and not the landing zone, so players there are extrapolated, and they are detected again on the pickup frame. Figures 8 and 11 show a sharp change of ball direction inside the window, an uncontrolled touch that is not a possession (specification p. 6); in such pairs the A6 straight-line distance understates the ball's path.

### Post hoc revision 2, amended (2026-10-28)

Decided by the project lead after the gates. Post hoc. It supersedes the text of revision 2 in "Post hoc revisions after A0 and A1"; the minimum gap of 3 frames on the whole window stays.

Reason, as given: G4 failed at the release frame because the camera follows the ball, so for long flights the landing zone and the players around it are off screen at release (in view: 94.5% detected; out of view: 33.0%). The figures also show that long windows contain a flight and then a scramble of several touches. The anchor and the window structure change; the thresholds do not. No outcome has been used; the test set stays locked.

| element | definition |
|:--|:--|
| contact | a window frame at which the ball's velocity changes direction by more than 30 degrees or speed by more than 3 m/s between consecutive detected frames, with a player within 1.5 m of the ball on that frame. Contacts can only be found on runs of consecutive detected ball frames; the share of window time that is uncovered is reported |
| legs | the window split at its contacts. The first leg runs from the release (frame_end of i) to the first contact, or to the pickup if there is none. The last leg runs from the last contact to the pickup, or is the whole window if there is none. Number of legs recorded per episode |
| anchor of a leg | the first frame from the leg's start onward at which the pickup point lies inside the camera polygon (image_corners_projection). Lead = pickup frame minus anchor frame, in seconds. A leg with no such frame has no anchor and counts as lost to the camera |
| candidate episodes | unchanged: main pairs, gap >= 3 frames on the whole window |

Implementation choices, logged before the run. Items marked "set by the project lead" were answered before any revised result was computed.

| item | choice |
|:--|:--|
| velocity (set by the project lead) | horizontal (ball_data.x, ball_data.y); velocity from consecutive frames at 10 per second, no smoothing |
| frames tested for a contact | window frames except the pickup frame (the pickup touch ends the window). A frame t is testable when the ball is detected on t-1, t and t+1; t-1 may be the release frame and t+1 the pickup frame |
| direction when the ball does not move | if the speed into or out of t is zero the direction is undefined; only the speed criterion applies |
| player within 1.5 m | any player in player_data on frame t, detected or not; horizontal distance to the ball |
| uncovered share | frames from release+1 to pickup-1 that are not testable, over all such frames |
| anchor search end (set by the project lead) | from the leg start to the leg end inclusive; a first leg whose pickup point only comes into view after the first contact has no first-leg anchor. A frame without all eight image_corners_projection values is not in view. Pickup point: tracking ball on the pickup frame, as before |
| A7 apex | frame of the largest ball_data.z among window frames with is_detected TRUE. Apex observed when the ball is detected on the frames before and after it, both with z not above it; otherwise unobserved. Apex time quantiles are on observed apexes |
| A8 path length | sum of horizontal distances between consecutive ball positions from the release frame to the pickup frame, detected or not; a step with a missing position is skipped and counted |
| A9 | players within 15 m of the pickup point on the last-leg anchor frame whose is_detected is FALSE on the release frame. First detected position: the first frame after the release, up to the pickup frame, with is_detected TRUE. Implied speed: horizontal distance between the release-frame position and that position, over the time between. Players absent from the release frame or not detected by the pickup frame are counted, not measured |
| G1 and G3 | re-run on the main set. Episode membership does not change under this revision, so they are expected to reproduce the earlier values |
| figures | seed 20261028 (numpy default_rng), 4 drawn without replacement from main pairs with 2 or more contacts |

### G4 at the anchors, logged before the gate code runs (2026-10-28)

Thresholds unchanged from the first G4. Procedure set by the project lead before the run.

| item | rule |
|:--|:--|
| anchors | G4 is run twice: at the first-leg anchor and at the last-leg anchor |
| set | main pairs whose leg has an anchor; pairs without one are excluded from that run and the share lost to the camera is reported beside it, by trigger class |
| anchor side | pooled share of detected players within 15 m of the pickup point on the anchor frame >= 0.85 |
| pickup side | pooled share of detected players within 15 m of the pickup point on the pickup frame >= 0.85, same set |
| winner | winner detected on the pickup frame in >= 0.90 of the same set |
| verdict | decided by the pooled shares. The episode-level share (episodes with at least 85% of the players within 15 m detected; an episode with nobody within 15 m counts as fully observed) is reported beside each, with no threshold |
| recheck | if a run fails, recheck that run once with a 10 m radius; a second failure fails that anchor |
| outcome | G4 passes at either anchor: the revised definitions go into DESIGN.md with the choice of leg left open as the first step 2 decision, and step 1 stops. G4 fails at both: stop and report; the fallback (restricting to episodes with lead >= 0.5 s) is the project lead's decision |

### A7 to A9, revision 2 amended (2026-10-28)

Script: scripts/a7_a9.py, run after commit b835981. Main pairs (gap >= 3), n = 466. Tables A8e and A8f are diagnostics added after the contact figures showed contacts at the window edges and on consecutive frames; they describe the rule and do not change it. audit/loose_episodes_exploration.csv now also carries the contact, leg, anchor, apex and path columns (A2 to A6 tables reproduced unchanged).

A7a (first leg). Anchors and leads by trigger class:

| trigger   |   pairs |   anchor at leg start |   no anchor |   lead s p10 |   lead s p50 |   lead s p90 |   lead < 0.5 s (of anchored) |
|:----------|--------:|----------------------:|------------:|-------------:|-------------:|-------------:|-----------------------------:|
| T1        |      26 |                 0.192 |       0.269 |        0.500 |        1.400 |        2.500 |                        0.053 |
| T2        |     135 |                 0.622 |       0.111 |        1.090 |        2.850 |        4.710 |                        0.017 |
| T3        |      32 |                 0.844 |       0.062 |        0.670 |        1.650 |        3.140 |                        0.100 |
| T4        |     137 |                 0.810 |       0.073 |        0.400 |        1.100 |        2.080 |                        0.150 |
| T5        |       8 |                 0.375 |       0.000 |        0.790 |        1.350 |        2.630 |                        0.125 |
| T6        |       5 |                 0.600 |       0.000 |        0.540 |        0.900 |        3.220 |                        0.000 |
| T7        |     123 |                 0.561 |       0.138 |        1.050 |        2.000 |        4.000 |                        0.019 |
| all       |     466 |                 0.648 |       0.109 |        0.600 |        1.700 |        3.900 |                        0.067 |

A7b (first leg). Anchors and leads, aerial or ground:

| flight   |   pairs |   anchor at leg start |   no anchor |   lead s p10 |   lead s p50 |   lead s p90 |   lead < 0.5 s (of anchored) |
|:---------|--------:|----------------------:|------------:|-------------:|-------------:|-------------:|-----------------------------:|
| aerial   |     211 |                 0.526 |       0.152 |        1.100 |        2.700 |        4.540 |                        0.028 |
| ground   |     255 |                 0.749 |       0.075 |        0.500 |        1.400 |        2.400 |                        0.097 |
| all      |     466 |                 0.648 |       0.109 |        0.600 |        1.700 |        3.900 |                        0.067 |

A7a (last leg). Anchors and leads by trigger class:

| trigger   |   pairs |   anchor at leg start |   no anchor |   lead s p10 |   lead s p50 |   lead s p90 |   lead < 0.5 s (of anchored) |
|:----------|--------:|----------------------:|------------:|-------------:|-------------:|-------------:|-----------------------------:|
| T1        |      26 |                 0.269 |       0.000 |        0.250 |        1.200 |        2.350 |                        0.192 |
| T2        |     135 |                 0.659 |       0.000 |        0.740 |        1.800 |        3.800 |                        0.052 |
| T3        |      32 |                 0.875 |       0.000 |        0.300 |        1.000 |        3.000 |                        0.219 |
| T4        |     137 |                 0.832 |       0.058 |        0.100 |        0.900 |        1.800 |                        0.295 |
| T5        |       8 |                 0.375 |       0.000 |        0.790 |        1.250 |        2.460 |                        0.125 |
| T6        |       5 |                 0.600 |       0.000 |        0.540 |        0.900 |        3.220 |                        0.000 |
| T7        |     123 |                 0.667 |       0.000 |        0.420 |        1.500 |        2.680 |                        0.106 |
| all       |     466 |                 0.700 |       0.017 |        0.300 |        1.400 |        3.100 |                        0.155 |

A7b (last leg). Anchors and leads, aerial or ground:

| flight   |   pairs |   anchor at leg start |   no anchor |   lead s p10 |   lead s p50 |   lead s p90 |   lead < 0.5 s (of anchored) |
|:---------|--------:|----------------------:|------------:|-------------:|-------------:|-------------:|-----------------------------:|
| aerial   |     211 |                 0.616 |       0.000 |        0.500 |        1.500 |        3.600 |                        0.090 |
| ground   |     255 |                 0.769 |       0.031 |        0.200 |        1.000 |        2.340 |                        0.211 |
| all      |     466 |                 0.700 |       0.017 |        0.300 |        1.400 |        3.100 |                        0.155 |

A7c. Aerial pairs: apex (largest detected ball_data.z) relative to pickup:

| trigger   |   aerial pairs |   apex unobserved |   apex before pickup s p10 |   apex before pickup s p50 |   apex before pickup s p90 |
|:----------|---------------:|------------------:|---------------------------:|---------------------------:|---------------------------:|
| T1        |             21 |             0.095 |                      1.100 |                      2.100 |                      4.140 |
| T2        |             96 |             0.115 |                      0.800 |                      2.400 |                      3.860 |
| T3        |             10 |             0.200 |                      0.500 |                      1.200 |                      3.150 |
| T4        |             10 |             0.000 |                      0.600 |                      1.050 |                      1.870 |
| T5        |              6 |             0.000 |                      0.850 |                      1.500 |                      2.550 |
| T7        |             68 |             0.029 |                      0.750 |                      2.350 |                      3.400 |
| all       |            211 |             0.081 |                      0.800 |                      2.250 |                      3.700 |

A8a. Contacts per pair by trigger class, and the share of testable window time:

| trigger   |   pairs |   0 contacts |     1 |     2 |   3 or more |   uncovered share of window time |
|:----------|--------:|-------------:|------:|------:|------------:|---------------------------------:|
| T1        |      26 |        0.654 | 0.269 | 0.038 |       0.038 |                            0.134 |
| T2        |     135 |        0.533 | 0.193 | 0.104 |       0.170 |                            0.082 |
| T3        |      32 |        0.625 | 0.250 | 0.094 |       0.031 |                            0.030 |
| T4        |     137 |        0.774 | 0.153 | 0.036 |       0.036 |                            0.193 |
| T5        |       8 |        0.875 | 0.000 | 0.125 |       0.000 |                            0.000 |
| T6        |       5 |        1.000 | 0.000 | 0.000 |       0.000 |                            0.587 |
| T7        |     123 |        0.463 | 0.228 | 0.171 |       0.138 |                            0.032 |
| all       |     466 |        0.609 | 0.193 | 0.097 |       0.101 |                            0.089 |

A8b. Release to first contact (pairs with a contact) and duration of the last leg (all pairs), seconds:

| trigger   |   pairs |   with a contact |   to first contact p10 |   to first contact p50 |   to first contact p90 |   last leg p10 |   last leg p50 |   last leg p90 |
|:----------|--------:|-----------------:|-----------------------:|-----------------------:|-----------------------:|---------------:|---------------:|---------------:|
| T1        |      26 |                9 |                   0.10 |                   0.10 |                   2.78 |           1.45 |           2.55 |           4.40 |
| T2        |     135 |               63 |                   0.10 |                   0.10 |                   3.30 |           1.00 |           2.40 |           5.10 |
| T3        |      32 |               12 |                   0.10 |                   0.30 |                   2.18 |           0.30 |           1.35 |           3.50 |
| T4        |     137 |               31 |                   0.10 |                   0.60 |                   1.40 |           0.10 |           1.00 |           2.40 |
| T5        |       8 |                1 |                   1.60 |                   1.60 |                   1.60 |           1.28 |           2.35 |           3.72 |
| T6        |       5 |                0 |                 nan    |                 nan    |                 nan    |           1.10 |           2.60 |           3.22 |
| T7        |     123 |               66 |                   0.10 |                   0.20 |                   2.60 |           0.60 |           1.80 |           4.18 |
| all       |     466 |              182 |                   0.10 |                   0.20 |                   2.90 |           0.35 |           1.70 |           4.25 |

A8c. Ball path length next to the straight-line distance of A6, metres:

| trigger   |   pairs |   path p50 |   straight p50 |   path / straight p10 |   path / straight p50 |   path / straight p90 |   pairs with a skipped step |
|:----------|--------:|-----------:|---------------:|----------------------:|----------------------:|----------------------:|----------------------------:|
| T1        |      26 |      29.68 |          28.01 |                  1.01 |                  1.01 |                  1.07 |                           0 |
| T2        |     135 |      30.93 |          20.22 |                  1.01 |                  1.21 |                  2.63 |                           0 |
| T3        |      32 |      12.56 |           9.71 |                  1.00 |                  1.04 |                  1.84 |                           0 |
| T4        |     137 |       5.12 |           5.10 |                  1.00 |                  1.02 |                  1.15 |                           1 |
| T5        |       8 |      19.12 |          17.78 |                  1.01 |                  1.01 |                  1.75 |                           0 |
| T6        |       5 |      20.69 |          19.64 |                  1.01 |                  1.02 |                  1.04 |                           0 |
| T7        |     123 |      23.14 |          19.35 |                  1.00 |                  1.08 |                  1.97 |                           0 |
| all       |     466 |      17.93 |          13.75 |                  1.00 |                  1.05 |                  1.96 |                           1 |

A8d. Legs per pair:

|   legs (4 = 4 or more) |   pairs |
|-----------------------:|--------:|
|                      1 |     284 |
|                      2 |      90 |
|                      3 |      45 |
|                      4 |      47 |

A8e (diagnostic). First contacts by frames after release, and last contacts by frames before pickup:

| contact       | frames from the window edge   |   contacts | player checked   |   share with that player within 1.5 m |
|:--------------|:------------------------------|-----------:|:-----------------|--------------------------------------:|
| first contact | 1 after release               |         81 | releasing player |                                 0.679 |
| first contact | 2 after release               |         13 | releasing player |                                 0.231 |
| first contact | 3-5 after release             |         10 | releasing player |                                 0.300 |
| first contact | 6 or more after release       |         78 | releasing player |                                 0.064 |
| last contact  | 1 before pickup               |         28 | winner           |                                 0.964 |
| last contact  | 2 before pickup               |          9 | winner           |                                 0.333 |
| last contact  | 3-5 before pickup             |          5 | winner           |                                 0.200 |
| last contact  | 6 or more before pickup       |        140 | winner           |                                 0.043 |

A8f (diagnostic). Contacts and runs of consecutive contact frames, by trigger class:

| trigger   |   pairs |   contacts |   runs |   contacts per run |   0 runs |   1 run |   2 runs |   3 or more runs |
|:----------|--------:|-----------:|-------:|-------------------:|---------:|--------:|---------:|-----------------:|
| T1        |      26 |         13 |     13 |              1.000 |    0.654 |   0.269 |    0.038 |            0.038 |
| T2        |     135 |        144 |     88 |              1.636 |    0.533 |   0.326 |    0.126 |            0.015 |
| T3        |      32 |         19 |     13 |              1.462 |    0.625 |   0.344 |    0.031 |            0.000 |
| T4        |     137 |         49 |     38 |              1.289 |    0.774 |   0.182 |    0.036 |            0.007 |
| T5        |       8 |          2 |      1 |              2.000 |    0.875 |   0.125 |    0.000 |            0.000 |
| T6        |       5 |          0 |      0 |            nan     |    1.000 |   0.000 |    0.000 |            0.000 |
| T7        |     123 |        130 |     94 |              1.383 |    0.463 |   0.350 |    0.154 |            0.033 |
| all       |     466 |        357 |    247 |              1.445 |    0.609 |   0.281 |    0.092 |            0.017 |

A9. Players within 15 m of the pickup point at the last-leg anchor, not detected at release:

| trigger   |   players within 15 m at anchor |   not detected at release |   absent at release |   not detected by pickup |   measured |   speed m/s p10 |   speed m/s p50 |   speed m/s p90 |   max m/s |   seconds to first detection p50 |   share above 9 m/s |
|:----------|--------------------------------:|--------------------------:|--------------------:|-------------------------:|-----------:|----------------:|----------------:|----------------:|----------:|---------------------------------:|--------------------:|
| T1        |                             106 |                        49 |                   0 |                        5 |         44 |            0.71 |            2.09 |            4.11 |      6.50 |                             1.70 |                0.00 |
| T2        |                             931 |                       191 |                   0 |                       15 |        176 |            1.18 |            2.54 |            4.29 |      7.40 |                             1.40 |                0.00 |
| T3        |                             286 |                        26 |                   0 |                       10 |         16 |            0.39 |            2.19 |            3.50 |      4.36 |                             1.55 |                0.00 |
| T4        |                            1071 |                        96 |                   0 |                       27 |         69 |            0.84 |            2.88 |            5.15 |      8.09 |                             1.30 |                0.00 |
| T5        |                              50 |                         5 |                   0 |                        2 |          3 |            2.43 |            2.98 |            3.58 |      3.73 |                             1.90 |                0.00 |
| T6        |                              25 |                         8 |                   0 |                        2 |          6 |            2.66 |            4.46 |            5.90 |      6.48 |                             1.55 |                0.00 |
| T7        |                             900 |                       207 |                   0 |                       19 |        188 |            0.82 |            2.28 |            4.14 |      5.58 |                             1.15 |                0.00 |
| all       |                            3369 |                       582 |                   0 |                       80 |        502 |            0.86 |            2.41 |            4.36 |      8.09 |                             1.30 |                0.00 |

A7 to A9 reading. Facts from the tables above.

| item | finding |
|:--|:--|
| A7 first leg | the anchor is the release frame for 64.8% of main pairs; no anchor for 10.9% (T1 26.9%, T7 13.8%; aerial 15.2%, ground 7.5%). Median lead 1.7 s (p10 0.6, p90 3.9); lead < 0.5 s for 6.7% of anchored pairs |
| A7 last leg | no anchor for 1.7% (8 pairs, all T4 and all ground). Median lead 1.4 s (p10 0.3, p90 3.1); lead < 0.5 s for 15.5% of anchored pairs, highest in T4 (29.5%) and T3 (21.9%). Part of the short leads come from last contacts on the frame before pickup (A8e) |
| A7 apex | 8.1% of aerial pairs have an unobserved apex; the observed apex falls a median 2.25 s before pickup (p10 0.8, p90 3.7) |
| A8 contacts | 60.9% of main pairs have no contact, 19.3% one, 9.7% two and 10.1% three or more. 8.9% of the window frames that could hold a contact (release+1 to pickup-1) are not testable (T4 19.3%, T6 58.7%). The first contact falls a median 0.2 s after release |
| A8e edge contacts | 81 of 182 first contacts are on the first window frame, 68% of them with the releasing player within 1.5 m; 28 last contacts are on the frame before pickup, 96% with the winner within 1.5 m. As specified, the rule picks up the release touch and the pickup touch at the window edges |
| A8f runs | one touch is flagged on consecutive frames: 357 contacts form 247 runs (1.45 contacts per run). Counted as runs, 1.7% of main pairs have 3 or more |
| A8c path | median path 17.9 m against a median straight-line distance of 13.8 m; ratio median 1.05, p90 1.96 (T2 p90 2.63) |
| A9 | 582 of 3,369 players within 15 m of the pickup point at the last-leg anchor were not detected at release. 502 were measured: none above 9 m/s (median 2.41, p90 4.36, maximum 8.09 m/s; median 1.3 s to first detection). 80 were not detected by the pickup frame; none was absent at release. The implied speed is an average over the time to first detection, so it rules out large jumps, not short-lived errors within that time |

### Gates after revision 2 amended (2026-10-28)

Script: scripts/gates_anchor.py, written and run after the G4 anchor procedure was committed (b835981). G1 and G3 use the same code as the first gate run.

Gate verdicts after revision 2 amended:

| gate                | criterion                                          | value              | threshold   | result   |
|:--------------------|:---------------------------------------------------|:-------------------|:------------|:---------|
| G1                  | merged scrambles, minimum over matches             | 74 (match 2007448) | >= 50       | pass     |
| G3                  | ball detected, share of window frames (n = 466)    | 0.919              | >= 0.85     | pass     |
| G3                  | pairs with a no-camera or empty window frame       | 0.067              | <= 0.25     | pass     |
| G4 first-leg anchor | pairs with an anchor (lost to the camera: 0.109)   | 415 of 466         |             |          |
| G4 first-leg anchor | players within 15 m detected at the anchor, pooled | 0.9250             | >= 0.85     | pass     |
| G4 first-leg anchor | same, episode level (reported)                     | 0.8193             | none        |          |
| G4 first-leg anchor | players within 15 m detected at pickup, pooled     | 0.9584             | >= 0.85     | pass     |
| G4 first-leg anchor | same, episode level (reported)                     | 0.9229             | none        |          |
| G4 first-leg anchor | winner detected on the pickup frame                | 0.9904             | >= 0.90     | pass     |
| G4 first-leg anchor | verdict                                            |                    |             | pass     |
| G4 last-leg anchor  | pairs with an anchor (lost to the camera: 0.017)   | 458 of 466         |             |          |
| G4 last-leg anchor  | players within 15 m detected at the anchor, pooled | 0.9261             | >= 0.85     | pass     |
| G4 last-leg anchor  | same, episode level (reported)                     | 0.8188             | none        |          |
| G4 last-leg anchor  | players within 15 m detected at pickup, pooled     | 0.9589             | >= 0.85     | pass     |
| G4 last-leg anchor  | same, episode level (reported)                     | 0.9214             | none        |          |
| G4 last-leg anchor  | winner detected on the pickup frame                | 0.9891             | >= 0.90     | pass     |
| G4 last-leg anchor  | verdict                                            |                    |             | pass     |

G4 at the first-leg anchor by trigger class (15 m; lost share over all main pairs, the rest over pairs with an anchor):

| trigger   |   pairs |   lost to the camera |   anchor pooled |   anchor episode level |   pickup pooled |   pickup episode level |   winner |
|:----------|--------:|---------------------:|----------------:|-----------------------:|----------------:|-----------------------:|---------:|
| T1        |      26 |                0.269 |           0.802 |                  0.526 |           0.961 |                  0.895 |    1.000 |
| T2        |     135 |                0.111 |           0.915 |                  0.800 |           0.963 |                  0.925 |    0.992 |
| T3        |      32 |                0.062 |           0.938 |                  0.867 |           0.949 |                  0.933 |    1.000 |
| T4        |     137 |                0.073 |           0.952 |                  0.898 |           0.959 |                  0.929 |    0.984 |
| T5        |       8 |                0.000 |           0.939 |                  0.875 |           0.968 |                  0.875 |    1.000 |
| T6        |       5 |                0.000 |           0.920 |                  0.800 |           0.630 |                  0.400 |    0.800 |
| T7        |     123 |                0.138 |           0.906 |                  0.783 |           0.964 |                  0.943 |    1.000 |
| all       |     466 |                0.109 |           0.925 |                  0.819 |           0.958 |                  0.923 |    0.990 |

G4 at the last-leg anchor by trigger class (15 m; lost share over all main pairs, the rest over pairs with an anchor):

| trigger   |   pairs |   lost to the camera |   anchor pooled |   anchor episode level |   pickup pooled |   pickup episode level |   winner |
|:----------|--------:|---------------------:|----------------:|-----------------------:|----------------:|-----------------------:|---------:|
| T1        |      26 |                0.000 |           0.840 |                  0.615 |           0.962 |                  0.885 |    0.962 |
| T2        |     135 |                0.000 |           0.905 |                  0.807 |           0.961 |                  0.926 |    0.993 |
| T3        |      32 |                0.000 |           0.927 |                  0.812 |           0.951 |                  0.938 |    1.000 |
| T4        |     137 |                0.058 |           0.954 |                  0.891 |           0.959 |                  0.922 |    0.984 |
| T5        |       8 |                0.000 |           0.920 |                  0.875 |           0.968 |                  0.875 |    1.000 |
| T6        |       5 |                0.000 |           0.920 |                  0.800 |           0.630 |                  0.400 |    0.800 |
| T7        |     123 |                0.000 |           0.924 |                  0.797 |           0.966 |                  0.943 |    1.000 |
| all       |     466 |                0.017 |           0.926 |                  0.819 |           0.959 |                  0.921 |    0.989 |

G4 passes at either anchor: True

Gate verdicts, summary.

| gate | number | threshold | result |
|:--|:--|:--|:--|
| G1 volume | fewest merged scrambles in a match: 74 (2007448), unchanged | >= 50 per match | pass |
| G3 ball seen | 0.919 detected; 0.067 camera loss, unchanged | >= 0.85; <= 0.25 | pass |
| G4 at the first-leg anchor (415 of 466 pairs; 10.9% lost to the camera) | anchor 0.9250; pickup 0.9584; winner 0.9904. Episode level (reported): anchor 0.8193, pickup 0.9229 | >= 0.85; >= 0.85; >= 0.90 | pass |
| G4 at the last-leg anchor (458 of 466 pairs; 1.7% lost to the camera) | anchor 0.9261; pickup 0.9589; winner 0.9891. Episode level (reported): anchor 0.8188, pickup 0.9214 | >= 0.85; >= 0.85; >= 0.90 | pass |

G4 passes at both anchors, so under the rule logged before the run the revised definitions go into DESIGN.md with the choice of leg left open, and step 1 stops. Qualifications: G4 is judged on the pairs with an anchor; the winner is detected in 0.990 of those against 0.972 of all main pairs, so the pairs lost to the camera hold a larger share of undetected winners. T1 is the weakest class at both anchors (0.802 and 0.840, below 0.85 on 26 pairs). At the episode level about 82% of anchored pairs reach 85% detection within 15 m at either anchor. The first-leg anchor depends on the first contact, which is often the release touch (A8e).

### Contact figures (2026-10-28)

Script: scripts/contact_figures.py. Seed 20261028; 4 drawn from the 92 main pairs with 2 or more contacts.

|   figure |   match_id |   seq_i | trigger   |   contacts |   gap | file                                                   |
|---------:|-----------:|--------:|:----------|-----------:|------:|:-------------------------------------------------------|
|        1 |    1959846 |      18 | T2        |          4 |    46 | audit/figures/contacts_seed20261028_01_1959846_18.png  |
|        2 |    1996436 |     121 | T2        |          2 |    40 | audit/figures/contacts_seed20261028_02_1996436_121.png |
|        3 |    1886347 |     176 | T2        |          8 |    71 | audit/figures/contacts_seed20261028_03_1886347_176.png |
|        4 |    1886347 |     979 | T7        |          2 |    23 | audit/figures/contacts_seed20261028_04_1886347_979.png |

Figure reading (all 4 inspected). The rule finds real touches: figure 2 frame 26 (direction turns 37 degrees, a player 0.25 m from the ball, a visible ricochet), figure 1 frames 33 to 36 and the cluster in figure 3. It also flags the release touch on the first window frames (figure 2 frame 1, figure 3 frame 1, figure 4 frames 1 and 2, the releasing player 1.1 to 1.4 m away), so figure 4 has no contact after the release touch. One touch spreads over consecutive frames (figure 1, four frames; figure 3, pairs of frames). No implementation error was found: each flagged frame meets the rule as specified on the three strips.

### Post hoc revision 3 (2026-10-28)

Decided by the project lead after A8e, A8f and the contact figures. Post hoc. Thresholds unchanged.

Reason, as given: the contact rule flagged the release kick (81 of 182 first contacts on the first window frame) and the control touch (28 last contacts on the frame before pickup), and counted one touch on consecutive frames as several (357 contacts in 247 runs). Neither is a contact inside the window.

| element | revision 3 |
|:--|:--|
| frames tested for a contact | release + 2 to pickup - 2. The text of the revision gave release + 1 to pickup - 2; release + 1 is the frame holding the 81 release-kick contacts, so the project lead set release + 2 to pickup - 2 before the run, to match the stated reason. A frame t is still testable only when the ball is detected on t-1, t and t+1 |
| consecutive contact frames | one contact, placed at the first frame of the run |
| unchanged | horizontal velocity, more than 30 degrees or more than 3 m/s, a player within 1.5 m (detected or extrapolated), detected ball frames only, the legs, the anchor rule, the candidate set |
| re-run | legs, anchors and leads recomputed; A7 and A8 re-run, with the distribution of frames from release to the first contact added; G4 at both anchors with the same thresholds and procedure (pooled decides; episode level reported; pairs without an anchor excluded and their share reported; 10 m recheck if a run fails); DESIGN.md updated. A9 and the CSV are in the same scripts and are re-run with them |
| figures | the four episodes drawn with seed 20261028 under revision 2 are redrawn under revision 3 (set by the project lead before the run, since a fresh draw from the revised pool would give different episodes), saved beside the earlier files with the suffix _rev3 |

### A7 to A9 under revision 3 (2026-10-28)

Script: scripts/a7_a9.py, run after commit 835875d. Main pairs, n = 466. A8e is now the requested distribution of frames from release to the first contact (and from the last contact to pickup); A8f is dropped because contacts and runs coincide by construction. A2 to A6 tables reproduced unchanged; the CSV carries the revision 3 contact, leg and anchor columns.

A7a (first leg). Anchors and leads by trigger class:

| trigger   |   pairs |   anchor at leg start |   no anchor |   lead s p10 |   lead s p50 |   lead s p90 |   lead < 0.5 s (of anchored) |
|:----------|--------:|----------------------:|------------:|-------------:|-------------:|-------------:|-----------------------------:|
| T1        |      26 |                 0.192 |       0.000 |        0.350 |        1.400 |        2.650 |                        0.154 |
| T2        |     135 |                 0.622 |       0.067 |        1.050 |        2.850 |        4.600 |                        0.016 |
| T3        |      32 |                 0.844 |       0.031 |        0.700 |        1.500 |        3.100 |                        0.097 |
| T4        |     137 |                 0.810 |       0.066 |        0.400 |        1.100 |        2.060 |                        0.148 |
| T5        |       8 |                 0.375 |       0.000 |        0.790 |        1.350 |        2.630 |                        0.125 |
| T6        |       5 |                 0.600 |       0.000 |        0.540 |        0.900 |        3.220 |                        0.000 |
| T7        |     123 |                 0.561 |       0.065 |        0.900 |        2.000 |        3.900 |                        0.017 |
| all       |     466 |                 0.648 |       0.058 |        0.600 |        1.700 |        3.900 |                        0.071 |

A7b (first leg). Anchors and leads, aerial or ground:

| flight   |   pairs |   anchor at leg start |   no anchor |   lead s p10 |   lead s p50 |   lead s p90 |   lead < 0.5 s (of anchored) |
|:---------|--------:|----------------------:|------------:|-------------:|-------------:|-------------:|-----------------------------:|
| aerial   |     211 |                 0.526 |       0.066 |        1.100 |        2.600 |        4.500 |                        0.025 |
| ground   |     255 |                 0.749 |       0.051 |        0.400 |        1.300 |        2.400 |                        0.107 |
| all      |     466 |                 0.648 |       0.058 |        0.600 |        1.700 |        3.900 |                        0.071 |

A7a (last leg). Anchors and leads by trigger class:

| trigger   |   pairs |   anchor at leg start |   no anchor |   lead s p10 |   lead s p50 |   lead s p90 |   lead < 0.5 s (of anchored) |
|:----------|--------:|----------------------:|------------:|-------------:|-------------:|-------------:|-----------------------------:|
| T1        |      26 |                 0.231 |       0.000 |        0.350 |        1.250 |        2.350 |                        0.154 |
| T2        |     135 |                 0.652 |       0.000 |        0.800 |        1.800 |        3.860 |                        0.044 |
| T3        |      32 |                 0.844 |       0.000 |        0.430 |        1.350 |        3.090 |                        0.125 |
| T4        |     137 |                 0.818 |       0.058 |        0.400 |        1.000 |        1.820 |                        0.178 |
| T5        |       8 |                 0.375 |       0.000 |        0.790 |        1.250 |        2.460 |                        0.125 |
| T6        |       5 |                 0.600 |       0.000 |        0.540 |        0.900 |        3.220 |                        0.000 |
| T7        |     123 |                 0.642 |       0.000 |        0.620 |        1.600 |        2.680 |                        0.073 |
| all       |     466 |                 0.682 |       0.017 |        0.400 |        1.400 |        3.100 |                        0.103 |

A7b (last leg). Anchors and leads, aerial or ground:

| flight   |   pairs |   anchor at leg start |   no anchor |   lead s p10 |   lead s p50 |   lead s p90 |   lead < 0.5 s (of anchored) |
|:---------|--------:|----------------------:|------------:|-------------:|-------------:|-------------:|-----------------------------:|
| aerial   |     211 |                 0.592 |       0.000 |        0.700 |        1.600 |        3.600 |                        0.066 |
| ground   |     255 |                 0.757 |       0.031 |        0.400 |        1.200 |        2.400 |                        0.134 |
| all      |     466 |                 0.682 |       0.017 |        0.400 |        1.400 |        3.100 |                        0.103 |

A7c. Aerial pairs: apex (largest detected ball_data.z) relative to pickup:

| trigger   |   aerial pairs |   apex unobserved |   apex before pickup s p10 |   apex before pickup s p50 |   apex before pickup s p90 |
|:----------|---------------:|------------------:|---------------------------:|---------------------------:|---------------------------:|
| T1        |             21 |             0.095 |                      1.100 |                      2.100 |                      4.140 |
| T2        |             96 |             0.115 |                      0.800 |                      2.400 |                      3.860 |
| T3        |             10 |             0.200 |                      0.500 |                      1.200 |                      3.150 |
| T4        |             10 |             0.000 |                      0.600 |                      1.050 |                      1.870 |
| T5        |              6 |             0.000 |                      0.850 |                      1.500 |                      2.550 |
| T7        |             68 |             0.029 |                      0.750 |                      2.350 |                      3.400 |
| all       |            211 |             0.081 |                      0.800 |                      2.250 |                      3.700 |

A8a. Contacts per pair by trigger class, and the share of frames from release+2 to pickup-2 that cannot be tested:

| trigger   |   pairs |   0 contacts |     1 |     2 |   3 or more |   untestable share of the contact frames |
|:----------|--------:|-------------:|------:|------:|------------:|-----------------------------------------:|
| T1        |      26 |        0.923 | 0.000 | 0.038 |       0.038 |                                    0.143 |
| T2        |     135 |        0.659 | 0.267 | 0.059 |       0.015 |                                    0.086 |
| T3        |      32 |        0.844 | 0.125 | 0.031 |       0.000 |                                    0.034 |
| T4        |     137 |        0.898 | 0.080 | 0.015 |       0.007 |                                    0.210 |
| T5        |       8 |        0.875 | 0.125 | 0.000 |       0.000 |                                    0.000 |
| T6        |       5 |        1.000 | 0.000 | 0.000 |       0.000 |                                    0.606 |
| T7        |     123 |        0.610 | 0.293 | 0.073 |       0.024 |                                    0.033 |
| all       |     466 |        0.751 | 0.189 | 0.045 |       0.015 |                                    0.093 |

A8b. Release to first contact (pairs with a contact) and duration of the last leg (all pairs), seconds:

| trigger   |   pairs |   with a contact |   to first contact p10 |   to first contact p50 |   to first contact p90 |   last leg p10 |   last leg p50 |   last leg p90 |
|:----------|--------:|-----------------:|-----------------------:|-----------------------:|-----------------------:|---------------:|---------------:|---------------:|
| T1        |      26 |                2 |                   2.90 |                   4.50 |                   6.10 |           1.80 |           2.65 |           4.50 |
| T2        |     135 |               46 |                   0.20 |                   1.55 |                   3.60 |           1.20 |           2.50 |           5.10 |
| T3        |      32 |                5 |                   0.24 |                   0.30 |                   1.12 |           0.43 |           1.60 |           3.50 |
| T4        |     137 |               14 |                   0.20 |                   0.50 |                   1.37 |           0.40 |           1.10 |           2.52 |
| T5        |       8 |                1 |                   1.60 |                   1.60 |                   1.60 |           1.31 |           2.35 |           3.72 |
| T6        |       5 |                0 |                 nan    |                 nan    |                 nan    |           1.10 |           2.60 |           3.22 |
| T7        |     123 |               48 |                   0.20 |                   1.50 |                   2.90 |           0.90 |           1.80 |           4.20 |
| all       |     466 |              116 |                   0.20 |                   1.30 |                   3.35 |           0.60 |           1.80 |           4.35 |

A8c. Ball path length next to the straight-line distance of A6, metres:

| trigger   |   pairs |   path p50 |   straight p50 |   path / straight p10 |   path / straight p50 |   path / straight p90 |   pairs with a skipped step |
|:----------|--------:|-----------:|---------------:|----------------------:|----------------------:|----------------------:|----------------------------:|
| T1        |      26 |      29.68 |          28.01 |                  1.01 |                  1.01 |                  1.07 |                           0 |
| T2        |     135 |      30.93 |          20.22 |                  1.01 |                  1.21 |                  2.63 |                           0 |
| T3        |      32 |      12.56 |           9.71 |                  1.00 |                  1.04 |                  1.84 |                           0 |
| T4        |     137 |       5.12 |           5.10 |                  1.00 |                  1.02 |                  1.15 |                           1 |
| T5        |       8 |      19.12 |          17.78 |                  1.01 |                  1.01 |                  1.75 |                           0 |
| T6        |       5 |      20.69 |          19.64 |                  1.01 |                  1.02 |                  1.04 |                           0 |
| T7        |     123 |      23.14 |          19.35 |                  1.00 |                  1.08 |                  1.97 |                           0 |
| all       |     466 |      17.93 |          13.75 |                  1.00 |                  1.05 |                  1.96 |                           1 |

A8d. Legs per pair:

|   legs (4 = 4 or more) |   pairs |
|-----------------------:|--------:|
|                      1 |     350 |
|                      2 |      88 |
|                      3 |      21 |
|                      4 |       7 |

A8e. Frames from release to the first contact, and from the last contact to pickup (pairs with a contact), with the share of contacts that have the releasing player or the winner within 1.5 m:

| contact       | frames from the window edge   |   contacts |   share of these contacts | player checked   |   share with that player within 1.5 m |
|:--------------|:------------------------------|-----------:|--------------------------:|:-----------------|--------------------------------------:|
| first contact | 2 after release               |         27 |                     0.233 | releasing player |                                 0.333 |
| first contact | 3 after release               |          2 |                     0.017 | releasing player |                                 0.000 |
| first contact | 4-5 after release             |          6 |                     0.052 | releasing player |                                 0.333 |
| first contact | 6-10 after release            |         13 |                     0.112 | releasing player |                                 0.000 |
| first contact | 11-20 after release           |         30 |                     0.259 | releasing player |                                 0.100 |
| first contact | 21 or more after release      |         38 |                     0.328 | releasing player |                                 0.000 |
| last contact  | 2 before pickup               |         11 |                     0.095 | winner           |                                 0.545 |
| last contact  | 3 before pickup               |          2 |                     0.017 | winner           |                                 0.000 |
| last contact  | 4-5 before pickup             |          3 |                     0.026 | winner           |                                 0.333 |
| last contact  | 6-10 before pickup            |         14 |                     0.121 | winner           |                                 0.000 |
| last contact  | 11-20 before pickup           |         53 |                     0.457 | winner           |                                 0.038 |
| last contact  | 21 or more before pickup      |         33 |                     0.284 | winner           |                                 0.030 |

A9. Players within 15 m of the pickup point at the last-leg anchor, not detected at release:

| trigger   |   players within 15 m at anchor |   not detected at release |   absent at release |   not detected by pickup |   measured |   speed m/s p10 |   speed m/s p50 |   speed m/s p90 |   max m/s |   seconds to first detection p50 |   share above 9 m/s |
|:----------|--------------------------------:|--------------------------:|--------------------:|-------------------------:|-----------:|----------------:|----------------:|----------------:|----------:|---------------------------------:|--------------------:|
| T1        |                             105 |                        49 |                   0 |                        5 |         44 |            0.71 |            2.09 |            4.11 |      6.50 |                             1.70 |                0.00 |
| T2        |                             923 |                       190 |                   0 |                       15 |        175 |            1.18 |            2.53 |            4.29 |      7.40 |                             1.40 |                0.00 |
| T3        |                             277 |                        23 |                   0 |                        9 |         14 |            0.38 |            2.14 |            3.23 |      4.36 |                             1.65 |                0.00 |
| T4        |                            1065 |                        99 |                   0 |                       28 |         71 |            0.83 |            2.73 |            5.13 |      8.09 |                             1.30 |                0.00 |
| T5        |                              50 |                         5 |                   0 |                        2 |          3 |            2.43 |            2.98 |            3.58 |      3.73 |                             1.90 |                0.00 |
| T6        |                              25 |                         8 |                   0 |                        2 |          6 |            2.66 |            4.46 |            5.90 |      6.48 |                             1.55 |                0.00 |
| T7        |                             899 |                       207 |                   0 |                       19 |        188 |            0.82 |            2.28 |            4.14 |      5.58 |                             1.15 |                0.00 |
| all       |                            3344 |                       581 |                   0 |                       80 |        501 |            0.85 |            2.40 |            4.36 |      8.09 |                             1.30 |                0.00 |

### Gates at the anchors under revision 3 (2026-10-28)

Script: scripts/gates_anchor.py, same thresholds and procedure as logged before the revision 2 run.

Gate verdicts at the anchors, contact rule of revision 3:

| gate                | criterion                                          | value              | threshold   | result   |
|:--------------------|:---------------------------------------------------|:-------------------|:------------|:---------|
| G1                  | merged scrambles, minimum over matches             | 74 (match 2007448) | >= 50       | pass     |
| G3                  | ball detected, share of window frames (n = 466)    | 0.919              | >= 0.85     | pass     |
| G3                  | pairs with a no-camera or empty window frame       | 0.067              | <= 0.25     | pass     |
| G4 first-leg anchor | pairs with an anchor (lost to the camera: 0.058)   | 439 of 466         |             |          |
| G4 first-leg anchor | players within 15 m detected at the anchor, pooled | 0.9208             | >= 0.85     | pass     |
| G4 first-leg anchor | same, episode level (reported)                     | 0.8018             | none        |          |
| G4 first-leg anchor | players within 15 m detected at pickup, pooled     | 0.9584             | >= 0.85     | pass     |
| G4 first-leg anchor | same, episode level (reported)                     | 0.9203             | none        |          |
| G4 first-leg anchor | winner detected on the pickup frame                | 0.9886             | >= 0.90     | pass     |
| G4 first-leg anchor | verdict                                            |                    |             | pass     |
| G4 last-leg anchor  | pairs with an anchor (lost to the camera: 0.017)   | 458 of 466         |             |          |
| G4 last-leg anchor  | players within 15 m detected at the anchor, pooled | 0.9237             | >= 0.85     | pass     |
| G4 last-leg anchor  | same, episode level (reported)                     | 0.8122             | none        |          |
| G4 last-leg anchor  | players within 15 m detected at pickup, pooled     | 0.9589             | >= 0.85     | pass     |
| G4 last-leg anchor  | same, episode level (reported)                     | 0.9214             | none        |          |
| G4 last-leg anchor  | winner detected on the pickup frame                | 0.9891             | >= 0.90     | pass     |
| G4 last-leg anchor  | verdict                                            |                    |             | pass     |

G4 at the first-leg anchor by trigger class (15 m; lost share over all main pairs, the rest over pairs with an anchor):

| trigger   |   pairs |   lost to the camera |   anchor pooled |   anchor episode level |   pickup pooled |   pickup episode level |   winner |
|:----------|--------:|---------------------:|----------------:|-----------------------:|----------------:|-----------------------:|---------:|
| T1        |      26 |                0.000 |           0.808 |                  0.577 |           0.962 |                  0.885 |    0.962 |
| T2        |     135 |                0.067 |           0.906 |                  0.778 |           0.962 |                  0.929 |    0.992 |
| T3        |      32 |                0.031 |           0.933 |                  0.839 |           0.950 |                  0.935 |    1.000 |
| T4        |     137 |                0.066 |           0.951 |                  0.891 |           0.959 |                  0.922 |    0.984 |
| T5        |       8 |                0.000 |           0.939 |                  0.875 |           0.968 |                  0.875 |    1.000 |
| T6        |       5 |                0.000 |           0.920 |                  0.800 |           0.630 |                  0.400 |    0.800 |
| T7        |     123 |                0.065 |           0.906 |                  0.765 |           0.965 |                  0.939 |    1.000 |
| all       |     466 |                0.058 |           0.921 |                  0.802 |           0.958 |                  0.920 |    0.989 |

G4 at the last-leg anchor by trigger class (15 m; lost share over all main pairs, the rest over pairs with an anchor):

| trigger   |   pairs |   lost to the camera |   anchor pooled |   anchor episode level |   pickup pooled |   pickup episode level |   winner |
|:----------|--------:|---------------------:|----------------:|-----------------------:|----------------:|-----------------------:|---------:|
| T1        |      26 |                0.000 |           0.829 |                  0.577 |           0.962 |                  0.885 |    0.962 |
| T2        |     135 |                0.000 |           0.905 |                  0.807 |           0.961 |                  0.926 |    0.993 |
| T3        |      32 |                0.000 |           0.928 |                  0.812 |           0.951 |                  0.938 |    1.000 |
| T4        |     137 |                0.058 |           0.950 |                  0.884 |           0.959 |                  0.922 |    0.984 |
| T5        |       8 |                0.000 |           0.920 |                  0.875 |           0.968 |                  0.875 |    1.000 |
| T6        |       5 |                0.000 |           0.920 |                  0.800 |           0.630 |                  0.400 |    0.800 |
| T7        |     123 |                0.000 |           0.922 |                  0.789 |           0.966 |                  0.943 |    1.000 |
| all       |     466 |                0.017 |           0.924 |                  0.812 |           0.959 |                  0.921 |    0.989 |

G4 passes at either anchor: True

| gate | number | threshold | result |
|:--|:--|:--|:--|
| G4 at the first-leg anchor (439 of 466 pairs; 5.8% lost to the camera) | anchor 0.9208; pickup 0.9584; winner 0.9886. Episode level (reported): anchor 0.8018, pickup 0.9203 | >= 0.85; >= 0.85; >= 0.90 | pass |
| G4 at the last-leg anchor (458 of 466 pairs; 1.7% lost to the camera) | anchor 0.9237; pickup 0.9589; winner 0.9891. Episode level (reported): anchor 0.8122, pickup 0.9214 | >= 0.85; >= 0.85; >= 0.90 | pass |

G1 (74) and G3 (0.919; 0.067) are unchanged. G4 passes at both anchors; DESIGN.md is updated with the revision 3 contact rule and the choice of leg still open.

### Revision 2 against revision 3 (2026-10-28)

| quantity | revision 2 | revision 3 |
|:--|--:|--:|
| main pairs with a contact | 182 | 116 |
| share with 0 / 1 / 2 / 3 or more contacts | 0.609 / 0.193 / 0.097 / 0.101 | 0.751 / 0.189 / 0.045 / 0.015 |
| release to first contact, median | 0.2 s | 1.3 s |
| first contacts on the first tested frame | 81 at release+1, 68% with the releasing player within 1.5 m | 27 at release+2, 33% (9) with the releasing player within 1.5 m |
| last contacts on the last tested frame | 28 at pickup-1, 96% with the winner within 1.5 m | 11 at pickup-2, 55% (6) with the winner within 1.5 m |
| untestable share of the contact frames | 0.089 | 0.093 |
| first leg: no anchor; lead median; lead < 0.5 s | 0.109; 1.7 s; 0.067 | 0.058; 1.7 s; 0.071 |
| last leg: no anchor; lead median; lead < 0.5 s | 0.017; 1.4 s; 0.155 | 0.017; 1.4 s; 0.103 |
| G4 pooled at the anchor, first leg / last leg | 0.9250 / 0.9261 | 0.9208 / 0.9237 |
| G4 episode level at the anchor, first leg / last leg | 0.8193 / 0.8188 | 0.8018 / 0.8122 |

Reading. Revision 3 removes the edge contacts at release+1 and pickup-1 and the duplicate frames: the first contact moves from a median 0.2 s to 1.3 s after release, and pairs with 3 or more contacts fall from 10.1% to 1.5%. A smaller edge effect remains one frame further in: 9 first contacts at release+2 have the releasing player within 1.5 m (contact figure 4: speed change 4.0 m/s, releaser 1.4 m away), and 6 last contacts at pickup-2 have the winner within 1.5 m. Pairs without a first-leg anchor fall from 10.9% to 5.8%, because fewer first legs are cut to one frame. G4 changes by less than 0.005 at either anchor and passes at both.

### Contact figures under revision 3 (2026-10-28)

Script: scripts/contact_figures.py. The four episodes drawn with seed 20261028 under revision 2, redrawn; the earlier files are kept for comparison.

|   figure |   match_id |   seq_i | trigger   |   contacts |   gap | file                                                        |
|---------:|-----------:|--------:|:----------|-----------:|------:|:------------------------------------------------------------|
|        1 |    1959846 |      18 | T2        |          1 |    46 | audit/figures/contacts_seed20261028_01_1959846_18_rev3.png  |
|        2 |    1996436 |     121 | T2        |          1 |    40 | audit/figures/contacts_seed20261028_02_1996436_121_rev3.png |
|        3 |    1886347 |     176 | T2        |          4 |    71 | audit/figures/contacts_seed20261028_03_1886347_176_rev3.png |
|        4 |    1886347 |     979 | T7        |          1 |    23 | audit/figures/contacts_seed20261028_04_1886347_979_rev3.png |

| figure | revision 2 contacts (frames after release) | revision 3 contacts | reading |
|:--|:--|:--|:--|
| 1 | 33, 34, 35, 36 | 33 | one touch, now one contact; lead at the last-leg anchor 1.3 s (was 1.0 s) |
| 2 | 1, 26 | 26 | release kick removed; the ricochet at 26 (37 degrees, player 0.25 m away) stays |
| 3 | 1, 43, 44, 47, 48, 51, 52, 54 | 43, 47, 51, 54 | release kick removed; frame pairs merged into four touches in the scramble |
| 4 | 1, 2 | 2 | the release kick still registers at release+2 (speed change 4.0 m/s, releaser 1.4 m away) |

## Step 2, the measures (exploration part)

Brief: docs/step2_brief.md. Exploration matches only; the MT1 marker is not logged in this step.

### Step 2 setup: DataBallPy and environment (2026-10-28)

| item | value |
|:--|:--|
| DataBallPy source | https://github.com/Alek050/databallpy, develop branch |
| pinned commit | 3f9de8d28531aa12d826ee99aed8de7aeee0897f (develop head on 2026-10-28; contains PR #408, merge dd67888fabc9b90ad91a18a61c6dd08f87fed06a of 2026-10-23, and pandas 3 support, PR #407) |
| recorded in | pyproject.toml ([tool.uv.sources] databallpy rev) and uv.lock |
| package version reported | 0.8.1 |
| API used | databallpy.optimization.constraints.TTIConstraint.tti(origin, destination, velocity), turning_penalty "shaw" (default) or "pleuler"; defaults reaction_time 0.7 s, max_velocity 5.0 m/s; no acceleration parameter |
| test | tests/test_databallpy_tti.py: for a player at (0, 0) moving at (5, 0) m/s and a target at (0, 10), shaw 2.819 s and pleuler 5.319 s; standing player 10 m away 2.700 s; unknown penalty refused. 3 passed |

Environment change. DataBallPy caps numpy below 2.3 and pyarrow below 23 on Python 3.12, so installing it moved:

| package | before | after |
|:--|:--|:--|
| numpy | 2.5.4 | 2.2.6 |
| pyarrow | 26.0.0 | 22.0.0 |
| pandas | 3.1.0 | 3.1.0 |
| scipy | not installed | 1.18.1 (now a direct dependency) |

Step 1 reproduction on the new environment: every step 1 script was re-run and its output compared with the output produced before the change.

| script | result |
|:--|:--|
| setup_check.py | identical to the setup table |
| a2_a6.py (and audit/loose_episodes_exploration.csv) | identical; CSV byte-identical |
| a7_a9.py (revision 3) | identical |
| gates.py (first G4 run) | identical |
| gates_anchor.py (revision 3) | identical |
| g4_diagnostic.py | identical |
| seeded episode draw (seed 20261027) | same 11 episodes |

Decisions taken by the project lead before any step 2 code, after the API and the brief were checked:

| # | question | decision |
|:--|:--|:--|
| 1 | install | pin develop head 3f9de8d and accept the numpy and pyarrow downgrade; step 1 re-verified (above) |
| 2 | calling the constraint (its constructor needs a databallpy Game and a frame; there is no standalone function) | a thin subclass whose constructor only sets reaction_time, max_velocity and turning_penalty, calling the package's tti unchanged; tested against the package class |
| 3 | D3 parameters (the brief's "speed and acceleration"; the model has reaction time and top speed) | package defaults, reaction_time 0.7 s and max_velocity 5.0 m/s, for all players |
| 4 | best time of a team with nobody in the race (brief: radius / top speed = 3.0 s) | reaction_time + radius / max_velocity = 3.7 s at 15 m, the time of a standing player on the radius |
| 5 | D5 forms (a two-team softmax with one temperature equals a logistic on the time difference without intercept) | logistic: sigmoid(a + b x (t_other - t_releasing)), oriented to the releasing team; softmax: the intercept-free one-parameter case, temperature T = 1 / b. B0 and B1 take the same orientation with an intercept |
| 6 | outcome use in S2, S4 and D7 (the brief's rule allows it only in S3 and S5) | read there as the brief specifies, for checks and the gate definition only; nothing is fitted or chosen on it outside S3 |
| 7 | episodes in S3's fit and the S5 dry run | the analysis set: main pairs with a last-leg anchor, kept by D7, not immediate (lead >= 0.5 s) |
| 8 | unit of the race | raw main pairs; the winner is the team of possession i+1 |

### Step 2 modules (2026-10-28)

Built in the order of the step 2 brief, each with unit tests on synthetic data before any match data was used. Full suite: 31 passed.

| module | content | tests |
|:--|:--|:--|
| velocities | Savitzky-Golay first derivative of x and y per track; window and order as arguments (5 and 2 by default) | 5: exact for linear and quadratic tracks, tracks split at gaps, short tracks, window 7, noise reduction |
| race | ReachModel (thin DataBallPy subclass), players within the radius at the anchor, static and dynamic reach times, team best times, flags; episode driver with radius, growing-radius speed, turning penalty, smoothing window, anchor shift and extrapolated-player drop as arguments | 5: equality with the package class for 50 random players under both penalties, ordering of static and moving reach times, radius and sides, flags, empty team |
| expectation | features dt, dn, dd; softmax, logistic, B0, B1; maximum-likelihood fit; leave-one-match-out; log-loss; calibration table | 6: parameter recovery, softmax identity, reference log-loss, held-out match never seen, orientation, shapes |
| decompose | deficit and credit shares, verdict, immediate class, team shares with bootstrap intervals | 4: definitions and sums, verdict boundaries, orientation to the loser, team means and intervals |
| gate | D7 keep rule, drop rates, releasing team's win-share difference with bootstrap interval | 3: boundaries, drop rates, interval |
| export_clips | match id, period, clock, frame, team, verdict | 1: columns, order, clock lookup |

Implementation choices inside the modules, set before any match data was used:

| item | choice |
|:--|:--|
| velocity at a track end | scipy savgol_filter mode "interp" (the polynomial fitted to the first or last window); a track is a run of consecutive frames of one player |
| track shorter than the window | no velocity; in the race the player gets velocity zero and the flag velocity_missing |
| goalkeeper flag | roster field player_role.acronym equal to "GK" |
| sides | named from the releasing team (team of possession i); every probability is the releasing team's |
| nearest distance of an empty team (B1) | the radius, consistent with the empty-team best time |
| D7 with nobody within the radius | counts as fully observed on the 85% condition, as in step 1's episode-level G4 |
| bootstrap intervals (D7 difference, team shares) | 2.5 and 97.5 percentiles, episodes resampled with replacement within each match, 2000 replicates |
| calibration table (S3) | five equal-width bins of predicted probability, on the leave-one-match-out predictions of the chosen form |
| clip export | frame: the measured anchor frame; team: the team that lost; clock: the tracking field timestamp of that frame |
| credit and deficit | an episode's credit for the winner equals its deficit for the loser (the two teams' probabilities sum to 1); team views differ only in which episodes enter |
