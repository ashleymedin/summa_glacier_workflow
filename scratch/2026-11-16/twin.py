#!/usr/bin/env python3
"""Twin experiments: can a calibration recover parameters from synthetic observations of a run with known values?

  truth      runs the case over its calibrate years with the truth values as the defaults of a copy of its settings,
             then writes its discharge and mass-balance targets, at the real observations' times, as synthetic
             observation files; a rerun against them must score perfectly
  calibrate  NSGA-II over the experiment's parameters only, against the synthetic observations; every other
             parameter is held at the truth, so this is the best case for recovery
  report     the truth, the best trial of each objective and the Pareto front's range of each parameter

Work goes to runs/<case>/twin_<experiment>. Needs SUMMA_DIR pointing at a build with glacierSnowFactor.

    twin.py truth wolverine_general snow
    twin.py calibrate wolverine_general snow --population 16 --generations 10 --ranks 9
    twin.py report wolverine_general snow
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys

import netCDF4 as nc4
import numpy as np

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "runs")
sys.path.insert(0, RUNS)
from calibrate import CASES, GLACIER, SUMMA_DIR, calibration_file, case_spec, config_text, fit12, periods  # noqa: E402

# truth values and search bounds; snow tests the snowfall multiplier, the precipitation gradient and the glacier
# snowfall multiplier against each other, melt the glacier wind and cooling against the snow albedo
EXPERIMENTS = {
    "snow": {"frozenPrecipMultip": (1.2, 0.3, 2.0), "precipElevGrad": (0.0010, 0.0, 0.0025),
             "glacierSnowFactor": (1.4, 1.0, 2.0)},
    "melt": {"glacierWindFactor": (0.8, 0.3, 1.5), "glacierTempReduction": (0.65, 0.5, 0.9),
             "albedoDecayRate": (1.5e6, 3.0e5, 5.0e6), "albedoMax": (0.84, 0.8, 0.9)},
}


def paths(case, exp):
    work = os.path.join(RUNS, case, f"twin_{exp}")
    return work, os.path.join(work, "settings"), os.path.join(work, "obs")


def truth_settings(case, exp):
    """A copy of the case's settings with the truth values as the defaults; the bounds are kept."""
    _, settings, _ = paths(case, exp)
    shutil.rmtree(settings, ignore_errors=True)
    shutil.copytree(os.path.join(RUNS, case, "summa_inputs"), settings)
    truth = {k: v[0] for k, v in EXPERIMENTS[exp].items()}
    path = os.path.join(settings, "localParamInfo.txt")
    out, seen = [], set()
    for line in open(path):
        key = line.split("|")[0].strip() if "|" in line and not line.lstrip().startswith("!") else ""
        if key in truth:
            f = line.split("|")
            line = f"{key:<26}| {fit12(truth[key])} |{f[2]}|{f[3].rstrip()}\n"
            seen.add(key)
        out.append(line)
    if seen != set(truth):
        raise SystemExit(f"{path} lacks {set(truth) - seen}")
    open(path, "w").writelines(out)
    return settings


def config(case, exp, work, settings, obs, n_samples, population, bounds):
    """calibrate.py's driver TOML for the case's calibrate years, over the experiment's parameters, against obs."""
    cal0, cal1 = periods(case)[:2]
    search = {"params": list(EXPERIMENTS[exp]), "logs": [], "chains": [], "bounds": bounds}
    text = config_text(case, os.path.join(RUNS, case), settings, work, cal0, cal1, cal0, cal1,
                       "nsga2" if n_samples > 1 else "dds", n_samples, population, temperature=False, search=search)
    real = os.path.join(GLACIER, CASES[case.split("_")[0]]["obs"]) + "/"
    return text.replace(f'obs_path  = "{real}"', f'obs_path  = "{obs}/"').replace(f'obs_path   = "{real}"', f'obs_path   = "{obs}/"')


def run_driver(work, text, settings, ranks):
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(os.path.join(work, "output"))
    os.makedirs(os.path.join(work, "state"))
    shutil.copy(os.path.join(settings, "coldState.nc"), os.path.join(work, "state"))
    with open(os.path.join(work, "config.toml"), "w") as f:
        f.write(text)
    exe = os.path.join(SUMMA_DIR, "bin", "summa_sundials_mizuroute_opt.exe")
    with open(os.path.join(work, "run.log"), "w") as log:
        status = subprocess.run(["mpirun", "-np", str(ranks), exe, "-c", os.path.join(work, "config.toml")],
                                stdout=log, stderr=subprocess.STDOUT).returncode
    if status:
        raise SystemExit(f"driver exited {status}; see {work}/run.log")


def objectives(work):
    with nc4.Dataset(calibration_file(work)) as d:
        return np.ma.filled(d["objective"][:].astype(float), np.nan), [t.strip() for t in d["objective"].target.split(",")]


