3c.0, report-only. Static expectation with its own temperature (b_static 1.8123 per second, fitted on the exploration matches only) on the 1003 test analysis episodes. Difference: log-loss of the comparison minus log-loss of the model; interval: 2000 bootstrap replicates within match, seed 0.

| model        | against      |   log-loss model |   log-loss against |   difference |      lo |     hi |   matches model lower (of 15) |
|:-------------|:-------------|-----------------:|-------------------:|-------------:|--------:|-------:|------------------------------:|
| p_dynamic    | p_static_own |           0.4578 |             0.5529 |       0.0951 |  0.0731 | 0.1154 |                            15 |
| p_dynamic    | p_B1         |           0.4578 |             0.5516 |       0.0938 |  0.0718 | 0.1140 |                            15 |
| p_static_own | p_B1         |           0.5529 |             0.5516 |      -0.0013 | -0.0028 | 0.0001 |                             4 |
