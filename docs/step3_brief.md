# Loose balls: step 3, package, figures, README, video, submission

Brief for step 3 in the loose-balls repository. MT1 passed on the 15 test matches (commit 93072e5). Step 3 turns the result into the submission. No measure, definition or frozen parameter changes in this step; anything that looks like it needs changing is reported, not fixed.

## Decisions taken

- Title: "Loose Balls: Second to the ball". Repository loose-balls, package looseball.
- Figure 2 is drawn in two versions (A and B below) and Amin chooses.
- A DataBallPy issue proposing the feature is optional, opened by Amin after the adapter exists, and not a dependency of anything here.
- The README draft goes to a fresh reader who has not seen the project before submission.
- Figure 2 is version A, with the interval bar moved below the bar (or drawn in the positioning colour) so it does not read as an interval on the reading share.
- Figure 1 is redrawn once by seed under a legibility constraint logged before the draw: a reading or positioning verdict, lead of at least 1.5 s, ball path of at least 10 m. The caption says the ball was drawn at random among such balls. (Amin may keep the current episode instead; then the constraint line is dropped.)
- "What would have been enough" (section 3h) is added after the README draft exists. "What the players should have done" is not built; it is one future-work sentence in the README.

## What the submission requires (Pretalx CfP, Analytics Cup 2.0)

- Public GitHub repository, all code under an open-source licence, LICENSE.md present, reproducible, datasets excluded. Code must run out of the box.
- README.md of at most 1,000 words with at most two figures or tables in total. The README holds the evidence and technical detail.
- One-minute public YouTube video, presented and voiced by Amin: the problem, what was built or found, why it matters.
- Submission through the Pretalx form with the GitHub and YouTube URLs; region USA (Boston final); sport football.

## Order of work

3a. Package and adapter. 3b. Figures. 3c. README (with 3c.0, one report-only line, first). 3h. What would have been enough. 3d. Video script and shot list. 3e. Reproducibility check from a fresh clone. 3f. Fresh-reader review and revision. 3g. Submission checklist.

Stops for Amin: after 3b (choose Figure 2), after 3c (read the README draft), after 3h (the distributions and four figures), after 3f (review results).

## 3c.0. One report-only line before the README

The static expectation shares the temperature fitted for the dynamic model, which is the right nesting for the decomposition but flatters V2. Fit a separate temperature for the static reach times on the exploration episodes by the same leave-one-match-out procedure (exploration only, logged, frozen), apply it to the test episodes, and report its log-loss next to B1 and the dynamic model, with the per-match count. The README states V2 against this line and against B1. Nothing else changes; the decomposition keeps the shared temperature, and DESIGN.md says why in one sentence.

## 3a. Package and adapter

Public API of looseball, each a documented function with a docstring stating inputs, outputs and the DESIGN.md section it implements:

- find_episodes(possessions, tracking, ...) returns the episode table: pairs, trigger class, legs, contacts, anchor, lead, pickup point, immediate flag, camera-gate flag. Inputs are DataBallPy-shaped tracking and event tables; adapters/skillcorner.py builds them from the open-data files. The function must not depend on SkillCorner column names anywhere outside the adapter.
- reach_times(episodes, tracking, radius=15.0, turning_penalty="shaw", reaction=0.7, top_speed=5.0, smoothing_window=5) returns per-player static and dynamic reach times at the anchor.
- expectations(reach, parameters) returns p_static and p_dynamic per team per episode. The frozen parameters ship inside the package as a JSON file (the values from audit/frozen_parameters.json); refitting is a separate function that is never called by the reproduction path.
- decompose(expectations, outcomes) returns the deficit and credit shares and the categorical verdict.
- team_report(decomposed) returns the team-level shares with bootstrap intervals (episodes resampled within match, 2,000 replicates, seed logged).
- export_clips(decomposed, ...) writes the timestamp table (match id, period, clock, anchor frame, losing team, verdict).
- A command-line entry point, looseball reproduce --data PATH --out PATH, that regenerates every MT1 table and both figures from the open-data clone, exactly, and nothing else. A second command, looseball run --data PATH --match ID, produces the team report and clip export for one match.

