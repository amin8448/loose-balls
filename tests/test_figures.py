import numpy as np
import pandas as pd

from looseball import figures
from looseball.decompose import SHARES


def test_caption_states_the_numbers_within_forty_words():
    for verdict in ("positioning", "reading"):
        text = figures.caption("Wellington Phoenix Football Club", 0.6713, 0.2342, verdict)
        assert len(text.split()) <= figures.MAX_CAPTION_WORDS
        assert "67.1%" in text and "23.4%" in text and verdict in text
        assert chr(0x2014) not in text  # no em dash


def test_seeded_draw_is_fixed_and_only_reading_or_positioning():
    eps = pd.DataFrame(
        {
            "match_id": [figures.WORKED_MATCH] * 6 + [1],
            "seq_i": [5, 1, 9, 3, 7, 2, 4],
            "verdict": [
                "reading",
                "after the anchor",
                "positioning",
                "reading",
                "after the anchor",
                "positioning",
                "reading",
            ],
        }
    )
    a, b = figures.draw_episode(eps), figures.draw_episode(eps.sample(frac=1, random_state=3))
    assert a["seq_i"] == b["seq_i"] and a["match_id"] == figures.WORKED_MATCH
    assert a["verdict"] in ("reading", "positioning")


def test_figure2_versions_render(tmp_path):
    rng = np.random.default_rng(0)
    teams = pd.DataFrame(
        {"team": ["One", "Two", "Three"], "sample-size flag": ["flag", np.nan, np.nan], "lost": [10, 20, 30]}
    )
    shares = rng.dirichlet([5, 1, 2], 3)
    for k, v in enumerate(SHARES):
        teams[v] = shares[:, k]
        teams[f"{v} lo"], teams[f"{v} hi"] = shares[:, k] * 0.8, np.minimum(shares[:, k] * 1.2, 1)
    episodes = pd.DataFrame({"match_id": np.repeat([1, 2], 20), "releasing_won": rng.integers(0, 2, 40)})
    for col in ("p_B0", "p_B1", "p_static", "p_dynamic"):
        episodes[col] = rng.uniform(0.05, 0.95, 40)
    out = figures.figure2(teams, episodes, tmp_path)
    assert (tmp_path / out["files"]["A"]).stat().st_size > 0 and (
        tmp_path / out["files"]["B"]
    ).stat().st_size > 0
