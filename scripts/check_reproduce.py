"""Compare a `looseball reproduce` output directory with the committed MT1 record.

Usage: python scripts/check_reproduce.py OUT

Every file of audit/mt1_test must be byte-identical in OUT, and OUT/report.md must equal the MT1
results logged in AUDIT.md (from "MT1 on the test matches" to the gate summary). Figures and the
Figure 1 caption, when present in OUT/figures, are compared byte for byte with figures/.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(out: Path) -> int:
    failures = []
    for f in sorted((ROOT / "audit" / "mt1_test").iterdir()):
        same = (out / f.name).exists() and (out / f.name).read_bytes() == f.read_bytes()
        print(f"{'identical' if same else 'DIFFERS  '}  {f.name}")
        failures += [] if same else [f.name]
    audit = (ROOT / "AUDIT.md").read_text()
    start = audit.index("MT1 on the test matches (15):")
    logged = audit[start : audit.index("\nGate verdicts.\n", start)].rstrip("\n")
    report = (out / "report.md").read_text().rstrip("\n") if (out / "report.md").exists() else ""
    same = report == logged
    print(
        f"{'identical' if same else 'DIFFERS  '}  report.md against AUDIT.md ({len(logged.splitlines())} lines)"
    )
    failures += [] if same else ["report.md"]
    if (out / "figures").exists():
        for f in sorted(p for p in (ROOT / "figures").iterdir() if p.is_file()):
            g = out / "figures" / f.name
            same = g.exists() and g.read_bytes() == f.read_bytes()
            print(f"{'identical' if same else 'DIFFERS  '}  figures/{f.name}")
            failures += [] if same else [f"figures/{f.name}"]
    print("all identical" if not failures else f"{len(failures)} differ: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
