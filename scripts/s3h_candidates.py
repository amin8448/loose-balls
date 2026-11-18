"""Step 3h: animation candidates for the video, and the four seed 20261118 clips redrawn (AUDIT.md,
"3h animation revision: choices and draw rule, logged before the draw").

Usage: python scripts/s3h_candidates.py [OUT_DIR]   (default audit/animations_v2)

Candidates, from the committed records: lost balls of the test analysis set, sorted by match_id and
seq_i, with lead at least 1.5 s, ball path at least 10 m, D3 share below 0.70 and the pickup point
inside the pitch markings. Pools: A, positioning verdicts with enough_type move, metres_short at
least 2 m and the enough player detected; B, the same for reading verdicts; C, positioning verdicts
with enough_type no_player_in_race. Seed 20261119, one numpy default_rng: six from A, then six from
B, then three from C, without replacement; a pool smaller than asked is taken whole. Each is written
as a full-length clip (from the release) with a contact sheet. Then the four seed 20261118 balls
(audit/animations/animations.csv) are redrawn with the revised drawing, for the record.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from looseball.animate import animate

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "opendata"
SEED = 20261119
KEY = ["match_id", "seq_i"]
ASK = (
    ("A", "positioning", "move", 6),
    ("B", "reading", "move", 6),
    ("C", "positioning", "no_player_in_race", 3),
)


def table() -> pd.DataFrame:
    a = ROOT / "audit"
    clips = pd.read_csv(a / "s3h_test" / "clips_enough.csv")
    paths = pd.read_csv(a / "s3h_test" / "pathcheck.csv")[[*KEY, "ball_path_m"]]
    eps = pd.read_csv(a / "mt1_test" / "episodes.csv")[[*KEY, "lead_s", "trigger"]]
    diag = pd.read_csv(a / "s3h_diagnostics" / "diagnostics.csv")[[*KEY, "d3_share", "pickup_outside"]]
    t = (
        clips.merge(paths, on=KEY, validate="1:1")
        .merge(eps, on=KEY, validate="1:1")
        .merge(diag, on=KEY, validate="1:1")
    )
    return t.sort_values(KEY).reset_index(drop=True)


def pools(t: pd.DataFrame) -> dict:
    base = t[
        (t["lead_s"] >= 1.5)
        & (t["ball_path_m"] >= 10.0)
        & (t["d3_share"] < 0.70)
        & ~t["pickup_outside"].astype(bool)
    ]
    detected = base["enough_player_extrapolated"].astype(str) == "False"
    out = {}
    for name, verdict, kind, _ in ASK:
        p = base[(base["verdict"] == verdict) & (base["enough_type"] == kind)]
        if kind == "move":
            p = p[(p["metres_short"] >= 2.0) & detected.reindex(p.index)]
        out[name] = p.reset_index(drop=True)
    return out


def write(balls: pd.DataFrame, folder: Path, prefix: str) -> pd.DataFrame:
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for k, b in enumerate(balls.itertuples(index=False), start=1):
        stem = f"{prefix}_{k:02d}_{b.verdict}_{b.enough_type}_{int(b.match_id)}_{int(b.seq_i)}"
        info = animate(
            DATA, int(b.match_id), int(b.seq_i), folder / f"{stem}.mp4", sheet=folder / f"{stem}_sheet.png"
        )
        rows.append({"clip": k, "match_id": int(b.match_id), "seq_i": int(b.seq_i), "trigger": b.trigger,
                     "verdict": b.verdict, "enough_type": b.enough_type, "lead_s": b.lead_s, "ball_path_m": b.ball_path_m,
                     "metres_short": b.metres_short, "seconds": info["seconds"],
                     "frames before the anchor": info["frames before the anchor"],
                     "of them with the drop zone in view": info["frames before the anchor with the drop zone in view"],
                     "margin at the pickup after the change": info["margin at the pickup point after the change"],
                     "file": Path(info["file"]).name, "sheet": f"{stem}_sheet.png"})  # fmt: skip
    out = pd.DataFrame(rows)
    out.to_csv(folder / f"{prefix}.csv", index=False, float_format="%.4f")
    return out


def main(out_dir: str | None) -> None:
    out = Path(out_dir) if out_dir else ROOT / "audit" / "animations_v2"
    t = table()
    p = pools(t)
    rng = np.random.default_rng(SEED)
    drawn = []
    for name, _verdict, _kind, n in ASK:
        pool = p[name]
        take = rng.choice(len(pool), min(n, len(pool)), replace=False) if len(pool) else []
        print(f"pool {name}: {len(pool)} balls, {len(take)} drawn of {n} asked")
        drawn += [pool.loc[i] for i in take]
    cands = write(pd.DataFrame(drawn).reset_index(drop=True), out / "candidates", f"candidate_seed{SEED}")
    print(cands.drop(columns=["sheet"]).to_markdown(index=False, floatfmt=".2f"))
    old = pd.read_csv(ROOT / "audit" / "animations" / "animations.csv")[KEY]
    rerun = write(old.merge(t, on=KEY, validate="1:1"), out / "seed20261118", "rerun_seed20261118")
    print(rerun.drop(columns=["sheet"]).to_markdown(index=False, floatfmt=".2f"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
