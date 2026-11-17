"""Command line.

looseball reproduce --data PATH --out PATH
    Regenerate every MT1 table and figure from the SkillCorner open-data clone at PATH.
looseball run --data PATH --match ID [--out PATH]
    Team report and clip export for one match, with the frozen parameters; clips_enough.csv adds
    the 3h columns (report-only).
"""

import argparse
from pathlib import Path

import pandas as pd

from looseball import decompose, expectations, export_clips, find_episodes, reach_times, team_report
from looseball.adapters.skillcorner import load_match
from looseball.enough import enough
from looseball.export_clips import export_clips_enough, match_clock


def run_match(data, match_id: int, out) -> dict:
    """One match: episodes, reach times, expectations, decomposition, team report and clips."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    m = load_match(data, match_id)
    ep = find_episodes(m.possessions, m.tracking, m.players)
    ep.to_csv(out / "episodes.csv", index=False)
    a = ep[ep["anchored"].astype(bool) & ep["kept"].astype(bool) & ~ep["immediate"].astype(bool)]
    summary = {"match": int(match_id), "episodes": len(ep), "analysed lost balls": len(a)}
    if a.empty:
        return summary
    reach = reach_times(a, m.tracking, m.players)
    e = expectations(reach)
    d = decompose(e, a[["match_id", "seq_i"]].assign(winning_team=a["team_id_next"].to_numpy()))
    d.to_csv(out / "decomposed.csv", index=False, float_format="%.4f")
    rep = team_report(d, team_names=m.team_names, matches_per_team={m.home_team_id: 1, m.away_team_id: 1})
    rep["verdicts"].to_csv(out / "team_verdicts.csv", index=False, float_format="%.4f")
    rep["shares"].to_csv(out / "team_shares.csv", index=False, float_format="%.4f")
    clocks = {m.match_id: match_clock(m.tracking)}
    export_clips(d, a, clocks, path=out / "clips.csv")
    balls = d[["match_id", "seq_i", "loser_side", "verdict"]].merge(
        a[["match_id", "seq_i", "pickup_x", "pickup_y"]], on=["match_id", "seq_i"], validate="1:1"
    )
    export_clips_enough(d, a, clocks, enough(reach, balls), path=out / "clips_enough.csv")
    summary["verdicts"] = d["verdict"].value_counts().to_dict()
    summary["bootstrap seed"] = rep["seed"]
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="looseball", description="Which team gets to a loose ball, and why."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("reproduce", help="regenerate every MT1 table and figure from the open-data clone")
    rep.add_argument("--data", required=True, help="path to the SkillCorner opendata clone")
    rep.add_argument("--out", required=True, help="output directory")
    run = sub.add_parser("run", help="team report and clip export for one match")
    run.add_argument("--data", required=True, help="path to the SkillCorner opendata clone")
    run.add_argument("--match", required=True, type=int, help="match id")
    run.add_argument("--out", default=None, help="output directory (default: looseball_<match id>)")
    args = parser.parse_args(argv)

    if args.command == "reproduce":
        from looseball.reproduce import reproduce

        summary = reproduce(args.data, args.out)
        print(pd.Series(summary).to_string())
        print(f"written to {args.out}")
    else:
        out = args.out or f"looseball_{args.match}"
        for k, v in run_match(args.data, args.match, out).items():
            print(f"{k}: {v}")
        print(f"written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
