Diagnostics on the test analysis set: 1003 lost balls.

D1. Balls with nobody of either team in the 15 m race at the anchor: 31.

| verdict          |   balls |
|:-----------------|--------:|
| after the anchor |      31 |

| trigger   |   balls |
|:----------|--------:|
| T2        |      20 |
| T4        |       4 |
| T7        |       4 |
| T3        |       2 |
| T6        |       1 |

Against the 31 balls with p_static and p_dynamic both 0.5000: 31 are in both sets; 0 D1 balls are not among them; 0 of them are not D1 balls.

D2. Outside the pitch markings (each match's pitch size; origin at the centre).

Pickup point:

| verdict          |   balls |   pickup_outside |   pickup_outside_1m |   pickup_outside share |   pickup_outside_1m share |
|:-----------------|--------:|-----------------:|--------------------:|-----------------------:|--------------------------:|
| after the anchor |     176 |                0 |                   0 |                  0.000 |                     0.000 |
| positioning      |     692 |                2 |                   1 |                  0.003 |                     0.001 |
| reading          |     135 |                0 |                   0 |                  0.000 |                     0.000 |
| all              |    1003 |                2 |                   1 |                  0.002 |                     0.001 |

| trigger   |   balls |   pickup_outside |   pickup_outside_1m |   pickup_outside share |   pickup_outside_1m share |
|:----------|--------:|-----------------:|--------------------:|-----------------------:|--------------------------:|
| T1        |      30 |                0 |                   0 |                  0.000 |                     0.000 |
| T2        |     281 |                1 |                   1 |                  0.004 |                     0.004 |
| T3        |      45 |                0 |                   0 |                  0.000 |                     0.000 |
| T4        |     327 |                1 |                   0 |                  0.003 |                     0.000 |
| T5        |      13 |                0 |                   0 |                  0.000 |                     0.000 |
| T6        |       7 |                0 |                   0 |                  0.000 |                     0.000 |
| T7        |     300 |                0 |                   0 |                  0.000 |                     0.000 |
| all       |    1003 |                2 |                   1 |                  0.002 |                     0.001 |

Ball on the anchor frame: position missing on 0 balls; ball detected on 997 of 1003 anchor frames.

Ball on the anchor frame:

| verdict          |   balls |   anchor_ball_outside |   anchor_ball_outside_1m |   anchor_ball_outside share |   anchor_ball_outside_1m share |
|:-----------------|--------:|----------------------:|-------------------------:|----------------------------:|-------------------------------:|
| after the anchor |     176 |                     0 |                        0 |                       0.000 |                          0.000 |
| positioning      |     692 |                     3 |                        0 |                       0.004 |                          0.000 |
| reading          |     135 |                     0 |                        0 |                       0.000 |                          0.000 |
| all              |    1003 |                     3 |                        0 |                       0.003 |                          0.000 |

| trigger   |   balls |   anchor_ball_outside |   anchor_ball_outside_1m |   anchor_ball_outside share |   anchor_ball_outside_1m share |
|:----------|--------:|----------------------:|-------------------------:|----------------------------:|-------------------------------:|
| T1        |      30 |                     0 |                        0 |                       0.000 |                          0.000 |
| T2        |     281 |                     0 |                        0 |                       0.000 |                          0.000 |
| T3        |      45 |                     0 |                        0 |                       0.000 |                          0.000 |
| T4        |     327 |                     3 |                        0 |                       0.009 |                          0.000 |
| T5        |      13 |                     0 |                        0 |                       0.000 |                          0.000 |
| T6        |       7 |                     0 |                        0 |                       0.000 |                          0.000 |
| T7        |     300 |                     0 |                        0 |                       0.000 |                          0.000 |
| all       |    1003 |                     3 |                        0 |                       0.003 |                          0.000 |

D3. Largest share of detected-ball window frames with one player within 1.5 m of the ball: 1002 balls with a detected window frame (1 without); p10 0.036, p25 0.077, p50 0.143, p75 0.270, p90 0.481; share at least 0.70 on 45 balls.

Balls with a window of at least 2 s: 559; of them, one player within 1.5 m on at least 70% of the detected-ball frames: 5. By trigger and that player's role:

| trigger   |   losing team |   winner |   winning team, not the winner |   all |   balls with a 2 s window |
|:----------|--------------:|---------:|-------------------------------:|------:|--------------------------:|
| T4        |             2 |        1 |                              1 |     4 |                        65 |
| T7        |             1 |        0 |                              0 |     1 |                       225 |
| all       |             3 |        1 |                              1 |     5 |                       559 |

| verdict          |   losing team |   winner |   winning team, not the winner |   all |
|:-----------------|--------------:|---------:|-------------------------------:|------:|
| after the anchor |             2 |        0 |                              0 |     2 |
| positioning      |             1 |        1 |                              0 |     2 |
| reading          |             0 |        0 |                              1 |     1 |
| all              |             3 |        1 |                              1 |     5 |
