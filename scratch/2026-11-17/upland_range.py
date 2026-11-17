#!/usr/bin/env python3
"""Is the upland snowfall multiplier's upper bound (2) what holds Gulkana's general fit back? From oat.py's calibrated
compromise at the default rain-snow split, upland 2 to 3.5 against glacier 0.8 to 1.4, the rest held, as pinned single
trials in runs/<case>/upland_range.

    upland_range.py run gulkana_general --jobs 8
    upland_range.py report gulkana_general
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import netCDF4 as nc4

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oat  # noqa: E402
import screen  # noqa: E402
from screen import RUNS  # noqa: E402
from calibrate import calibration_file  # noqa: E402

UPLAND = (2.0, 2.5, 3.0, 3.5)
GLACIER = (0.8, 1.0, 1.2, 1.4)


def tasks(case):
    base, _ = oat.compromise(case)
    return [(f"u{u:.2f}_g{g:.2f}", u, g, dict(base, **{"frozenPrecipMultip@upland": u, "frozenPrecipMultip@glacier": g,
                                                       "tempCritRain": 273.16, "tempRangeTimestep": 2.0}))
            for u in UPLAND for g in GLACIER]


def run(case, jobs):
    s = oat.search(case)
    s = dict(s, bounds=dict(s["bounds"], **{"frozenPrecipMultip@upland": (0.3, 4.0)}))
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(lambda t: screen.run_one(case, s, t[0], t[3], folder="upland_range"), tasks(case)))


def report(case):
    print(f"{case}: default split, the compromise's other parameters")
    for name, u, g, _ in tasks(case):
        try:
            with nc4.Dataset(calibration_file(os.path.join(RUNS, case, "upland_range", f"sample_{name}"))) as d:
                o = d["objective"][0]
                print(f"  upland {u:.2f} glacier {g:.2f}: KGE {float(o[0]):.4f}  RMSE {float(o[1]):.0f}")
        except (SystemExit, OSError):
            print(f"  upland {u:.2f} glacier {g:.2f}: missing")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("mode", choices=("run", "report"))
    p.add_argument("case")
    p.add_argument("--jobs", type=int, default=8)
    a = p.parse_args()
    run(a.case, a.jobs) if a.mode == "run" else report(a.case)


if __name__ == "__main__":
    main()
