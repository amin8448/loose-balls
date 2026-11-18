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

### S1 and S2 procedure, logged before the run (2026-10-28)

| item | rule |
|:--|:--|
| S1 speed check | smoothed speed (window 5, order 2) on every player-frame of the five matches with is_detected TRUE and a velocity; criterion: share above 10 m/s at most 1% |
| S1 anchor velocities | players in the race (15 m) on the last-leg anchor frame of the anchored main pairs; share with is_detected FALSE (velocity from an extrapolated track) and share without a velocity |
| S2 winner reach time | the winning player (player of possession i+1), from his position and smoothed velocity on the last-leg anchor frame to the pickup point, shaw, reaction 0.7 s, top speed 5.0 m/s, wherever he is on the pitch; compared with the lead of that anchor |
| S2 criterion | share with winner reach time <= lead + 0.3 s; at least 70% expected |
| S2 sets | headline: the analysis set (anchored, kept by D7 at 15 m, lead >= 0.5 s). Beside it: all anchored main pairs, and anchored pairs with lead >= 0.5 s. Pooled and by trigger |

### S1 and S2 (2026-10-28)

Script: scripts/s1_s2.py, run after the procedure above was logged. Race at 15 m, shaw, reaction 0.7 s, top speed 5.0 m/s, smoothing window 5.

| set | episodes |
|:--|--:|
| anchored main pairs (last-leg anchor) | 458 |
| kept by D7 at 15 m | 367 |
| immediate (lead < 0.5 s) | 47 |
| analysis set (kept, not immediate) | 326 |

S1a. Smoothed speed (window 5, order 2) on detected player-frames, all frames of each match:

| match   |   detected player-frames |   with a velocity |   p50 m/s |   p99 m/s |   p99.9 m/s |   max m/s |   frames > 10 m/s |   share > 10 m/s |
|:--------|-------------------------:|------------------:|----------:|----------:|------------:|----------:|------------------:|-----------------:|
| 1886347 |                   566778 |            566778 |   2.13216 |   6.71658 |     8.08621 |  13.74006 |                26 |          0.00005 |
| 1959846 |                   536373 |            536373 |   1.95489 |   6.94370 |     8.45575 |  13.76258 |                25 |          0.00005 |
| 1996436 |                   524840 |            524840 |   1.82877 |   6.65433 |     8.15045 |  14.56665 |                43 |          0.00008 |
| 1996435 |                   630145 |            630145 |   1.98980 |   6.74562 |     8.18707 |  29.78472 |                 8 |          0.00001 |
| 2007448 |                   525931 |            525931 |   1.98305 |   6.65192 |     8.08151 |  16.91362 |                45 |          0.00009 |
| all     |                  2784067 |           2784067 |   1.97891 |   6.74999 |     8.20000 |  29.78472 |               147 |          0.00005 |

S1b. Players in the race (15 m) on the last-leg anchor frame, anchored main pairs:

| trigger   |   players |   share extrapolated (is_detected FALSE) |   share without a velocity |   share goalkeepers |
|:----------|----------:|-----------------------------------------:|---------------------------:|--------------------:|
| T1        |       105 |                                    0.171 |                      0.000 |               0.010 |
| T2        |       923 |                                    0.095 |                      0.000 |               0.028 |
| T3        |       277 |                                    0.072 |                      0.000 |               0.058 |
| T4        |      1065 |                                    0.050 |                      0.000 |               0.009 |
| T5        |        50 |                                    0.080 |                      0.000 |               0.020 |
| T6        |        25 |                                    0.080 |                      0.000 |               0.000 |
| T7        |       899 |                                    0.078 |                      0.000 |               0.024 |
| all       |      3344 |                                    0.076 |                      0.000 |               0.023 |

S2a. Analysis set (anchored, kept by D7, lead >= 0.5 s), headline:

| trigger   |   episodes |   winner not on anchor frame |   share reach <= lead + 0.3 s |   winner distance p50 m |   reach minus lead p10 s |   reach minus lead p50 s |   reach minus lead p90 s |
|:----------|-----------:|-----------------------------:|------------------------------:|------------------------:|-------------------------:|-------------------------:|-------------------------:|
| T1        |         11 |                            0 |                         0.636 |                   4.663 |                   -1.042 |                   -0.072 |                    1.070 |
| T2        |        104 |                            0 |                         0.760 |                   5.414 |                   -1.741 |                   -0.158 |                    0.578 |
| T3        |         22 |                            0 |                         0.682 |                   4.454 |                   -1.856 |                    0.143 |                    0.611 |
| T4        |         90 |                            0 |                         0.667 |                   4.147 |                   -0.291 |                    0.150 |                    0.438 |
| T5        |          7 |                            0 |                         0.571 |                   7.443 |                   -0.169 |                    0.215 |                    0.492 |
| T6        |          3 |                            0 |                         0.333 |                   7.121 |                    0.216 |                    0.430 |                    0.467 |
| T7        |         89 |                            0 |                         0.708 |                   5.898 |                   -0.848 |                    0.025 |                    0.588 |
| all       |        326 |                            0 |                         0.702 |                   5.082 |                   -1.149 |                    0.045 |                    0.585 |

S2b. All anchored main pairs:

| trigger   |   episodes |   winner not on anchor frame |   share reach <= lead + 0.3 s |   winner distance p50 m |   reach minus lead p10 s |   reach minus lead p50 s |   reach minus lead p90 s |
|:----------|-----------:|-----------------------------:|------------------------------:|------------------------:|-------------------------:|-------------------------:|-------------------------:|
| T1        |         26 |                            0 |                         0.462 |                   2.861 |                   -0.594 |                    0.350 |                    0.915 |
| T2        |        135 |                            0 |                         0.711 |                   5.539 |                   -1.685 |                   -0.082 |                    0.657 |
| T3        |         32 |                            0 |                         0.594 |                   4.179 |                   -1.143 |                    0.192 |                    0.657 |
| T4        |        129 |                            0 |                         0.566 |                   3.457 |                   -0.304 |                    0.219 |                    0.644 |
| T5        |          8 |                            0 |                         0.500 |                   7.371 |                   -0.168 |                    0.295 |                    0.678 |
| T6        |          5 |                            0 |                         0.400 |                   3.220 |                   -1.281 |                    0.321 |                    0.457 |
| T7        |        123 |                            0 |                         0.675 |                   5.523 |                   -0.872 |                    0.041 |                    0.709 |
| all       |        458 |                            0 |                         0.631 |                   4.674 |                   -1.086 |                    0.111 |                    0.689 |

S2c. Anchored main pairs with lead >= 0.5 s:

| trigger   |   episodes |   winner not on anchor frame |   share reach <= lead + 0.3 s |   winner distance p50 m |   reach minus lead p10 s |   reach minus lead p50 s |   reach minus lead p90 s |
|:----------|-----------:|-----------------------------:|------------------------------:|------------------------:|-------------------------:|-------------------------:|-------------------------:|
| T1        |         22 |                            0 |                         0.545 |                   3.177 |                   -0.596 |                    0.215 |                    1.039 |
| T2        |        129 |                            0 |                         0.744 |                   5.785 |                   -1.713 |                   -0.111 |                    0.600 |
| T3        |         28 |                            0 |                         0.679 |                   5.284 |                   -1.382 |                    0.143 |                    0.624 |
| T4        |        106 |                            0 |                         0.689 |                   4.296 |                   -0.374 |                    0.141 |                    0.424 |
| T5        |          7 |                            0 |                         0.571 |                   7.443 |                   -0.169 |                    0.215 |                    0.492 |
| T6        |          5 |                            0 |                         0.400 |                   3.220 |                   -1.281 |                    0.321 |                    0.457 |
| T7        |        114 |                            0 |                         0.728 |                   5.838 |                   -0.892 |                    0.020 |                    0.599 |
| all       |        411 |                            0 |                         0.703 |                   5.152 |                   -1.119 |                    0.052 |                    0.585 |

| check | number | criterion | result |
|:--|:--|:--|:--|
| S1 speed | 147 of 2,784,067 detected player-frames above 10 m/s (0.005%); p99.9 8.20 m/s | at most 1% | pass |
| S1 anchor velocities | 7.6% of the 3,344 players in the race at the anchor are extrapolated (T1 17.1%, T2 9.5%); none lacks a velocity; 2.3% are goalkeepers | report | reported |
| S2 headline (analysis set) | 0.702 of 326 episodes have winner reach time <= lead + 0.3 s | at least 70% | pass by 0.2 points |
| S2, all anchored main pairs | 0.631 of 458 | report | below 70% |
| S2, lead >= 0.5 s | 0.703 of 411 | report | at 70% |

Reading. S1 gives no sign of a smoothing or alignment fault. S2 passes on the set logged as the headline, by 0.2 points; by trigger, T2 (0.760) and T7 (0.708) are above 70% and T4 (0.667, 90 episodes), T3 (0.682), T1 (0.636) and the small T5 and T6 classes are below. The winner's reach time minus the lead has median +0.05 s (p10 -1.15 s, p90 +0.59 s), so with the package defaults the model's timing is centred on the observed leads with a long early tail. Including the 47 immediate episodes lowers the share to 0.631: with a reaction time of 0.7 s no winner can meet lead + 0.3 s when the lead is under 0.4 s. The winner was on the anchor frame in every episode.

### S2 finding, recorded by the project lead (2026-10-28)

S2 passes as logged (0.702 on the analysis set). Recorded as a finding, not a change; no parameter changes. As given: the margin is thin because the reach model's fixed 0.7 s reaction time cannot be met at short leads, and T1 and T4 fall below 0.70 for that reason.

Supporting tables (scripts/s1_s2.py, S2d and S2e, added after the finding; S1 and S2a to S2c unchanged):

S2d. Analysis set: share with reach <= lead + 0.3 s by lead band, for T1, T4 and the other triggers:

| group          | lead band s   |   episodes |   share |
|:---------------|:--------------|-----------:|--------:|
| T1             | 0.5 to 1.0    |          2 |   0.500 |
| T1             | 1.0 to 1.5    |          1 |   0.000 |
| T1             | 1.5 to 2.0    |          3 |   1.000 |
| T1             | 2.0 or more   |          5 |   0.600 |
| T4             | 0.5 to 1.0    |         32 |   0.562 |
| T4             | 1.0 to 1.5    |         29 |   0.759 |
| T4             | 1.5 to 2.0    |         20 |   0.700 |
| T4             | 2.0 or more   |          9 |   0.667 |
| other triggers | 0.5 to 1.0    |         33 |   0.515 |
| other triggers | 1.0 to 1.5    |         52 |   0.712 |
| other triggers | 1.5 to 2.0    |         52 |   0.731 |
| other triggers | 2.0 or more   |         88 |   0.795 |

S2e. Analysis set: median lead by trigger:

| trigger   |   episodes |   median lead s |
|:----------|-----------:|----------------:|
| T1        |         11 |            1.90 |
| T2        |        104 |            1.90 |
| T3        |         22 |            1.65 |
| T4        |         90 |            1.10 |
| T5        |          7 |            1.30 |
| T6        |          3 |            0.90 |
| T7        |         89 |            1.60 |
| all       |        326 |            1.50 |

Qualification from these tables. At leads of 0.5 to 1.0 s the share is low for every trigger (T4 0.562, other triggers 0.515), which supports the finding. T4 has the shortest median lead of the large classes (1.10 s; 32 of its 90 episodes are in the 0.5 to 1.0 s band), so the finding fits T4. T1 does not fit it as well: its median lead is 1.90 s, the same as T2 (which passes at 0.760), and its 11 episodes include 5 with leads of 2 s or more that pass at 0.600.

### MT1 plan additions, logged before S3 (2026-10-28)

Set by the project lead before S3; these extend the brief's MT1 section and are part of the plan when MT1 is logged.

| # | addition | specification |
|:--|:--|:--|
| 1 | V3 variant: reaction time 0.35 s | everything else unchanged (radius, shaw, top speed 5.0 m/s, window 5, frozen D5 parameter). It tests both the parameter and the fact that velocity enters the DataBallPy model only as drift during the reaction window |
| 2 | report-only, not a gate: a constant-acceleration reach model | implemented in looseball. The player accelerates toward the pickup point from his current velocity at 3 m/s^2, capped at 5 m/s. Solved in one dimension along the line to the pickup point: the initial speed is the current velocity projected on that line (negative when moving away; a projected speed above 5 m/s starts at 5); the sideways component is ignored; no reaction time; time in closed form. Its own expectation parameter: the form chosen in S3, fitted on its dynamic times on the exploration analysis set and frozen before MT1. Compared with the DataBallPy model on test-set log-loss and on the share of verdicts that agree. A candidate follow-up to the package, not the entry's model. Empty team: the time of a standing player on the radius under this model |

Procedure points set by the project lead before S3:

| item | rule |
|:--|:--|
| S3 candidates | softmax (no intercept, one parameter) and logistic (intercept and slope) on dt from dynamic best times, as decided in step 2 setup; the two named forms are the same function without and with the intercept. The one with the lower pooled leave-one-match-out log-loss is chosen; B0 and B1 are fitted the same way and reported. All four are frozen by a fit on the whole analysis set |
| S3 calibration | five equal-width bins on the leave-one-match-out predictions of the chosen form |
| V3 episodes | the base analysis set's lost balls stay fixed; a variant changes only the reach times and hence the probabilities, with the frozen D5 parameter; D7 and the immediate rule are not re-applied under a variant |
| S5 dry run probabilities | the frozen parameters applied to the exploration analysis set: the code path MT1 will run, in-sample, so a bug check |
| S5 per-match rule | the brief's "same direction in at least 10 of 15 matches" is reported as a count out of 5 |

### S3, the expectation model (2026-10-28)

Script: scripts/s3.py, run after commit a3ce7bc. Analysis set: 326 episodes (anchored, kept by D7 at 15 m, lead >= 0.5 s); the releasing team won 0.442 of them. Frozen values written to audit/frozen_parameters.json.

S3a. Leave-one-match-out log-loss on the analysis set (dynamic best times for softmax and logistic):

| model    |   pooled |   1886347 |   1959846 |   1996435 |   1996436 |   2007448 |
|:---------|---------:|----------:|----------:|----------:|----------:|----------:|
| softmax  |   0.4525 |    0.3929 |    0.4722 |    0.5060 |    0.4123 |    0.4775 |
| logistic |   0.4547 |    0.3927 |    0.4906 |    0.5026 |    0.4094 |    0.4767 |
| B0       |   0.6547 |    0.6442 |    0.7084 |    0.6474 |    0.6482 |    0.6212 |
| B1       |   0.5545 |    0.5526 |    0.5730 |    0.5545 |    0.5267 |    0.5694 |

chosen form: softmax

S3b. Parameters fitted on the whole analysis set (frozen):

| model    | feature   |   a (intercept) |   b (slope) |   temperature 1/b |   in-sample log-loss |
|:---------|:----------|----------------:|------------:|------------------:|---------------------:|
| softmax  | dt        |          0.0000 |      2.9273 |            0.3416 |               0.4498 |
| logistic | dt        |         -0.1435 |      2.9148 |          nan      |               0.4482 |
| B0       | dn        |          0.0678 |      0.3610 |          nan      |               0.6495 |
| B1       | dd        |         -0.0530 |      0.3595 |          nan      |               0.5499 |

S3c. Calibration of the chosen form (softmax), leave-one-match-out predictions:

| bin        |   episodes |   mean predicted |   observed share |
|:-----------|-----------:|-----------------:|-----------------:|
| 0.0 to 0.2 |         85 |            0.069 |            0.094 |
| 0.2 to 0.4 |         62 |            0.297 |            0.194 |
| 0.4 to 0.6 |         60 |            0.499 |            0.433 |
| 0.6 to 0.8 |         60 |            0.699 |            0.683 |
| 0.8 to 1.0 |         59 |            0.929 |            0.966 |

