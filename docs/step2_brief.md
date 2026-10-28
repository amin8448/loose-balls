# Loose balls: step 2, the measures and the main-test plan

Brief for step 2 in the loose-balls repository. Step 1 (the audit, revisions 1 to 3) is closed; its episode definition in DESIGN.md is the starting point. Step 2 defines what is measured on each episode, checks it on the exploration matches, and writes the main-test plan MT1. Nothing from the 15 test matches is read until the MT1 marker is logged, and then once.

## The question, stated for the README

When a ball is loose, which team gets there, and why? For every loose ball a team lost, the entry says how much of the loss was already decided by where its players stood when the drop zone came into view, how much by where they were moving, and how much by what happened after that. Three words a coach already uses: positioning, reading, and the race itself.

## Decisions for Amin

D1. Unit: the last leg of each episode (from the last contact, or the release if there is none, to the pickup). The first leg is not used. Episodes whose lead at the last-leg anchor is under 0.5 s are a reported class, "immediate", counted by trigger and by winner and excluded from the verdicts. The number of legs is a descriptor.

D2. Radius: 15 m around the pickup point, fixed. The growing radius max(15 m, 8 m/s times lead) is a stability variant only.

D3. Reachability: time to reach the pickup point for every player within the radius at the anchor, under DataBallPy's time-to-intercept constraint with the "shaw" turning default and the package's default speed and acceleration parameters, one set for all players. No per-player speeds, no season aggregates. The "pleuler" turning penalty is a stability variant.

D4. Velocities: a Savitzky-Golay filter, window 5 frames, order 2, on each player's track, fixed in advance. Window 7 is a stability variant. Players not detected at the anchor (at most 15% within the radius, by the camera gate) keep SkillCorner's extrapolated position and the velocity of that track, and are flagged; dropping them is a stability variant.

D5. Expectation model: the probability that a team wins the loose ball from the two teams' best reach times. Two candidate forms, a softmax with one temperature and a logistic on the time difference; the form is chosen by leave-one-match-out log-loss on the exploration episodes and the parameter is frozen before MT1. This is the only place the outcome is used before the test set.

D6. The decomposition: three nested expectations at the anchor. Static: positions only, velocities set to zero. Dynamic: positions and velocities. Actual: who controlled the ball. For a team that lost, the deficit of 1 splits as positioning (1 minus static), reading (static minus dynamic, negative when movement helped), and after the anchor (dynamic). For a team that won, the credit of 1 splits the same way. The categorical verdict for a lost ball, used for clip lists: positioning if static is below 0.5; reading if static is at least 0.5 and dynamic is below 0.5; after the anchor otherwise.

D7. Camera gate: an episode is kept when at least 85% of the players within the radius are detected at the anchor and the winner is detected at pickup. Drop rates by trigger and by winner are reported, with the difference in the releasing team's win share between dropped and kept episodes and its interval.

D8. Reporting: team level only. Per team, the deficit shares over its lost loose balls and the credit shares over its won ones, with bootstrap intervals; no player values. A timestamp export per verdict for video review. One match drawn by seed as the worked example.

## Rules for the step

- Exploration matches only until the MT1 marker. Scripts load through the package so the guard applies.
- No SkillCorner model outputs anywhere (xthreat, xpass_completion, EPV, pressure bands, passing_option_score, engagement flags).
- The outcome (who won) is used before MT1 only in S3, for the one expectation parameter, and in the S5 dry run, which is a bug check and not a result.
- Every number goes into AUDIT.md with its step label and date. Definitions that change after a result are logged as post hoc. Figures are for finding bugs, episodes drawn by seed.
- A failed check is a result to report, not a reason to retune.

## Definitions

Episode, legs, contacts, anchor, lead and pickup point: as frozen in DESIGN.md after revision 3. The measured leg is the last leg (D1). The anchor is the first frame from the leg's start at which the pickup point is inside the camera polygon; lead is pickup minus anchor in seconds.

Players in the race: every player of both teams, goalkeepers included, within 15 m of the pickup point on the anchor frame. Goalkeepers are flagged, since they are mostly extrapolated.

Reach time t_j: the time for player j to reach the pickup point from his position and smoothed velocity at the anchor, under the model in D3. Static reach time: the same with velocity zero.

