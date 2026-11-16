#!/usr/bin/env python3
"""Winter and summer balance of each HRU's clean-ice glacier domain at the default parameters, against the stakes.

Runs the spun-up case (summa_inputs/coldState.nc) from the spin-up year through the calibration years with daily SWE and
glacier mass change, then, for each stake-year, differences the domain's mass between the
stake's previous fall date, spring date and fall date; glacMass4AreaChange holds the snow and the ice together. Stakes go to the HRU whose glacier domain is nearest in elevation,
as in correct_forcing_to_station.py. The simulated winter balance is carried to the stake's elevation with the case's
precipElevGrad; the summer balance is not. Balances in m w.e.

    stake_seasons.py run wolverine_added
    stake_seasons.py compare wolverine_added data/domain_Wolverine/observations/storage/mass_balance/Input_Wolverine_Glaciological_Data.csv
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

import netCDF4 as nc4
import numpy as np
import pandas as pd

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "runs")
sys.path.insert(0, RUNS)
from calibrate import SUMMA_DIR, config_text, periods  # noqa: E402

OUTPUTS = ["scalarSWE", "glacMass4AreaChange", "scalarSnowfall", "DOMelev"]


def work_dir(case):
    return os.path.join(RUNS, case, "stake_seasons")


def run(case):
    """Default-parameter run of the spin-up and calibration years with daily output in <case>/stake_seasons."""
    run_dir = os.path.join(RUNS, case)
    work = work_dir(case)
    settings = os.path.join(work, "settings")
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(os.path.join(run_dir, "summa_inputs"), settings)
    with open(os.path.join(settings, "outputControl.txt"), "a") as f:
        f.writelines(["\n"] + [f"{v:<26}| day | mean\n" for v in OUTPUTS])
    os.makedirs(os.path.join(work, "output"))
    os.makedirs(os.path.join(work, "state"))
    cal0, cal1 = periods(case)[:2]
    start = str(int(cal0[:4]) - 1) + cal0[4:]
    config = config_text(case, run_dir, settings, work, start, cal1, start, cal1, "dds", 1, 1, temperature=False)
    config = config[:config.index("\n[calibration]")]
    config = re.sub(r"^use_mizuroute .*", "use_mizuroute    = false", config, flags=re.M)
    config = config.replace("write_timeseries = false", "write_timeseries = true")
    shutil.copy(os.path.join(settings, "coldState.nc"), os.path.join(work, "state", "coldState.nc"))
    with open(os.path.join(work, "config.toml"), "w") as f:
        f.write(config)
    exe = os.path.join(SUMMA_DIR, "bin", "summa_sundials_mizuroute.exe")
    with open(os.path.join(work, "run.log"), "w") as log:
        status = subprocess.run([exe, "-c", os.path.join(work, "config.toml")], cwd=work, stdout=log,
                                stderr=subprocess.STDOUT).returncode
    print(f"{case}: run {'failed' if status else 'done'}, {work}/output")


def domain_mass(case):
    """Daily mass (m w.e.) of each HRU's clean-ice glacier domain, its elevation, and precipElevGrad."""
    work = work_dir(case)
    out = [f for f in os.listdir(os.path.join(work, "output")) if f.endswith(".nc") and "timestep" not in f]
    with nc4.Dataset(os.path.join(work, "output", sorted(out)[0])) as d:
        time = pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False,
                                           only_use_python_datetimes=True)).normalize()
        gm = np.ma.filled(d["glacMass4AreaChange_mean"][:], np.nan)
        elev = np.ma.filled(d["DOMelev_mean"][0], np.nan)
    with nc4.Dataset(os.path.join(work, "settings", "coldState.nc")) as c:
        c.set_auto_mask(False)
        clean = (c["nGlce"][:] > 0) & (c["nSoil"][:] == 0)
    grad = 0.0
    for line in open(os.path.join(work, "settings", "localParamInfo.txt")):
        if line.split("|")[0].strip() == "precipElevGrad":
            grad = float(line.split("|")[1])
    change = np.diff(gm, axis=0, prepend=gm[:1])  # the counter holds snow and ice together
    reset = (time.month == 10) & (time.day == 2)  # the yearly area update zeroes the counter on 2 October
    change[reset] = gm[reset]
    mass = np.cumsum(change, axis=0) / 1000.0
    series = {}
    for h in range(clean.shape[0]):
        m = int(np.argmax(clean[h]))
        series[h] = (pd.Series(mass[:, h, m], index=time), float(elev[h, m]))
    return series, grad


def compare(case, stakes_csv):
    series, grad = domain_mass(case)
    s = pd.read_csv(stakes_csv, parse_dates=["spring_date", "fall_date"])
    t0, t1 = next(iter(series.values()))[0].index[[0, -1]]
    s = s[(s.spring_date > t0) & (s.fall_date <= t1)].copy()
    prev = pd.read_csv(stakes_csv, parse_dates=["fall_date"])[["Year", "site_name", "fall_date"]]
    prev["Year"] += 1
    s = s.merge(prev.rename(columns={"fall_date": "prev_fall"}), on=["Year", "site_name"], how="left")
    s["prev_fall"] = s.prev_fall.fillna(pd.to_datetime((s.Year - 1).astype(str) + "-10-01"))
    s = s[s.prev_fall >= t0]
    rows = []
    for _, r in s.iterrows():
        h = min(series, key=lambda k: abs(series[k][1] - r.elevation))
        m, z = series[h]
        at = lambda t: float(m.asof(t))  # noqa: E731
        bw = (at(r.spring_date) - at(r.prev_fall)) * (1 + grad * (r.elevation - z))
        bs = at(r.fall_date) - at(r.spring_date)
        rows.append(dict(year=r.Year, site=r.site_name, z=r.elevation, hru=h + 1, z_dom=round(z), bw_obs=r.bw, bw_sim=bw,
                         bs_obs=r.ba - r.bw, bs_sim=bs, ba_obs=r.ba, ba_sim=bw + bs))
    t = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(f"{case}: precipElevGrad {grad}")
    print(t.round(2).to_string(index=False))
    g = t.groupby("hru")[["z", "bw_obs", "bw_sim", "bs_obs", "bs_sim", "ba_obs", "ba_sim"]].mean().round(2)
    g["n"] = t.groupby("hru").size()
    print("\nmean by HRU (sim - obs: winter, summer, annual)")
    g["d_bw"], g["d_bs"], g["d_ba"] = (g.bw_sim - g.bw_obs).round(2), (g.bs_sim - g.bs_obs).round(2), (g.ba_sim - g.ba_obs).round(2)
    print(g.to_string())


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("action", choices=["run", "compare"])
    p.add_argument("case")
    p.add_argument("stakes", nargs="?")
    a = p.parse_args()
    run(a.case) if a.action == "run" else compare(a.case, a.stakes)


if __name__ == "__main__":
    main()