S3d. Constant-acceleration model (report-only), chosen form fitted on its dynamic times:

| model                          |   a (intercept) |   b (slope) |   leave-one-match-out log-loss |   DataBallPy model, same form |
|:-------------------------------|----------------:|------------:|-------------------------------:|------------------------------:|
| constant acceleration, softmax |          0.0000 |      2.1821 |                         0.4738 |                        0.4525 |


| item | value |
|:--|:--|
| chosen form | softmax: pooled leave-one-match-out log-loss 0.4525 against 0.4547 for the logistic |
| frozen D5 parameter | b = 2.9273 per second, temperature T = 1 / b = 0.3416 s; p_releasing = sigmoid(2.9273 x (t_other - t_releasing)) |
| frozen B0 | sigmoid(0.0678 + 0.3610 x (n_releasing - n_other)) |
| frozen B1 | sigmoid(-0.0530 + 0.3595 x (nearest_other - nearest_releasing)) |
| frozen constant-acceleration model (report-only) | softmax, b = 2.1821 per second |

Reading. Both forms of p_dynamic are well below B1 (0.5545) and B0 (0.6547) on leave-one-match-out log-loss, in every match. The softmax is lower than the logistic by 0.0022 pooled, driven by one match (1959846: 0.4722 against 0.4906); in the other four matches the logistic is lower, by at most 0.0034. The fitted intercept of the logistic is small (-0.14), so the choice between the two forms changes little. The calibration table shows the 0.2 to 0.4 bin over-predicting (0.297 against 0.194, 62 episodes); the other bins are within 0.07. The constant-acceleration model has a higher leave-one-match-out log-loss than the DataBallPy model (0.4738 against 0.4525). These are exploration values; the comparison that counts is on the test set.

### S4, camera gate and the immediate class (2026-10-28)

Script: scripts/s4.py. Anchored main pairs, race at 15 m. The winner is read here for the D7 definition and the by-winner splits only (step 2 setup, decision 6).

anchored main pairs: 458

S4a. D7 drop rates by trigger:

| trigger   |   episodes |   dropped |   drop rate |
|:----------|-----------:|----------:|------------:|
| T1        |         26 |        12 |       0.462 |
| T2        |        135 |        27 |       0.200 |
| T3        |         32 |         6 |       0.188 |
| T4        |        129 |        17 |       0.132 |
| T5        |          8 |         1 |       0.125 |
| T6        |          5 |         2 |       0.400 |
| T7        |        123 |        26 |       0.211 |
| all       |        458 |        91 |       0.199 |

S4b. D7 drop rates by winner:

| winner         |   episodes |   dropped |   drop rate |
|:---------------|-----------:|----------:|------------:|
| other team     |        252 |        45 |       0.179 |
| releasing team |        206 |        46 |       0.223 |
| all            |        458 |        91 |       0.199 |

S4c. Reason for dropping:

| reason                                                       |   episodes |
|:-------------------------------------------------------------|-----------:|
| under 85% of players within 15 m detected at the anchor only |         86 |
| winner not detected at pickup only                           |          5 |
| both                                                         |          0 |
| kept                                                         |        367 |

S4d. Releasing team's win share, dropped against kept (interval: 2000 bootstrap replicates within match, seed 0):

|   win share dropped |   win share kept |   difference |     lo |    hi |
|--------------------:|-----------------:|-------------:|-------:|------:|
|               0.505 |            0.436 |        0.070 | -0.039 | 0.183 |

S4e. Immediate class (lead < 0.5 s) by trigger, all anchored main pairs:

| trigger   |   episodes |   immediate |   share |
|:----------|-----------:|------------:|--------:|
| T1        |         26 |           4 |   0.154 |
| T2        |        135 |           6 |   0.044 |
| T3        |         32 |           4 |   0.125 |
| T4        |        129 |          23 |   0.178 |
| T5        |          8 |           1 |   0.125 |
| T6        |          5 |           0 |   0.000 |
| T7        |        123 |           9 |   0.073 |
| all       |        458 |          47 |   0.103 |

S4e. Immediate class (lead < 0.5 s) by winner, all anchored main pairs:

| winner         |   episodes |   immediate |   share |
|:---------------|-----------:|------------:|--------:|
| other team     |        252 |          28 |   0.111 |
| releasing team |        206 |          19 |   0.092 |
| all            |        458 |          47 |   0.103 |

S4e. Immediate class (lead < 0.5 s) by trigger, pairs kept by D7:

| trigger   |   episodes |   immediate |   share |
|:----------|-----------:|------------:|--------:|
| T1        |         14 |           3 |   0.214 |
| T2        |        108 |           4 |   0.037 |
| T3        |         26 |           4 |   0.154 |
| T4        |        112 |          22 |   0.196 |
| T5        |          7 |           0 |   0.000 |
| T6        |          3 |           0 |   0.000 |
| T7        |         97 |           8 |   0.082 |
| all       |        367 |          41 |   0.112 |

S4e. Immediate class (lead < 0.5 s) by winner, pairs kept by D7:

| winner         |   episodes |   immediate |   share |
|:---------------|-----------:|------------:|--------:|
| other team     |        207 |          25 |   0.121 |
| releasing team |        160 |          16 |   0.100 |
| all            |        367 |          41 |   0.112 |

Reading. D7 drops 19.9% of anchored main pairs, below the 30% line that MT1 sets for the test set; 86 of the 91 drops are for player detection at the anchor and 5 for an undetected winner. Clearances (T1) lose 46.2% (12 of 26). The drop rate is 22.3% when the releasing team won and 17.9% when the other team won; the releasing team's win share is 0.070 higher among dropped than among kept episodes, with an interval from -0.039 to 0.183 that includes 0. The immediate class is 10.3% of anchored pairs (T4 17.8%, T2 4.4%) and 11.2% of kept pairs.

### S5, dry run of V1 to V3 (2026-10-28)

A bug check, not a test: the frozen parameters were fitted on these same 326 episodes, so every number below is in-sample. Script: scripts/s5.py (frozen values from audit/frozen_parameters.json); per-episode output audit/s5_episodes_exploration.csv, team shares audit/s5_team_shares_exploration.csv, clip export audit/s5_clips_exploration.csv. Bootstrap: 2000 replicates within match, seed 0.

V1 and V2 (dry run). Differences are log-loss of the comparison minus log-loss of the better-expected model:

| check               | model     | comparison   |   log-loss model |   log-loss comparison |   difference |     lo |     hi | interval excludes 0   |   matches with the same direction (of 5) |
|:--------------------|:----------|:-------------|-----------------:|----------------------:|-------------:|-------:|-------:|:----------------------|-----------------------------------------:|
| V1 against B0       | p_dynamic | p_B0         |           0.4498 |                0.6495 |       0.1997 | 0.1475 | 0.2523 | True                  |                                        5 |
| V1 against B1       | p_dynamic | p_B1         |           0.4498 |                0.5499 |       0.1002 | 0.0664 | 0.1348 | True                  |                                        5 |
| V2 against p_static | p_dynamic | p_static     |           0.4498 |                0.5744 |       0.1246 | 0.0786 | 0.1744 | True                  |                                        5 |

V3 (dry run). Verdicts of lost balls unchanged under each variant on its own (frozen D5 parameter, base set fixed):

| variant                                |   lost balls |   verdict unchanged | at least 0.70   |
|:---------------------------------------|-------------:|--------------------:|:----------------|
| anchor 0.2 s later                     |          326 |               0.899 | True            |
| growing radius max(15 m, 8 m/s x lead) |          326 |               0.985 | True            |
| pleuler turning penalty                |          326 |               0.899 | True            |
| smoothing window 7                     |          326 |               1.000 | True            |
| extrapolated players dropped           |          326 |               0.982 | True            |
| reaction time 0.35 s                   |          326 |               0.951 | True            |

Camera gate (dry run, anchored main pairs):

|   anchored pairs |   dropped |   drop share | at most 0.30   |   drop rate, releasing team won |   drop rate, other team won |   difference |
|-----------------:|----------:|-------------:|:---------------|--------------------------------:|----------------------------:|-------------:|
|              458 |        91 |        0.199 | True           |                           0.223 |                       0.179 |        0.045 |

Report-only (dry run). Calibration of p_dynamic, frozen parameter, five bins:

| bin        |   episodes |   mean predicted |   observed share |
|:-----------|-----------:|-----------------:|-----------------:|
| 0.0 to 0.2 |         85 |            0.069 |            0.106 |
| 0.2 to 0.4 |         61 |            0.295 |            0.180 |
| 0.4 to 0.6 |         60 |            0.496 |            0.417 |
| 0.6 to 0.8 |         57 |            0.690 |            0.667 |
| 0.8 to 1.0 |         63 |            0.922 |            0.968 |

Report-only (dry run). Mean deficit shares of the losing team by trigger:

| trigger   |   lost balls |   deficit positioning |   deficit reading |   deficit after the anchor |
|:----------|-------------:|----------------------:|------------------:|---------------------------:|
| T1        |           11 |                 0.771 |             0.025 |                      0.205 |
| T2        |          104 |                 0.673 |             0.051 |                      0.276 |
| T3        |           22 |                 0.574 |             0.121 |                      0.304 |
| T4        |           90 |                 0.681 |             0.032 |                      0.287 |
| T5        |            7 |                 0.611 |             0.087 |                      0.302 |
| T6        |            3 |                 0.835 |             0.073 |                      0.092 |
| T7        |           89 |                 0.633 |             0.020 |                      0.347 |
| all       |          326 |                 0.661 |             0.042 |                      0.297 |

Report-only (dry run). Share of lost loose balls under each verdict, pooled over teams:

| verdict          |   lost balls |   share |
|:-----------------|-------------:|--------:|
| positioning      |          239 |   0.733 |
| reading          |           34 |   0.104 |
| after the anchor |           53 |   0.163 |

Report-only (dry run). Constant-acceleration model against the DataBallPy model:

|   log-loss DataBallPy p_dynamic |   log-loss constant-acceleration p_dynamic |   verdicts that agree |
|--------------------------------:|-------------------------------------------:|----------------------:|
|                          0.4498 |                                     0.4707 |                0.9601 |

Team shares (dry run): deficit over lost balls, credit over won balls, 95% bootstrap intervals within match:

| team name       |   lost |   won |   deficit positioning |   deficit positioning lo |   deficit positioning hi |   deficit reading |   deficit reading lo |   deficit reading hi |   deficit after the anchor |   deficit after the anchor lo |   deficit after the anchor hi |
|:----------------|-------:|------:|----------------------:|-------------------------:|-------------------------:|------------------:|---------------------:|---------------------:|---------------------------:|------------------------------:|------------------------------:|
| Adelaide United |     35 |    35 |                 0.683 |                    0.600 |                    0.766 |             0.000 |               -0.045 |                0.044 |                      0.316 |                         0.237 |                         0.398 |
| Melbourne V FC  |     36 |    30 |                 0.662 |                    0.567 |                    0.745 |             0.016 |               -0.035 |                0.067 |                      0.322 |                         0.242 |                         0.411 |
| Sydney FC       |     35 |    35 |                 0.679 |                    0.582 |                    0.767 |             0.019 |               -0.029 |                0.070 |                      0.302 |                         0.218 |                         0.395 |
| Perth Glory     |     28 |    30 |                 0.596 |                    0.483 |                    0.707 |             0.024 |               -0.063 |                0.107 |                      0.379 |                         0.270 |                         0.491 |
| Brisbane FC     |     30 |    28 |                 0.711 |                    0.603 |                    0.812 |             0.053 |               -0.018 |                0.128 |                      0.236 |                         0.161 |                         0.319 |
| Western United  |     30 |    36 |                 0.631 |                    0.545 |                    0.715 |             0.061 |                0.010 |                0.114 |                      0.308 |                         0.232 |                         0.385 |
| Macarthur FC    |     36 |    34 |                 0.586 |                    0.500 |                    0.669 |             0.086 |                0.035 |                0.137 |                      0.328 |                         0.255 |                         0.407 |
| Newcastle       |     30 |    32 |                 0.589 |                    0.495 |                    0.683 |             0.108 |                0.040 |                0.179 |                      0.303 |                         0.217 |                         0.400 |
| Auckland FC     |     66 |    66 |                 0.731 |                    0.677 |                    0.783 |             0.031 |               -0.009 |                0.071 |                      0.238 |                         0.187 |                         0.289 |


Clip export: audit/s5_clips_exploration.csv, 326 rows (match_id, period, clock, frame, team, verdict). The clock is the tracking timestamp, a match clock: period 2 starts at 00:45:00.00 (checked on 1886347).

| dry-run item | number | MT1 rule | as it would read |
|:--|:--|:--|:--|
| V1 against B0 | log-loss 0.4498 against 0.6495; difference 0.1997 (0.1475 to 0.2523); 5 of 5 matches | interval excludes 0, at least 10 of 15 matches | holds |
| V1 against B1 | 0.4498 against 0.5499; 0.1002 (0.0664 to 0.1348); 5 of 5 | same | holds |
| V2 against p_static | 0.4498 against 0.5744; 0.1246 (0.0786 to 0.1744); 5 of 5 | same | holds |
| V3, six variants | verdict unchanged 0.899 to 1.000; lowest: anchor 0.2 s later and pleuler, both 0.899 | at least 0.70 each | holds |
| camera gate | 19.9% dropped; drop rate 0.223 when the releasing team won, 0.179 when the other team won | at most 30% | holds |
| constant-acceleration model (report-only) | log-loss 0.4707 against 0.4498; verdicts agree in 0.960 | report | reported |
| headline (report-only) | of 326 lost balls: positioning 0.733, reading 0.104, after the anchor 0.163 | report | reported |

Reading, as a bug check. The code path that MT1 will run produces every V1 to V3 quantity, the camera-gate figures, the report-only tables, the team shares and the clip export without error, and the numbers are consistent across tables: the team lost and won counts mirror within each match and sum to 326, and the clip export has one row per lost ball. The smoothing-window variant changes velocities only slightly (median speed difference 0.009 m/s on 1886347, p_dynamic by at most 0.008), so no verdict moves under it; this is a property of the already smooth tracking positions, not a fault. The growing radius exceeds 15 m in 34.4% of the episodes (p90 25.6 m) and reaches 50.4 m at the longest lead in the analysis set (6.3 s). Because the parameters were fitted on these episodes, V1 and V2 here say nothing about the test set.

### S5 figures (2026-10-28)

Script: scripts/s5_figures.py. Seed 20261028, 4 episodes drawn without replacement from the 326 analysis-set episodes (sorted by match and sequence).

|   figure |   match_id |   seq_i | trigger   | verdict     | file                                                     |
|---------:|-----------:|--------:|:----------|:------------|:---------------------------------------------------------|
|        1 |    1886347 |     859 | T4        | reading     | audit/figures/s5_episode_seed20261028_01_1886347_859.png |
|        2 |    1996435 |     697 | T2        | positioning | audit/figures/s5_episode_seed20261028_02_1996435_697.png |
|        3 |    1886347 |      38 | T2        | positioning | audit/figures/s5_episode_seed20261028_03_1886347_38.png  |
|        4 |    1886347 |     826 | T2        | positioning | audit/figures/s5_episode_seed20261028_04_1886347_826.png |

Team deficit figure: audit/figures/s5_team_deficit_exploration.png (nine teams; Auckland FC pooled over its two matches).

Figure reading (all inspected). In each episode figure the nearest players, the direction of the velocity arrows and the printed probabilities agree: in figure 1 the other team's nearest player (about 5 m away) is moving away from the pickup point, which lifts the releasing team from p_static 0.23 to p_dynamic 0.53 and gives the loser the verdict reading. The 1.0 s contour of a standing player has a 1.5 m radius, as 0.7 + d / 5 requires, and dynamic contours are shifted by velocity times 0.7 s. Figure 2 shows a near-tie (the loser's p_static 0.49) that the 0.5 line turns into positioning, which is the kind of episode V3 probes. No bug found.

