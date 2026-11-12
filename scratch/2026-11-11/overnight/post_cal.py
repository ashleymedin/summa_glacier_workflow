#!/usr/bin/env python3
"""After a case's calibration ends: rerun its best discharge, balanced and best mass-balance front members with daily
output and yearly glacier grids (rerun_trials.py), the f_A the balanced rerun's ITS_LIVE speeds imply (glen_factor.py),
then every front member's held-out scores (calibrate.py evaluate), the balanced member's scored pairs for the figures
(rerun_trials.py --aligned, through the held-out years and over the calibration years alone) and its glacier against
the surveys and imagery (compare_glacier_change.py). Waits for <case>/calibration to finish first.

    ./post_cal.py wolverine_general [log folder under runs/logs, default 2026-11-11]
"""
import glob
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
LOGS = os.path.join(RUNS, "logs", sys.argv[2] if len(sys.argv) > 2 else "2026-11-11")
VELOCITY = {"wolverine_added": "data/domain_Wolverine/observations/storage/velocity/itslive_annual.npz",
            "gulkana_added": "data/domain_Gulkana/observations/storage/velocity/itslive_annual.npz",
            "wolverine_general": "data/domain_Wolverine_general/observations/storage/velocity/itslive_annual.npz",
            "gulkana_general": "data/domain_Gulkana_general/observations/storage/velocity/itslive_annual.npz"}


def run(args, log):
    print(f"$ {' '.join(args)}", flush=True)
    with open(log, "a") as f:
        return subprocess.run(args, cwd=RUNS, stdout=f, stderr=subprocess.STDOUT).returncode


def picks(case):
    """Sample numbers (1-based) of the best-KGE, balanced and best mass-change members of the front."""
    with nc4.Dataset(sorted(glob.glob(os.path.join(RUNS, case, "calibration", "output", "*_calibration.nc")))[0]) as d:
        front = np.flatnonzero(np.asarray(d["pareto_front"][:]) == 1)
        obj = np.ma.filled(d["objective"][:].astype(float), np.nan)[front]
    kge, mb = obj[:, 0], obj[:, 1]
    span = lambda x: (x.max() - x.min()) or 1.0
    bal = np.argmin(np.hypot((kge.max() - kge) / span(kge), (mb - mb.min()) / span(mb)))
    return [int(front[i]) + 1 for i in (np.argmax(kge), bal, np.argmin(mb))], len(front)


def main():
    case = sys.argv[1]
    log = os.path.join(LOGS, f"post_{case}.log")
    cal_log = os.path.join(LOGS, f"calibrate_{case}.log")
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
         os.path.join(GLACIER, VELOCITY.get(case, VELOCITY["_".join(case.split("_")[:2])]))], log)
    run([PY, "calibrate.py", "evaluate", case, "--name", "calibration", "--ranks", "2", "--jobs", "3"], log)
    aligned = ["--targets", "discharge,mass_balance,wgms_amce", "--aligned", "--extra", "scalarGlceMelt", "--ranks", "2"]
    run([PY, "rerun_trials.py", case, "calibration", str(bal), *aligned, "--label", "aligned"], log)
    run([PY, "rerun_trials.py", case, "calibration", str(bal), *aligned, "--calibration-years", "--label", "aligned_cal"], log)
    basin = case.split("_")[0]
    domain = case if case.endswith("general") else basin
    run([PY, os.path.join(GLACIER, "compare_glacier_change.py"), os.path.join(GLACIER, "domains", f"{domain}.yaml"),
         os.path.join(RUNS, case, "calibration_rerun", f"sample_{bal}"),
         *(["--observations", os.path.join(GLACIER, "domains", f"{basin}.yaml")] if domain != basin else [])], log)
    print(f"{case}: done", flush=True)


if __name__ == "__main__":
    main()
