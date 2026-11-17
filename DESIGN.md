# Design

## Loose-ball episode definition, frozen after step 1 (2026-10-28)

Frozen after the step 1 gates passed on the five exploration matches (AUDIT.md, "Gates after revision 2 amended": G1, G2, G3 pass; G4 passes at the first-leg and the last-leg anchor). No outcome was used and the test set stays locked. Any change from here is a revision of a frozen definition and is logged in AUDIT.md as such, with the reason, before outcome work uses it. Code: the research version that produced steps 1 and 2 and MT1 is src/looseball_research/episodes.py (moved verbatim in step 3a, imports renamed only); the public, provider-neutral version is src/looseball/episodes.py (find_episodes; identical episodes on the exploration matches, and looseball reproduce regenerates MT1 byte for byte; AUDIT.md, 3a). Path named 2026-11-17 (documentation fix).

| revision | date | change | where logged |
|:--|:--|:--|:--|
| frozen | 2026-10-28 | definitions below, contact rule of revision 2 amended | AUDIT.md, gates after revision 2 amended |
| revision 3 (post hoc) | 2026-10-28 | contact rule: tested from release + 2 to pickup - 2; consecutive contact frames are one contact. G4 re-run at both anchors, passes | AUDIT.md, post hoc revision 3 and the sections after it |

### Inputs

Dynamic events (player_possession rows: frame_start, frame_end, period, team_id, player_id, player_position, start_type, end_type, pass_outcome, is_header, game_interruption_before, game_interruption_after, x_start, y_start, attacking_side, fully_extrapolated), phases of play, and tracking positions, detection flags and image_corners_projection. No SkillCorner model output. The tracking possession field is not used. Nothing is smoothed.

### Episodes

| element | definition |
|:--|:--|
| possession pair | consecutive player_possession rows i and i+1 of a match, sorted by frame_start (ties by the CSV field index) |
| retained pair | dropped when the pair spans a period boundary; when i+1 starts from a restart (start_type throw_in, free_kick, goal_kick or corner, reception or interception); when pass_outcome of i is offside; when game_interruption_after of i or game_interruption_before of i+1 is set; when end_type of i is foul_suffered |
| trigger class, tested in this order | T5 header non-pass (is_header TRUE, end_type not pass or shot); T1 clearance; T2 failed pass (end_type pass, pass_outcome unsuccessful); T3 shot; T4 dispossession (possession_loss); T6 unknown end_type; T7 completed pass not controlled (end_type pass, pass_outcome successful, start_type of i+1 recovery or keep_possession); T0 completed pass (reference only) |
| resolution class | start_type of i+1 |
| continuity class | same player, same team (different player), change of team |
| gap | frame_start of i+1 minus frame_end of i, frames at 10 per second |
| candidate episode | retained pair with trigger T1 to T7, resolution recovery or keep_possession, not a T3 pair won by a player whose player_position is GK, not the same player, and gap >= 3 frames |
| release frame | frame_end of i |
| pickup frame | frame_start of i+1 |
| window | frames strictly after the release frame up to and including the pickup frame |
| pickup point | tracking ball (ball_data.x, ball_data.y) on the pickup frame |
| aerial episode | ball_data.z > 1.8 m on any window frame with ball_data.is_detected TRUE; ground otherwise |
| scramble | candidate episodes are merged when the winning possession of one is the releasing possession of the next candidate episode, lasts fewer than 5 frames (frame_end minus frame_start < 5) and ends in possession_loss, clearance or unknown. Its trigger is that of its first episode, its winner the team of i+1 of its last episode |
| winner | team of possession i+1 (of the last episode, for a scramble). Recorded only; it never enters the definition |

### Window structure

| element | definition |
|:--|:--|
| contact (revision 3) | a frame t with release + 2 <= t <= pickup - 2, with the ball detected on t-1, t and t+1, at which the horizontal ball velocity (ball_data.x, ball_data.y, from consecutive frames) turns by more than 30 degrees or changes speed by more than 3 m/s, and some player (detected or not) is within 1.5 m of the ball on t. When the speed into or out of t is zero, only the speed criterion applies. Consecutive contact frames are one contact, placed at the first frame of the run |
| legs | the window split at its contacts. First leg: release frame to the first contact, or to the pickup frame if there is none. Last leg: last contact to the pickup frame, or the whole window if there is none |
| anchor of a leg | the first frame from the leg start to the leg end (inclusive) at which the pickup point lies inside the camera polygon (image_corners_projection, all eight values present). A leg with no such frame has no anchor and the episode is lost to the camera for that leg |
| lead | pickup frame minus anchor frame, in seconds |

### Step 2 decision 1, closed: the last-leg anchor

Closed (documentation fix, 2026-11-17): the measures are taken at the last-leg anchor (step 2, D1), fixed in the MT1 plan ("MT1 definitions" below). The text and evidence as written before the decision follow.