### Bug check log, S5 (2026-10-28)

| change | when | effect |
|:--|:--|:--|
| a leftover assignment of losing_team and an unused import removed from scripts/s5.py | before its first run | none |
| V1 and V2 table rebuilt with fixed columns (it printed empty columns) | after the first run | display only; every value and every other table identical (checked by diff) |

No bug in the measures was found; the package code was not changed during S5.

### Step 2 interpretations of the brief, exploration part (2026-10-28)

Where the brief had to be read rather than followed. "Lead" marks a decision by the project lead before the result; "logged" marks a choice made in the code and logged before match data or before the run; "deferred" marks brief items not done in this step.

| # | brief item | reading | by |
|:--|:--|:--|:--|
| 1 | D3 "DataBallPy's time-to-intercept constraint" | the package's TTIConstraint.tti, called through a thin subclass because the constructor needs a Game | lead |
| 2 | D3 "default speed and acceleration parameters" | the model has no acceleration: reaction 0.7 s and top speed 5.0 m/s, the package defaults | lead |
| 3 | empty team best time "radius divided by top speed" | reaction time + radius / top speed (3.7 s at 15 m), the time of a standing player on the radius | lead |
| 4 | D5 softmax and logistic | identical without an intercept; softmax taken as the one-parameter form, logistic with an intercept, oriented to the releasing team; S3's "both forms, with and without the intercept" read as these two | lead |
| 5 | outcome only in S3 and S5 | S2, S4 and D7 read the winner as checks and as the gate definition, nothing fitted there | lead |
| 6 | episodes for S3 and S5 | the analysis set: anchored, kept by D7, lead >= 0.5 s | lead |
| 7 | unit of the race | raw main pairs, winner the team of possession i+1 | lead |
| 8 | S2 set for the 70% check | the analysis set, the other sets reported beside it | logged |
| 9 | S1 "anchor-frame velocities from extrapolated tracks" | share of players in the race with is_detected FALSE on the anchor frame | logged |
| 10 | D4 "Savitzky-Golay on each player's track" | first derivative within runs of consecutive frames, scipy "interp" mode at track ends; a track shorter than the window gets no velocity (none occurred at an anchor) | logged |
| 11 | goalkeeper flag | roster field player_role.acronym equal to "GK" | logged |
| 12 | B0 and B1 differences | oriented to the releasing team; an empty team's nearest distance is the radius | logged |
| 13 | D7 with nobody within the radius | counts as observed on the 85% condition | logged |
| 14 | bootstrap intervals (D7, D8, V1, V2) | percentile intervals, episodes resampled within match, 2000 replicates, seed 0 | logged |
| 15 | calibration tables | five equal-width bins; S3 on leave-one-match-out predictions, S5 on the frozen parameter | logged |
| 16 | clip export "clock, frame, team" | frame: the measured anchor; team: the team that lost; clock: tracking timestamp (a match clock) | logged |
| 17 | V3 variants | base analysis set fixed; a variant changes only reach times; D7 and the immediate rule not re-applied; frozen D5 parameter | lead |
| 18 | V3 growing radius | max(15 m, 8 m/s x lead) with the lead at the measured anchor; the empty-team time uses the grown radius | logged |
| 19 | MT1 "10 of 15 matches" in the dry run | reported as a count out of 5 | lead |
| 20 | S5 dry run probabilities | the frozen parameters on the exploration analysis set (the MT1 code path, in-sample) | lead |
| 21 | constant-acceleration model | one dimension along the line to the pickup point, no reaction time, its own frozen softmax fit | lead |
| 22 | S5 figures "the three numbers" | the losing team's three deficit shares, with p_static and p_dynamic of the releasing team beside them | logged |
| 23 | DESIGN.md "under the decomposition" | a new step 2 section holding the decomposition and the sentence; the rest of step 2 is frozen when MT1 is logged | logged |
| 24 | the DESIGN.md sentence on drift | it describes the frozen shaw model; under the pleuler variant velocity also enters through the turning term | logged |
| 25 | D8 "one match drawn by seed as the worked example" | not part of S1 to S5 | deferred |
| 26 | deliverable shape (find_episodes on DataBallPy tracking and event tables, SkillCorner adapter) | not built; the modules read this package's own tables | deferred |

## MT1, the main-test plan (2026-10-29)

Logged after S1 to S5 were read by the project lead. Run once on the 15 test matches with `scripts/mt1.py test`; outputs to audit/mt1_test/. After this entry no code changes except logged bug fixes, and none to the measures.

| item | value |
|:--|:--|
| code | commit 682aa2c (scripts/mt1.py, src/looseball, DataBallPy develop 3f9de8d28531aa12d826ee99aed8de7aeee0897f) |
| frozen parameters | audit/frozen_parameters.json, sha256 129bfdea2d1dd5547e3f8fdeb1f1f5de57514ca3b79ab5de2bb16a93fa9fab4c |
| test matches | 1874553, 1899585, 1925299, 1927964, 1953632, 1986691, 2006229, 2006363, 2007721, 2010085, 2011166, 2013725, 2015213, 2016236, 2017461 |
| rehearsal | scripts/mt1.py exploration (audit/mt1_exploration/) reproduces S5: V1 differences 0.1997 and 0.1002, V2 0.1246, V3 0.8988 to 1.0000, camera-gate drop 0.1987 |

Episodes and measures, as frozen:

| element | definition |
|:--|:--|
| episodes | DESIGN.md, step 1 definition with revision 3; the measured leg is the last leg; its anchor and lead |
| analysis set | anchored main pairs kept by D7 at 15 m, with lead >= 0.5 s; every one is a lost ball for one team |
| immediate class | lead < 0.5 s; reported, not decomposed |
| race | every player of both teams within 15 m of the pickup point on the anchor frame, goalkeepers included and flagged; Savitzky-Golay velocities, window 5, order 2 |
| reach model | DataBallPy TTIConstraint.tti, turning penalty shaw, reaction 0.7 s, top speed 5.0 m/s; static: velocity zero; an empty team gets 0.7 + radius / 5.0 |
| p_static, p_dynamic | releasing team: sigmoid(2.9273 x (t_other - t_releasing)) on static and dynamic best times (softmax, temperature 0.3416 s) |
| baselines | B0: sigmoid(0.0678 + 0.3610 x (n_releasing - n_other)); B1: sigmoid(-0.0530 + 0.3595 x (nearest_other - nearest_releasing)) |
| decomposition and verdict | DESIGN.md, step 2 measures, D6 |
| winner | team of possession i+1 |

Gates:

| gate | rule |
|:--|:--|
| V1 | p_dynamic has a lower log-loss than B0, and than B1, on the analysis set: for each, the difference (log-loss of the baseline minus log-loss of p_dynamic) has a 95% bootstrap interval above 0 and p_dynamic is lower in at least 10 of the 15 matches |
| V2 | the same rule for p_dynamic against p_static |
| V3 | for the lost balls of the analysis set, the verdict is unchanged in at least 70% of episodes under each variant on its own: anchor 0.2 s later; growing radius max(15 m, 8 m/s x lead); pleuler turning penalty; smoothing window 7; extrapolated players dropped; reaction time 0.35 s. The base set stays fixed, the frozen D5 parameter is used, and D7 and the immediate rule are not re-applied |
| camera gate | at most 30% of anchored main pairs dropped by D7 at 15 m; the drop-rate difference by winner reported |
| intervals | percentile, 2000 bootstrap replicates resampling episodes within match, seed 0 |

Consequences, fixed in the brief: V1 fails, the entry reports the audit and the descriptives and makes no verdicts. V2 fails, the reading term is dropped and the decomposition is positioning against the race. V3 fails, verdicts are shown with their variants and never as one label. The camera gate drops more than 30%, the radius falls to 10 m for the main analysis (frozen D5 parameter kept; the growing-radius variant becomes max(10 m, 8 m/s x lead)) and the change is logged.

Report-only on the test set, in this order:

| # | item | reading |
|:--|:--|:--|
| R1 | categorical verdict shares of lost balls, pooled over teams | the headline if V1 to V3 hold |
| R2 | the same with the camera gate off, extrapolated positions kept | anchored main pairs with lead >= 0.5 s, whatever D7 says; also by trigger, and for the dropped episodes alone |
| R3 | continuous deficit shares | pooled and by trigger |
| R4 | calibration of p_dynamic | five equal-width bins |
| R5 | immediate class | anchored main pairs, by trigger and by winner |
| R6 | D7 drop rates | by trigger and by winner, with the releasing team's win-share difference and its interval |
| R7 | S2 reachability check | by trigger, on the analysis set, on all anchored pairs and on lead >= 0.5 s |
| R8 | constant-acceleration model | log-loss of its p_dynamic (frozen softmax, b = 2.1821) and the share of verdicts that agree with the DataBallPy model |
| R9 | team level | categorical verdict shares and continuous deficit shares over lost balls, 95% intervals as above; flagged for sample size: teams in 2 or fewer test matches, and Newcastle (team id 1805) |

The worked-example match (D8) is drawn after the run with seed 20261029 (numpy default_rng) from the 15 test match ids in ascending order, as an illustration and never a check. The find_episodes adapter, the README, the figures and the video are step 3.

MAIN-TEST-PLAN: MT1, logged 2026-10-29, code at commit 682aa2c, frozen parameters sha256 129bfdea2d1dd5547e3f8fdeb1f1f5de57514ca3b79ab5de2bb16a93fa9fab4c

### MT1 results on the 15 test matches (2026-10-29)

Run once, `scripts/mt1.py test`, after the marker commit 3a104ab; code unchanged since 682aa2c; no bug fixes. Outputs: audit/mt1_test/ (episodes.csv with the verdict under each V3 variant, episodes_ungated.csv, team_verdicts.csv, team_shares.csv, clips.csv, gates.json).

MT1 on the test matches (15): anchored main pairs 1566; camera-gate drop share at 15 m 0.2771; radius of the main analysis 15 m; analysis set 1003 lost balls

Gates V1 and V2 (difference: log-loss of the comparison minus log-loss of p_dynamic):

| gate                | comparison   |   log-loss p_dynamic |   log-loss comparison |   difference |     lo |     hi |   matches p_dynamic lower (of 15) | result   |
|:--------------------|:-------------|---------------------:|----------------------:|-------------:|-------:|-------:|----------------------------------:|:---------|
| V1 against B0       | p_B0         |               0.4578 |                0.6397 |       0.1819 | 0.1471 | 0.2162 |                                15 | pass     |
| V1 against B1       | p_B1         |               0.4578 |                0.5516 |       0.0938 | 0.0718 | 0.1140 |                                15 | pass     |
| V2 against p_static | p_static     |               0.4578 |                0.5743 |       0.1165 | 0.0902 | 0.1440 |                                15 | pass     |

Gate V3 (verdict unchanged under each variant on its own; base set fixed; frozen D5 parameter):

| variant                                  |   lost balls |   verdict unchanged | result   |
|:-----------------------------------------|-------------:|--------------------:|:---------|
| anchor 0.2 s later                       |         1003 |              0.9113 | pass     |
| growing radius max(radius, 8 m/s x lead) |         1003 |              0.9771 | pass     |
| pleuler turning penalty                  |         1003 |              0.9242 | pass     |
| smoothing window 7                       |         1003 |              0.9970 | pass     |
| extrapolated players dropped             |         1003 |              0.9940 | pass     |
| reaction time 0.35 s                     |         1003 |              0.9372 | pass     |

Camera gate (D7, at most 30% of anchored main pairs dropped):

|   anchored pairs |   dropped at 15 m |   drop share at 15 m | result   |   drop rate, releasing team won |   drop rate, other team won |   difference |
|-----------------:|------------------:|---------------------:|:---------|--------------------------------:|----------------------------:|-------------:|
|             1566 |               434 |               0.2771 | pass     |                          0.2815 |                      0.2738 |       0.0078 |

Consequences fixed in the brief:

| gate        | result   | consequence       |
|:------------|:---------|:------------------|
| V1          | pass     | verdicts reported |
| V2          | pass     | reading term kept |
| V3          | pass     | one verdict label |
| camera gate | pass     | 15 m radius       |

R1. Categorical verdict shares of lost loose balls, pooled over teams (headline: True):

| verdict          |   gated (D7 on) |   ungated (D7 off, extrapolated positions kept) |
|:-----------------|----------------:|------------------------------------------------:|
| positioning      |          0.6899 |                                          0.6952 |
| reading          |          0.1346 |                                          0.1261 |
| after the anchor |          0.1755 |                                          0.1788 |
| lost balls       |       1003.0000 |                                       1404.0000 |

R2. Gated against ungated, by trigger (share of lost balls under each verdict):

| set     | trigger   |   lost balls |   positioning |   reading |   after the anchor |
|:--------|:----------|-------------:|--------------:|----------:|-------------------:|
| gated   | T1        |           30 |         0.867 |     0.067 |              0.067 |
| gated   | T2        |          281 |         0.641 |     0.125 |              0.235 |
| gated   | T3        |           45 |         0.622 |     0.178 |              0.200 |
| gated   | T4        |          327 |         0.743 |     0.153 |              0.104 |
| gated   | T5        |           13 |         1.000 |     0.000 |              0.000 |
| gated   | T6        |            7 |         0.714 |     0.000 |              0.286 |
| gated   | T7        |          300 |         0.657 |     0.133 |              0.210 |
| ungated | T1        |           69 |         0.797 |     0.043 |              0.159 |
| ungated | T2        |          401 |         0.661 |     0.115 |              0.224 |
| ungated | T3        |           74 |         0.581 |     0.189 |              0.230 |
| ungated | T4        |          405 |         0.743 |     0.146 |              0.111 |
| ungated | T5        |           21 |         0.952 |     0.048 |              0.000 |
| ungated | T6        |            9 |         0.778 |     0.000 |              0.222 |
| ungated | T7        |          425 |         0.671 |     0.127 |              0.202 |

R2b. The 401 lost balls that D7 drops, verdict shares:

|   lost balls |   positioning |   reading |   after the anchor |
|-------------:|--------------:|----------:|-------------------:|
|      401.000 |         0.708 |     0.105 |              0.187 |

R3. Continuous deficit shares of the losing team, pooled and by trigger:

| trigger   |   lost balls |   deficit positioning |   deficit reading |   deficit after the anchor |
|:----------|-------------:|----------------------:|------------------:|---------------------------:|
| T1        |           30 |                 0.814 |             0.071 |                      0.116 |
| T2        |          281 |                 0.635 |             0.055 |                      0.310 |
| T3        |           45 |                 0.601 |             0.098 |                      0.300 |
| T4        |          327 |                 0.672 |             0.042 |                      0.286 |
| T5        |           13 |                 0.762 |             0.055 |                      0.183 |
| T6        |            7 |                 0.654 |             0.031 |                      0.315 |
| T7        |          300 |                 0.626 |             0.043 |                      0.331 |
| all       |         1003 |                 0.650 |             0.049 |                      0.301 |

R4. Calibration of p_dynamic, five bins:

| bin        |   episodes |   mean predicted |   observed share |
|:-----------|-----------:|-----------------:|-----------------:|
| 0.0 to 0.2 |        241 |            0.080 |            0.087 |
| 0.2 to 0.4 |        207 |            0.299 |            0.188 |
| 0.4 to 0.6 |        215 |            0.496 |            0.433 |
| 0.6 to 0.8 |        140 |            0.697 |            0.786 |
| 0.8 to 1.0 |        200 |            0.927 |            0.905 |

R5. Immediate class (lead < 0.5 s), anchored main pairs, by trigger and by winner:

| trigger   |   episodes |   immediate |   share |
|:----------|-----------:|------------:|--------:|
| T1        |         79 |          10 |   0.127 |
| T2        |        415 |          14 |   0.034 |
| T3        |         89 |          15 |   0.169 |
| T4        |        500 |          95 |   0.190 |
| T5        |         24 |           3 |   0.125 |
| T6        |         13 |           4 |   0.308 |
| T7        |        446 |          21 |   0.047 |
| all       |       1566 |         162 |   0.103 |

