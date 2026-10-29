import numpy as np
import pandas as pd
import pytest

from looseball_research.velocities import smooth_velocities


def _track(player_id, frames, x, y, detected=True):
    return pd.DataFrame({"frame": frames, "player_id": player_id, "x": x, "y": y, "is_detected": detected})


def test_constant_velocity_is_exact_including_track_ends():
    f = np.arange(100, 130)
    t = (f - f[0]) / 10
    v = smooth_velocities(_track(7, f, 1 + 3 * t, 2 - 4 * t))
    assert np.allclose(v["vx"], 3.0) and np.allclose(v["vy"], -4.0)
    assert np.allclose(v["speed"], 5.0)


def test_quadratic_track_derivative_is_exact_for_order_two():
    f = np.arange(0, 40)
    t = f / 10
    v = smooth_velocities(_track(1, f, t**2, np.zeros_like(t)))
    assert np.allclose(v["vx"], 2 * t)


def test_tracks_split_at_gaps_and_short_tracks_have_no_velocity():
    a = _track(1, np.arange(0, 10), np.arange(10) * 0.5, np.zeros(10))  # 5 m/s
    b = _track(1, np.arange(20, 23), [0.0, 9.0, 0.0], [0.0, 0.0, 0.0])  # 3 frames, after a gap
    c = _track(2, np.arange(0, 10), np.zeros(10), np.arange(10) * -0.2)  # -2 m/s in y
    v = smooth_velocities(pd.concat([b, c, a]))
    p1 = v[v["player_id"] == 1].set_index("frame")
    assert np.allclose(p1.loc[0:9, "vx"], 5.0)
    assert p1.loc[20:22, "vx"].isna().all()
    assert np.allclose(v.loc[v["player_id"] == 2, "vy"], -2.0)


def test_window_seven_variant_and_invalid_windows():
    f = np.arange(0, 20)
    v = smooth_velocities(_track(3, f, f * 0.1, f * 0.0), window=7)
    assert np.allclose(v["vx"], 1.0)
    for bad in (4, 1):
        with pytest.raises(ValueError):
            smooth_velocities(_track(3, f, f * 0.1, f * 0.0), window=bad)


def test_smoothing_reduces_frame_to_frame_noise():
    rng = np.random.default_rng(0)
    f = np.arange(0, 400)
    x = f * 0.5 + rng.normal(0, 0.05, len(f))
    v = smooth_velocities(_track(4, f, x, np.zeros(len(f))))
    raw = np.diff(x) * 10
    assert v["vx"].std() < raw.std()
    assert abs(v["vx"].mean() - 5.0) < 0.05
