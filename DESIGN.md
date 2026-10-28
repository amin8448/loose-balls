# Design

## Loose-ball episode definition, frozen after step 1 (2026-10-28)

Frozen after the step 1 gates passed on the five exploration matches (AUDIT.md, "Gates after revision 2 amended": G1, G2, G3 pass; G4 passes at the first-leg and the last-leg anchor). No outcome was used and the test set stays locked. Any change from here is a revision of a frozen definition and is logged in AUDIT.md as such, with the reason, before outcome work uses it. Code: src/looseball/episodes.py.

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
| contact | a window frame t other than the pickup frame, with the ball detected on t-1, t and t+1, at which the horizontal ball velocity (ball_data.x, ball_data.y, from consecutive frames) turns by more than 30 degrees or changes speed by more than 3 m/s, and some player (detected or not) is within 1.5 m of the ball on t. When the speed into or out of t is zero, only the speed criterion applies |
| legs | the window split at its contacts. First leg: release frame to the first contact, or to the pickup frame if there is none. Last leg: last contact to the pickup frame, or the whole window if there is none |
| anchor of a leg | the first frame from the leg start to the leg end (inclusive) at which the pickup point lies inside the camera polygon (image_corners_projection, all eight values present). A leg with no such frame has no anchor and the episode is lost to the camera for that leg |
| lead | pickup frame minus anchor frame, in seconds |

### Step 2 decision 1, open: which leg anchors the measures

The anchor at which positioning is measured is either the first-leg anchor or the last-leg anchor. This is the first decision of step 2 and is not taken here. Step 1 evidence for it (AUDIT.md, A7, A8 and the gates after revision 2 amended):

| | first-leg anchor | last-leg anchor |
|:--|:--|:--|
| G4 pooled detection within 15 m at the anchor | 0.925 | 0.926 |
| main pairs lost to the camera | 10.9% (T1 26.9%, T7 13.8%) | 1.7% (8 pairs, all T4) |
| median lead (p10, p90) | 1.7 s (0.6, 3.9) | 1.4 s (0.3, 3.1) |
| lead < 0.5 s, of anchored pairs | 6.7% | 15.5% |

### Known behaviour of the contact rule (step 1 audit, not changed)

Recorded so that step 2 starts from it; the definition above is unchanged.

| behaviour | evidence |
|:--|:--|
| the release touch and the pickup touch are flagged at the window edges | 81 of 182 first contacts on the first window frame, 68% with the releasing player within 1.5 m; 28 last contacts on the frame before pickup, 96% with the winner within 1.5 m (AUDIT.md A8e; contact figures 2, 3 and 4). This shortens many first legs to one frame, which moves the first-leg anchor or removes it, and shortens some last legs |
| one touch is flagged on consecutive frames | 357 contacts form 247 runs of consecutive frames (AUDIT.md A8f; contact figures 1 and 3), so contact and leg counts overstate the number of touches |
| contacts cannot be tested where the ball is not detected | 8.9% of window frames from release+1 to pickup-1 are not testable (T4 19.3%) |

### Release-frame positioning as a secondary quantity

A9: of the players within 15 m of the pickup point at the last-leg anchor who were not detected at release, none moved at an implied speed above 9 m/s between the extrapolated release position and the first detected position (502 measured; median 2.41 m/s, maximum 8.09 m/s, median 1.3 s to first detection; 80 not detected by the pickup frame). This is the step 1 evidence on whether release-frame positioning can be reported as a secondary quantity; the decision belongs to step 2.
