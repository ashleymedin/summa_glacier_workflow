#!/usr/bin/env python3
"""One-change experiments on the summer melt deficit: a case's summa_inputs with parameter, attribute or forcing
changes, run from the spun-up state 2004-10 to 2024-09 with daily energy-balance output, scored against the stakes
(summer, winter by HRU, as stake_seasons.py) and, at Gulkana, the 2024 Site B campaign.

    exp.py run gulkana_added base
    exp.py run gulkana_added mh15 --attr mHeight=1.5
    exp.py run gulkana_added nocool --param glacierTempReduction=1.0
    exp.py stakes gulkana_added base mh15 nocool
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

HERE = os.path.dirname(os.path.abspath(__file__))
GLACIER = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RUNS = os.path.join(GLACIER, "runs")
sys.path.insert(0, RUNS)
from calibrate import SUMMA_DIR, config_text  # noqa: E402

OUTPUTS = ["scalarSWE", "glacMass4AreaChange", "scalarSnowfall", "DOMelev", "scalarSenHeatGround",
           "scalarLatHeatGround", "scalarLWNetGround", "scalarGroundAbsorbedSolar", "scalarGroundNetNrgFlux",
           "scalarGroundAlbedo", "scalarSurfaceTemp", "airtemp", "windspd", "SWRadAtm", "LWRadAtm", "spechum"]
STAKES = {"gulkana": "data/domain_Gulkana/observations/storage/mass_balance/Input_Gulkana_Glaciological_Data.csv",
          "wolverine": "data/domain_Wolverine/observations/storage/mass_balance/Input_Wolverine_Glaciological_Data.csv"}
START, END = "2004-10-01", "2024-09-30"


def exp_dir(case, name):
    return os.path.join(HERE, "runs", case, name)


def set_param(path, name, value):
    out, hit = [], False
    for line in open(path):
        f = line.split("|")
        if len(f) > 3 and f[0].strip() == name:
            f[1] = f" {value:>12} "
            line, hit = "|".join(f), True
        out.append(line)
    if not hit:
        raise SystemExit(f"{name} not in {path}")
    open(path, "w").writelines(out)


def run(case, name, params, attrs, forcing, decisions):
    work = exp_dir(case, name)
    settings = os.path.join(work, "settings")
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(os.path.join(RUNS, case, "summa_inputs"), settings)
    with open(os.path.join(settings, "outputControl.txt"), "a") as f:
        f.writelines(["\n"] + [f"{v:<26}| day | mean\n" for v in OUTPUTS])
    for kv in params:
        k, v = kv.split("=")
        with nc4.Dataset(os.path.join(settings, "trialParams.nc")) as d:
            if k in d.variables:
                raise SystemExit(f"{k} is in trialParams.nc; not handled")
        set_param(os.path.join(settings, "localParamInfo.txt"), k, v)
    for kv in attrs:  # name=value or name@hru=value
        k, v = kv.split("=")
        k, _, h = k.partition("@")
        with nc4.Dataset(os.path.join(settings, "attributes.nc"), "a") as d:
            x = d[k][:]
            if h:
                x[list(np.asarray(d["hruId"][:])).index(int(h))] = float(v)
            else:
                x[:] = float(v)
            d[k][:] = x
    for kv in decisions:
        k, v = kv.split("=")
        p = os.path.join(settings, "modelDecisions.txt")
        txt = re.sub(rf"^({k}\s+)\S+", rf"\g<1>{v}", open(p).read(), flags=re.M)
        open(p, "w").write(txt)
    os.makedirs(os.path.join(work, "output"))
    os.makedirs(os.path.join(work, "state"))
    config = config_text(case, os.path.join(RUNS, case), settings, work, START, END, START, END, "dds", 1, 1,
                         temperature=False)
    config = config[:config.index("\n[calibration]")]
    config = re.sub(r"^use_mizuroute .*", "use_mizuroute    = false", config, flags=re.M)
    config = config.replace("write_timeseries = false", "write_timeseries = true")
    if forcing:
        config = re.sub(r'^forcing_path .*', f'forcing_path  = "{os.path.abspath(forcing)}/"', config, flags=re.M)
    shutil.copy(os.path.join(settings, "coldState.nc"), os.path.join(work, "state", "coldState.nc"))
    open(os.path.join(work, "config.toml"), "w").write(config)
    open(os.path.join(work, "change.txt"), "w").write(" ".join(params + attrs + decisions + ([forcing] if forcing else [])) + "\n")
    exe = os.path.join(SUMMA_DIR, "bin", "summa_sundials_mizuroute.exe")
    with open(os.path.join(work, "run.log"), "w") as log:
        status = subprocess.run([exe, "-c", os.path.join(work, "config.toml")], cwd=work, stdout=log,
                                stderr=subprocess.STDOUT).returncode
    print(f"{case} {name}: run {'failed' if status else 'done'}")


def load(case, name):
    """Daily output as {var: array(time, hru, dom)}, the time index, and the clean-glacier domain of each HRU."""
    work = exp_dir(case, name)
    out = [f for f in os.listdir(os.path.join(work, "output")) if f.endswith(".nc") and "timestep" not in f]
    with nc4.Dataset(os.path.join(work, "output", sorted(out)[0])) as d:
        time = pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False,
                                           only_use_python_datetimes=True)).normalize()
        v = {k.removesuffix("_mean"): np.ma.filled(d[k][:].astype(float), np.nan) for k in d.variables if k.endswith("_mean")}
    with nc4.Dataset(os.path.join(work, "settings", "coldState.nc")) as c:
        c.set_auto_mask(False)
        clean = (c["nGlce"][:] > 0) & (c["nSoil"][:] == 0)
    dom = {h: int(np.argmax(clean[h])) for h in range(clean.shape[0])}
    return v, time, dom


def mass_series(v, time, dom):
    gm = v["glacMass4AreaChange"]
    change = np.diff(gm, axis=0, prepend=gm[:1])
    reset = (time.month == 10) & (time.day == 2)
    change[reset] = gm[reset]
    mass = np.cumsum(change, axis=0) / 1000.0
    return {h: (pd.Series(mass[:, h, m], index=time), float(v["DOMelev"][0, h, m])) for h, m in dom.items()}


def stakes(case, name, years=(2006, 2015)):
    v, time, dom = load(case, name)
    series = mass_series(v, time, dom)
    path = os.path.join(GLACIER, STAKES[case.split("_")[0]])
    s = pd.read_csv(path, parse_dates=["spring_date", "fall_date"])
    s = s[(s.Year >= years[0]) & (s.Year <= years[1])]
    prev = pd.read_csv(path, parse_dates=["fall_date"])[["Year", "site_name", "fall_date"]]
    prev["Year"] += 1
    s = s.merge(prev.rename(columns={"fall_date": "prev_fall"}), on=["Year", "site_name"], how="left")
    s["prev_fall"] = s.prev_fall.fillna(pd.to_datetime((s.Year - 1).astype(str) + "-10-01"))
    rows = []
    for _, r in s.iterrows():
        h = min(series, key=lambda k: abs(series[k][1] - r.elevation))
        m = series[h][0]
        at = lambda t: float(m.asof(t))  # noqa: E731
        rows.append(dict(hru=h + 1, bw_obs=r.bw, bw_sim=at(r.spring_date) - at(r.prev_fall), bs_obs=r.ba - r.bw,
                         bs_sim=at(r.fall_date) - at(r.spring_date)))
    t = pd.DataFrame(rows)
    return t.groupby("hru").mean()


def summer_budget(case, name, years=(2006, 2015)):
    """JJA mean energy terms (W m-2) on each HRU's clean-glacier domain over the given years."""
    v, time, dom = load(case, name)
    sel = time.month.isin([6, 7, 8]) & (time.year >= years[0]) & (time.year <= years[1])
    rows = []
    for h, m in dom.items():
        r = {"hru": h + 1}
        for k, lab in [("scalarGroundAbsorbedSolar", "SWnet"), ("scalarLWNetGround", "LWnet"),
                       ("scalarSenHeatGround", "H"), ("scalarLatHeatGround", "LE"), ("scalarGroundAlbedo", "alb"),
                       ("airtemp", "T"), ("windspd", "U"), ("SWRadAtm", "SWin"), ("LWRadAtm", "LWin")]:
            if k in v:
                r[lab] = np.nanmean(v[k][sel, h, m] if v[k].ndim == 3 else v[k][sel, h])
        if "T" in r:
            r["T"] -= 273.15
        rows.append(r)
    return pd.DataFrame(rows).set_index("hru")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("action", choices=["run", "stakes", "budget"])
    p.add_argument("case")
    p.add_argument("names", nargs="+")
    p.add_argument("--param", action="append", default=[])
    p.add_argument("--attr", action="append", default=[])
    p.add_argument("--decision", action="append", default=[])
    p.add_argument("--forcing")
    p.add_argument("--years", default="2006-2015", help="stake years, first-last")
    a = p.parse_args()
    pd.set_option("display.width", 200)
    if a.action == "run":
        run(a.case, a.names[0], a.param, a.attr, a.forcing, a.decision)
        return
    for n in a.names:
        print(f"== {a.case} {n}: {open(os.path.join(exp_dir(a.case, n), 'change.txt')).read().strip()}")
        if a.action == "stakes":
            t = stakes(a.case, n, tuple(int(y) for y in a.years.split("-")))
            t["d_bw"], t["d_bs"] = t.bw_sim - t.bw_obs, t.bs_sim - t.bs_obs
            print(t.round(2).to_string())
        else:
            print(summer_budget(a.case, n).round(2).to_string())


if __name__ == "__main__":
    main()