| winner         |   episodes |   immediate |   share |
|:---------------|-----------:|------------:|--------:|
| other team     |        884 |         104 |   0.118 |
| releasing team |        682 |          58 |   0.085 |
| all            |       1566 |         162 |   0.103 |

R6. D7 drop rates by trigger and by winner, and the releasing team's win-share difference:

| trigger   |   episodes |   dropped |   drop rate |
|:----------|-----------:|----------:|------------:|
| T1        |         79 |        44 |       0.557 |
| T2        |        415 |       123 |       0.296 |
| T3        |         89 |        32 |       0.360 |
| T4        |        500 |        92 |       0.184 |
| T5        |         24 |         8 |       0.333 |
| T6        |         13 |         4 |       0.308 |
| T7        |        446 |       131 |       0.294 |
| all       |       1566 |       434 |       0.277 |

| winner         |   episodes |   dropped |   drop rate |
|:---------------|-----------:|----------:|------------:|
| other team     |        884 |       242 |       0.274 |
| releasing team |        682 |       192 |       0.282 |
| all            |       1566 |       434 |       0.277 |

|   win share dropped |   win share kept |   difference |     lo |    hi |
|--------------------:|-----------------:|-------------:|-------:|------:|
|               0.442 |            0.433 |        0.010 | -0.043 | 0.069 |

R7. S2 reachability check by trigger (winner reach time <= lead + 0.3 s):

analysis set:

| trigger   |   episodes |   share |   winner not on anchor frame |
|:----------|-----------:|--------:|-----------------------------:|
| T1        |         30 |   0.700 |                            0 |
| T2        |        281 |   0.744 |                            0 |
| T3        |         45 |   0.689 |                            0 |
| T4        |        327 |   0.682 |                            0 |
| T5        |         13 |   0.462 |                            0 |
| T6        |          7 |   0.571 |                            0 |
| T7        |        300 |   0.767 |                            0 |
| all       |       1003 |   0.722 |                            0 |

all anchored pairs:

| trigger   |   episodes |   share |   winner not on anchor frame |
|:----------|-----------:|--------:|-----------------------------:|
| T1        |         79 |   0.557 |                            0 |
| T2        |        415 |   0.747 |                            1 |
| T3        |         89 |   0.573 |                            0 |
| T4        |        500 |   0.554 |                            0 |
| T5        |         24 |   0.500 |                            0 |
| T6        |         13 |   0.462 |                            0 |
| T7        |        446 |   0.722 |                            0 |
| all       |       1566 |   0.653 |                            1 |

lead >= 0.5 s:

| trigger   |   episodes |   share |   winner not on anchor frame |
|:----------|-----------:|--------:|-----------------------------:|
| T1        |         69 |   0.638 |                            0 |
| T2        |        401 |   0.773 |                            1 |
| T3        |         74 |   0.689 |                            0 |
| T4        |        405 |   0.684 |                            0 |
| T5        |         21 |   0.571 |                            0 |
| T6        |          9 |   0.667 |                            0 |
| T7        |        425 |   0.758 |                            0 |
| all       |       1404 |   0.728 |                            1 |

R8. Constant-acceleration model (report-only):

|   log-loss DataBallPy p_dynamic |   log-loss constant-acceleration p_dynamic |   verdicts that agree |
|--------------------------------:|-------------------------------------------:|----------------------:|
|                          0.4578 |                                     0.4697 |                0.9472 |

R9a. Team-level categorical verdict shares over lost balls, 95% bootstrap intervals within match:

| team            | sample-size flag   |   matches in the set |   lost |   positioning |   positioning lo |   positioning hi |   reading |   reading lo |   reading hi |   after the anchor |   after the anchor lo |   after the anchor hi |
|:----------------|:-------------------|---------------------:|-------:|--------------:|-----------------:|-----------------:|----------:|-------------:|-------------:|-------------------:|----------------------:|----------------------:|
| Adelaide United | flag               |                    2 |     67 |         0.642 |            0.523 |            0.755 |     0.149 |        0.066 |        0.243 |              0.209 |                 0.111 |                 0.310 |
| Wellington P FC |                    |                    3 |    109 |         0.752 |            0.673 |            0.832 |     0.073 |        0.028 |        0.126 |              0.174 |                 0.105 |                 0.246 |
| Melbourne V FC  |                    |                    3 |    100 |         0.710 |            0.617 |            0.802 |     0.150 |        0.083 |        0.224 |              0.140 |                 0.078 |                 0.212 |
| Sydney FC       | flag               |                    1 |     40 |         0.775 |            0.647 |            0.896 |     0.125 |        0.028 |        0.231 |              0.100 |                 0.023 |                 0.205 |
| CC Mariners     |                    |                    4 |    141 |         0.695 |            0.617 |            0.770 |     0.156 |        0.098 |        0.219 |              0.149 |                 0.092 |                 0.209 |
| Perth Glory     | flag               |                    1 |     35 |         0.629 |            0.465 |            0.795 |     0.171 |        0.056 |        0.313 |              0.200 |                 0.071 |                 0.333 |
| Brisbane FC     | flag               |                    2 |     65 |         0.738 |            0.623 |            0.840 |     0.092 |        0.030 |        0.169 |              0.169 |                 0.083 |                 0.269 |
| Western United  |                    |                    3 |    110 |         0.682 |            0.590 |            0.762 |     0.136 |        0.078 |        0.204 |              0.182 |                 0.114 |                 0.257 |
| Macarthur FC    | flag               |                    1 |     36 |         0.583 |            0.421 |            0.730 |     0.167 |        0.056 |        0.300 |              0.250 |                 0.121 |                 0.400 |
| Melbourne City  |                    |                    3 |     65 |         0.692 |            0.571 |            0.797 |     0.123 |        0.049 |        0.211 |              0.185 |                 0.100 |                 0.284 |
| Western Sydney  | flag               |                    2 |     52 |         0.692 |            0.574 |            0.814 |     0.212 |        0.111 |        0.321 |              0.096 |                 0.020 |                 0.183 |
| Auckland FC     |                    |                    5 |    183 |         0.656 |            0.590 |            0.724 |     0.126 |        0.080 |        0.174 |              0.219 |                 0.160 |                 0.281 |

R9b. Team-level continuous deficit shares over lost balls, 95% bootstrap intervals within match:

| name            |   matches in the set | sample-size flag   |   lost |   won |   deficit positioning |   deficit positioning lo |   deficit positioning hi |   deficit reading |   deficit reading lo |   deficit reading hi |   deficit after the anchor |   deficit after the anchor lo |   deficit after the anchor hi |
|:----------------|---------------------:|:-------------------|-------:|------:|----------------------:|-------------------------:|-------------------------:|------------------:|---------------------:|---------------------:|---------------------------:|------------------------------:|------------------------------:|
| Adelaide United |                    2 | flag               |     67 |    68 |                 0.621 |                    0.562 |                    0.681 |             0.041 |                0.003 |                0.079 |                      0.338 |                         0.280 |                         0.398 |
| Wellington P FC |                    3 |                    |    109 |    94 |                 0.686 |                    0.639 |                    0.735 |             0.038 |                0.010 |                0.067 |                      0.276 |                         0.232 |                         0.323 |
| Melbourne V FC  |                    3 |                    |    100 |   108 |                 0.678 |                    0.629 |                    0.725 |             0.030 |               -0.001 |                0.061 |                      0.292 |                         0.252 |                         0.332 |
| Sydney FC       |                    1 | flag               |     40 |    34 |                 0.671 |                    0.586 |                    0.754 |             0.062 |               -0.007 |                0.127 |                      0.267 |                         0.204 |                         0.336 |
| CC Mariners     |                    4 |                    |    141 |   109 |                 0.639 |                    0.596 |                    0.681 |             0.051 |                0.023 |                0.081 |                      0.309 |                         0.271 |                         0.349 |
| Perth Glory     |                    1 | flag               |     35 |    31 |                 0.593 |                    0.492 |                    0.695 |             0.086 |                0.037 |                0.137 |                      0.320 |                         0.238 |                         0.402 |
| Brisbane FC     |                    2 | flag               |     65 |    64 |                 0.643 |                    0.578 |                    0.704 |             0.018 |               -0.023 |                0.059 |                      0.339 |                         0.281 |                         0.402 |
| Western United  |                    3 |                    |    110 |   115 |                 0.661 |                    0.610 |                    0.709 |             0.062 |                0.034 |                0.091 |                      0.276 |                         0.236 |                         0.321 |
| Macarthur FC    |                    1 | flag               |     36 |    19 |                 0.603 |                    0.509 |                    0.692 |             0.087 |                0.038 |                0.142 |                      0.311 |                         0.237 |                         0.390 |
| Melbourne City  |                    3 |                    |     65 |   108 |                 0.685 |                    0.619 |                    0.747 |             0.045 |                0.003 |                0.091 |                      0.270 |                         0.213 |                         0.330 |
| Western Sydney  |                    2 | flag               |     52 |    76 |                 0.644 |                    0.583 |                    0.708 |             0.062 |                0.021 |                0.104 |                      0.294 |                         0.236 |                         0.351 |
| Auckland FC     |                    5 |                    |    183 |   177 |                 0.631 |                    0.593 |                    0.672 |             0.053 |                0.028 |                0.077 |                      0.316 |                         0.278 |                         0.355 |


Gate verdicts.

| gate | number | rule | result |
|:--|:--|:--|:--|
| V1 against B0 | log-loss 0.4578 against 0.6397; difference 0.1819 (0.1471 to 0.2162); p_dynamic lower in 15 of 15 matches | interval above 0, at least 10 of 15 | pass |
| V1 against B1 | 0.4578 against 0.5516; difference 0.0938 (0.0718 to 0.1140); 15 of 15 | same | pass |
| V2 against p_static | 0.4578 against 0.5743; difference 0.1165 (0.0902 to 0.1440); 15 of 15 | same | pass |
| V3 | verdict unchanged: anchor 0.2 s later 0.911, pleuler 0.924, reaction 0.35 s 0.937, growing radius 0.977, extrapolated dropped 0.994, window 7 0.997 | at least 0.70 each | pass |
| camera gate | 434 of 1566 anchored pairs dropped (0.277); drop rate 0.282 when the releasing team won, 0.274 when the other team won (difference 0.008) | at most 0.30 | pass |

Consequences: all gates pass, so verdicts are reported as one label, the reading term is kept and the radius stays 15 m.

Headline (R1): of 1003 lost loose balls in the analysis set, 69.0% are positioning, 13.5% reading and 17.6% after the anchor.

Gated against ungated (R1, R2): with D7 off (1404 lost balls, extrapolated positions kept), 69.5% positioning, 12.6% reading, 17.9% after the anchor. The 401 lost balls that D7 drops split 70.8%, 10.5% and 18.7%. The largest differences by trigger are in T1 (gated 30 lost balls: 86.7% positioning; ungated 69: 79.7%) and T5 (13 and 21). D7 drops 55.7% of T1 episodes and 18.4% of T4.

Notes. Newcastle (team id 1805) plays in none of the 15 test matches; its only match is exploration match 1886347, so its sample-size flag has nothing to apply to. Teams flagged for sample size (2 or fewer test matches): Adelaide United, Brisbane FC, Western Sydney (2), Sydney FC, Perth Glory, Macarthur FC (1). In R7 one anchored pair (T2) has the winner absent from the anchor frame; it is counted as not meeting the criterion and is not in the analysis set. Team lost and won counts each sum to 1003. Calibration (R4) over-predicts in the 0.2 to 0.4 bin (0.299 against 0.188, 207 episodes), as on exploration, and under-predicts in the 0.6 to 0.8 bin (0.697 against 0.786, 140 episodes).

### Worked-example match, D8 (2026-10-29)

Drawn after the run as logged: seed 20261029, numpy default_rng, from the 15 test match ids in ascending order. Illustration only, never a check.

| match | teams | date | lost balls in the analysis set |
|:--|:--|:--|--:|
| 1927964 | Western Sydney v Wellington P FC | 2024-12-22 | 61 |

## Step 3, package and figures

Brief: docs/step3_brief.md. No measure, definition or frozen parameter changes.

### 3a. Package: decisions and structure (2026-10-29)

Decisions by the project lead before the package was written:

| # | question | decision |
|:--|:--|:--|
| 1 | input shape (DataBallPy has no possession table, and its tracking has no detection flags and no camera polygon) | tracking in DataBallPy's wide TrackingData layout (frame, period_id, ball_x/y/z, home_N_x/_y, away_N_x/_y) with documented extension columns (clock, ball and per-player detection, eight camera-polygon corners); a looseball-defined possessions table in DataBallPy naming with a neutral start and end vocabulary; a players table mapping player ids to tracking column ids (looseball/schema.py) |
| 2 | what the grep test treats as a SkillCorner column name | a curated list of the SkillCorner fields the adapter reads that DataBallPy does not use; distinctive names matched as whole words anywhere in looseball outside adapters/, generic words (index, timestamp, number, acronym, possession) as exact string literals |
| 3 | the test-set guard in the public path | not in the adapter; the guard stays on the research loaders |
| 4 | clip-export headers | the MT1 headers frame and team are kept, so reproduce matches byte for byte; frame is the anchor frame and team the losing team |
| 5 | where the step 1 and 2 research code lives | verbatim in src/looseball_research (imports renamed only); scripts/ and the research tests (tests/research) import it; looseball is the public, provider-neutral package |

Structure and checks:

| item | value |
|:--|:--|
| public API (looseball) | find_episodes, reach_times, expectations, decompose, team_report, export_clips; adapters/skillcorner.py; reproduce.py; cli.py (looseball reproduce, looseball run); frozen parameters in looseball/data/frozen_parameters.json (byte-identical to audit/frozen_parameters.json); refit() is a separate function, never imported or called by reproduce.py or cli.py (test) |
| research record | src/looseball_research: the step 1 and 2 modules unchanged except the package name; scripts/mt1.py exploration reproduces its earlier output byte for byte after the move |
| research tests | two guard tests asserted that the real repository is locked, which the committed MT1 marker (3a104ab) lifted; they now simulate a repository without the marker and keep proving the rule, and a new test checks that the real repository is unlocked |
| tests | 30 on the public API (synthetic data, written and passed before each next function) and 34 research tests: 64 passed |
| early equivalence | on the five exploration matches, find_episodes gives the research code's 466 episodes with identical triggers, contacts, both anchors, pickup points and winner detection, and for the 458 anchored pairs identical lead, immediate flag, D7 counts and D7 flag |
| grep list | "period" is left out: it is the MT1 clip-export header (decision 4); the neutral tables use period_id |
| README.md | a title-only placeholder until 3c, so the README-limit test runs; the test counts words after stripping markdown (link URLs and comments dropped, image captions, table text and code counted) and counts images and markdown tables together |
| licence | LICENSE.md, MIT, copyright Amin Nabavi; pyproject declares license MIT and the looseball command |
| wheel | builds with both packages, the frozen-parameter JSON, LICENSE.md and the entry point |

### 3a. Reproduce against the MT1 record (2026-10-29)

`looseball reproduce --data data/opendata --out OUT`, run after commit 12bd6f2, through the public API and the SkillCorner adapter with the packaged frozen parameters; compared with `scripts/check_reproduce.py OUT`.

| output | against | result |
|:--|:--|:--|
| episodes.csv, episodes_ungated.csv, team_verdicts.csv, team_shares.csv, clips.csv, gates.json | audit/mt1_test | byte-identical, all six |
| report.md (every MT1 gate and report-only table) | the MT1 results logged in AUDIT.md, 215 lines | identical |
| run | Python 3.12.3, numpy 2.2.6, pandas 3.1.0, DataBallPy 3f9de8d | 4 min 40 s wall time, 821 MB peak memory |

