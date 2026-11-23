#!/usr/bin/env python3
"""Lemon Creek's copy of scratch/2026-11-23/r8/post_merge.py, without the f_A step (no velocity file). After both seeds of a case's calibration end: merge their Pareto fronts, take the best-discharge, balanced and best
mass-change members of the merged front (balanced as post_cal.py: nearest the ideal corner, each objective scaled by the merged
front's span), then post-process them as scratch/2026-11-17/paper1/post_cal.py does, each in the calibration folder it came from:
daily reruns, f_A from ITS_LIVE, every front member's held-out scores (both folders), the balanced member's aligned reruns
and its glacier against the surveys. Writes the picks to <log folder>/picks_<case>.txt.

    ./post_merge.py wolverine_general 2026-11-23r8 calibration calibration_s43
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


def run(args, log):
    print(f"$ {' '.join(args)}", flush=True)
    with open(log, "a") as f:
        return subprocess.run(args, cwd=RUNS, stdout=f, stderr=subprocess.STDOUT).returncode


def merged_picks(case, names):
    """(folder, sample) of the best-discharge, balanced and best mass-change members of the merged front, and its size."""
    k, m, src = [], [], []
    for n in names:
        with nc4.Dataset(sorted(glob.glob(os.path.join(RUNS, case, n, "output", "*_calibration.nc")))[0]) as d:
            front = np.flatnonzero(np.asarray(d["pareto_front"][:]) == 1)
            obj = np.ma.filled(d["objective"][:].astype(float), np.nan)[front]
        k += list(obj[:, 0]); m += list(obj[:, 1]); src += [(n, int(i) + 1) for i in front]
    k, m = np.array(k), np.array(m)
    keep = [i for i in range(len(k)) if not np.any((k >= k[i]) & (m <= m[i]) & ((k > k[i]) | (m < m[i])))]
    k, m, src = k[keep], m[keep], [src[i] for i in keep]
    span = lambda x: (x.max() - x.min()) or 1.0  # noqa: E731
    bal = int(np.argmin(np.hypot((k.max() - k) / span(k), (m - m.min()) / span(m))))
    return [src[i] for i in (int(np.argmax(k)), bal, int(np.argmin(m)))], len(k), (k[bal], m[bal])


def main():
    case, logdir, names = sys.argv[1], os.path.join(RUNS, "logs", sys.argv[2]), sys.argv[3:]
    log = os.path.join(logdir, f"post_{case}.log")
    for n in names:
        cal_log = os.path.join(logdir, f"calibrate_{case}_{n}.log")
        while "calibration written" not in (open(cal_log).read() if os.path.exists(cal_log) else ""):
            if os.path.exists(cal_log) and "exited" in open(cal_log).read():
                raise SystemExit(f"{case} {n}: calibration failed; see {cal_log}")
            time.sleep(60)
    picks, size, (kb, mb) = merged_picks(case, names)
    q, bal, mbest = picks
    text = f"{case}: merged front of {size}; best discharge {q}, balanced {bal} ({kb:.3f}, {mb:.0f}), best mass change {mbest}"
    print(text, flush=True)
    open(os.path.join(logdir, f"picks_{case}.txt"), "w").write(text + "\n")
    for n in names:
        samples = sorted({s for f, s in picks if f == n})
        if samples:
            run([PY, "rerun_trials.py", case, n, *map(str, samples), "--jobs", "2", "--ranks", "2"], log)
    name, s = bal
    for n in names:
        run([PY, "calibrate.py", "evaluate", case, "--name", n, "--ranks", "2", "--jobs", "2"], log)
    aligned = ["--targets", "discharge,mass_balance,wgms_amce", "--aligned", "--extra", "scalarGlceMelt", "--ranks", "2"]
    run([PY, "rerun_trials.py", case, name, str(s), *aligned, "--label", "aligned"], log)
    run([PY, "rerun_trials.py", case, name, str(s), *aligned, "--calibration-years", "--label", "aligned_cal"], log)
    basin = "lemon_creek"  # no ITS_LIVE file for Lemon Creek, so no f_A step
    domain = basin + "_general" if case.endswith("general") else basin
    run([PY, os.path.join(GLACIER, "compare_glacier_change.py"), os.path.join(GLACIER, "domains", f"{domain}.yaml"),
         os.path.join(RUNS, case, f"{name}_rerun", f"sample_{s}"),
         *(["--observations", os.path.join(GLACIER, "domains", f"{basin}.yaml")] if domain != basin else [])], log)
    print(f"{case}: done", flush=True)


if __name__ == "__main__":
    main()