The anchor at which positioning is measured is either the first-leg anchor or the last-leg anchor. This is the first decision of step 2 and is not taken here. Step 1 evidence for it, under the revision 3 contact rule (AUDIT.md, A7, A8 and the gates under revision 3):

| | first-leg anchor | last-leg anchor |
|:--|:--|:--|
| G4 pooled detection within 15 m at the anchor | 0.921 | 0.924 |
| G4 episode level at the anchor (reported, no threshold) | 0.802 | 0.812 |
| main pairs lost to the camera | 5.8% (T2 6.7%, T4 6.6%, T7 6.5%) | 1.7% (8 pairs, all T4) |
| median lead (p10, p90) | 1.7 s (0.6, 3.9) | 1.4 s (0.4, 3.1) |
| lead < 0.5 s, of anchored pairs | 7.1% | 10.3% |
| main pairs with no contact, where the two anchors coincide | 75.1% | 75.1% |

### Known behaviour of the contact rule (step 1 audit, after revision 3)

| behaviour | evidence |
|:--|:--|
| a smaller edge effect remains one frame further in | 27 of 116 first contacts are on release + 2, 9 of them with the releasing player within 1.5 m; 11 last contacts are on pickup - 2, 6 of them with the winner within 1.5 m (AUDIT.md A8e under revision 3; contact figure 4, revision 3) |
| contacts cannot be tested where the ball is not detected | 9.3% of the frames from release + 2 to pickup - 2 are not testable (T4 21.0%) |
| release-edge and duplicate contacts of revision 2 | removed by revision 3: the first contact moved from a median 0.2 s to 1.3 s after release, and pairs with 3 or more contacts fell from 10.1% to 1.5% |

### Release-frame positioning as a secondary quantity

A9 under revision 3: of the players within 15 m of the pickup point at the last-leg anchor who were not detected at release (581 of 3,344), none moved at an implied speed above 9 m/s between the extrapolated release position and the first detected position (501 measured; median 2.40 m/s, maximum 8.09 m/s, median 1.3 s to first detection; 80 not detected by the pickup frame). The implied speed is an average over the time to first detection, so it rules out large jumps, not short-lived errors. This is the step 1 evidence on whether release-frame positioning can be reported as a secondary quantity; the decision belongs to step 2.

## Step 2 measures (2026-10-28)

The step 2 definitions are in docs/step2_brief.md (D1 to D8), with the decisions and additions logged in AUDIT.md under step 2. They are frozen here when the MT1 marker is logged; this section holds what has been fixed so far.

### Decomposition (D6)

At the last-leg anchor, three nested expectations for a team: static (positions only, velocities set to zero), dynamic (positions and smoothed velocities), and actual (who controlled the ball). For a team that lost, the deficit of 1 splits as positioning (1 minus p_static), reading (p_static minus p_dynamic, negative when movement helped) and after the anchor (p_dynamic). For a team that won, the credit of 1 splits as p_static, p_dynamic minus p_static, and 1 minus p_dynamic. Verdict for a lost ball: positioning if p_static is below 0.5; reading if p_static is at least 0.5 and p_dynamic is below 0.5; after the anchor otherwise. Episodes with a lead under 0.5 s are the immediate class, reported and not decomposed.

Under the DataBallPy reach model, velocity acts only as drift during the reaction window, so the reading term measures how much current momentum changes who is closer after that window.

The decomposition keeps the one temperature fitted on the dynamic reach times for both p_static and p_dynamic, because positioning and reading are read off the same expectation with and without velocity and only a shared scale leaves their difference to movement alone; the static model with its own temperature (AUDIT.md, 3c.0) is a report-only benchmark for V2.

## MT1 definitions, frozen when the MT1 marker was logged (2026-10-29)

Copied on 2026-11-17 (documentation fix) from AUDIT.md, "MT1, the main-test plan", where they were frozen with the marker (code at commit 682aa2c, frozen parameters sha256 129bfdea2d1dd5547e3f8fdeb1f1f5de57514ca3b79ab5de2bb16a93fa9fab4c). AUDIT.md stays the source; nothing here differs from it.

| element | definition |
|:--|:--|
| episodes | DESIGN.md, step 1 definition with revision 3; the measured leg is the last leg; its anchor and lead |
| analysis set | anchored main pairs kept by D7 at 15 m, with lead >= 0.5 s; every one is a lost ball for one team |
| camera gate D7 | (docs/step2_brief.md, D7) an episode is kept when at least 85% of the players within the radius are detected at the anchor and the winner is detected at pickup; nobody within the radius counts as observed |
| immediate class | lead < 0.5 s; reported, not decomposed |
| race | every player of both teams within 15 m of the pickup point on the anchor frame, goalkeepers included and flagged; Savitzky-Golay velocities, window 5, order 2 |
| reach model | DataBallPy TTIConstraint.tti, turning penalty shaw, reaction 0.7 s, top speed 5.0 m/s; static: velocity zero; an empty team gets 0.7 + radius / 5.0 |
| p_static, p_dynamic | releasing team: sigmoid(2.9273 x (t_other - t_releasing)) on static and dynamic best times (softmax, temperature 0.3416 s) |
| baselines | B0: sigmoid(0.0678 + 0.3610 x (n_releasing - n_other)); B1: sigmoid(-0.0530 + 0.3595 x (nearest_other - nearest_releasing)) |
| decomposition and verdict | DESIGN.md, step 2 measures, D6 |
| winner | team of possession i+1 |