No difference: the public package regenerates MT1 exactly.

### 3b. Figures (2026-10-29)

Script: src/looseball/figures.py, called by `looseball reproduce` after the tables (part of the reproduce path). Files in figures/, regenerated by the full reproduce run (5 min 15 s) and compared byte for byte by scripts/check_reproduce.py; a second drawing from the same tables gives identical bytes.

| figure | content | source of every number |
|:--|:--|:--|
| figures/figure1_seed20261029.png and figures/figure1_caption.txt | the worked episode, see below | episodes.csv of the reproduce output (p_static, p_dynamic, verdict, teams, frames), the adapter's tracking for the positions and the match clock, the package's reach model for the shading |
| figures/figure2_A.png | left: the 12 test-set teams, categorical verdict shares over their lost loose balls as stacked bars, 95% interval on the positioning share, teams with two test matches or fewer marked; right: per-match log-loss of B0, B1, static and dynamic across the 15 test matches, connected within match | team_verdicts.csv and episodes.csv of the reproduce output (identical to audit/mt1_test) |
| figures/figure2_B.png | the left panel of A alone | team_verdicts.csv |

Figure 1 draw, logged as the brief asks:

| item | value |
|:--|:--|
| seed | 20261029 (numpy default_rng), one draw from the pool sorted by seq_i |
| pool | the 52 lost balls of match 1927964 with a reading or positioning verdict (of 61 in the analysis set) |
| drawn episode | match 1927964, seq_i 255: T4 dispossession, anchor frame 11497, lead 0.7 s, no contact; Western Sydney lost to Wellington P FC; verdict reading |
| caption (34 words) | When the drop zone came into view, Western Sydney had a 67.1% chance from where their players stood, but how they were moving cut it to 23.4%. Lost on reading: moving the wrong way. |

Figure choices made in this step (no measure involved):

| item | choice |
|:--|:--|
| Figure 1 shading | each team's best dynamic reach time to every point of the panel, from all of that team's players on the anchor frame (not only the 15 m race), with the frozen reach model; shown as the winning team's margin, clipped at 2 s either way, with the level line drawn |
| Figure 1 extent | 22 m around the pickup point, cut at the pitch boundary plus 2 m |
| palette | blue, orange and aqua from the reference categorical palette, checked with the palette validator: all checks pass in light mode for all pairs; aqua is under 3:1 against the background, so its segments carry dark-ink labels and the legend names every colour |
| Figure 2 bar labels | whole percent inside segments of at least 7% (the tables keep the full values) |
| Figure 2 right panel | per-match log-loss computed from the four-decimal probabilities in episodes.csv; p_dynamic is lowest in 15 of 15 matches, as in MT1 |
| file names | Figure 1 carries its seed; Figure 2 carries the version letter |

### 3c.0. Static expectation with its own temperature: procedure, logged before the fit (2026-10-29)

Report-only. The decomposition keeps the shared temperature; this line only benchmarks V2. Decisions by the project lead before the fit: it is regenerated by `looseball reproduce` as a separate output; its value goes in a new frozen file, so audit/frozen_parameters.json (hash in the MT1 marker) is untouched.

| item | rule |
|:--|:--|
| model | softmax on the static best-time difference: p_static_own = sigmoid(b_static x (static best time of the other team minus that of the releasing team)), no intercept |
| fit | exploration analysis set (326 episodes, the S3 set); leave-one-match-out log-loss reported as in S3; b_static frozen by a fit on all 326; written to audit/frozen_static_temperature.json and shipped in the package |
| test | applied unchanged to the 1003 test analysis episodes; log-loss next to B1 and p_dynamic; for each comparison the difference (log-loss of the other model minus log-loss of p_dynamic, or of B1 minus p_static_own), its 95% interval (2000 bootstrap replicates within match, seed 0) and the number of the 15 matches where p_dynamic is lower |

### 3b revision: Figure 1 legibility constraint, logged before the draw (2026-10-29)

Decided by the project lead after seeing the first Figure 1 (seq_i 255: a 0.7 s lead and a ball path of about 1.5 m, too short to read). One new seeded draw under a constraint fixed here, before the draw.

| item | rule |
|:--|:--|
| pool | lost balls of match 1927964 in the test analysis set with a reading or positioning verdict, a lead of at least 1.5 s, and a ball path of at least 10 m |
| ball path | path length: the sum of the steps between consecutive tracked ball positions (ball_x, ball_y) from the release frame to the pickup frame, steps with a missing position skipped (as in A8c) |
| draw | seed 20261029 (numpy default_rng, the seed already logged for Figure 1), one draw from the pool sorted by seq_i |
| caption | says that the shading shows which team reaches each point first and that the ball was drawn at random among such balls, with the three numbers; at most 40 words |
| previous Figure 1 | kept as figures/previous/figure1_unconstrained_seed20261029.png with its caption; not part of the reproduce path |

### 3c.0. Static expectation with its own temperature: results (2026-10-29)

Exploration fit (scripts/s3c0_static_temperature.py, after the procedure above was logged):

| model                   |   pooled |   1886347 |   1959846 |   1996435 |   1996436 |   2007448 |
|:------------------------|---------:|----------:|----------:|----------:|----------:|----------:|
| static, own temperature |   0.5516 |    0.5533 |    0.5588 |    0.5540 |    0.5268 |    0.5683 |

| item | value |
|:--|:--|
| frozen | b_static = 1.8123 per second (temperature 0.5518 s), audit/frozen_static_temperature.json, shipped as looseball/data/frozen_static_temperature.json |
| exploration context (S3) | dynamic softmax 0.4525, B1 0.5545 (leave-one-match-out) |

Test set (`looseball reproduce`, output static_temperature.md, kept as audit/static_temperature_test.md; the MT1 outputs stay identical):

| model        | against      |   log-loss model |   log-loss against |   difference |      lo |     hi |   matches model lower (of 15) |
|:-------------|:-------------|-----------------:|-------------------:|-------------:|--------:|-------:|------------------------------:|
| p_dynamic    | p_static_own |           0.4578 |             0.5529 |       0.0951 |  0.0731 | 0.1154 |                            15 |
| p_dynamic    | p_B1         |           0.4578 |             0.5516 |       0.0938 |  0.0718 | 0.1140 |                            15 |
| p_static_own | p_B1         |           0.5529 |             0.5516 |      -0.0013 | -0.0028 | 0.0001 |                             4 |

Reading. With its own temperature the static expectation reaches a log-loss of 0.5529 on the test episodes, no better than B1 (0.5516; difference -0.0013, interval -0.0028 to 0.0001, lower in 4 of 15 matches). The dynamic expectation is lower than it by 0.0951 (0.0731 to 0.1154) and in 15 of 15 matches, so V2 still holds against the fairer static line, by a margin close to V1's margin over B1 (0.0938). With the shared temperature, V2's margin was 0.1165.

### 3a packaging bug, found and fixed during 3c.0 (2026-10-29)

| item | value |
|:--|:--|
| bug | the .gitignore rule `data/` also matched src/looseball/data, so the packaged frozen parameters (looseball/data/frozen_parameters.json) were never committed in 3a; a fresh clone would have lacked them. The 3a wheel check passed because it built from the working tree |
| fix | the rule is anchored to the repository root (`/data/`); the open-data link and the cache stay ignored; src/looseball/data/frozen_parameters.json and frozen_static_temperature.json are committed |
| effect on results | none: the files' contents are unchanged (byte-identical to the audit copies, test_frozen_parameters) |

### 3b revision: figures redrawn (2026-10-29)

| item | value |
|:--|:--|
| Figure 1 draw | under the constraint logged above, seed 20261029: pool of 17 lost balls in match 1927964; drawn match 1927964, seq_i 323: T6 (unknown end), lead 1.5 s, ball path 19.0 m, verdict positioning; Wellington P FC lost to Western Sydney |
| Figure 1 caption (40 words) | Shading: which team reaches each point first. When the drop zone came into view, Wellington P FC had 1.1% from position, 0.3% with movement: lost on positioning. Randomly drawn among lost balls with lead 1.5 s+ and path 10 m+. |
| Figure 1 file | figures/figure1_constrained_seed20261029.png and figures/figure1_caption.txt; the previous draw kept as figures/previous/figure1_unconstrained_seed20261029.png (not regenerated) |
| Figure 1 rendering fix | players outside the panel are no longer drawn (their arrows had reached into the panel without a marker) |
| Figure 2 A (chosen) and B | the 95% interval on the positioning share moved below each bar, so it cannot be read as an interval on the reading share; the footnote wrapped onto two lines |
| reproduce diff | `looseball reproduce` (5 min 47 s, 826 MB peak) checked with scripts/check_reproduce.py: the six MT1 files, report.md, static_temperature.md and all four figure files identical; a second drawing from the same tables gives identical bytes |

Reproduce runs so far, same machine (Python 3.12.3, numpy 2.2.6, pandas 3.1.0):

| run | wall time | peak memory |
|:--|:--|:--|
| 3a, tables only | 4 min 40 s | 821 MB |
| 3b, with figures | 5 min 15 s | 825 MB |
| 3c.0 | 5 min 52 s | 813 MB |
| figure revision, first | 7 min 10 s | 846 MB |
| figure revision, final | 5 min 47 s | 826 MB |

### 3c. README numbers and their sources (2026-10-29)

Every number in README.md, with its source. Derived values are computed from the logged values shown.

| README number | source |
|:--|:--|
| 20 matches, 5 build, 15 held out; A-League 2024/25 | step 1 and MT1 match lists |
| 69.0%, 13.5%, 17.6% | MT1 R1, gated |
| 1,566 balls; about 104 a match | MT1, anchored main pairs; 1,566 / 15 = 104.4 |
| 10.3% decided within half a second | MT1 R5, immediate share of anchored pairs |
| 35.2% drop zone off screen at release (build matches) | diagnostic after G4: 164 of 466 main pairs |
| 33.0% of players near it seen | diagnostic after G4, release frame, pickup point outside the view, 15 m |
| 0.7 s reaction, 5 m/s top speed | step 2 setup, decision 3 |
| 28.4% lower log-loss than the player count (B0) | MT1 V1: (0.6397 - 0.4578) / 0.6397 = 0.1819 / 0.6397 |
| 17.0% lower than the nearest player (B1) | MT1 V1: 0.0938 / 0.5516 |
| in all 15 matches; intervals clear of zero | MT1 V1 and V2 (15 of 15; intervals 0.1471 to 0.2162 and 0.0718 to 0.1140) |
| 17.2% lower than the static expectation with its own temperature, in all 15 matches | 3c.0: 0.0951 / 0.5529; 15 of 15; interval 0.0731 to 0.1154 |
| static line no better than the nearest player, lower in 4 of 15 | 3c.0: difference -0.0013 (-0.0028 to 0.0001), 4 of 15 |
| six changes, anchor 0.2 s later to 0.35 s reaction; 91.1% to 99.7% | MT1 V3 |
| camera gate: 85% within 15 m; 27.7% dropped; limit 30%; 28.2% and 27.4% | D7 and MT1 camera gate |
| 1,404 lost balls ungated; 69.5%, 12.6%, 17.9% | MT1 R1, ungated |
| about one lost ball in seven | MT1 R1 reading share 13.5% (1 / 0.135 = 7.4) |
| worked match: 61 lost balls; 46, 6, 9 | audit/mt1_test/episodes.csv, match 1927964 (MT1 worked-example draw) |
| 55.7% of clearances dropped; 30 remain | MT1 R6 (T1 drop rate) and R2 (T1 gated, 30) |
| calibration 29.9% against 18.8%, 69.7% against 78.6% | MT1 R4, bins 0.2 to 0.4 and 0.6 to 0.8 |
| 1 to 5 held-out matches per team | MT1 R9a, matches in the set |
| commit 4340d27; Python 3.12; Git LFS | setup; environment; the open-data clone stores *.jsonl with Git LFS (.gitattributes) |
| about 6 minutes, about 0.8 GB | 3b revision, reproduce runs (final run 5 min 47 s, 826 MB) |

### Repository history rewritten before the first push (2026-11-17)

Done at the project lead's request, before the repository was first pushed to GitHub (private). The step 3 brief says "The commit history stays as it is"; this entry records the departure. Every commit was replayed in order with the same message, author, author date, committer and committer date. Changes inside the replayed commits:

| item | change |
|:--|:--|
| a local tool configuration file | not part of the entry: removed from every commit; kept as an untracked local file |
| docs/step1_audit_brief.md, step2_brief.md, step3_brief.md | wording about how the briefs were used removed: opening lines now "Brief for step N", "Rules for the session" now "Rules for the step", an appendix of the step 1 brief that reproduced that local file, and two lines on commit wording, removed, one reviewer description shortened. No definition, threshold, check or consequence changed |
| AUDIT.md | five phrasings: "in this session" (twice) and "the session rule" now refer to the step or the brief; "the session brief" now "the step 2 brief"; "the brief or the session instructions" now "the brief". Every cited commit hash replaced by the new hash of the same commit (11 lines, including the MT1 marker line, whose code commit now reads 682aa2c) |
| scripts/a1_gap_crosstab.py, tests/research/test_guard.py | one cited commit hash each, in a docstring |

Checks, from `git diff backup/pre-rewrite main` (the backup branch holds the old history, local only): the seven files above are the only files that differ; every file under audit/, figures/ and src/ is byte-identical. No result, table, figure, parameter or definition changed. The test suite passed on the rewritten main (69 passed). The guard reads the marker line from AUDIT.md at HEAD and still finds it.

Old and new hashes, paired in order (21 commits; subjects identical in every pair):

| old | new | date | subject |
|:--|:--|:--|:--|
| 6259f5f | 86143df | 2026-10-27 | Repository setup |
| a1fbde1 | 67b1fb3 | 2026-10-27 | Step 1 A0 and A1 |
| 5b7f354 | 1f0b65c | 2026-10-27 | Step 1: post hoc revisions after A1, gate thresholds |
| bbb9c05 | 690aa58 | 2026-10-27 | Step 1 A2 to A6 and gates G1 to G4 |
| 55edb30 | b835981 | 2026-10-28 | Step 1: revision 2 amended, G4 anchor procedure logged |
| 39bb95b | d1cb351 | 2026-10-28 | Step 1 revision 2: A7 to A9, gates at the anchors |
| 34b934f | 835875d | 2026-10-28 | Step 1: revision 3 of the contact rule, logged before the run |
| f5d4168 | 35babf9 | 2026-10-28 | Step 1 revision 3: re-run, DESIGN.md updated |
| 472bb7d | e808636 | 2026-10-28 | Step 2: DataBallPy pinned, modules |
| b58291d | df0bac7 | 2026-10-28 | Step 2 S1 and S2 |
| 992112d | a3ce7bc | 2026-10-28 | Step 2: S2 finding, MT1 additions |
| ad85d79 | a0923f9 | 2026-10-28 | Step 2 S3 to S5 |
| 5096022 | 682aa2c | 2026-10-29 | Step 2: MT1 script, rehearsed on the exploration matches |
| e4d9edf | 3a104ab | 2026-10-29 | MT1: main-test plan and marker logged |
| cc25f90 | 93072e5 | 2026-10-29 | MT1 run on the 15 test matches |
| c56f6c7 | 12bd6f2 | 2026-10-29 | Step 3a: public looseball API |
| 5b05927 | 4562c80 | 2026-10-29 | Step 3a: reproduce matches the MT1 record |
| 4637521 | b3703b8 | 2026-10-29 | Step 3b: Figures 1 and 2 |
| 5479e62 | aa8ebda | 2026-10-29 | Step 3c.0: static expectation with its own temperature |
| 70d453e | d5d0c56 | 2026-10-29 | Step 3b revision: Figure 1 redrawn |
| 18e56ed | aaabf90 | 2026-11-17 | Step 3c: README draft and its number sources |

