#!/usr/bin/env python3
"""Each stake winter's balance error against the forcing's and the station's winter precipitation.

    winter_forcing_vs_station.py gulkana_added:468:1480 wolverine_added:472:990

Winter is fall stake date to spring stake date, from the rerun's aligned pairs. Forcing precipitation and the share
falling below 0 C are at each glacier HRU (unscaled by the snowfall multipliers); the station's is its gauge, uncorrected.
"""
import os
import sys

import netCDF4 as nc
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from summer_forcing_vs_station import WF, aligned, forcing, station  # noqa: E402

for spec in sys.argv[1:]:
    case, sample, elev = spec.split(":")
    basin, elev = case.split("_")[0], int(elev)
    mb = aligned(f"{WF}/runs/{case}/calibration_rerun/sample_{sample}_aligned/output")["mass_balance"]
    z = np.asarray(nc.Dataset(f"{WF}/runs/{case}/summa_inputs/attributes.nc")["elevation"][:], float)
    fo = {i: forcing(case, zi)[0] for i, zi in enumerate(z)}  # each HRU's own forcing, unlapsed
    st = station(basin, elev)
    rows, d = [], list(mb.index)
    for k in range(1, len(d)):
        a, b = d[k - 1], d[k]
        if not (7 <= a.month <= 11 and 3 <= b.month <= 6):
            continue
        w = slice(a.normalize(), b.normalize())
        r = {"winter": b.year, "err": mb.sim[b] - mb.obs[b], "obs": mb.obs[b]}
        for i, f in fo.items():
            f = f.loc[w]
            r[f"P{i + 1}"] = f.P.sum()
            r[f"snow{i + 1}"] = f.P[f["T"] < 0].sum() / max(f.P.sum(), 1)
        s = st.loc[w, "P"]
        r["P_st"] = s.sum() / s.notna().mean() if s.notna().mean() > 0.8 else np.nan
        rows.append(r)
    df = pd.DataFrame(rows).set_index("winter")
    print(f"== {case} {sample}: HRUs at {np.round(z).astype(int).tolist()} m, station {elev} m")
    print(df.round(2).to_string())
    for c in [c for c in df if c not in ("err",)]:
        ok = df[[c, "err"]].dropna()
        if len(ok) > 4:
            print(f"    error vs {c:6s} r {ok[c].corr(ok.err):+.2f} (n {len(ok)})")
    e = df.err
    print(f"  mean error {e.mean():.0f}, WY2006-15 {e[df.index <= 2015].mean():.0f}, 2016-26 {e[df.index > 2015].mean():.0f}; "
          f"sd obs {df.obs.std():.0f}, sim {(df.obs + e).std():.0f}")
