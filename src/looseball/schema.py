"""The input tables of looseball: provider-neutral and DataBallPy-shaped.

An adapter (looseball.adapters) builds these from a provider's files; nothing else in the
package knows a provider's field names.

Tracking: one row per frame, frames consecutive from 0, in DataBallPy's TrackingData layout:
    frame, period_id, ball_x, ball_y, ball_z, and for every player column id c
    ("home_<shirt>" or "away_<shirt>"): c_x, c_y (pitch metres, origin at the centre).
    Extensions not in DataBallPy, which the episode definition needs:
    clock (match clock as text), ball_detected (bool), c_detected (bool: the player was seen by
    the camera rather than estimated), and the camera's view on the pitch as a polygon,
    camera_top_left_x, camera_top_left_y, camera_top_right_x, ..., camera_bottom_left_y
    (all NaN when the view is unknown).

Possessions: one row per player possession (a player in control of the ball):
    match_id, event_index (provider order, breaks ties), start_frame, end_frame, period_id,
    team_id, player_id, goalkeeper (bool), header (bool: the possession was a header),
    start_kind: how it started, one of START_KINDS,
    end_kind: how it ended, one of END_KINDS,
    end_result: for passes, one of END_RESULTS,
    interruption_before, interruption_after (bool: a stoppage is marked at that boundary).

Players: id, team_id, column_id (the tracking column id), position ("goalkeeper" for
goalkeepers, as in DataBallPy).
"""

START_KINDS = ("reception", "interception", "recovery", "kept", "restart", "unknown")
END_KINDS = ("pass", "shot", "clearance", "loss", "foul", "unknown")
END_RESULTS = ("success", "fail", "offside")
CORNERS = ("top_left", "top_right", "bottom_right", "bottom_left")
CAMERA_COLUMNS = [f"camera_{c}_{a}" for c in CORNERS for a in ("x", "y")]
FPS = 10
