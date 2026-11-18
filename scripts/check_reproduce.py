"""Compare a `looseball reproduce` output directory with the committed MT1 record.

Usage: python scripts/check_reproduce.py OUT

Every file of audit/mt1_test must be byte-identical in OUT, and OUT/report.md must equal the MT1
results logged in AUDIT.md (from "MT1 on the test matches" to the gate summary), and
OUT/static_temperature.md must equal audit/static_temperature_test.md (3c.0). Figures and the
Figure 1 caption, when present in OUT/figures, are compared byte for byte with figures/.

Added in step 3h (AUDIT.md, "3h on the test matches"): OUT/clips_enough.csv, written by looseball
reproduce, must equal audit/s3h_test/clips_enough.csv; and when OUT/s3h exists (written by
`python scripts/s3h.py test OUT/s3h`), its report.md must equal audit/s3h_test/report.md.
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
    record = ROOT / "audit" / "static_temperature_test.md"
    same = (out / "static_temperature.md").exists() and (
        out / "static_temperature.md"
    ).read_bytes() == record.read_bytes()
    print(
        f"{'identical' if same else 'DIFFERS  '}  static_temperature.md against audit/static_temperature_test.md"
    )
    failures += [] if same else ["static_temperature.md"]
    if (out / "figures").exists():
        for f in sorted(p for p in (ROOT / "figures").iterdir() if p.is_file()):
            g = out / "figures" / f.name
            same = g.exists() and g.read_bytes() == f.read_bytes()
            print(f"{'identical' if same else 'DIFFERS  '}  figures/{f.name}")
            failures += [] if same else [f"figures/{f.name}"]
    pairs = [(out / "clips_enough.csv", ROOT / "audit" / "s3h_test" / "clips_enough.csv")]
    if (out / "s3h").exists():
        pairs.append((out / "s3h" / "report.md", ROOT / "audit" / "s3h_test" / "report.md"))
    for got, record in pairs:
        same = got.exists() and got.read_bytes() == record.read_bytes()
        print(
            f"{'identical' if same else 'DIFFERS  '}  {got.relative_to(out)} against {record.relative_to(ROOT)}"
        )
        failures += [] if same else [str(got.relative_to(out))]
    print("all identical" if not failures else f"{len(failures)} differ: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
