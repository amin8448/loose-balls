"""3c.0: a separate temperature for the static reach times, fitted on the exploration matches only.

Same procedure as S3: leave-one-match-out log-loss on the exploration analysis set, then a fit
on the whole set, frozen in audit/frozen_static_temperature.json. Report-only; the
decomposition keeps the shared temperature.
"""

import json

import pandas as pd
from step2_common import analysis_set, episode_table

from looseball_research import expectation as ex
from looseball_research import paths

OUT = paths.AUDIT_DIR / "frozen_static_temperature.json"


def main() -> None:
    t = analysis_set(episode_table())
    y, match = t["releasing_won"].to_numpy(), t["match_id"].to_numpy()
    dt_static = ex.features(t, "static")["dt"]
    lomo = ex.leave_one_match_out(dt_static, y, match, intercept=False)
    row = {"model": "static, own temperature", "pooled": ex.log_loss(y, lomo)}
    row.update({str(m): ex.log_loss(y[match == m], lomo[match == m]) for m in sorted(set(match))})
    print(f"exploration analysis set: {len(t)} episodes\n")
    print("Leave-one-match-out log-loss on the exploration analysis set:\n")
    print(pd.DataFrame([row]).to_markdown(index=False, floatfmt=".4f"))
    a, b = ex.fit(dt_static, y, intercept=False)
    frozen = {"form": "softmax", "feature": "static best-time difference", "a": a, "b": b,
              "fitted on": "exploration analysis set, 326 episodes (3c.0, report-only)"}  # fmt: skip
    OUT.write_text(json.dumps(frozen, indent=2) + "\n")
    print(
        f"\nfrozen: b_static = {b:.4f} per second (temperature {1 / b:.4f} s), in {OUT.relative_to(paths.ROOT)}"
    )


if __name__ == "__main__":
    main()
