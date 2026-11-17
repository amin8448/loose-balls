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
