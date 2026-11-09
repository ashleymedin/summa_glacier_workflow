#!/usr/bin/env python3
"""After a case's calibration ends: rerun its best discharge, balanced and best mass-balance front members with daily
output and yearly glacier grids (rerun_trials.py), the f_A the balanced rerun's ITS_LIVE speeds imply (glen_factor.py),
then every front member's held-out scores (calibrate.py evaluate). Waits for <case>/calibration to finish first.

    ./post_cal.py wolverine_general
"""
import os
import subprocess
import sys
import time

import netCDF4 as nc4
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GLACIER = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RUNS = os.path.join(GLACIER, "runs")
PY = sys.executable
VELOCITY = {"wolverine": "data/domain_Wolverine/observations/storage/velocity/itslive_annual.npz",
            "gulkana": "data/domain_Gulkana/observations/storage/velocity/itslive_annual.npz"}


def run(args, log):
    print(f"$ {' '.join(args)}", flush=True)
    with open(log, "a") as f:
        return subprocess.run(args, cwd=RUNS, stdout=f, stderr=subprocess.STDOUT).returncode


def picks(case):
    """Sample numbers (1-based) of the best-KGE, balanced and best mass-change members of the front."""
    with nc4.Dataset(os.path.join(RUNS, case, "calibration", "output", f"{case}_calibration.nc")) as d:
        front = np.flatnonzero(np.asarray(d["pareto_front"][:]) == 1)
        obj = np.ma.filled(d["objective"][:].astype(float), np.nan)[front]
    kge, mb = obj[:, 0], obj[:, 1]
    span = lambda x: (x.max() - x.min()) or 1.0
    bal = np.argmin(np.hypot((kge.max() - kge) / span(kge), (mb - mb.min()) / span(mb)))
    return [int(front[i]) + 1 for i in (np.argmax(kge), bal, np.argmin(mb))], len(front)


def main():
    case = sys.argv[1]
    log = os.path.join(RUNS, "logs", "2026-11-09", f"post_{case}.log")
    cal_log = os.path.join(RUNS, "logs", "2026-11-09", f"calibrate_{case}.log")
    while True:
        text = open(cal_log).read() if os.path.exists(cal_log) else ""
        if "calibration written" in text:
            break
        if "exited" in text:
            raise SystemExit(f"{case}: calibration failed; see {cal_log}")
        time.sleep(60)
    (q, bal, mb), n = picks(case)
    print(f"{case}: front of {n}; best discharge {q}, balanced {bal}, best mass change {mb}", flush=True)
    samples = sorted({q, bal, mb})
    run([PY, "rerun_trials.py", case, "calibration", *map(str, samples), "--jobs", str(len(samples)), "--ranks", "2"], log)
    run([PY, os.path.join(GLACIER, "glen_factor.py"), os.path.join(RUNS, case, "calibration_rerun", f"sample_{bal}"),
         os.path.join(GLACIER, VELOCITY[case.split("_")[0]])], log)
    run([PY, "calibrate.py", "evaluate", case, "--name", "calibration", "--ranks", "2", "--jobs", "3"], log)
    print(f"{case}: done", flush=True)


if __name__ == "__main__":
    main()
