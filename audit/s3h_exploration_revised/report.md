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