### Documentation fixes (2026-11-17)

Documentation only; no result, definition or parameter changes.

| file | fix |
|:--|:--|
| DESIGN.md | "Step 2 decision 1" closed: the last-leg anchor, fixed in the MT1 plan |
| DESIGN.md | the MT1 definitions copied from the MT1 plan ("MT1, the main-test plan" above) into a new section; DESIGN.md said they would be frozen there when the marker was logged, and that was not done |
| DESIGN.md | the code of the frozen definitions named: the research version src/looseball_research/episodes.py (moved verbatim in 3a) and the public version src/looseball/episodes.py (equivalent on the exploration matches, 3a; reproduces MT1 byte for byte) |
| docs/step3_brief.md | README section 6: "1 to 7 matches per team" corrected to 1 to 5 (MT1 R9a: 1 to 5 test matches per team) |
| docs/step3_brief.md | 3h metres short: "Closed form under the shaw model" corrected: DataBallPy's "shaw" option has no turning term (t = reaction + distance from the drifted position / top speed), so 5 m/s times D is exact for any player under the frozen model |

### 3h. What would have been enough: definitions, decisions and checks, logged before any code touches match data (2026-11-17)

Report-only. 3h and the path check below are new code written and run after MT1, on the test matches only in the next step; neither changes any measure, verdict, parameter or the six MT1 files. The definitions are frozen in DESIGN.md, "3h. What would have been enough". Decisions by the project lead:

| # | question | decision |
|:--|:--|:--|
| 1 | set | the lost balls of the analysis set (gated). Ungated medians of metres_short and enough_degrees are one report-only line |
| 2 | winner time and deficit | t_w = the winning side's best dynamic reach time in the race; D = the losing side's best dynamic reach time minus t_w; deficit_s = D for every lost ball, negative when the loser was the dynamic favourite |
| 3 | best-placed player | the losing player with the smallest dynamic reach time; ties within 1e-9 s broken by distance to the pickup point, then column_id |
| 4 | metres short | 5 x D for balls with D > 0, exact under the frozen model (no turning term). Under the pleuler variant only: bisection on the displacement along the line from the drifted position to the pickup point |
| 5 | redirection | per losing player with speed above zero: d = distance to the pickup point, r = 0.7 x speed, R = 5 x (t_w - 0.7); a flip by rotation is possible when \|d - r\| <= R; the smallest rotation that flips is max(0, phi - theta), phi the angle between his velocity and the direction to the pickup point, theta = arccos((d^2 + r^2 - R^2) / (2 d r)) clipped to [-1, 1]. Players without a velocity cannot be redirected |
| 6 | enough change | the redirection with the smallest rotation if any player has one; otherwise the best-placed player moved by metres_short |
| 7 | enough_type | redirect, move, already_favourite (positioning verdict with D <= 0), no_player_in_race (empty losing side), blank for after-the-anchor verdicts |
| 8 | eligibility | goalkeepers and extrapolated players are eligible and flagged |
| 9 | output | clips.csv is not touched. New file clips_enough.csv (columns in DESIGN.md), written by looseball run and looseball reproduce. A committed record for it is added only after the test run |

Set in writing the definitions, before any data, and flagged for confirmation because the decisions do not state them:

