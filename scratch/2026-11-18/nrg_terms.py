#!/usr/bin/env python3
"""Glacier surface energy balance of each stake summer in a rerun written with the energy terms (queue_nrg.sh), and
how each term rises with the summer's positive degree-days; then the summer-balance sensitivity of each rerun.

    nrg_terms.py wolverine_added:990:472_nrg,472_cool06,472_ice065 gulkana_added:1480:468_nrg

Terms are means over the glacier domain of each HRU (domType 2), summed over the summer as melt-equivalent
mm w.e. (W m-2 x seconds / 334 kJ kg-1). The first rerun of each case gives the terms; every rerun gives the
summer balance per degree-day against the stakes'.
"""
import glob
import os
import sys

import netCDF4 as nc
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from summer_forcing_vs_station import WF, aligned, forcing  # noqa: E402

TERMS = ["scalarGroundAbsorbedSolar", "scalarLWNetGround", "scalarSenHeatGround", "scalarLatHeatGround",
         "scalarGroundNetNrgFlux"]
LF = 333.7e3


def summers(mb):
    d = list(mb.index)
    return [(d[k - 1], d[k]) for k in range(1, len(d))
            if 3 <= d[k - 1].month <= 6 and 7 <= d[k].month <= 10 and (d[k] - d[k - 1]).days < 200]


for spec in sys.argv[1:]:
    case, elev, runs = spec.split(":")
    fo, _ = forcing(case, int(elev))
    print(f"== {case}")
    for j, run in enumerate(runs.split(",")):
        out = f"{WF}/runs/{case}/calibration_rerun/sample_{run}/output"
        mb = aligned(out)["mass_balance"]
        ss = summers(mb)
        pdd = pd.Series({b.year: fo["T"].loc[a.normalize():b.normalize()].clip(lower=0).sum() for a, b in ss})
        obs = pd.Series({b.year: mb.obs[b] for a, b in ss})
        sim = pd.Series({b.year: mb.sim[b] for a, b in ss})
        e = sim - obs
        print(f"  {run}: summer balance per degree-day obs {np.polyfit(pdd, obs, 1)[0]:.2f}, sim {np.polyfit(pdd, sim, 1)[0]:.2f}; "
              f"summer bias {e.mean():.0f}, rmse {np.sqrt((e ** 2).mean()):.0f}; error vs PDD r {e.corr(pdd):+.2f}")
        for t, df in aligned(out).items():
            if t.startswith("discharge"):
                cal, ev = df[df.index < "2015-10-01"], df[df.index >= "2015-10-01"]
                kge = lambda d: 1 - np.sqrt((d.obs.corr(d.sim) - 1) ** 2 + (d.sim.std() / d.obs.std() - 1) ** 2 + (d.sim.mean() / d.obs.mean() - 1) ** 2)
                print(f"     discharge KGE {kge(cal):.3f} / {kge(ev):.3f}; seasonal MB RMSE "
                      f"{np.sqrt(((mb.sim - mb.obs)[mb.index < '2015-10-01'] ** 2).mean()):.0f} / "
                      f"{np.sqrt(((mb.sim - mb.obs)[mb.index >= '2015-10-01'] ** 2).mean()):.0f}")
        if j:
            continue
        f = [p for p in glob.glob(f"{out}/*_day.nc") if "spinup" not in p][0]
        with nc.Dataset(f) as d:
            t = pd.to_datetime(nc.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False,
                                           only_use_python_datetimes=True))
            glac = np.ma.filled(d["domType"][:].astype(int), -1) == 2
            area = np.where(glac, np.ma.filled(d["DOMarea_mean"][0].astype(float), 0), 0)
            nh = glac.any(axis=0).sum()
            for h in range(glac.shape[1]):
                if not glac[:, h].any():
                    continue
                rows = {}
                for v in TERMS + ["scalarSnowAlbedo", "scalarSWE"]:
                    x = np.ma.filled(d[v][:].astype(float), np.nan)
                    x = np.where(np.abs(x) > 9000, np.nan, x)
                    rows[v] = pd.Series(np.nansum(x[:, :, h] * area[:, h], axis=1) / area[:, h].sum(), index=t)
                tab = {}
                for a, b in ss:
                    w = slice(a.normalize(), b.normalize())
                    r = {k: rows[k].loc[w].sum() * 86400 / LF for k in TERMS}
                    r["albedo"] = rows["scalarSnowAlbedo"].loc[w].mean()
                    r["snowfree_days"] = (rows["scalarSWE"].loc[w] < 1).sum()
                    tab[b.year] = r
                tab = pd.DataFrame(tab).T
                tab["pdd"] = pdd
                print(f"   HRU {h + 1} glacier, summer totals as melt-equivalent mm w.e. (mean, and per degree-day across summers)")
                for c in tab:
                    if c == "pdd":
                        continue
                    print(f"     {c:28s} mean {tab[c].mean():8.1f}   per degree-day {np.polyfit(tab.pdd, tab[c], 1)[0]:+.3f}")
