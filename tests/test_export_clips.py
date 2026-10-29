import pandas as pd

from looseball import export_clips
from looseball.export_clips import COLUMNS


def test_export_columns_order_clock_and_file(tmp_path):
    decomposed = pd.DataFrame(
        {
            "match_id": [2, 1, 1],
            "seq_i": [5, 9, 3],
            "losing_team": [10, 20, 10],
            "verdict": ["reading", "positioning", "after the anchor"],
        }
    )
    episodes = pd.DataFrame(
        {"match_id": [1, 1, 2], "seq_i": [3, 9, 5], "period_id": [1, 2, 1], "anchor_frame": [30, 900, 50]}
    )
    clocks = {1: pd.Series({30: "00:00:02.00", 900: "00:46:29.00"}), 2: pd.Series({50: "00:00:04.00"})}
    out = export_clips(decomposed, episodes, clocks, path=tmp_path / "clips.csv")
    assert list(out.columns) == COLUMNS
    assert list(zip(out["match_id"], out["frame"], out["period"])) == [(1, 30, 1), (1, 900, 2), (2, 50, 1)]
    assert list(out["clock"]) == ["00:00:02.00", "00:46:29.00", "00:00:04.00"]
    assert list(out["team"]) == [10, 20, 10]
    assert pd.read_csv(tmp_path / "clips.csv").shape == (3, 6)
