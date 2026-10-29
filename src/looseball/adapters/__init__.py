"""Adapters from providers' files to the looseball tables (looseball.schema)."""

from dataclasses import dataclass

import pandas as pd


@dataclass
class Match:
    """One match in looseball tables."""

    match_id: int
    tracking: pd.DataFrame
    possessions: pd.DataFrame
    players: pd.DataFrame
    home_team_id: int
    away_team_id: int
    team_names: dict
    pitch_dimensions: tuple[float, float]
