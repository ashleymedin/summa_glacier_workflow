#!/usr/bin/env python3
"""One run of a spun-up case at its default parameters, from the calibration start to the end of the evaluation years,
with daily means of runoff, glacier and snow variables, into runs/<case>/default; then its daily discharge KGE against the
gauge and its glacier-wide annual mass balance beside the observed.

    default_run.py lemon_added
"""
import os
import re
import shutil
import subprocess
import sys

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(WF, "runs"))
from calibrate import CASES, HERE, SUMMA_DIR, config_text, periods  # noqa: E402
from rerun_trials import OUTPUTS  # noqa: E402

import netCDF4 as nc4  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def run(case):
    run_dir = os.path.join(HERE, case)
    work = os.path.join(run_dir, "default")
    settings = os.path.join(work, "settings")
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(os.path.join(run_dir, "summa_inputs"), settings)
    with open(os.path.join(settings, "outputControl.txt"), "a") as f:
        f.writelines(f"{v:<26}| day | mean\n" for v in OUTPUTS)
    os.makedirs(os.path.join(work, "output"))
    os.makedirs(os.path.join(work, "state"))
    shutil.copy(os.path.join(settings, "coldState.nc"), os.path.join(work, "state", "coldState.nc"))
    cal0, _, _, ev1 = periods(case)
    config = config_text(case, run_dir, settings, work, cal0, ev1, cal0, ev1, "dds", 1, 1, temperature=False)
    config = config[:config.index("\n[calibration]")]
    config = re.sub(r"^use_mizuroute .*", "use_mizuroute    = false", config, flags=re.M)
    config = config.replace("write_timeseries = false", "write_timeseries = true")
    with open(os.path.join(work, "config.toml"), "w") as f:
        f.write(config)
    exe = os.path.join(SUMMA_DIR, "bin", "summa_sundials_mizuroute.exe")
    with open(os.path.join(work, "run.log"), "w") as log:
        status = subprocess.run([exe, "-c", os.path.join(work, "config.toml")], cwd=work, stdout=log, stderr=subprocess.STDOUT).returncode
    if status:
        raise SystemExit(f"{case} default run failed ({status}); see {work}/run.log")
    return work


def kge(s, o):
    m = np.isfinite(s) & np.isfinite(o)
    s, o = s[m], o[m]
    r = np.corrcoef(s, o)[0, 1]
    return 1 - np.sqrt((r - 1) ** 2 + (s.std() / o.std() - 1) ** 2 + (s.mean() / o.mean() - 1) ** 2), r, s.mean() / o.mean(), s.std() / o.std()


def score(case, work):
    c = CASES[case.split("_")[0]]
    out = sorted(f for f in os.listdir(os.path.join(work, "output")) if f.endswith(".nc") and "restart" not in f)
    print("outputs:", out)
    with nc4.Dataset(os.path.join(work, "output", [f for f in out if "timestep" in f][0])) as d:
        t = pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False))
        q = np.asarray(d["averageRoutedRunoff"][:]).squeeze()  # m s-1 over the GRU, hourly
        area = float(np.sum(nc4.Dataset(os.path.join(work, "settings", "attributes.nc"))["HRUarea"][:]))
    sim = pd.Series(q * area, index=t - pd.Timedelta(hours=9)).resample("D").mean()  # the gauge's UTC-9 days
    with nc4.Dataset(os.path.join(WF, c["obs"], c["flow"])) as d:
        to = (pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)) - pd.Timedelta(days=1)).normalize()  # stamped at the day's end
        name = "q_obs"
        obs = pd.Series(np.ma.filled(d[name][:].astype(float), np.nan).squeeze(), index=to)
    print(f"observed variable {name}; sim mean {sim.mean():.3f} m3/s")
    cal0, cal1, ev0, ev1 = periods(case)
    for label, a, b in (("calibrate", cal0, cal1), ("evaluate", ev0, ev1)):
        s, o = sim[a:b], obs.reindex(sim[a:b].index)
        k, r, beta, alpha = kge(s.values, o.values)
        print(f"{label} {a}..{b}: KGE {k:.2f} (r {r:.2f}, mean ratio {beta:.2f}, sd ratio {alpha:.2f}), {np.isfinite(o.values).sum()} days")
    clim = pd.DataFrame({"sim": sim, "obs": obs.reindex(sim.index)}).groupby(sim.index.month).mean()
    print("monthly mean discharge (m3/s), sim / obs:")
    print(clim.round(2).T.to_string())
    sim.to_csv(os.path.join(work, "discharge_m3s.csv"), header=["sim"])


if __name__ == "__main__":
    case = sys.argv[1]
    work = os.path.join(HERE, case, "default")
    if "--score" not in sys.argv:
        work = run(case)
    score(case, work)