Team best time: the minimum reach time over the team's players in the race. Episodes where one team has nobody in the race get that team's best time set to the radius divided by the model's top speed, and are flagged.

Expectation p_A: the probability that team A wins, from the two best times under the frozen D5 model. p_static uses static reach times, p_dynamic the full ones. The baseline models for V1 are B0, a logistic on the difference in the number of players in the race, and B1, a logistic on the difference in nearest-player distance, both fitted on exploration by the same leave-one-match-out procedure and frozen.

Deficit shares for a losing team (D6): positioning 1 minus p_static; reading p_static minus p_dynamic; after the anchor p_dynamic. They sum to 1. Credit shares for the winner are p_static, p_dynamic minus p_static, and 1 minus p_dynamic.

Immediate: lead under 0.5 s. Reported, not decomposed.

## Exploration checks, S-series

S1, velocity sanity. Speed distribution after smoothing on detected frames: the share of player-frames above 10 m/s, and the share of anchor-frame velocities that come from extrapolated tracks. A share above 1% over 10 m/s means the smoother or the frame alignment is wrong; fix before going on.

S2, reachability sanity. For the winning player, his reach time to the pickup point against the actual lead. The share of episodes where the winner's reach time is at most lead plus 0.3 s, pooled and by trigger. Report only, but if it is under 70% the model's parameters are off for this data and that is a finding to discuss before S3.

S3, the expectation model. Leave-one-match-out log-loss on exploration episodes for the softmax and the logistic forms of p_dynamic, and for B0 and B1. Pick the form with the lower log-loss, freeze its parameter, and log the fitted values. Calibration table (five bins) for the chosen form.

S4, camera gate and the immediate class. Drop rates by trigger and by winner under D7; the share of immediate episodes by trigger and by winner.

S5, dry run of V1 to V3 on the exploration episodes, labelled as a bug check and not a test. Includes the seeded figures: four episodes with reach-time contours for both teams at the anchor, the smoothed velocity arrows, the pickup point, and the three numbers; and the team-level deficit figure for the exploration teams. Any bug found and fixed is logged. After S5, the code is not changed except for logged bug fixes.

## Main-test plan MT1

Logged as MAIN-TEST-PLAN in AUDIT.md after S5, then run once on the 15 test matches.

V1, the race is predictable: p_dynamic has lower log-loss than both B0 and B1 on the test episodes, with a 95% bootstrap interval of each difference (episodes resampled within match) excluding 0, and the same direction in at least 10 of 15 matches.

V2, movement adds to position: p_dynamic has lower log-loss than p_static, same interval and same per-match rule.

V3, verdicts are stable: for lost loose balls with a verdict, the categorical verdict is unchanged in at least 70% of episodes under each variant on its own: anchor 0.2 s later; growing radius; pleuler turning penalty; smoothing window 7; extrapolated players dropped.

Camera gate: at most 30% of episodes dropped under D7, with the drop-rate difference by winner reported.

Consequences fixed in advance. If V1 fails, the entry reports the audit and the descriptives and makes no verdicts. If V2 fails, the reading term is dropped and the decomposition is positioning against the race. If V3 fails, verdicts are shown with their variants and never as one label. If the camera gate drops more than 30%, the radius falls to 10 m for the main analysis and the change is logged.

Report-only on the test set: calibration of p_dynamic; deficit shares by trigger; the immediate class by trigger and winner; the share of lost loose balls under each verdict pooled over teams, which is the headline number if V1 to V3 hold.

## Deliverable shape

The package looseball exposes: find_episodes (possessions and tracking in, episodes with legs, contacts and anchors out), reach_times, expectations, decompose, and export_clips (match id, period, clock, frame, team, verdict, for a video tool). Inputs follow DataBallPy's tracking and event tables, with the SkillCorner open-data loader as one adapter, so the module can run on any provider the package loads. The README's two figures are the single-episode figure and the team deficit figure.

## Outputs to bring back from the exploration part

AUDIT.md sections S1 to S5 with the gate values, the frozen D5 parameters, the four episode figures, and a short list of anything in the definitions that had to be interpreted. The MT1 marker is not logged until Amin has read S1 to S5.
