"""Metadata, roster, dynamic events and phases of play, read through the guard."""

import json

import pandas as pd

from looseball_research import guard


def load_metadata(match_id: int) -> dict:
    with open(guard.match_path(match_id, "match")) as f:
        return json.load(f)


def load_roster(match_id: int) -> pd.DataFrame:
    meta = load_metadata(match_id)
    return pd.json_normalize(meta["players"], sep=".")


def load_events(match_id: int) -> pd.DataFrame:
    return pd.read_csv(guard.match_path(match_id, "events"), low_memory=False)


def load_phases(match_id: int) -> pd.DataFrame:
    return pd.read_csv(guard.match_path(match_id, "phases"), low_memory=False)
