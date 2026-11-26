#!/usr/bin/env python3
"""Slate Creek at its default parameters, one spun-up case per deep thermal option: a routed run through the calibration
driver (runs/<case>/default_routed), then discharge KGE and water-temperature RMSE at the gauge's reach, and each HRU's
yearly maximum thaw depth and the temperature at the soil column's base.

    slate_default.py slate_stream slate_stream_none slate_stream_airgw          (run and score)
    slate_default.py --score slate_stream ...                                   (score only)
"""
import os
import sys

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(WF, "runs"))
sys.path.insert(0, os.path.join(WF, "scratch", "2026-11-24"))
import default_run  # noqa: E402
from calibrate import CASES, HERE, case_spec, periods  # noqa: E402

import netCDF4 as nc4  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

LAYERS = ["mLayerTemp", "mLayerVolFracIce", "mLayerHeight", "mLayerDepth", "scalarAquiferTemp"]


def obs_series(path, name):
    """A daily observation on the gauge's UTC-9 days (stamped at the day's end)."""
    with nc4.Dataset(path) as d:
        t = (pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)) - pd.Timedelta(days=1)).normalize()
        return pd.Series(np.ma.filled(d[name][:].astype(float), np.nan).squeeze(), index=t)


def kge(s, o):
    m = np.isfinite(s) & np.isfinite(o)
    s, o = s[m], o[m]
    r = np.corrcoef(s, o)[0, 1]
    return 1 - np.sqrt((r - 1) ** 2 + (s.std() / o.std() - 1) ** 2 + (s.mean() / o.mean() - 1) ** 2), r, s.mean() / o.mean(), s.std() / o.std()


def reach_scores(case, work):
    c = CASES[case.split("_")[0]]
    seg = case_spec(case).get("gauge_reach", 1) - 1
    f = [x for x in os.listdir(os.path.join(work, "output")) if x.endswith("_timestep.nc") and "spinup" not in x][0]
    with nc4.Dataset(os.path.join(work, "output", f)) as d:
        t = pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)) - pd.Timedelta(hours=9)
        q = pd.Series(np.ma.filled(d["Q_reach"][:, seg, 0], np.nan), index=t).resample("D").mean()
        temp = pd.Series(np.ma.filled(d["T_reach"][:, seg], np.nan), index=t).resample("D").mean()
    if np.nanmean(temp) > 200:
        temp -= 273.15
    qo = obs_series(os.path.join(WF, c["obs"], c["flow"]), "q_obs").reindex(q.index)
    to = obs_series(os.path.join(WF, c["obs"], c["temp"]), "t_obs").reindex(temp.index)
    cal0, cal1, ev0, ev1 = periods(case)
    rows = []
    for label, a, b in (("calibrate", cal0, cal1), ("evaluate", ev0, ev1)):
        k, r, beta, alpha = kge(q[a:b].values, qo[a:b].values)
        e = (temp[a:b] - to[a:b]).dropna()
        rows.append(dict(case=case, period=f"{label} {a[:7]}..{b[:7]}", KGE=k, r=r, beta=beta, alpha=alpha,
                         T_rmse=np.sqrt((e ** 2).mean()), T_bias=e.mean(), T_days=len(e)))
    clim = pd.DataFrame({"Q_sim": q, "Q_obs": qo, "T_sim": temp.where(to.notna()), "T_obs": to}).groupby(q.index.month).mean()
    return pd.DataFrame(rows), clim


def thaw(case, work):
    """Each upland HRU's yearly maximum thaw depth (m, the deepest soil layer above 0 C on any day's end) and the yearly
    mean temperature (C) of the column's deepest layer; layer values are instantaneous at each day's end."""
    f = [x for x in os.listdir(os.path.join(work, "output")) if x.endswith("_day.nc") and "spinup" not in x][0]
    with nc4.Dataset(os.path.join(work, "output", f)) as d:
        d.set_auto_mask(False)
        t = pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False))
        temp = d["mLayerTemp"][:]  # time, midToto, hru, dom
        height = d["mLayerHeight"][:, 1:]  # on the interface dimension, mid-layer heights from its second entry
        hru_id = d["hruId"][:]
    with nc4.Dataset(os.path.join(work + "_settings", "attributes.nc")) as a:
        n_gru = len(a.dimensions["gru"])
    stream = set(sorted(hru_id)[-n_gru:])  # add_stream_grus.py numbers each GRU's stream HRU after the land HRUs
    years = np.asarray(t.year + (t.month >= 10))  # water years
    out = {}
    for h in range(temp.shape[2]):
        if hru_id[h] in stream:
            continue
        tt = np.full((len(t), 30), np.nan)
        for i in range(len(t)):  # soil and bedrock layers, below the snow (negative heights)
            ok = (height[i, :, h, 0] >= 0) & (height[i, :, h, 0] < 1e3)
            n = ok.sum()
            tt[i, :n] = temp[i, ok, h, 0] - 273.15
            if i == 0:
                z = height[0, ok, h, 0]
        nlay = len(z)
        tt = tt[:, :nlay]
        rows = {}
        for wy in np.unique(years):
            x = tt[years == wy]
            thawed = np.nanmax(x, axis=0) > 0
            rows[wy] = dict(max_thaw_m=z[np.nonzero(thawed)[0].max()] if thawed.any() else 0.0,
                            frozen_all_year_below_m=z[np.nonzero(~thawed)[0].min()] if (~thawed).any() else np.nan,
                            base_T_C=np.nanmean(x[:, -1]))
        out[int(hru_id[h])] = pd.DataFrame(rows).T.loc[: years[-1] - 1]  # whole water years only
    return out, nlay, z


if __name__ == "__main__":
    cases = [a for a in sys.argv[1:] if not a.startswith("--")]
    pd.set_option("display.width", 200)
    scores = []
    default_run.OUTPUTS = default_run.OUTPUTS + LAYERS
    for case in cases:
        work = os.path.join(HERE, case, "default_routed")
        if "--score" not in sys.argv:
            default_run.run_routed(case)
        s, clim = reach_scores(case, work)
        scores.append(s)
        print(f"\n== {case}\nmonthly means at the gauge (Q m3/s, T C on observed days):\n{clim.round(2).T.to_string()}")
        try:
            hrus, nlay, z = thaw(case, work)
            print(f"{nlay} layers, mid-depths (m): {np.round(z, 2).tolist()}")
            for h, df in hrus.items():
                print(f"HRU {h}: max thaw (m) {df.max_thaw_m.round(2).tolist()}  frozen all year from (m) "
                      f"{df.frozen_all_year_below_m.round(2).tolist()}  base layer mean T (C) {df.base_T_C.round(2).tolist()}")
        except (KeyError, IndexError) as e:
            print(f"no layer output ({e})")
    print("\n" + pd.concat(scores).round(3).to_string(index=False))
