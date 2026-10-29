import numpy as np
import pandas as pd

from looseball import figures
from looseball.decompose import SHARES


def test_caption_states_the_numbers_within_forty_words():
    for verdict in ("positioning", "reading"):
        text = figures.caption("Wellington P FC", 0.6713, 0.2342, verdict)
        assert len(text.split()) <= figures.MAX_CAPTION_WORDS
        assert "67.1%" in text and "23.4%" in text and f"lost on {verdict}" in text
        assert "reaches each point first" in text and "Randomly drawn" in text
        assert chr(0x2014) not in text  # no em dash


def test_seeded_draw_is_fixed_and_respects_the_constraint():
    eps = pd.DataFrame(
        {
            "match_id": [figures.WORKED_MATCH] * 6 + [1],
            "seq_i": [5, 1, 9, 3, 7, 2, 4],
            "verdict": [
                "reading",
                "after the anchor",
                "positioning",
                "reading",
                "reading",
                "positioning",
                "reading",
            ],
            "lead_s": [2.0, 3.0, 1.6, 1.4, 2.5, 1.8, 2.0],
        }
    )
    paths = pd.Series({5: 12.0, 1: 30.0, 9: 15.0, 3: 20.0, 7: 9.0, 2: 11.0, 4: 40.0})
    (a, n), (b, _) = (
        figures.draw_episode(eps, paths),
        figures.draw_episode(eps.sample(frac=1, random_state=3), paths),
    )
    assert n == 3  # 5, 9 and 2: not 1 (after the anchor), 3 (lead 1.4 s), 7 (path 9 m), 4 (other match)
    assert a["seq_i"] == b["seq_i"] and a["seq_i"] in (5, 9, 2)


def test_ball_path_length_skips_missing_steps():
    t = pd.DataFrame({"ball_x": [0.0, 3.0, np.nan, 3.0, 6.0], "ball_y": [0.0, 4.0, np.nan, 4.0, 8.0]})
    assert figures.ball_path_length(t, 0, 4) == 10.0


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
