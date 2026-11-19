"""numpy-only soak test for the rare ValueError seen in np.linalg.norm (AUDIT.md, "Test-suite failure
at the 3c revision commit").

Usage: python scripts/numpy_norm_soak.py [MINUTES]   (default 10)

Calls np.linalg.norm(d, axis=-1) on fresh two-element vectors, the call the frozen reach model makes,
for the given number of minutes, and prints the calls and errors after each pass of 400,001 angles
and a final line. Every error is printed with the vector. Needs numpy only; run it on another
machine to see whether the fault follows the machine or numpy. Exit status 1 when any error was seen.
"""

import platform
import sys
import time

import numpy as np

ANGLES = 400_001


def main(minutes: float) -> int:
    print(
        f"numpy {np.__version__}, Python {platform.python_version()}, {platform.platform()}, {platform.processor()}"
    )
    end = time.time() + 60 * minutes
    a = np.linspace(0.0, np.pi, ANGLES)
    pos, target = np.array([2.0, 0.0]), np.array([0.0, 0.0])
    calls = errors = 0
    while time.time() < end:
        for x in a:
            d = target - (pos + 0.7 * 5.0 * np.array([-np.cos(x), np.sin(x)]))
            try:
                np.linalg.norm(d, axis=-1)
            except ValueError as e:  # the fault under test: record it and go on; anything else stops the run
                errors += 1
                print(f"ERROR at call {calls}: {type(e).__name__}: {e}; d={d!r}", flush=True)
            calls += 1
        print(f"{calls} calls, {errors} errors", flush=True)
    print(f"done: {minutes} min, {calls} calls, {errors} errors", flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(float(sys.argv[1]) if len(sys.argv) > 1 else 10.0))
