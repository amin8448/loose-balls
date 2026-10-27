# Loose balls: step 1, the exploration audit

Brief for step 1. Audit only. Nothing in this step fits a model, ranks a team or relates anything to who won a loose ball. The point is to learn whether SkillCorner's possession segmentation leaves a measurable loose-ball window, and whether the camera sees it.

## The idea being audited

A loose ball is a stretch of play in which no player has the ball: after a clearance, an unsuccessful pass that nobody intercepts cleanly, a blocked or saved shot, a header that is not a pass, a tackle that leaves the ball free. The entry would ask, for every loose ball, which team got there and why, and would decompose a lost loose ball into positioning at release, movement during the loose window (reading), and the reaction after the ball is released. That decomposition is step 2. Step 1 only establishes that the window exists and is observed.

## Decisions taken

1. New repository, clean slate. No analysis code is carried over from analytics-cup-football or competition_analytics-cup-2-football. The data loader, the parquet cache and the test-set guard carry no analysis and may be rewritten or copied; everything else is written fresh. Working name: loose-balls (repository), looseball (package). Rename freely.
2. Same split as before. Exploration: 1886347, 1959846, 1996436, 1996435, 2007448. Test, locked: 1874553, 1899585, 1925299, 1927964, 1953632, 1986691, 2006229, 2006363, 2007721, 2010085, 2011166, 2013725, 2015213, 2016236, 2017461. The guard refuses a test match unless a main-test plan marker is logged in the committed AUDIT.md; no such plan exists in step 1, so no test match is read.
3. Gate thresholds are the ones in the Gates section. Log them in AUDIT.md before the first run. A threshold changed after a result is logged as post hoc.

## Repository setup

- Data: a link at data/opendata to the SkillCorner open-data clone at commit 4340d27, never committed. The parquet cache is built under data/cache on first use (about 5 MB per match).
- Specifications: copy the Dynamic Events and Phases of Play specification PDFs (SkillCorner, 2025-02-16) from the previous project's data/specs into data/specs. A0 quotes from them.
- Package layout: src/looseball with paths (match ids and the two sets), io (metadata, roster, events, phases), tracking (frames and players as tables, cached, with a frame class: camera, no camera, empty), guard (the test-set rule), and episodes (everything defined below). Scripts load through the package only.
- Logs: AUDIT.md holds every result with its step label and date; DESIGN.md holds the frozen definitions once step 1 is done. Figures go to audit/figures with the seed in the file name.
- Commits: plain messages.

## Rules for the step

- Exploration matches only, loaded through the package so the guard applies.
- No SkillCorner model outputs enter any definition in this step (no xthreat, xpass_completion, EPV, pressure bands, passing_option_score, or engagement outcome flags). Possession boundaries, start_type, end_type, pass_outcome, is_header, game_interruption fields, phases and tracking are the inputs.
- The tracking possession field (possession.player_id, possession.group) is not used; it is filled on about half of the frames and disagrees with the events.
- Every number goes into AUDIT.md as a table with the step label (A0 to A6, G1 to G4) and the date. Figures are for finding bugs; the episodes to draw are chosen by a seeded random draw, never by hand.
- Any change to a definition after a result is logged as post hoc, with the reason.

## Definitions, provisional

These definitions produce the audit tables. After the audit, the final episode definition is frozen in DESIGN.md before any outcome work begins; the audit is allowed to change them, step 2 is not.

Possession sequence. All player_possession rows of a match, sorted by frame_start. Consecutive rows i and i+1 form a pair. Pairs are dropped when they span a period boundary; when possession i+1 starts from a restart (start_type in throw_in_reception, free_kick_reception, goal_kick_reception, corner_reception, or the restart interception types); when possession i has pass_outcome == offside; or when a game_interruption field marks a stoppage between them.

Gap. gap = frame_start(i+1) minus frame_end(i), in frames at 10 per second. A gap of 0 means the next touch is on the same frame as the last touch.

Release frame. frame_end(i). Pickup frame: frame_start(i+1). Loose window: the frames strictly after the release frame up to and including the pickup frame.

Pickup point. The tracking ball position (ball_data.x, ball_data.y) on the pickup frame. Compare it with the event coordinates x_start, y_start of possession i+1 after rotating the event frame to the tracking frame; the two should agree within a few meters. Report the disagreement distribution (A2).

Trigger class of a pair, from possession i:
- T1 clearance: end_type == clearance
- T2 failed pass: end_type == pass and pass_outcome == unsuccessful
- T3 shot: end_type == shot
- T4 dispossession: end_type == possession_loss
- T5 header, non-pass: is_header == TRUE and end_type not in (pass, shot)
- T6 unknown: end_type == unknown
- T0 normal: end_type == pass and pass_outcome == successful (not loose; kept in the cross-tab as the reference)

Resolution class of a pair, from possession i+1: start_type (pass_reception, pass_interception, recovery, keep_possession, unknown).

Continuity class of a pair: same player, same team but a different player, or a change of team.

