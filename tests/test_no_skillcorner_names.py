"""Nothing in looseball outside adapters/ may reference a SkillCorner field name.

The list holds every SkillCorner field the adapter reads that DataBallPy does not use itself
(decided before the package was written, AUDIT.md step 3). Distinctive names are matched as
whole words anywhere in the source; generic words are matched as exact string literals.
"period" is not listed: it is the MT1 clip-export header, kept so reproduce matches exactly.
"""

import ast
import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "looseball"

DISTINCTIVE = [
    "event_type", "start_type", "end_type", "pass_outcome", "is_header", "game_interruption_before",
    "game_interruption_after", "player_position", "frame_start", "frame_end", "x_start", "y_start",
    "attacking_side", "fully_extrapolated", "ball_data", "image_corners_projection", "player_data",
    "is_detected", "player_role", "trackable_object", "match_periods", "home_team_side", "short_name",
    "date_time", "pitch_length", "pitch_width",
    *[f"{a}_{c}" for a in ("x", "y") for c in ("top_left", "top_right", "bottom_left", "bottom_right")],
]  # fmt: skip
GENERIC = ["index", "timestamp", "number", "acronym", "possession"]


def _package_files():
    return [p for p in PACKAGE.rglob("*.py") if "adapters" not in p.relative_to(PACKAGE).parts]


def test_no_skillcorner_field_outside_the_adapter():
    found = []
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, DISTINCTIVE)) + r")\b")
    for path in _package_files():
        text = path.read_text()
        found += [(path.name, m.group(1)) for m in pattern.finditer(text)]
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in GENERIC:
                found.append((path.name, node.value))
    assert not found, f"SkillCorner field names outside the adapter: {found}"


def test_the_adapter_does_use_them():
    text = (PACKAGE / "adapters" / "skillcorner.py").read_text()
    assert all(
        name in text for name in ("start_type", "is_detected", "image_corners_projection", "ball_data")
    )
