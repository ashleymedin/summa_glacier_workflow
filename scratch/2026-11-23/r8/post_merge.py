#!/usr/bin/env python3
"""After both seeds of a case's calibration end: merge their Pareto fronts, take the best-discharge, balanced and best
mass-change members of the merged front, then post-process them as scratch/2026-11-17/paper1/post_cal.py does, each in the calibration folder it came from:
daily reruns, f_A from ITS_LIVE, every front member's held-out scores (both folders), the balanced member's aligned reruns
and its glacier against the surveys. Writes the picks to <log folder>/picks_<case>.txt.

The balanced member is, with --pick span (the default), the one nearest the front's best KGE and smallest RMSE, each scaled by
the front's span (post_cal.py); with --pick rsr, the one nearest a perfect fit on fixed scales, hypot(1 - KGE, RMSE / s), s the
year-to-year standard deviation of the observed balances over the calibration years pooled over balance types (winter, summer,
annual) so the seasonal cycle does not count; RMSE / s is the RMSE-observations standard deviation ratio (RSR) of Moriasi et al.
(2007). The rsr pick does not move when a front gains or loses a member at one end, but weights mass balance more.

    ./post_merge.py wolverine_general 2026-11-23r8 calibration calibration_s43
    ./post_merge.py wolverine_general 2026-11-23r8 calibration calibration_s43 --picks-only --pick rsr
"""
import glob
import os
import subprocess
import sys
import time

import netCDF4 as nc4
import numpy as np
import pandas as pd
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
GLACIER = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RUNS = os.path.join(GLACIER, "runs")
PY = sys.executable
sys.path.insert(0, os.path.join(GLACIER, "scratch", "2026-11-17", "paper1"))
from post_cal import VELOCITY  # noqa: E402
sys.path.insert(0, RUNS)
from calibrate import periods  # noqa: E402


def run(args, log):
    print(f"$ {' '.join(args)}", flush=True)
    with open(log, "a") as f:
        return subprocess.run(args, cwd=RUNS, stdout=f, stderr=subprocess.STDOUT).returncode


def balance_scale(case, name):
    """Pooled year-to-year standard deviation (mm) of the observed balances of the case's mass target over its calibration years."""
    with open(os.path.join(RUNS, case, name, "config.toml"), "rb") as f:
        target = [t for t in tomllib.load(f)["calibration"]["target"] if t["metric"] == "rmse"][0]
    cal0, cal1 = periods(case)[:2]
    with nc4.Dataset(os.path.join(target["obs_path"], target["obs_file"])) as d:
        end = pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False,
                                          only_use_python_datetimes=True))
        b = d["time_bnds"][:]
        span = (b[:, 1] - b[:, 0]) / 1440.0
        obs = np.ma.filled(d[target["vname_obs"]][:].astype(float), np.nan)
    keep = (end >= pd.Timestamp(cal0)) & (end <= pd.Timestamp(cal1)) & np.isfinite(obs)
    kind = np.where(span > 300, "annual", np.where(end.month <= 7, "winter", "summer"))[keep]
    obs = obs[keep]
    return float(np.sqrt(np.mean([np.var(obs[kind == k], ddof=1) for k in np.unique(kind)])))


def merged_picks(case, names, rule="span"):
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
    if rule == "rsr":
        bal = int(np.argmin(np.hypot(1.0 - k, m / balance_scale(case, names[0]))))
    else:
        span = lambda x: (x.max() - x.min()) or 1.0  # noqa: E731
        bal = int(np.argmin(np.hypot((k.max() - k) / span(k), (m - m.min()) / span(m))))
    return [src[i] for i in (int(np.argmax(k)), bal, int(np.argmin(m)))], len(k), (k[bal], m[bal])


def main():
    argv = sys.argv[1:]
    rule = argv[argv.index("--pick") + 1] if "--pick" in argv else "span"
    args = [a for i, a in enumerate(argv) if a not in ("--picks-only", "--pick") and (i == 0 or argv[i - 1] != "--pick")]
    case, logdir, names = args[0], os.path.join(RUNS, "logs", args[1]), args[2:]
    if "--picks-only" in argv:
        print(case, rule, f"s = {balance_scale(case, names[0]):.0f} mm", merged_picks(case, names, rule))
        return
    log = os.path.join(logdir, f"post_{case}.log")
    for n in names:
        cal_log = os.path.join(logdir, f"calibrate_{case}_{n}.log")
        while "calibration written" not in (open(cal_log).read() if os.path.exists(cal_log) else ""):
            if os.path.exists(cal_log) and "exited" in open(cal_log).read():
                raise SystemExit(f"{case} {n}: calibration failed; see {cal_log}")
            time.sleep(60)
    picks, size, (kb, mb) = merged_picks(case, names, rule)
    q, bal, mbest = picks
    text = f"{case}: merged front of {size}; best discharge {q}, balanced {bal} ({kb:.3f}, {mb:.0f}), best mass change {mbest}"
    print(text, flush=True)
    open(os.path.join(logdir, f"picks_{case}.txt"), "w").write(text + "\n")
    for n in names:
        samples = sorted({s for f, s in picks if f == n})
        if samples:
            run([PY, "rerun_trials.py", case, n, *map(str, samples), "--jobs", "2", "--ranks", "2"], log)
    name, s = bal
    run([PY, os.path.join(GLACIER, "glen_factor.py"), os.path.join(RUNS, case, f"{name}_rerun", f"sample_{s}"),
         os.path.join(GLACIER, VELOCITY[case])], log)
    for n in names:
        run([PY, "calibrate.py", "evaluate", case, "--name", n, "--ranks", "2", "--jobs", "2"], log)
    aligned = ["--targets", "discharge,mass_balance,wgms_amce", "--aligned", "--extra", "scalarGlceMelt", "--ranks", "2"]
    run([PY, "rerun_trials.py", case, name, str(s), *aligned, "--label", "aligned"], log)
    run([PY, "rerun_trials.py", case, name, str(s), *aligned, "--calibration-years", "--label", "aligned_cal"], log)
    basin = case.split("_")[0]
    domain = case if case.endswith("general") else basin
    run([PY, os.path.join(GLACIER, "compare_glacier_change.py"), os.path.join(GLACIER, "domains", f"{domain}.yaml"),
         os.path.join(RUNS, case, f"{name}_rerun", f"sample_{s}"),
         *(["--observations", os.path.join(GLACIER, "domains", f"{basin}.yaml")] if domain != basin else [])], log)
    print(f"{case}: done", flush=True)


if __name__ == "__main__":
    main()