| # | point | rule used |
|:--|:--|:--|
| a | precedence when two types apply | blank for after the anchor; then already_favourite (D <= 0); then no_player_in_race; then redirect; then move. A positioning ball with an empty losing side and D <= 0 (possible when the winner's best dynamic time exceeds the empty-team time of 3.7 s) is therefore already_favourite |
| b | ties between redirections | rotation within 1e-9 rad, then distance to the pickup point, then column_id, as for the best-placed player |
| c | a player exactly on the pickup point (d = 0) | cannot be redirected: rotation does not change his distance |
| d | redirection under the pleuler variant (V3 stability only) | the closed form assumes no turning term; under pleuler the smallest rotation is found by bisection on the rotation angle, since the pleuler reach time increases with the angle between velocity and the direction to the pickup point |
| e | the other V3 variants | the enough change is recomputed from that variant's reach table with its parameters (reaction 0.35 s gives r = 0.35 x speed and R = 5 x (t_w - 0.35)) |
| f | file format | clips_enough.csv rows and order as clips.csv (sorted by match and anchor frame); floats to four decimals; blank where a value does not apply |

Checks, report-only, run on the rehearsal set first and on the test set in the next step. All on lost balls of the stated set; intervals, where given, 2000 bootstrap replicates resampling episodes within match, seed 0.

| # | check | set | statistic |
|:--|:--|:--|:--|
| C1 | counts by enough_type | analysis set | counts by enough_type, by verdict and by trigger |
| C2 | metres short | balls with D > 0, positioning and reading separately | p10, p50, p90 of metres_short |
| C3 | rotation | redirect balls, positioning and reading separately | p10, p50, p90 of enough_degrees |
| C4 | reading fixed by one redirection | reading verdicts | share with enough_type redirect |
| C5 | flags | balls with an enough player (redirect or move) | share with the enough player extrapolated; share with the enough player a goalkeeper |
| C6 | stability under each V3 variant | positioning and reading balls whose verdict is unchanged under that variant | share left out (verdict changed) reported; share with enough_type and enough_player both unchanged (a player missing under the variant counts as changed); Spearman correlation of the magnitude within each type (redirect: enough_degrees; move: enough_metres) over balls with that type in both |
| C7 | ungated line | ungated lost balls (D7 off), positioning and reading | medians of metres_short and enough_degrees |

Reading rule, fixed now: if the median metres_short is above 10 m for positioning or for reading, the model is saying something other than "nearly there"; that is reported and not adjusted.

### Path check: procedure, logged before it runs (2026-11-17)

Report-only, new. Reason, as given by the project lead: reach times are measured to the pickup point, which is where the winner took the ball, so the loser may look worse placed by construction.

| item | rule |
|:--|:--|
| set | lost balls of the analysis set that are ground episodes (DESIGN.md: no window frame with the ball detected and ball z above 1.8 m) |
| frames | every frame f from the anchor to the pickup frame inclusive with the ball detected and its position present; target = the ball position on f |
| players | anchor-frame positions and smoothed velocities (window 5, order 2; no velocity gives velocity zero, as in the race) of all rostered players of each team on the anchor frame, not only the 15 m race |
| model | the frozen reach model (DataBallPy shaw, reaction 0.7 s, top speed 5 m/s) |
| reach | a team reaches f when its best reach time to the target on f is at most (f - anchor) / 10 + 0.3 s (the S2 tolerance); also reported with tolerance 0 |
| path favourite | the team with the earlier first reachable frame; equal frames are a tie; if neither team reaches any frame the ball is "unreached" and counted |
| versions | static (velocity zero) and dynamic |
| frozen favourite | the team with p_dynamic above 0.5 (p_static for the static comparison); 0.5 is no favourite |
| report P1 | share of balls whose dynamic path favourite is the frozen dynamic favourite, with the counts of ties, unreached balls and disagreements |
| report P2 | cross-tab of the frozen verdict by the loser's static path status (loser is path favourite, winner is, tie, unreached) |
| report P3 | share of positioning verdicts where the loser is the static path favourite (ties and unreached count as not), with its interval |

Consequence, fixed now: the P3 number goes into the README limitations whatever it is. No verdict or headline changes.

### 3h build: code, tests and the equivalence check (2026-11-17)

| item | value |
|:--|:--|
| src/looseball/enough.py | the 3h definitions (DESIGN.md): deficit, best-placed player, metres short (closed form; bisection under pleuler), redirection (closed form; bisection under pleuler), enough change and type, flags |
| src/looseball/pathcheck.py | the path check as logged: ground flag, first reachable frame per team, path favourite, static and dynamic, tolerances 0.3 s and 0 |
| src/looseball/export_clips.py | export_clips_enough writes clips_enough.csv; export_clips and its six columns unchanged |
| src/looseball/reproduce.py | compute() also returns the per-player reach table and each V3 variant's reach table; enough_tables() and write_enough(); reproduce() writes clips_enough.csv after the MT1 files. write() is unchanged |
| src/looseball/cli.py | looseball run also writes clips_enough.csv |
| tests | 16 new on synthetic data: moving by 5 x D gives t_w; the rotation formula against a brute-force scan over angles (including a 3.5 m drift on a 2 m distance) and against the bisection; no rotation possible; pleuler bisections reach t_w; smallest rotation and its tie rule; best-placed ties on distance then column_id; empty losing side; D <= 0; after the anchor; the new file's columns, rows and order equal clips.csv on its six columns; clips.csv bytes unchanged; looseball run writes both; check_reproduce passes with the extra file and fails when clips.csv changes; path check favourite rule, loser first on the path, unreached, tie, aerial, undetected frames. Full suite: 85 passed |

Equivalence check, exploration matches only (the full `looseball reproduce` reads the test matches and is not run in this step). The MT1 compute and write were run on the five exploration matches with the code before this build (commit fc816df) and after it; all seven outputs (clips.csv, episodes.csv, episodes_ungated.csv, gates.json, team_shares.csv, team_verdicts.csv, report.md) are byte-identical, 326 analysis-set balls. Five of them are also byte-identical to the committed audit/mt1_exploration record; gates.json differs from that record as it did before the build (the public writer labels the set "test" and applies the 10-of-15 match rule to 5 matches). `looseball run --match 1886347` writes the same clips_enough.csv rows as the reproduce path (62 balls). Run time of the exploration compute: 96 s before, 102 s after (with the 3h tables), peak memory 0.7 GB.


### 3h rehearsal on the exploration matches (2026-11-17)

A bug check on the five exploration matches (326 lost balls in the analysis set), not a test; run after the 3h definitions, checks and the path check were logged (commit fc816df) and the code was built (commit 3365a0d). No test match was read. Script: scripts/s3h.py exploration; outputs audit/s3h_exploration/ (report.md, clips_enough.csv, enough_all_sets.csv, pathcheck.csv) and four figures in audit/figures/. Every table below is report.md as written by the script.

3h rehearsal on 5 matches: 326 lost balls in the analysis set.

C1. Counts by enough_type, by verdict and by trigger:

| verdict          |   redirect |   move |   already_favourite |   no_player_in_race |   blank (after the anchor) |   all |
|:-----------------|-----------:|-------:|--------------------:|--------------------:|---------------------------:|------:|
| after the anchor |          0 |      0 |                   0 |                   0 |                         53 |    53 |
| positioning      |         52 |    141 |                  19 |                  27 |                          0 |   239 |
| reading          |         24 |     10 |                   0 |                   0 |                          0 |    34 |
| all              |         76 |    151 |                  19 |                  27 |                         53 |   326 |

| trigger   |   redirect |   move |   already_favourite |   no_player_in_race |   blank (after the anchor) |   all |
|:----------|-----------:|-------:|--------------------:|--------------------:|---------------------------:|------:|
| T1        |          2 |      2 |                   0 |                   4 |                          3 |    11 |
| T2        |         22 |     47 |                   4 |                  12 |                         19 |   104 |
| T3        |          6 |      9 |                   1 |                   2 |                          4 |    22 |
| T4        |         23 |     53 |                   4 |                   3 |                          7 |    90 |
| T5        |          1 |      2 |                   0 |                   2 |                          2 |     7 |
| T6        |          0 |      2 |                   0 |                   1 |                          0 |     3 |
| T7        |         22 |     36 |                  10 |                   3 |                         18 |    89 |
| all       |         76 |    151 |                  19 |                  27 |                         53 |   326 |

C2 and C3. metres_short (balls with D > 0) and enough_degrees (redirect balls), by verdict:

| quantity                | verdict     |   n |   p10 |   p50 |    p90 |
|:------------------------|:------------|----:|------:|------:|-------:|
| metres_short, m         | positioning | 220 |  0.81 |  3.09 |   8.95 |
| enough_degrees          | positioning |  52 | 14.15 | 51.17 | 105.62 |
| enough_metres (move), m | positioning | 141 |  1.15 |  3.34 |   8.01 |
| metres_short, m         | reading     |  34 |  0.10 |  0.81 |   2.88 |
| enough_degrees          | reading     |  24 |  3.08 | 41.44 |  95.10 |
| enough_metres (move), m | reading     |  10 |  0.42 |  0.81 |   2.92 |

Reading rule (median metres_short above 10 m): positioning 3.09 m, reading 0.81 m; neither is above 10 m.

C4. Reading verdicts fixed by one redirection: 24 of 34 (0.706).

C5. Of 227 balls with an enough player: extrapolated at the anchor 5 (0.022); goalkeeper 0 (0.000).

C6. Stability under each V3 variant (positioning and reading balls whose verdict is unchanged):

| variant                                  |   balls |   left out (verdict changed) |   kept |   type and player unchanged |   redirect: n both |   redirect: Spearman |   move: n both |   move: Spearman |
|:-----------------------------------------|--------:|-----------------------------:|-------:|----------------------------:|-------------------:|---------------------:|---------------:|-----------------:|
| anchor 0.2 s later                       |     273 |                        0.059 |    257 |                       0.829 |                 47 |                0.925 |            142 |            0.960 |
| growing radius max(radius, 8 m/s x lead) |     273 |                        0.000 |    273 |                       0.967 |                 76 |                1.000 |            151 |            1.000 |
| pleuler turning penalty                  |     273 |                        0.033 |    264 |                       0.542 |                 57 |                0.624 |             77 |            0.935 |
| smoothing window 7                       |     273 |                        0.000 |    273 |                       1.000 |                 76 |                0.999 |            151 |            1.000 |
| extrapolated players dropped             |     273 |                        0.018 |    268 |                       0.978 |                 72 |                1.000 |            150 |            0.998 |
| reaction time 0.35 s                     |     273 |                        0.055 |    258 |                       0.740 |                 32 |                0.338 |            142 |            0.939 |

C7. Ungated lost balls (D7 off), report-only line:

| verdict     |   ungated lost balls |   median metres_short |   median enough_degrees |
|:------------|---------------------:|----------------------:|------------------------:|
| positioning |                  296 |                  3.40 |                   50.79 |
| reading     |                   43 |                  0.78 |                   43.04 |

Diagnostics: precedence rule (a) (D <= 0 with an empty losing side, typed already_favourite) applied to 0 balls; the best-placed tie rule decided 0 balls and the rotation tie rule 0.

Bug check: after the enough change the player's reach time equals t_w for all 227 redirect and move balls (largest difference 1.55e-15 s).

Path check on 326 lost balls: 179 ground, 147 aerial (left out). Ball-detected path frames per ground ball: median 14.

P1, tolerance 0.3 s. Dynamic path favourite against the frozen dynamic favourite (share agree 0.598 of 179):

| category             |   balls |
|:---------------------|--------:|
| agree                |     107 |
| disagree             |      25 |
| path: tie            |       7 |
| path: unreached      |      38 |
| frozen: no favourite |       2 |

P2, tolerance 0.3 s. Frozen verdict by the loser's static path status:

| verdict          |   loser is path favourite |   tie |   unreached |   winner is |   all |
|:-----------------|--------------------------:|------:|------------:|------------:|------:|
| after the anchor |                        10 |     2 |          12 |           1 |    25 |
| positioning      |                        13 |     2 |          50 |          69 |   134 |
| reading          |                         8 |     1 |          11 |           0 |    20 |
| all              |                        31 |     5 |          73 |          70 |   179 |

P3, tolerance 0.3 s. Positioning verdicts where the loser is the static path favourite: 13 of 134, 0.097 (95% interval 0.052 to 0.149).

P1, tolerance 0 s. Dynamic path favourite against the frozen dynamic favourite (share agree 0.374 of 179):

| category             |   balls |
|:---------------------|--------:|
| agree                |      67 |
| disagree             |      10 |
| path: tie            |       4 |
| path: unreached      |      96 |
| frozen: no favourite |       2 |

P2, tolerance 0 s. Frozen verdict by the loser's static path status:

| verdict          |   loser is path favourite |   tie |   unreached |   winner is |   all |
|:-----------------|--------------------------:|------:|------------:|------------:|------:|
| after the anchor |                         8 |     1 |          15 |           1 |    25 |
| positioning      |                         7 |     1 |          83 |          43 |   134 |
| reading          |                         3 |     0 |          16 |           1 |    20 |
| all              |                        18 |     2 |         114 |          45 |   179 |

P3, tolerance 0 s. Positioning verdicts where the loser is the static path favourite: 7 of 134, 0.052 (95% interval 0.022 to 0.090).

Figures: seed 20261117 (numpy default_rng), two drawn without replacement from the 76 redirect balls, then two from the 151 move balls, each pool sorted by match and seq_i.

|   figure |   match_id |   seq_i | trigger   | verdict     | enough_type   | enough_player   |   magnitude | file                                                                   |
|---------:|-----------:|--------:|:----------|:------------|:--------------|:----------------|------------:|:-----------------------------------------------------------------------|
|        1 |    1959846 |     340 | T3        | positioning | redirect      | home_10         |       25.95 | audit/figures/s3h_exploration_seed20261117_01_redirect_1959846_340.png |
|        2 |    1996436 |     329 | T7        | positioning | redirect      | home_6          |       86.20 | audit/figures/s3h_exploration_seed20261117_02_redirect_1996436_329.png |
|        3 |    1996436 |     618 | T3        | positioning | move          | home_27         |        7.72 | audit/figures/s3h_exploration_seed20261117_03_move_1996436_618.png     |
|        4 |    1959846 |     114 | T7        | positioning | move          | home_3          |        2.70 | audit/figures/s3h_exploration_seed20261117_04_move_1959846_114.png     |

Ground flag against step 1: the path check's ground flag agrees with the aerial column of audit/loose_episodes_exploration.csv on all 326 balls (179 ground, 147 aerial; step 1 A5: 45% of main pairs aerial).

Figure reading (all four inspected). In each figure the enough player is ringed; after the change his drifted position (black square) lies on the dotted circle of radius 5 x (t_w - 0.7) around the pickup point, as the definition requires. Figures 1 and 2: the rotation is partial, not a full turn to the pickup point (figure 1: 26 degrees for a player already moving near the pickup point; figure 2: 86 degrees for a slow player whose 0.7 s drift is short). Figures 3 and 4: the displacement runs parallel to the line from the recorded drifted position (orange square) to the pickup point, by metres_short. One rendering bug fixed before the final run: players outside the square panel had their velocity arrows drawn without a marker (the panel filter used a circle); the tables were identical before and after the fix.

Findings from the rehearsal, reported and not acted on (no definition changed):

| # | finding | evidence |
|:--|:--|:--|
| 1 | redirect is tried before move, so a positioning verdict often gets a movement change as its enough change | 52 of 239 positioning balls are typed redirect (median 51 degrees) |
| 2 | the redirection acts only through the 0.7 s reaction drift (r = 0.7 x speed), so its type and size depend strongly on the reaction parameter and on pleuler | C6: type and player unchanged 0.740 under reaction 0.35 s and 0.542 under pleuler (0.83 to 1.00 for the other variants); redirect Spearman 0.338 (n 32) under reaction 0.35 s and 0.624 (n 57) under pleuler |
| 3 | metres_short is defined for every ball with D > 0, including the 27 no_player_in_race balls, where there is no player to move; C2 includes them | C1 and C2 |
| 4 | 19 of 239 positioning balls (7.9%) are already_favourite: the loser was the dynamic favourite (reading term negative) | C1 |
| 5 | the path check covers ground balls only, 179 of 326 (55%) | path check header |
| 6 | P3 counts unreached balls as "not loser favourite"; at 0.3 s, 50 of the 134 positioning balls are unreached by both teams (83 at 0 s). Among positioning balls with a path favourite, the loser is it in 13 of 82 (0.159), read off P2; this is not a logged statistic | P2 and P3 |
| 7 | P1 compares a path favourite from all players on the frame with a frozen favourite from the 15 m race | P1: 25 disagreements at 0.3 s |
| 8 | the goalkeeper and extrapolated flags rarely fire | C5: goalkeeper 0 of 227, extrapolated 5 of 227 |
| 9 | precedence rule (a) and both tie rules were never needed on these matches | diagnostics line |

Reading rule: the median metres_short is 3.09 m for positioning and 0.81 m for reading, neither above 10 m.

### 3h post hoc revisions after the exploration rehearsal (2026-11-18)

Decided by the project lead after the 3h rehearsal on the exploration matches and before any test match was read by 3h code. Post hoc. Reasons as given. Logged and committed before any code runs on match data. No measure, verdict or frozen parameter changes; the six MT1 files are not affected. DESIGN.md, "3h. What would have been enough", holds the revised definitions.

| # | revision | reason, as given |
|:--|:--|:--|
| R1 | the enough change is the move only: the best-placed losing player started metres_short closer. enough_type values: move, already_favourite, no_player_in_race, or blank. Redirection (C3, C4 and its C6 rows) stays as report-only tables in the audit report and is in no export | redirection acts only through the 0.7 s drift and was unstable in rehearsal (Spearman 0.338 under reaction 0.35 s; type and player unchanged 0.542 under pleuler), and it put a movement change on 52 balls with a positioning verdict |
| R2 | metres_short is blank for no_player_in_race, and C2 leaves those balls out | there is no player to move (rehearsal finding 3) |
| R3 | clips_enough.csv columns: match_id, seq_i, period, clock, frame, team, verdict, deficit_s, metres_short, enough_type, enough_player, enough_player_gk, enough_player_extrapolated | follows from R1: enough_metres would repeat metres_short and enough_degrees no longer applies |
| R4 | path check additions. P3b: the P3 share among positioning verdicts that have a path favourite (ties and unreached left out), with the same bootstrap interval. P1b: P1 with the frozen favourite recomputed at the pickup point from all players on the frame, so both sides use the same players. Fixed now: the README limitation will cite P3b at 0.3 s with its denominator and say it covers ground balls only; P3 is reported beside it in AUDIT.md | rehearsal findings 6 and 7: P3 counted unreached balls as "loser not favourite", and P1 compared all players with the 15 m race |
| R5 | wording: moving by 5 x D makes the race level under the model. Reports and labels say "level", never "would have won" | at D = 0 the expectation is exactly one half |

Checks after the revision, otherwise as logged on 2026-11-17:

| # | check | change |
|:--|:--|:--|
| C1 | counts by enough_type, by verdict and by trigger | the revised types |
| C2 | p10, p50, p90 of metres_short, positioning and reading separately | no_player_in_race balls left out (blank) |
| C3, C4 | rotation of the smallest redirection; share of reading verdicts that one redirection makes level | report-only, from the redirection table, not the enough change |
| C5 | enough player extrapolated; goalkeeper | over move balls |
| C6 | stability under each V3 variant on balls whose verdict is unchanged | enough change: share with type and player unchanged (a missing player counts as changed), Spearman of metres_short over balls typed move in both. Redirection rows, report-only: Spearman of the smallest rotation over balls with a redirection in both |
| C7 | ungated medians | median metres_short; median rotation of the smallest redirection (report-only) |
| P1b, P3b | as R4 | new |

Descriptor added to the path-check output, for the animation draw logged later: ball path length from the release to the pickup, as in the Figure 1 constraint (AUDIT.md, 3b revision).


### 3h rehearsal after the revisions, exploration matches (2026-11-18)

Bug check with the revised definitions (R1 to R5), on the five exploration matches (326 lost balls); no test match read. Script: `python scripts/s3h.py exploration audit/s3h_exploration_revised` (the first rehearsal's outputs stay in audit/s3h_exploration/). The script's figure code was removed with R1 (it drew redirections); the first rehearsal's four figures stay in audit/figures/. Code changes since the first rehearsal: enough.py returns the move-only enough change and a separate report-only redirection table (redirection(), in no export); clips_enough.csv has the R3 columns; the path check adds the pickup-point favourite from all players (P1b) and the ball path length (descriptor for the animation draw). Tests updated: 86 passed. Every table below is report.md as written by the script.

3h on 5 matches: 326 lost balls in the analysis set.

C1. Counts by enough_type, by verdict and by trigger:

| verdict          |   move |   already_favourite |   no_player_in_race |   blank (after the anchor) |   all |
|:-----------------|-------:|--------------------:|--------------------:|---------------------------:|------:|
| after the anchor |      0 |                   0 |                   0 |                         53 |    53 |
| positioning      |    193 |                  19 |                  27 |                          0 |   239 |
| reading          |     34 |                   0 |                   0 |                          0 |    34 |
| all              |    227 |                  19 |                  27 |                         53 |   326 |

| trigger   |   move |   already_favourite |   no_player_in_race |   blank (after the anchor) |   all |
|:----------|-------:|--------------------:|--------------------:|---------------------------:|------:|
| T1        |      4 |                   0 |                   4 |                          3 |    11 |
| T2        |     69 |                   4 |                  12 |                         19 |   104 |
| T3        |     15 |                   1 |                   2 |                          4 |    22 |
| T4        |     76 |                   4 |                   3 |                          7 |    90 |
| T5        |      3 |                   0 |                   2 |                          2 |     7 |
| T6        |      2 |                   0 |                   1 |                          0 |     3 |
| T7        |     58 |                  10 |                   3 |                         18 |    89 |
| all       |    227 |                  19 |                  27 |                         53 |   326 |

C2 and C3. metres_short (move balls: D > 0 with a losing player in the race) and, report-only, the rotation of the smallest redirection (balls where one exists), by verdict:

| quantity                       | verdict     |   n |   p10 |   p50 |    p90 |
|:-------------------------------|:------------|----:|------:|------:|-------:|
| metres_short, m                | positioning | 193 |  0.74 |  2.61 |   7.53 |
| redirect_degrees (report-only) | positioning |  52 | 14.15 | 51.17 | 105.62 |
| metres_short, m                | reading     |  34 |  0.10 |  0.81 |   2.88 |
| redirect_degrees (report-only) | reading     |  24 |  3.08 | 41.44 |  95.10 |

Reading rule (median metres_short above 10 m): positioning 2.61 m, reading 0.81 m; neither is above 10 m.

C4 (report-only). Reading verdicts where one redirection makes the race level: 24 of 34 (0.706).

C5. Of 227 move balls: enough player extrapolated at the anchor 5 (0.022); goalkeeper 0 (0.000).

C6. Stability under each V3 variant (positioning and reading balls whose verdict is unchanged):

| variant                                  |   balls |   left out (verdict changed) |   kept |   type and player unchanged |   move: n both |   move: Spearman metres_short |   redirect (report-only): n both |   redirect: Spearman degrees |
|:-----------------------------------------|--------:|-----------------------------:|-------:|----------------------------:|---------------:|------------------------------:|---------------------------------:|-----------------------------:|
| anchor 0.2 s later                       |     273 |                        0.059 |    257 |                       0.883 |            210 |                         0.949 |                               47 |                        0.925 |
| growing radius max(radius, 8 m/s x lead) |     273 |                        0.000 |    273 |                       0.967 |            227 |                         1.000 |                               76 |                        1.000 |
| pleuler turning penalty                  |     273 |                        0.033 |    264 |                       0.659 |            199 |                         0.759 |                               57 |                        0.624 |
| smoothing window 7                       |     273 |                        0.000 |    273 |                       1.000 |            227 |                         1.000 |                               76 |                        0.999 |
| extrapolated players dropped             |     273 |                        0.018 |    268 |                       0.978 |            222 |                         0.999 |                               72 |                        1.000 |
| reaction time 0.35 s                     |     273 |                        0.055 |    258 |                       0.868 |            210 |                         0.882 |                               32 |                        0.338 |

C7. Ungated lost balls (D7 off), report-only line:

| verdict     |   ungated lost balls |   median metres_short |   median redirect_degrees (report-only) |
|:------------|---------------------:|----------------------:|----------------------------------------:|
| positioning |                  296 |                  2.96 |                                   50.79 |
| reading     |                   43 |                  0.78 |                                   43.04 |

Diagnostics: the precedence rule (D <= 0 with an empty losing side, typed already_favourite) applied to 0 balls; the best-placed tie rule decided 0 balls.

Bug check: after the move the best-placed player's reach time equals t_w, so the race is level, for all 227 move balls (largest difference 1.22e-15 s).

Path check on 326 lost balls: 179 ground, 147 aerial (left out). Ball-detected path frames per ground ball: median 14.

P1, tolerance 0.3 s. Dynamic path favourite against the frozen dynamic favourite (15 m race) (share agree 0.598 of 179):

| category                   |   balls |
|:---------------------------|--------:|
| agree                      |     107 |
| disagree                   |      25 |
| path: tie                  |       7 |
| path: unreached            |      38 |
| no favourite at the pickup |       2 |

P1b, tolerance 0.3 s. Dynamic path favourite against the favourite at the pickup point from all players (share agree 0.598 of 179):

| category                   |   balls |
|:---------------------------|--------:|
| agree                      |     107 |
| disagree                   |      25 |
| path: tie                  |       7 |
| path: unreached            |      40 |
| no favourite at the pickup |       0 |

P2, tolerance 0.3 s. Frozen verdict by the loser's static path status:

| verdict          |   loser is path favourite |   tie |   unreached |   winner is |   all |
|:-----------------|--------------------------:|------:|------------:|------------:|------:|
| after the anchor |                        10 |     2 |          12 |           1 |    25 |
| positioning      |                        13 |     2 |          50 |          69 |   134 |
| reading          |                         8 |     1 |          11 |           0 |    20 |
| all              |                        31 |     5 |          73 |          70 |   179 |

P3, tolerance 0.3 s. Positioning verdicts where the loser is the static path favourite: 13 of 134, 0.097 (95% interval 0.052 to 0.149).

P3b, tolerance 0.3 s. Positioning verdicts where the loser is the static path favourite among those with a path favourite (ties and unreached left out): 13 of 82, 0.159 (95% interval 0.085 to 0.238).

P1, tolerance 0 s. Dynamic path favourite against the frozen dynamic favourite (15 m race) (share agree 0.374 of 179):

| category                   |   balls |
|:---------------------------|--------:|
| agree                      |      67 |
| disagree                   |      10 |
| path: tie                  |       4 |
| path: unreached            |      96 |
| no favourite at the pickup |       2 |

P1b, tolerance 0 s. Dynamic path favourite against the favourite at the pickup point from all players (share agree 0.374 of 179):

| category                   |   balls |
|:---------------------------|--------:|
| agree                      |      67 |
| disagree                   |      10 |
| path: tie                  |       4 |
| path: unreached            |      98 |
| no favourite at the pickup |       0 |

P2, tolerance 0 s. Frozen verdict by the loser's static path status:

| verdict          |   loser is path favourite |   tie |   unreached |   winner is |   all |
|:-----------------|--------------------------:|------:|------------:|------------:|------:|
| after the anchor |                         8 |     1 |          15 |           1 |    25 |
| positioning      |                         7 |     1 |          83 |          43 |   134 |
| reading          |                         3 |     0 |          16 |           1 |    20 |
| all              |                        18 |     2 |         114 |          45 |   179 |

P3, tolerance 0 s. Positioning verdicts where the loser is the static path favourite: 7 of 134, 0.052 (95% interval 0.022 to 0.090).

P3b, tolerance 0 s. Positioning verdicts where the loser is the static path favourite among those with a path favourite (ties and unreached left out): 7 of 50, 0.140 (95% interval 0.056 to 0.238).

Reading. The tables that do not depend on R1 and R2 reproduce the first rehearsal exactly (redirection rotations, C4, C7 redirect medians, P1 to P3). Under R1 every positioning or reading ball with a losing player in the race and D > 0 is a move ball (227); R2 removes the 27 no_player_in_race balls from C2, so the positioning median metres_short falls from 3.09 m to 2.61 m. The move is the least stable under pleuler (type and player unchanged 0.659, Spearman 0.759) and reaction 0.35 s (0.868, 0.882). P1b differs from P1 only in the 2 balls with no favourite in the race (equal empty-team times), which become unreached: using all players instead of the 15 m race changes no favourite at the pickup point on these matches.


### 3h on the test matches (2026-11-18)

Run after the revisions were committed (e46bae9) and the revised code was rehearsed (afbfe77). Report-only; nothing was changed after the results were seen.

Reproduce first. `looseball reproduce --data data/opendata --out OUT` with the 3h code in place (6 min 14 s wall time, 861 MB peak memory; Python 3.12.3, numpy 2.2.6, pandas 3.1.0, DataBallPy 3f9de8d), then `scripts/check_reproduce.py OUT`: the six MT1 files, report.md (215 lines against AUDIT.md), static_temperature.md and the four figure files (figure1_caption.txt, figure1_constrained_seed20261029.png, figure2_A.png, figure2_B.png) are all identical. The MT1 record is unchanged by the 3h code.

The 3h run, once: `python scripts/s3h.py test` (7 min 7 s, 876 MB), outputs in audit/s3h_test/ (report.md, clips_enough.csv, enough_all_sets.csv, pathcheck.csv). Its clips_enough.csv is byte-identical to the one looseball reproduce wrote. Every table below is report.md as written.

3h on 15 matches: 1003 lost balls in the analysis set.

C1. Counts by enough_type, by verdict and by trigger:

| verdict          |   move |   already_favourite |   no_player_in_race |   blank (after the anchor) |   all |
|:-----------------|-------:|--------------------:|--------------------:|---------------------------:|------:|
| after the anchor |      0 |                   0 |                   0 |                        176 |   176 |
| positioning      |    557 |                  50 |                  85 |                          0 |   692 |
| reading          |    135 |                   0 |                   0 |                          0 |   135 |
| all              |    692 |                  50 |                  85 |                        176 |  1003 |

| trigger   |   move |   already_favourite |   no_player_in_race |   blank (after the anchor) |   all |
|:----------|-------:|--------------------:|--------------------:|---------------------------:|------:|
| T1        |     13 |                   0 |                  15 |                          2 |    30 |
| T2        |    169 |                  16 |                  30 |                         66 |   281 |
| T3        |     36 |                   0 |                   0 |                          9 |    45 |
| T4        |    261 |                  16 |                  16 |                         34 |   327 |
| T5        |     11 |                   0 |                   2 |                          0 |    13 |
| T6        |      4 |                   0 |                   1 |                          2 |     7 |
| T7        |    198 |                  18 |                  21 |                         63 |   300 |
| all       |    692 |                  50 |                  85 |                        176 |  1003 |

C2 and C3. metres_short (move balls: D > 0 with a losing player in the race) and, report-only, the rotation of the smallest redirection (balls where one exists), by verdict:

| quantity                       | verdict     |   n |   p10 |   p50 |    p90 |
|:-------------------------------|:------------|----:|------:|------:|-------:|
| metres_short, m                | positioning | 557 |  0.75 |  2.51 |   7.06 |
| redirect_degrees (report-only) | positioning | 127 | 11.78 | 50.39 | 124.77 |
| metres_short, m                | reading     | 135 |  0.23 |  1.08 |   2.99 |
| redirect_degrees (report-only) | reading     | 106 |  7.57 | 43.17 | 103.05 |

Reading rule (median metres_short above 10 m): positioning 2.51 m, reading 1.08 m; neither is above 10 m.

C4 (report-only). Reading verdicts where one redirection makes the race level: 106 of 135 (0.785).

C5. Of 692 move balls: enough player extrapolated at the anchor 15 (0.022); goalkeeper 1 (0.001).

C6. Stability under each V3 variant (positioning and reading balls whose verdict is unchanged):

| variant                                  |   balls |   left out (verdict changed) |   kept |   type and player unchanged |   move: n both |   move: Spearman metres_short |   redirect (report-only): n both |   redirect: Spearman degrees |
|:-----------------------------------------|--------:|-----------------------------:|-------:|----------------------------:|---------------:|------------------------------:|---------------------------------:|-----------------------------:|
| anchor 0.2 s later                       |     827 |                        0.068 |    771 |                       0.909 |            632 |                         0.941 |                              144 |                        0.801 |
| growing radius max(radius, 8 m/s x lead) |     827 |                        0.000 |    827 |                       0.970 |            692 |                         1.000 |                              233 |                        1.000 |
| pleuler turning penalty                  |     827 |                        0.022 |    809 |                       0.637 |            610 |                         0.661 |                              200 |                        0.511 |
| smoothing window 7                       |     827 |                        0.002 |    825 |                       0.995 |            690 |                         1.000 |                              229 |                        0.999 |
| extrapolated players dropped             |     827 |                        0.004 |    824 |                       0.981 |            688 |                         0.981 |                              228 |                        1.000 |
| reaction time 0.35 s                     |     827 |                        0.073 |    767 |                       0.846 |            629 |                         0.861 |                              113 |                        0.599 |

C7. Ungated lost balls (D7 off), report-only line:

| verdict     |   ungated lost balls |   median metres_short |   median redirect_degrees (report-only) |
|:------------|---------------------:|----------------------:|----------------------------------------:|
| positioning |                  976 |                  2.73 |                                   48.38 |
| reading     |                  177 |                  1.11 |                                   41.76 |

Diagnostics: the precedence rule (D <= 0 with an empty losing side, typed already_favourite) applied to 0 balls; the best-placed tie rule decided 0 balls.

Bug check: after the move the best-placed player's reach time equals t_w, so the race is level, for all 692 move balls (largest difference 2.22e-15 s).

Path check on 1003 lost balls: 554 ground, 449 aerial (left out). Ball-detected path frames per ground ball: median 13.

P1, tolerance 0.3 s. Dynamic path favourite against the frozen dynamic favourite (15 m race) (share agree 0.625 of 554):

| category                   |   balls |
|:---------------------------|--------:|
| agree                      |     346 |
| disagree                   |      58 |
| path: tie                  |      26 |
| path: unreached            |     113 |
| no favourite at the pickup |      11 |

P1b, tolerance 0.3 s. Dynamic path favourite against the favourite at the pickup point from all players (share agree 0.632 of 554):

| category                   |   balls |
|:---------------------------|--------:|
| agree                      |     350 |
| disagree                   |      58 |
| path: tie                  |      26 |
| path: unreached            |     120 |
| no favourite at the pickup |       0 |

P2, tolerance 0.3 s. Frozen verdict by the loser's static path status:

| verdict          |   loser is path favourite |   tie |   unreached |   winner is |   all |
|:-----------------|--------------------------:|------:|------------:|------------:|------:|
| after the anchor |                        34 |     5 |          28 |           8 |    75 |
| positioning      |                        25 |    20 |         162 |         186 |   393 |
| reading          |                        39 |     1 |          40 |           6 |    86 |
| all              |                        98 |    26 |         230 |         200 |   554 |

P3, tolerance 0.3 s. Positioning verdicts where the loser is the static path favourite: 25 of 393, 0.064 (95% interval 0.041 to 0.087).

P3b, tolerance 0.3 s. Positioning verdicts where the loser is the static path favourite among those with a path favourite (ties and unreached left out): 25 of 211, 0.118 (95% interval 0.075 to 0.162).

P1, tolerance 0 s. Dynamic path favourite against the frozen dynamic favourite (15 m race) (share agree 0.375 of 554):

| category                   |   balls |
|:---------------------------|--------:|
| agree                      |     208 |
| disagree                   |      23 |
| path: tie                  |      18 |
| path: unreached            |     294 |
| no favourite at the pickup |      11 |

P1b, tolerance 0 s. Dynamic path favourite against the favourite at the pickup point from all players (share agree 0.381 of 554):

| category                   |   balls |
|:---------------------------|--------:|
| agree                      |     211 |
| disagree                   |      23 |
| path: tie                  |      18 |
| path: unreached            |     302 |
| no favourite at the pickup |       0 |

P2, tolerance 0 s. Frozen verdict by the loser's static path status:

| verdict          |   loser is path favourite |   tie |   unreached |   winner is |   all |
|:-----------------|--------------------------:|------:|------------:|------------:|------:|
| after the anchor |                        22 |     2 |          41 |          10 |    75 |
| positioning      |                        17 |    10 |         249 |         117 |   393 |
| reading          |                        20 |     3 |          61 |           2 |    86 |
| all              |                        59 |    15 |         351 |         129 |   554 |

P3, tolerance 0 s. Positioning verdicts where the loser is the static path favourite: 17 of 393, 0.043 (95% interval 0.025 to 0.064).

P3b, tolerance 0 s. Positioning verdicts where the loser is the static path favourite among those with a path favourite (ties and unreached left out): 17 of 134, 0.127 (95% interval 0.074 to 0.181).

Checker addition (logged as an addition, after the record existed): scripts/check_reproduce.py also compares OUT/clips_enough.csv with audit/s3h_test/clips_enough.csv, and, when OUT/s3h exists (written by `python scripts/s3h.py test OUT/s3h`), OUT/s3h/report.md with audit/s3h_test/report.md. Run on the reproduce output above: all identical. Tests: 89 passed.

Reading, report-only. The verdict counts agree with MT1 R1 (692 positioning, 135 reading, 176 after the anchor). Of 692 positioning balls, 557 have a move, 50 are already_favourite (7.2%) and 85 have nobody of the losing team in the 15 m race (12.3%; 15 of the 30 gated clearances). The median metres_short is 2.51 m for positioning and 1.08 m for reading, below the 10 m line. The enough player is extrapolated in 15 of 692 move balls and a goalkeeper in 1. The move is least stable under the pleuler variant (type and player unchanged 0.637, Spearman 0.661) and next under reaction 0.35 s (0.846, 0.861); 0.909 to 0.995 under the others. The path check covers 554 ground balls of 1003; at 0.3 s, P3 is 25 of 393 positioning verdicts (0.064, 0.041 to 0.087) and P3b, the number the README limitation will cite, 25 of 211 positioning verdicts with a path favourite (0.118, 0.075 to 0.162); 162 of the 393 are reached by neither team within the tolerance. P1 and P1b agree on 346 and 350 of 554 balls; the 11 balls with no favourite in the race (equal empty-team times) have one under P1b.

### 3h animation: draw rule, logged before the draw (2026-11-18)

Command: `looseball animate --data PATH --match ID --episode SEQ_I --out FILE [--hold SECONDS]` (src/looseball/animate.py). Not part of looseball reproduce and not byte-checked. Specification as given by the project lead: part one "as recorded" from the release frame to the pickup frame, each data frame held 0.25 s, nothing interpolated; before the anchor dots with velocity arrows, hollow when not detected, the camera view outlined, the ball with its trail (hollow at its last detected position when not detected), "drop zone not yet in view", no shading and no pickup marker; at the anchor a 1.5 s hold, the shading as in Figure 1, the pickup marker, the 15 m race circle and one caption line (the losing team's chance from position, with movement, and the verdict); anchor to pickup recorded positions with the shading recomputed each frame; the pickup frame held 1 s naming the team that won the ball. Part two, labelled "model: one change" throughout, only for enough_type move: the anchor frame frozen, the best-placed player as a ghost at his recorded spot and at the moved spot, an arrow with the distance in metres, the shading recomputed with the change, the label "The model now has the race level."; held 3 s. Shirt numbers only; team names as in the figures; mp4 through ffmpeg when present, GIF otherwise.

Choices made in writing it, before the draw (presentation only):

| item | choice |
|:--|:--|
| colours | the winning team blue, the losing team orange, the shading from orange (losing team first) through neutral (level) to blue (winning team first), as in Figure 1 |
| shading | each team's best dynamic reach time from all its players on the frame, frozen reach model, as the winning team's margin clipped at 2 s, 140 x 140 grid, with the level line |
| extent | fixed for the whole animation: the ball path from release to pickup and 16 m around the pickup point, padded 4 m, cut at the pitch boundary plus 2 m |
| arrows | one second of current movement (smoothed velocity, window 5), as in Figure 1 |
| frame size | 1000 x 840 pixels, mp4 (H.264, yuv420p) at 4 frames a second for a 0.25 s hold |
| model part | the moved player keeps his recorded velocity; his marker is drawn filled; the caption line of part one stays on screen |
| bug check | the margin at the pickup point after the change, from all players, is printed with each animation (zero when the race is level) |

Draw, fixed now:

| item | rule |
|:--|:--|
| pool | lost balls of the test analysis set (all 15 matches) with enough_type move (audit/s3h_test/clips_enough.csv), lead at least 1.5 s (audit/mt1_test/episodes.csv), ball path at least 10 m (audit/s3h_test/pathcheck.csv, ball_path_m, the Figure 1 path length) and the enough player detected on the anchor frame (enough_player_extrapolated False); sorted by match_id and seq_i |
| draw | seed 20261118, one numpy default_rng: two without replacement from the pool's positioning verdicts, then two from its reading verdicts |
| output | audit/animations/animation_seed20261118_K_VERDICT_MATCH_SEQ.mp4 and animations.csv; all four are written |
| script | scripts/s3h_animations.py |


### 3h animation: the draw and the four animations (2026-11-18)

Run after the draw rule was committed (f24382c): `python scripts/s3h_animations.py audit/animations`. Pool: 237 balls (195 positioning, 42 reading). Drawn with seed 20261118, written to audit/animations/ (mp4 through ffmpeg, 1000 x 840, 4 frames a second); the margin at the pickup point after the change is 0.0000 s in all four (the race is level from all players on the frame, as from the race).

|   animation |   match_id |   seq_i | trigger   | verdict     |   lead_s |   ball_path_m |   metres_short | enough_player   |   seconds |   margin at the pickup after the change |
|------------:|-----------:|--------:|:----------|:------------|---------:|--------------:|---------------:|:----------------|----------:|----------------------------------------:|
|           1 |    1899585 |     275 | T7        | positioning |     2.50 |         51.62 |           0.75 | home_27         |     16.00 |                                    0.00 |
|           2 |    1986691 |     803 | T4        | positioning |     1.70 |         11.38 |           5.80 | away_10         |     23.00 |                                    0.00 |
|           3 |    2017461 |     483 | T2        | reading     |     2.50 |         45.97 |           0.72 | home_14         |     21.75 |                                    0.00 |
|           4 |    2006229 |     849 | T2        | reading     |     1.60 |         63.94 |           0.36 | away_39         |     23.50 |                                    0.00 |

Files: animation_seed20261118_1_positioning_1899585_275.mp4, animation_seed20261118_2_positioning_1986691_803.mp4, animation_seed20261118_3_reading_2017461_483.mp4, animation_seed20261118_4_reading_2006229_849.mp4.

Inspected as contact sheets of every sixth or eighth frame, all four. Before the anchor: dots, arrows, hollow estimated players, the camera outline moving with the play, the ball trail (hollow at the last detected position when the ball is not detected), no shading and no pickup marker. From the anchor: shading, the pickup marker and the 15 m circle; the pickup frame names the winning team; the model part shows the ghost, the moved spot, the arrow and the distance, and the level line passes through the pickup point. Reported, not changed:

| # | observation |
|:--|:--|
| 1 | three of the four moves are under 1 m (0.75, 0.72, 0.36 m): the arrow and the distance label sit on top of the player's dot and the change is hard to see |
| 2 | the animations run 16.0 to 23.5 s at 0.25 s a frame, mostly before the anchor (animation 2: about 5.4 s of play before the drop zone comes into view); the step 3 brief gives the animation 12 s of the video (30 to 42 s) |
| 3 | shirt numbers are 7.5 point inside the dots and hard to read at reduced size |
| 4 | the shading is the minimum over each team's players of a reach time without a turning term, so its level lines are straight-edged and angular |
