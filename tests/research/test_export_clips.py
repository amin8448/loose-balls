import pandas as pd

from looseball_research.export_clips import COLUMNS, export_clips


def test_export_columns_order_and_clock_lookup():
    table = pd.DataFrame(
        {
            "match_id": [2, 1, 1],
            "period": [1, 2, 1],
            "frame": [50, 900, 30],
            "team": [10, 20, 10],
            "verdict": ["reading", "positioning", "after the anchor"],
        }
    )
    clocks = {1: pd.Series({30: "00:00:02.00", 900: "00:01:29.00"}), 2: pd.Series({50: "00:00:04.00"})}
    out = export_clips(table, clocks)
    assert list(out.columns) == COLUMNS
    assert list(zip(out["match_id"], out["frame"])) == [(1, 30), (1, 900), (2, 50)]
    assert list(out["clock"]) == ["00:00:02.00", "00:01:29.00", "00:00:04.00"]
    assert list(out["verdict"]) == ["after the anchor", "positioning", "reading"]