Candidate loose-ball episode (provisional): a pair whose trigger is T1 to T6, or whose resolution is recovery or unknown, with gap >= 1 frame, excluding same-player pairs. The audit tables (A1) decide whether this stays, widens or narrows.

Scramble. A run of consecutive candidate episodes in which each winning possession lasts fewer than 5 frames (0.5 s) and ends in possession_loss, clearance or unknown, with the next possession again a candidate. A scramble is one episode whose end is the first possession that lasts 5 frames or more, or ends in a pass, shot or restart. Report both views: raw pairs and merged scrambles.

Aerial episode: an episode in which the tracking ball_data.z exceeds 1.8 m on any frame of the loose window, measured only on frames where ball_data.is_detected is TRUE. Ground episode otherwise.

Winner. The team of possession i+1 (or of the possession that ends a scramble). Recorded for the counts in A5 only. No predictor is related to it in this step.

## Checks

A0. Specification. Quote from the Dynamic Events specification (around pp. 40 to 41) the definitions of start_type values recovery, pass_interception, keep_possession and unknown, and of end_type values clearance, possession_loss and unknown; also is_header (p. 76). Record the exact wording in AUDIT.md. The decision whether a "recovery" is a loose-ball pickup or includes clean tackles depends on this wording and on A1.

A1. Gap cross-tab. For every retained pair in the five matches, a table of trigger class by resolution class with the pair count and, in each cell, the gap quantiles (10th, 50th, 90th percentile, in seconds) and the share of pairs with gap >= 3 frames. The same table split by continuity class (same player, same team, change of team). A histogram of gap in frames, 0 to 50, one panel per trigger class, is the bug-finding figure for this step.

A2. Pickup point agreement. Distribution of the distance between the tracking ball on the pickup frame and the rotated event x_start, y_start of possession i+1, for candidate episodes. Report the share within 2 m and within 5 m. If the share within 5 m is under 90%, check the rotation and the frame alignment before anything else.

A3. Ball visibility in the window. For candidate episodes with gap >= 3 frames: the share of window frames on which ball_data.is_detected is TRUE, pooled and by trigger class; the share of episodes with at least one no-camera or empty frame inside the window, pooled and by trigger class; the share of episodes whose release frame or pickup frame is not a camera frame.

A4. Player visibility around the loose ball. On the release frame and on the pickup frame of each candidate episode: the number of players within 10 m and within 15 m of the pickup point, by team, and the share of them with is_detected TRUE. Also the share of episodes in which the winning player (player of possession i+1) is detected on the pickup frame, and the share in which possession i+1 has fully_extrapolated TRUE.

A5. Volume and structure. Candidate episodes per match (raw pairs and merged scrambles), by trigger class and by aerial or ground; how many scrambles have 2, 3, 4 or more links; the share of chaotic and direct phases that contain at least one episode, and the share of episodes that fall inside a chaotic phase. Winner counts by match and team, as a plain count only.

A6. Flight geometry. For candidate episodes with gap >= 3 frames: the maximum detected ball_data.z in the window, the horizontal distance the ball travels from release to pickup, and the window duration. Quantiles pooled and by trigger class. This tells step 2 how long the reading window is and how often it is aerial.

## Gates, fixed before the run

G1. Volume: at least 50 candidate episodes per exploration match (merged scrambles, gap >= 3 frames) after the exclusions. Fail: the idea is too thin for team-level work; stop.

G2. The window exists, judged on raw candidate pairs with gap >= 1 before any merging or further filtering: the median gap is at least 0.5 s, and at least 60% of pairs have gap >= 3 frames. Fail: SkillCorner's segmentation does not leave a loose window; the idea stops here and the 1v1 approach idea is next.

G3. Ball seen: ball_data.is_detected is TRUE on at least 85% of window frames pooled, and at most 25% of candidate episodes contain a no-camera or empty frame (these episodes would be dropped in step 2, so this is the share lost to the camera, reported by trigger class so a drop that falls on one trigger is visible). Fail by a small margin: restrict to windows up to 2 s and recheck once; fail again: stop.

G4. Players seen: on both the release frame and the pickup frame, at least 85% of players within 15 m of the pickup point are detected, and the winning player is detected on the pickup frame in at least 90% of episodes. Fail: restrict to the 10 m radius and recheck once; fail again: stop.

G1 to G4 all pass: freeze the episode definition in DESIGN.md and move to step 2.

## Outputs to bring back

- AUDIT.md section "Step 1, loose-ball audit" with A0 to A6 and the gate verdicts.
- audit/loose_episodes_exploration.csv: one row per candidate pair with match id, index of i and i+1, trigger class, resolution class, continuity class, gap, aerial flag, scramble id, release and pickup frames, pickup point, ball detection share, player counts and detection shares at both frames, winner team.
- Six seeded episode figures: ball path through the window, players within 15 m at release and pickup with detection flags, the pickup point from tracking and from the event.

What comes next, once these are in hand: the episode definition is frozen, and step 2 writes the three measures (reachability at release, movement during the window, reaction after release), each with its own pre-registered check, before the main test is planned.
