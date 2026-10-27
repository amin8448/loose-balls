"""Repository paths and the two match sets.

Paths to files of a single match are not built here; they come from guard.match_path
and guard.cache_path, so that every read of match data passes the test-set rule.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OPENDATA = DATA / "opendata"
MATCHES_DIR = OPENDATA / "data" / "matches"
CACHE = DATA / "cache"
SPECS = DATA / "specs"
AUDIT_DIR = ROOT / "audit"
FIGURES = AUDIT_DIR / "figures"
AUDIT_MD = ROOT / "AUDIT.md"
DESIGN_MD = ROOT / "DESIGN.md"

EXPLORATION = (1886347, 1959846, 1996436, 1996435, 2007448)
TEST = (
    1874553,
    1899585,
    1925299,
    1927964,
    1953632,
    1986691,
    2006229,
    2006363,
    2007721,
    2010085,
    2011166,
    2013725,
    2015213,
    2016236,
    2017461,
)

# File name suffix of each raw file kind inside data/opendata/data/matches/<id>/.
RAW_SUFFIX = {
    "match": "_match.json",
    "events": "_dynamic_events.csv",
    "phases": "_phases_of_play.csv",
    "tracking": "_tracking_extrapolated.jsonl",
}

FPS = 10
