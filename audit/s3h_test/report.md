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