Also: pyproject with DataBallPy pinned at develop 3f9de8d; LICENSE.md, MIT (matches the data licence and the DataBallPy ecosystem; Amin confirms); tests for every public function on synthetic data; a test that fails if README.md exceeds 1,000 words (markdown stripped, figure captions counted) or contains more than two figures or tables; a test that the frozen parameters in the package equal audit/frozen_parameters.json.

Nothing from this conversation or from AUDIT.md's post hoc log is removed; AUDIT.md and DESIGN.md stay in the repository as the record. The commit history stays as it is.

## 3b. Figures

Figure 1, the worked episode. From match 1927964, draw one lost ball by seed among those with a reading or positioning verdict (log the seed and the episode id). One panel, the anchor frame: the pitch section around the pickup point; both teams' players with smoothed velocity arrows; detected and extrapolated players distinguished; the ball path from release to pickup; the pickup point; the dynamic reach-time difference between the teams as a filled contour (who gets to each point first, and by how much); a caption of at most 40 words stating the three numbers (p_static, p_dynamic, verdict) in coaching words.

Figure 2, two versions, both drawn from audit/mt1_test:
- Version A, two panels. Left: the 12 test-set teams, categorical verdict shares over their lost loose balls as stacked horizontal bars with the interval on the positioning share, teams with two matches or fewer marked. Right: the per-match log-loss of the four models (B0, B1, static, dynamic) across the 15 test matches, one point per match per model, connected within match, so the 15 of 15 reads without a table.
- Version B, one panel: the left panel of A alone, with the validation numbers left to the README prose.

Figure standard: readable at README width on GitHub; colour-blind-safe palette; team short names; no em dashes in any label or caption; the figure script is part of the reproduce path. Save both versions under figures/ with the version in the name. Stop and show both to Amin.

## 3c. README (at most 1,000 words, two figures)

Sections, in this order, with the numbers taken from AUDIT.md and audit/mt1_test and nothing rounded beyond one decimal:

1. The answer. Four sentences: the coach's question; the data (20 A-League 2024/25 broadcast-tracking matches, 5 to build and 15 held out); the headline with its qualifier, in this form: on the 15 held-out matches, 69.0% of lost loose balls were already lost on positioning by the time the drop zone came into view, 13.5% on reading, 17.6% in the race itself; what the package does.
2. What a loose ball is here. The definition (a release after which nobody controls the ball directly); the trigger classes in plain words; about 100 a match; what is excluded and why (clean receptions and interceptions, held saves, contests shorter than half a second).
3. How a lost ball is read. The anchor and why the broadcast forces it (the camera follows the ball; at release the drop zone is off screen for a third of episodes); the three nested expectations, one sentence each; what each verdict means in coaching terms; the sentence that the verdicts are parameter-free (with no intercept, the expectation is one half exactly when the two best reach times are equal, whatever the fitted slope), so only the continuous shares depend on the one fitted value.
4. What held. V1, V2, V3 and the camera gate as numbers in prose; the gated against ungated comparison; one sentence reconciling V2's size with the reading share (movement matters for who wins, and flips a favourable position in about one lost ball in seven); one sentence on prior work (second balls studied with event data by Sears 2025 and Lamberts 2025; a tracking-based decomposition of why a loose ball was lost is new).
5. For the coaching staff. The clip export and what to do with it; the worked match in one sentence; how each verdict maps to a training week, three short clauses; one sentence on "what would have been enough" (section 3h): for each lost ball the clip table also gives the smallest change under the model that would have made the team the favourite, one player, how far or which way.
6. Limitations. First-sight anchor (positioning means positioning when the drop zone came into view, not shape before the kick); clearances (55.7% dropped by the camera gate, 30 remain); velocity enters the reach model only as drift during the reaction window; calibration is slightly under-confident at the fitted slope; team level only, 1 to 5 matches per team; one league.
7. Reproduce and reuse. Install; the data clone command with the commit; the one reproduce command with its run time and memory; the adapter and how another provider would plug in; what a DataBallPy contribution would add. One future-work sentence: what the players should have done tactically needs a model of team behaviour and the coach's game model (positional optimisation as in Shah 2026, or learned typical movement as in Le et al. 2017), and is not attempted here. A closing line crediting SkillCorner and PySport for the data and DataBallPy for the reach model.

