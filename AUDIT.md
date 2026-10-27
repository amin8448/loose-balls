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
