"""S3: the expectation model on the exploration analysis set.

Leave-one-match-out log-loss for softmax, logistic, B0 and B1 on dynamic best times; the form
with the lower pooled log-loss is chosen; all four are frozen by a fit on the whole analysis
set and written to audit/frozen_parameters.json. Calibration table of the chosen form on its
leave-one-match-out predictions. The constant-acceleration model (report-only) gets its own
frozen fit of the chosen form.
"""

import numpy as np
import pandas as pd
from step2_common import analysis_set, episode_table, save_frozen

from looseball_research import expectation as ex


def main() -> None:
    t = analysis_set(episode_table())
    y, match = t["releasing_won"].to_numpy(), t["match_id"].to_numpy()
    feats = ex.features(t, "dynamic")
    print(f"analysis set: {len(t)} episodes; releasing team won {y.mean():.3f}\n")

    table, preds = ex.compare(feats, y, match)
    print(
        "S3a. Leave-one-match-out log-loss on the analysis set (dynamic best times for softmax and logistic):\n"
    )
    print(table.to_markdown(index=False, floatfmt=".4f"))

    chosen = min(("softmax", "logistic"), key=lambda m: table.set_index("model").loc[m, "pooled"])
    print(f"\nchosen form: {chosen}\n")

    frozen = {"chosen_form": chosen}
    rows = []
    for name, (col, intercept) in ex.MODELS.items():
        a, b = ex.fit(feats[col], y, intercept)
        frozen[name] = {"feature": col, "intercept": intercept, "a": a, "b": b}
        rows.append({"model": name, "feature": col, "a (intercept)": a, "b (slope)": b,
                     "temperature 1/b": 1 / b if name == "softmax" else np.nan,
                     "in-sample log-loss": ex.log_loss(y, ex.predict((a, b), feats[col]))})  # fmt: skip
    frozen["chosen"] = frozen[chosen]
    print("S3b. Parameters fitted on the whole analysis set (frozen):\n")
    print(pd.DataFrame(rows).to_markdown(index=False, floatfmt=".4f"))

    print(f"\nS3c. Calibration of the chosen form ({chosen}), leave-one-match-out predictions:\n")
    print(ex.calibration(preds[chosen], y).to_markdown(index=False, floatfmt=".3f"))

    ca = episode_table(keys=t, model_name="constant_acceleration").set_index(["match_id", "seq_i"])
    ca = ca.loc[list(zip(t["match_id"], t["seq_i"]))].reset_index()
    ca_dt = ex.features(ca, "dynamic")["dt"]
    col, intercept = ex.MODELS[chosen]
    a, b = ex.fit(ca_dt, y, intercept)
    frozen["constant_acceleration"] = {
        "feature": "dt",
        "intercept": intercept,
        "a": a,
        "b": b,
        "form": chosen,
    }
    lomo_ca = ex.leave_one_match_out(ca_dt, y, match, intercept)
    print("\nS3d. Constant-acceleration model (report-only), chosen form fitted on its dynamic times:\n")
    print(pd.DataFrame([{"model": f"constant acceleration, {chosen}", "a (intercept)": a, "b (slope)": b,
                         "leave-one-match-out log-loss": ex.log_loss(y, lomo_ca),
                         "DataBallPy model, same form": table.set_index("model").loc[chosen, "pooled"]}]
                       ).to_markdown(index=False, floatfmt=".4f"))  # fmt: skip

    save_frozen(frozen)
    print("\nfrozen: audit/frozen_parameters.json")


if __name__ == "__main__":
    main()
