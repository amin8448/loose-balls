"""looseball: which team gets to a loose ball, and why.

Public API, in pipeline order: find_episodes, reach_times, expectations, decompose,
team_report, export_clips. Inputs are the provider-neutral tables of looseball.schema;
looseball.adapters.skillcorner builds them from the SkillCorner open data.
"""

from looseball.decompose import decompose
from looseball.episodes import find_episodes
from looseball.expectation import expectations
from looseball.export_clips import export_clips
from looseball.race import reach_times
from looseball.report import team_report

__all__ = ["find_episodes", "reach_times", "expectations", "decompose", "team_report", "export_clips"]  # noqa: RUF022 (pipeline order)
