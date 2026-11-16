#!/usr/bin/env python3
"""Profile twin of the rain-snow split: can the two snowfall multipliers make up a wrong threshold or range?

The truth is twin.py's phase experiment (multipliers 0.9 upland and 1.4 glacier, threshold 273.66 K, range 3 K). Each
profile point pins the threshold and range and searches only the two multipliers against the synthetic observations;
the point at the truth is the control that shows the search budget finds the truth.

    twin_profile.py truth wolverine_general
    twin_profile.py point wolverine_general default --population 12 --generations 8 --ranks 6
    twin_profile.py report wolverine_general
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "2026-11-16"))
import twin  # noqa: E402

POINTS = {"truth": (273.66, 3.0), "default": (273.16, 2.0), "cold1K": (272.66, 3.0), "narrow": (273.66, 1.0)}
MULT = {"frozenPrecipMultip@upland": (0.3, 2.0), "frozenPrecipMultip@glacier": (0.3, 3.0)}


def point(case, name, population, generations, ranks):
    work, settings, obs = twin.paths(case, "phase")
    tc, tr = POINTS[name]
    bounds = dict(MULT, tempCritRain=(tc, tc), tempRangeTimestep=(tr, tr))
    run = os.path.join(work, f"profile_{name}")
    twin.run_driver(run, twin.config(case, "phase", run, settings, obs, population * generations, population, bounds),
                    settings, ranks)


def report(case):
    work, _, _ = twin.paths(case, "phase")
    print(f"{case}: truth upland 0.9, glacier 1.4")
    for name, (tc, tr) in POINTS.items():
        run = os.path.join(work, f"profile_{name}")
        if not os.path.isdir(run):
            continue
        obj, names = twin.objectives(run)
        import netCDF4 as nc4
        with nc4.Dataset(twin.calibration_file(run)) as d:
            v = {k: np.ma.filled(d[k][:].astype(float), np.nan) for k in MULT}
            front = np.asarray(d["pareto_front"][:]) == 1
        q, m = np.nanargmax(obj[:, 0]), np.nanargmin(obj[:, 1])
        ok = np.isfinite(obj).all(axis=1)
        # compromise: the front member nearest the ideal after scaling each objective by its front range
        f = obj[front & ok]
        span = np.maximum(np.ptp(f, axis=0), 1e-9)
        c = np.flatnonzero(front & ok)[np.argmin(np.hypot((1 - f[:, 0]) / span[0], f[:, 1] / span[1]))]
        print(f"{name:<8} Tcrit {tc:.2f} range {tr:.1f}: best KGE {obj[q, 0]:.4f} (rmse {obj[q, 1]:6.1f}), best rmse {obj[m, 1]:6.1f} "
              f"(KGE {obj[m, 0]:.4f}); compromise KGE {obj[c, 0]:.4f} rmse {obj[c, 1]:6.1f} upland {v['frozenPrecipMultip@upland'][c]:.3f} "
              f"glacier {v['frozenPrecipMultip@glacier'][c]:.3f}; {ok.sum()} trials")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("mode", choices=("truth", "point", "report"))
    p.add_argument("case")
    p.add_argument("name", nargs="?", choices=sorted(POINTS))
    p.add_argument("--population", type=int, default=12)
    p.add_argument("--generations", type=int, default=8)
    p.add_argument("--ranks", type=int, default=6)
    a = p.parse_args()
    if a.mode == "truth":
        twin.truth(a.case, "phase")
    elif a.mode == "point":
        point(a.case, a.name, a.population, a.generations, a.ranks)
    else:
        report(a.case)


if __name__ == "__main__":
    main()
