"""Step 3h: the seeded draw of four test-set balls for the animation, and the four animations
(AUDIT.md, "3h animation: draw rule, logged before the draw").

Usage: python scripts/s3h_animations.py OUT_DIR

Pool, from the committed 3h test record and the MT1 record: lost balls of the test analysis set
with enough_type move, lead at least 1.5 s, ball path at least 10 m and the enough player detected
on the anchor frame, sorted by match_id and seq_i. Seed 20261118 (numpy default_rng, one
generator): two drawn without replacement from the positioning verdicts of the pool, then two from
the reading verdicts. Each is written by looseball animate with the default hold of 0.25 s.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from looseball.animate import animate

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "opendata"
SEED = 20261118
MIN_LEAD, MIN_PATH = 1.5, 10.0
KEY = ["match_id", "seq_i"]


def pool() -> pd.DataFrame:
    clips = pd.read_csv(ROOT / "audit" / "s3h_test" / "clips_enough.csv")
    paths = pd.read_csv(ROOT / "audit" / "s3h_test" / "pathcheck.csv")[[*KEY, "ball_path_m"]]
    eps = pd.read_csv(ROOT / "audit" / "mt1_test" / "episodes.csv")[[*KEY, "lead_s", "trigger"]]
    t = clips.merge(paths, on=KEY, validate="1:1").merge(eps, on=KEY, validate="1:1")
    t = t[
        (t["enough_type"] == "move")
        & (t["lead_s"] >= MIN_LEAD)
        & (t["ball_path_m"] >= MIN_PATH)
        & (t["enough_player_extrapolated"].astype(str) == "False")
    ]
    return t.sort_values(KEY).reset_index(drop=True)


def draw(p: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    picks = []
    for verdict in ("positioning", "reading"):
        sub = p[p["verdict"] == verdict].reset_index(drop=True)
        picks += [sub.loc[i] for i in rng.choice(len(sub), 2, replace=False)]
    return pd.DataFrame(picks).reset_index(drop=True)


def main(out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = pool()
    print(f"pool: {len(p)} balls ({(p['verdict'] == 'positioning').sum()} positioning, "
          f"{(p['verdict'] == 'reading').sum()} reading)")  # fmt: skip
    drawn = draw(p)
    rows = []
    for k, b in drawn.iterrows():
        name = f"animation_seed{SEED}_{k + 1}_{b.verdict}_{int(b.match_id)}_{int(b.seq_i)}.mp4"
        info = animate(DATA, int(b.match_id), int(b.seq_i), out / name)
        rows.append({"animation": k + 1, "match_id": int(b.match_id), "seq_i": int(b.seq_i), "trigger": b.trigger,
                     "verdict": b.verdict, "lead_s": b.lead_s, "ball_path_m": b.ball_path_m, "metres_short": b.metres_short,
                     "enough_player": b.enough_player, "file": Path(info["file"]).name, "seconds": info["seconds"],
                     "margin at the pickup after the change": info["margin at the pickup point after the change"]})  # fmt: skip
    table = pd.DataFrame(rows)
    table.to_csv(out / "animations.csv", index=False, float_format="%.4f")
    print(table.to_markdown(index=False, floatfmt=".2f"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "audit" / "animations"))
