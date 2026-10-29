"""The parameters shipped in the package are the ones frozen before MT1."""

import json
from pathlib import Path

from looseball.expectation import frozen_parameters

AUDIT_FILE = Path(__file__).resolve().parents[1] / "audit" / "frozen_parameters.json"


def test_package_parameters_equal_the_frozen_file():
    assert frozen_parameters() == json.loads(AUDIT_FILE.read_text())


def test_frozen_values_as_logged():
    p = frozen_parameters()
    assert p["chosen_form"] == "softmax" and p["chosen"] == p["softmax"]
    assert p["chosen"]["a"] == 0.0 and round(p["chosen"]["b"], 4) == 2.9273