Style: no em dashes; no bullet lists inside sections 1 to 6; numbers carry their units; no claim without a number from AUDIT.md behind it; nothing about the project's history or the earlier entries. Stop and hand the draft to Amin with the word count.

## 3h. What would have been enough

An extension of the decomposition, not a second idea. For every lost loose ball with a positioning or reading verdict, the smallest change to one player of the losing team that would have made that team the favourite under the frozen reach model. Nothing is fitted; it is a deterministic function of the model already validated. It is never called "what should have happened".

Definitions. The verdicts are parameter-free: the losing team becomes the favourite exactly when its best dynamic reach time drops to the winner's best dynamic reach time. Let the deficit be D = (losing team's best time) minus (winning team's best time), in seconds, with D > 0 for every such ball.

- Metres short: 5 m/s times D, the distance the best-placed losing player would have needed to start closer along the line from his drifted position (position plus 0.7 s of his velocity) to the pickup point. Exact under the frozen model, which has no turning term (DataBallPy's "shaw" option is reaction plus distance from the drifted position over top speed); report for every lost ball with a verdict. Corrected 2026-11-17; the 3h definitions as frozen are in DESIGN.md.
- Redirection: for each losing player, keep his speed and point his velocity at the pickup point; recompute his reach time; the flip is achieved if it is at most the winner's best time. Among the players for whom it is, take the smallest angle change. Report the player, the angle, and the new reach time.
- The "enough" change for a ball: the redirection with the smallest angle if any redirection suffices; otherwise the displacement of the best-placed player by the metres short. Record the type (redirect or move), the player, and the magnitude. For after-the-anchor verdicts there is nothing to compute; the model already favoured the losing team.

Columns added to the clip export: deficit_s, metres_short, enough_type, enough_player, enough_magnitude (degrees or metres). The reproduce path regenerates them.

Checks, report-only, logged before they run: the distribution of metres short and of the angle change, by verdict and by trigger; the share of reading verdicts that one redirection fixes; stability of the enough change under the V3 variants (share of balls where the type and the player are unchanged; rank correlation of the magnitude); and the share of balls where the enough player is extrapolated at the anchor. If the median metres short is above 10 m the model is saying something other than "nearly there", and that is reported, not adjusted.

Animation: looseball animate --match ID --episode N --out FILE writes a short clip. First half, as recorded: the frames from the anchor to the pickup, both teams, arrows, the shading recomputed each frame. Second half, labelled "model: one change": the anchor frame with the enough change applied and the shading recomputed, then the altered player moving on the altered path at the model's speed while every other player follows the recorded track. The label stays on screen for the whole second half. Four animations drawn by seed (two reading, two positioning) for Amin to check; the one used in the video is chosen from them.

## 3d. Video script and shot list

Sixty seconds, about 140 words, written for Amin's voice, with a shot list that uses only Figure 1, Figure 2, one animation from 3h and screen captures of the clip export: 0 to 10 s the coach's question and what a loose ball is; 10 to 30 s the mechanism on Figure 1 (anchor, contours, arrows, the three numbers); 30 to 42 s the animation, as recorded and then with the one change; 42 to 52 s the headline and what a coach does with it; 52 to 60 s the package, the repository name, the held-out validation in one clause. No sentence in the script that is not also in the README.

## 3e. Reproducibility check

From a fresh clone in a clean virtual environment, following only the README: install, clone the data at the stated commit, run looseball reproduce, and diff every regenerated table and figure against the committed ones. Record the environment, the run time and any step that needed knowledge not in the README; those steps are README bugs and are fixed in 3f.

## 3f. Fresh-reader review

The README and the public repository go to a reader who has not seen the project (Amin's outside readers), with this ask: score each of the five criteria out of 20 with two sentences of reasons; name the three sentences that are weakest or least clear; say what a coach would do with the result on Monday; say what the entry claims that the evidence does not support. Revise, re-check the word count, repeat 3e if the README changed.

## 3g. Submission checklist

Repository public; LICENSE.md present; data excluded and gitignored; README within limits (the test passes); both figures render on GitHub; video public on YouTube, voiced by Amin, under 60 s; a tagged release (v1.0.0) at the submitted commit; Pretalx form filled with the two URLs, region USA, sport football; the repository stays frozen at the tag after submission.