def truth(case, exp):
    work, settings, obs = paths(case, exp)
    settings = truth_settings(case, exp)
    pinned = {k: (v[0], v[0]) for k, v in EXPERIMENTS[exp].items()}
    real = os.path.join(GLACIER, CASES[case.split("_")[0]]["obs"])
    run = os.path.join(work, "truth")
    text = config(case, exp, run, settings, real, 1, 1, pinned)
    text = text.replace("write_timeseries = false", "write_timeseries = true").replace("write_aligned = false", "write_aligned = true")
    run_driver(run, text, settings, 2)
    out = [f for f in glob.glob(os.path.join(run, "output", "*.nc")) if "calibration" not in f and "trialParams" not in f]
    shutil.rmtree(obs, ignore_errors=True)
    os.makedirs(obs)
    targets = case_spec(case).get("targets")
    files = {"discharge": ("flow", "q_obs"), "wgms_amce": ("wgms_amce", "mb_obs"), "mass_balance": ("mb", "mb_obs")}
    c = CASES[case.split("_")[0]]
    for f in out:
        with nc4.Dataset(f) as d:
            if "evaluation" not in d.groups:
                continue
            for name, g in d["evaluation"].groups.items():
                key, var = files[name]
                if name not in targets:
                    continue
                sim_time = np.asarray(g["time"][:], float)
                sim_units = g["time"].units
                sim = np.ma.filled(g[[v for v in g.variables if "sim" in v.lower()][0]][:].astype(float), np.nan)
                src = os.path.join(real, c[key])
                dst = os.path.join(obs, c[key])
                shutil.copy(src, dst)
                with nc4.Dataset(dst, "r+") as o:
                    t = nc4.num2date(o["time"][:], o["time"].units, only_use_cftime_datetimes=False)
                    ts = nc4.num2date(sim_time, sim_units, only_use_cftime_datetimes=False)
                    lookup = {x.replace(tzinfo=None): v for x, v in zip(ts, sim)}
                    new = np.array([lookup.get(x.replace(tzinfo=None), np.nan) for x in t])
                    o[var][:] = new
                    o.setncattr("comment", f"synthetic: twin.py truth {case} {exp}, " + ", ".join(f"{k} {v[0]}" for k, v in EXPERIMENTS[exp].items()))
                print(f"{dst}: {np.isfinite(new).sum()} synthetic values of {np.isfinite(sim).sum()} simulated")
    check = os.path.join(work, "truth_check")
    run_driver(check, config(case, exp, check, settings, obs, 1, 1, pinned), settings, 2)
    obj, names = objectives(check)
    print(f"{case} {exp}: truth against its own series scores", dict(zip(names, obj[0])))


def calibrate(case, exp, population, generations, ranks):
    work, settings, obs = paths(case, exp)
    bounds = {k: (v[1], v[2]) for k, v in EXPERIMENTS[exp].items()}
    run = os.path.join(work, "calibration")
    run_driver(run, config(case, exp, run, settings, obs, population * generations, population, bounds), settings, ranks)
    report(case, exp)


def report(case, exp):
    work, _, _ = paths(case, exp)
    path = calibration_file(os.path.join(work, "calibration"))
    obj, names = objectives(os.path.join(work, "calibration"))
    with nc4.Dataset(path) as d:
        front = np.asarray(d["pareto_front"][:]) == 1
        vals = {k: np.ma.filled(d[k][:].astype(float), np.nan) for k in EXPERIMENTS[exp]}
    done = np.isfinite(obj).all(axis=1)
    print(f"{case} {exp}: {done.sum()} trials, {front.sum()} on the front; objectives {names}")
    best = {n: int(np.nanargmax(obj[:, i]) if n == "discharge" else np.nanargmin(obj[:, i])) for i, n in enumerate(names)}
    print(f"{'parameter':<22}{'truth':>10}{'lower':>10}{'upper':>10}" + "".join(f"{'best ' + n:>18}" for n in names) + f"{'front min':>12}{'front max':>12}")
    for k, (t, lo, hi) in EXPERIMENTS[exp].items():
        row = f"{k:<22}{t:>10.4g}{lo:>10.4g}{hi:>10.4g}" + "".join(f"{vals[k][i]:>18.4g}" for i in best.values())
        print(row + f"{np.nanmin(vals[k][front]):>12.4g}{np.nanmax(vals[k][front]):>12.4g}")
    print("best objectives:", {n: [round(float(x), 4) for x in obj[i]] for n, i in best.items()})


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("mode", choices=("truth", "calibrate", "report"))
    p.add_argument("case")
    p.add_argument("experiment", choices=sorted(EXPERIMENTS))
    p.add_argument("--population", type=int, default=16)
    p.add_argument("--generations", type=int, default=10)
    p.add_argument("--ranks", type=int, default=9)
    a = p.parse_args()
    if a.mode == "truth":
        truth(a.case, a.experiment)
    elif a.mode == "calibrate":
        calibrate(a.case, a.experiment, a.population, a.generations, a.ranks)
    else:
        report(a.case, a.experiment)


if __name__ == "__main__":
    main()
