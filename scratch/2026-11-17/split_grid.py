#!/usr/bin/env python3
"""Does SUMMA's default rain-snow split fit the real data as well as a calibrated one, once the snowfall multipliers
are re-fitted? From oat.py's calibrated compromise, every node of an 8 x 8 multiplier grid around its multipliers is run
at the compromise's split and at the default (273.16 K, 2 K), the rest held, as pinned single trials against the real
targets in runs/<case>/split_grid/sample_<split>_u<upland>_g<glacier>.

    split_grid.py run wolverine_general --jobs 4
    split_grid.py report wolverine_general
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import netCDF4 as nc4
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oat  # noqa: E402
import screen  # noqa: E402
from screen import RUNS  # noqa: E402
from calibrate import calibration_file  # noqa: E402

DEFAULT = (273.16, 2.0)


def axes(base):
    """Eight multipliers 0.1 apart for each domain, covering the compromise's, inside the search bounds."""
    out = []
    for p, lo, hi in (("frozenPrecipMultip@upland", 0.3, 2.0), ("frozenPrecipMultip@glacier", 0.3, 3.0)):
        start = min(max(round(base[p] - 0.35, 1), lo), hi - 0.7)
        out.append(np.round(start + 0.1 * np.arange(8), 2))
    return out


def tasks(case):
    base, _ = oat.compromise(case)
    splits = {"calibrated": (base["tempCritRain"], base["tempRangeTimestep"]), "default": DEFAULT}
    up, gl = axes(base)
    out = []
    for s, (tc, tr) in splits.items():
        for u in up:
            for g in gl:
                v = dict(base, **{"frozenPrecipMultip@upland": float(u), "frozenPrecipMultip@glacier": float(g),
                                  "tempCritRain": tc, "tempRangeTimestep": tr})
                out.append((f"{s}_u{u:.2f}_g{g:.2f}", s, u, g, v))
    return out, splits


def run(case, jobs):
    s = oat.search(case)
    todo, _ = tasks(case)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(lambda t: screen.run_one(case, s, t[0], t[4], folder="split_grid"), todo))


def report(case):
    todo, splits = tasks(case)
    res = {}
    for name, s, u, g, _ in todo:
        try:
            with nc4.Dataset(calibration_file(os.path.join(RUNS, case, "split_grid", f"sample_{name}"))) as d:
                res.setdefault(s, []).append((u, g, *np.ma.filled(d["objective"][0].astype(float), np.nan)[:2]))
        except (SystemExit, OSError):
            pass
    _, cal = oat.compromise(case)
    print(f"{case}: calibrated compromise KGE {cal[0]:.4f}, RMSE {cal[1]:.0f}")
    fronts = {}
    for s, rows in res.items():
        r = np.array(rows)
        r = r[np.isfinite(r[:, 2:]).all(axis=1)]
        k, m = np.argmax(r[:, 2]), np.argmin(r[:, 3])
        front = [x for x in r if not any((y[2] >= x[2]) and (y[3] <= x[3]) and ((y[2] > x[2]) or (y[3] < x[3])) for y in r)]
        fronts[s] = np.array(sorted(front, key=lambda x: -x[2]))
        tc, tr = splits[s]
        print(f"{s:<11} {tc:.2f} K {tr:.2f} K ({len(r)} nodes): best KGE {r[k, 2]:.4f} at {r[k, 0]:.2f}/{r[k, 1]:.2f} (RMSE {r[k, 3]:.0f}); "
              f"best RMSE {r[m, 3]:.0f} at {r[m, 0]:.2f}/{r[m, 1]:.2f} (KGE {r[m, 2]:.4f})")
        for x in fronts[s]:
            print(f"      front  upland {x[0]:.2f} glacier {x[1]:.2f}  KGE {x[2]:.4f}  RMSE {x[3]:.0f}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("mode", choices=("run", "report"))
    p.add_argument("case")
    p.add_argument("--jobs", type=int, default=4)
    a = p.parse_args()
    run(a.case, a.jobs) if a.mode == "run" else report(a.case)


if __name__ == "__main__":
    main()
