"""Step 3h diagnostics D1 to D3 on the test analysis set (report-only; AUDIT.md "3h diagnostics D1
to D3: procedure").

Usage: python scripts/s3h_diagnostics.py [OUT]   (default audit/s3h_diagnostics)

D1: balls with nobody of either team in the 15 m race at the anchor, compared with the balls whose
p_static and p_dynamic are both 0.5000. D2: pickup point and anchor-frame ball outside the pitch
markings (and more than 1 m outside). D3: the largest share of detected-ball window frames on which
one player is within 1.5 m of the ball, and that player's role.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from looseball import find_episodes, reach_times
from looseball.adapters.skillcorner import load_match
from looseball.episodes import long_players
from looseball.reproduce import TEST_MATCHES
from looseball.schema import FPS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "opendata"
KEY = ["match_id", "seq_i"]
NEAR = 1.5  # metres
MIN_WINDOW_FRAMES = 20  # 2 s
STAY = 0.70


def md(t: pd.DataFrame, floatfmt: str = ".3f") -> str:
    return t.to_markdown(index=False, floatfmt=floatfmt)


def outside(x, y, length, width, margin=0.0):
    return (np.abs(x) > length / 2 + margin) | (np.abs(y) > width / 2 + margin)


def match_rows(mid: int, record: pd.DataFrame) -> list[dict]:
    m = load_match(DATA, mid)
    ep = find_episodes(m.possessions, m.tracking, m.players, radius=15.0)
    a = ep[ep["anchored"].astype(bool) & ep["kept"].astype(bool) & ~ep["immediate"].astype(bool)]
    a = a.reset_index(drop=True)
    want = set(record.loc[record["match_id"] == mid, "seq_i"])
    if set(a["seq_i"]) != want:
        raise SystemExit(f"match {mid}: analysis set differs from audit/mt1_test/episodes.csv")
    reach = reach_times(a, m.tracking, m.players)
    empty = reach.groupby(KEY)["empty_team"].agg(lambda s: bool(s.astype(bool).all()))
    length, width = m.pitch_dimensions
    tr = m.tracking
    bx, by = tr["ball_x"].to_numpy(dtype=float), tr["ball_y"].to_numpy(dtype=float)
    bdet = tr["ball_detected"].fillna(False).to_numpy(dtype=bool)
    pl = long_players(tr)
    pf, px, py, pc = (
        pl["frame"].to_numpy(),
        pl["x"].to_numpy(float),
        pl["y"].to_numpy(float),
        pl["column_id"].to_numpy(),
    )
    column_of = m.players.set_index("id")["column_id"]
    team_of = m.players.set_index("column_id")["team_id"]
    rows = []
    for e in a.itertuples(index=False):
        rec = record[(record["match_id"] == mid) & (record["seq_i"] == e.seq_i)].iloc[0]
        rel, pk, anc = int(e.release_frame), int(e.pickup_frame), int(e.anchor_frame)
        frames = np.arange(rel + 1, pk + 1)
        frames = frames[bdet[frames] & np.isfinite(bx[frames]) & np.isfinite(by[frames])]
        counts: dict = {}
        for f in frames:
            lo, hi = np.searchsorted(pf, [f, f + 1])
            near = np.hypot(px[lo:hi] - bx[f], py[lo:hi] - by[f]) <= NEAR
            for c in set(pc[lo:hi][near]):
                counts[c] = counts.get(c, 0) + 1
        if counts and len(frames):
            top = max(counts.values())
            player = min(c for c, n in counts.items() if n == top)
            share = top / len(frames)
            winner_col = column_of.get(e.player_id_next)
            team = team_of.get(player)
            role = (
                "winner"
                if player == winner_col
                else "losing team"
                if team == rec["losing_team"]
                else "winning team, not the winner"
                if team == rec["winning_team"]
                else "unknown"
            )
        else:
            share, player, role = (0.0 if len(frames) else np.nan), None, None
        ax, ay = bx[anc], by[anc]
        rows.append(
            {
                "match_id": mid,
                "seq_i": e.seq_i,
                "trigger": rec["trigger"],
                "verdict": rec["verdict"],
                "p_half": bool(rec["p_static"] == 0.5 and rec["p_dynamic"] == 0.5),
                "d1_nobody_in_race": bool(empty.loc[(mid, e.seq_i)]),
                "pickup_outside": bool(outside(e.pickup_x, e.pickup_y, length, width)),
                "pickup_outside_1m": bool(outside(e.pickup_x, e.pickup_y, length, width, 1.0)),
                "anchor_ball_missing": not (np.isfinite(ax) and np.isfinite(ay)),
                "anchor_ball_detected": bool(bdet[anc]),
                "anchor_ball_outside": bool(np.isfinite(ax) and outside(ax, ay, length, width)),
                "anchor_ball_outside_1m": bool(np.isfinite(ax) and outside(ax, ay, length, width, 1.0)),
                "window_s": (pk - rel) / FPS,
                "detected_window_frames": len(frames),
                "d3_share": share,
                "d3_player": player,
                "d3_role": role,
            }
        )
    return rows


def by(t: pd.DataFrame, col: str, flags: list[str]) -> str:
    out = []
    for key in ("verdict", "trigger"):
        g = t.groupby(key)
        rows = [{key: k, "balls": len(d), **{f: int(d[f].sum()) for f in flags},
                 **{f"{f} share": d[f].mean() for f in flags}} for k, d in g]  # fmt: skip
        rows.append({key: "all", "balls": len(t), **{f: int(t[f].sum()) for f in flags},
                     **{f"{f} share": t[f].mean() for f in flags}})  # fmt: skip
        out.append(md(pd.DataFrame(rows)))
    return f"{col}:\n\n" + "\n\n".join(out) + "\n"


def main(out_dir: str | None) -> None:
    out = Path(out_dir) if out_dir else ROOT / "audit" / "s3h_diagnostics"
    out.mkdir(parents=True, exist_ok=True)
    record = pd.read_csv(ROOT / "audit" / "mt1_test" / "episodes.csv")
    t = pd.DataFrame([r for mid in TEST_MATCHES for r in match_rows(mid, record)])
    t.to_csv(out / "diagnostics.csv", index=False, float_format="%.4f")
    text = [f"Diagnostics on the test analysis set: {len(t)} lost balls.\n"]

    d1 = t[t["d1_nobody_in_race"]]
    text.append(f"D1. Balls with nobody of either team in the 15 m race at the anchor: {len(d1)}.\n")
    for key in ("verdict", "trigger"):
        text.append(md(d1[key].value_counts().rename_axis(key).reset_index(name="balls"), ".0f") + "\n")
    both = int((t["d1_nobody_in_race"] & t["p_half"]).sum())
    text.append(
        f"Against the {int(t['p_half'].sum())} balls with p_static and p_dynamic both 0.5000: {both} are in both sets; "
        f"{int((t['d1_nobody_in_race'] & ~t['p_half']).sum())} D1 balls are not among them; "
        f"{int((~t['d1_nobody_in_race'] & t['p_half']).sum())} of them are not D1 balls.\n"
    )

    text.append("D2. Outside the pitch markings (each match's pitch size; origin at the centre).\n")
    text.append(by(t, "Pickup point", ["pickup_outside", "pickup_outside_1m"]))
    text.append(
        f"Ball on the anchor frame: position missing on {int(t['anchor_ball_missing'].sum())} balls; ball detected on "
        f"{int(t['anchor_ball_detected'].sum())} of {len(t)} anchor frames.\n"
    )
    text.append(by(t, "Ball on the anchor frame", ["anchor_ball_outside", "anchor_ball_outside_1m"]))

    s = t["d3_share"].dropna()
    q = s.quantile([0.1, 0.25, 0.5, 0.75, 0.9])
    text.append(
        f"D3. Largest share of detected-ball window frames with one player within 1.5 m of the ball: "
        f"{len(s)} balls with a detected window frame ({int(t['d3_share'].isna().sum())} without); "
        f"p10 {q[0.1]:.3f}, p25 {q[0.25]:.3f}, p50 {q[0.5]:.3f}, p75 {q[0.75]:.3f}, p90 {q[0.9]:.3f}; "
        f"share at least 0.70 on {int((s >= STAY).sum())} balls.\n"
    )
    long_w = t[t["window_s"] >= MIN_WINDOW_FRAMES / FPS]
    stay = long_w[long_w["d3_share"] >= STAY]
    text.append(
        f"Balls with a window of at least 2 s: {len(long_w)}; of them, one player within 1.5 m on at least 70% of "
        f"the detected-ball frames: {len(stay)}. By trigger and that player's role:\n"
    )
    if stay.empty:
        text.append("none\n")
    else:
        tab = pd.crosstab(stay["trigger"], stay["d3_role"], margins=True, margins_name="all")
        tab = tab.join(long_w["trigger"].value_counts().rename("balls with a 2 s window"), how="left")
        tab.loc["all", "balls with a 2 s window"] = len(long_w)
        text.append(md(tab.reset_index(), ".0f") + "\n")
        verdicts = pd.crosstab(stay["verdict"], stay["d3_role"], margins=True, margins_name="all")
        text.append(md(verdicts.reset_index(), ".0f") + "\n")
    (out / "report.md").write_text("\n".join(text))
    print("\n".join(text))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