| gate | rule |
|:--|:--|
| V1 | p_dynamic has a lower log-loss than B0, and than B1, on the analysis set: for each, the difference (log-loss of the baseline minus log-loss of p_dynamic) has a 95% bootstrap interval above 0 and p_dynamic is lower in at least 10 of the 15 matches |
| V2 | the same rule for p_dynamic against p_static |
| V3 | for the lost balls of the analysis set, the verdict is unchanged in at least 70% of episodes under each variant on its own: anchor 0.2 s later; growing radius max(15 m, 8 m/s x lead); pleuler turning penalty; smoothing window 7; extrapolated players dropped; reaction time 0.35 s. The base set stays fixed, the frozen D5 parameter is used, and D7 and the immediate rule are not re-applied |
| camera gate | at most 30% of anchored main pairs dropped by D7 at 15 m; the drop-rate difference by winner reported |
| intervals | percentile, 2000 bootstrap replicates resampling episodes within match, seed 0 |

Consequences fixed in the plan: V1 fails, the entry reports the audit and the descriptives and makes no verdicts. V2 fails, the reading term is dropped and the decomposition is positioning against the race. V3 fails, verdicts are shown with their variants and never as one label. The camera gate drops more than 30%, the radius falls to 10 m for the main analysis. All four passed (AUDIT.md, MT1 results).

## 3h. What would have been enough, frozen before any code touched match data (2026-11-17)

Report-only extension of the decomposition (step 3 brief, 3h; decisions in AUDIT.md, "3h. What would have been enough"). Nothing is fitted; every quantity is a deterministic function of the frozen race and reach model. Never called "what should have happened". Code: src/looseball/enough.py.

| element | definition |
|:--|:--|
| set | the lost balls of the analysis set (gated). Ungated values are report-only |
| t_w | the winning side's best dynamic reach time in the race (an empty side: the empty-team time) |
| deficit_s | D = the losing side's best dynamic reach time minus t_w, for every lost ball; negative when the loser was the dynamic favourite |
| best-placed player | the losing player in the race with the smallest dynamic reach time; ties within 1e-9 s broken by distance to the pickup point, then column_id |
| metres_short | 5 x D, for balls with D > 0; blank otherwise. Exact under the frozen model: its reach time is reaction + (distance from the drifted position, position + reaction x velocity, to the pickup point) / top speed, with no turning term, so moving the start point along the line from the drifted position to the pickup point by 5 x D lowers the best-placed player's time by D, to t_w. Under the pleuler variant (V3 stability only): the displacement along that line found by bisection |
| redirection | for each losing player in the race with a velocity and speed above zero, not standing on the pickup point: d = distance from his position to the pickup point, r = reaction x speed, R = top speed x (t_w - reaction). A flip by rotation, keeping his speed, is possible when \|d - r\| <= R. The smallest rotation that flips is max(0, phi - theta), phi the angle between his velocity and the direction to the pickup point, theta = arccos((d^2 + r^2 - R^2) / (2 d r)), the cosine clipped to [-1, 1]. Ties: rotation within 1e-9 rad, then distance, then column_id. Under the pleuler variant: the smallest rotation by bisection on the angle |
| enough change | the redirection with the smallest rotation if any losing player has one; otherwise the best-placed player moved by metres_short |
| enough_type, in order of precedence | blank for after-the-anchor verdicts; already_favourite when D <= 0; no_player_in_race when the losing side has nobody in the race; redirect; move |
| eligibility | goalkeepers and extrapolated players (not detected on the anchor frame) are eligible and flagged |
| clips_enough.csv | match_id, seq_i, period, clock, frame, team, verdict, deficit_s, metres_short, enough_type, enough_player (column_id), enough_metres (move), enough_degrees (redirect), enough_player_gk, enough_player_extrapolated. Same rows and order as clips.csv, which is not touched. Written by looseball run and looseball reproduce |

### Path check (report-only)

Code: src/looseball/pathcheck.py. Procedure as logged in AUDIT.md, "Path check: procedure". On ground lost balls of the analysis set, each team's first frame from the anchor to the pickup at which it reaches the ball's tracked position, from anchor-frame positions of all its rostered players under the frozen reach model, with a 0.3 s tolerance (and 0); static and dynamic. The path favourite is the team with the earlier first reachable frame. It changes no verdict; its positioning number goes into the README limitations.
