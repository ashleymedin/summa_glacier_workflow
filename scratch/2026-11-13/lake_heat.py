#!/usr/bin/env python3
"""Does Wolverine's lake add the missing summer heat? Trial 459 of the added-data calibration rerun on the stream
case (lake_heat_runs.sh): no lake, the lake from its volume, and the lake with a fetch-limited water roughness.
Prints the scores, the monthly water-temperature error, the lake area against the imagery and the heat the lake
adds; writes the figure and the LaTeX table for glacier_forcing_runs.tex.

    ./lake_heat.py RUNS_DIR OBS_DIR LAKE_DIR FIG.pdf TABLE.tex
      RUNS_DIR  runs/wolverine_stream/calibration_added_rerun
      OBS_DIR   data/domain_Wolverine/observations/calibration
      LAKE_DIR  data/domain_Wolverine/observations/lake_area
"""
import glob
import os
import sys

import matplotlib
import netCDF4 as nc4
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RUNS = [("nolake", "no lake"), ("lake", "lake held full"), ("infill", "filling, all sediment trapped"),
        ("settle", "filling with settling silt"), ("fetch", "settling, roughness from wind and fetch")]
COLORS = ["#1b6ca8", "#e07b39", "#3a923a", "#9b59b6", "#c0392b"]
AREA_RUNS = ["lake", "infill", "settle", "fetch"]
CAL, EVAL = ("2015-10-01", "2019-09-30"), ("2019-10-01", "2026-09-30")
MONTHS = [5, 6, 7, 8, 9, 10]
RHOC = 1000.0 * 4181.0
WET = (0, 3)  # the wetland: HRU index 0, domain index 3


def times(d):
    return pd.Timestamp("1990-01-01") + pd.to_timedelta(np.round(np.array(d["time"][:], float)), unit="s")


def load(runs_dir, label, wet=WET):
    out = os.path.join(glob.glob(os.path.join(runs_dir, f"sample_*_{label}"))[0], "output")
    with nc4.Dataset(glob.glob(os.path.join(out, "*sample000001_timestep.nc"))[0]) as d:
        hourly = pd.DataFrame({"Q": np.array(d["Q_reach"][:, 0, 0], float), "T": np.array(d["T_reach"][:, 0], float)},
                              index=times(d))
    # USGS daily means are over Alaska standard days, stamped at their end, 09:00 UTC
    day = hourly.resample("24h", offset="9h").mean()
    day.index = day.index + pd.Timedelta("24h")
    with nc4.Dataset(glob.glob(os.path.join(out, "*sample000001_day.nc"))[0]) as d:
        g = lambda v: np.ma.filled(d[v][:, wet[0], wet[1]].astype(float), np.nan)
        wet = pd.DataFrame({"area": g("DOMarea_mean"), "Tw": g("scalarStreamTemp_mean"),
                            "qin": g("scalarStreamLatInflow_mean"), "qout": g("scalarStreamOutflow_mean")}, index=times(d))
    return day, wet


def obs_series(path, var):
    with nc4.Dataset(path) as d:
        return pd.Series(np.ma.filled(d[var][:].astype(float), np.nan), index=times_obs(d)).dropna()


def times_obs(d):
    t = nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)
    return pd.to_datetime([str(x) for x in t])


def kge(s, o):
    r = np.corrcoef(s, o)[0, 1]
    return 1 - np.sqrt((r - 1) ** 2 + (s.std() / o.std() - 1) ** 2 + (s.mean() / o.mean() - 1) ** 2)


def lake_imagery(lake_dir):
    """July-August median open water by year from 2013, scenes under half snow or ice (infill_fit.py)."""
    from infill_fit import imagery
    return imagery(lake_dir)


def main():
    runs_dir, obs_dir, lake_dir, fig_out, tab_out = sys.argv[1:6]
    tobs = obs_series(os.path.join(obs_dir, "USGS_15236900_daily_temperature.nc"), "t_obs")
    qobs = obs_series(os.path.join(obs_dir, "USGS_15236900_daily_flow.nc"), "q_obs")
    if tobs.max() > 200:
        tobs = tobs - 273.15
    res, rows = {}, []
    for label, name in RUNS:
        day, wet = load(runs_dir, label)
        T = day["T"] - 273.15
        e = (T.reindex(tobs.index) - tobs).dropna()
        q = pd.concat([day["Q"].reindex(qobs.index), qobs], axis=1, keys=["s", "o"]).dropna()
        qe = q[EVAL[0]:EVAL[1]]
        sc = {"kge": kge(qe.s, qe.o),
              "cal": np.sqrt((e[CAL[0]:CAL[1]] ** 2).mean()), "eval": np.sqrt((e[EVAL[0]:EVAL[1]] ** 2).mean()),
              "month": e.groupby(e.index.month).mean().reindex(MONTHS)}
        open_ = wet.index[wet.area > 0]
        # heat the lake adds to the glacier water it passes (W): outflow at the lake's temperature, inflow at freezing
        summer = wet[wet.index.month.isin([6, 7, 8, 9]) & (wet.area > 0)]
        heat = RHOC * summer.qout * (summer.Tw - 273.15)
        sc.update(opened=open_[0] if len(open_) else None, wet=wet, heat=heat, day=day, err=e)
        res[label] = sc
        print(f"{name:28s} KGE {sc['kge']:.3f}  T RMSE cal {sc['cal']:.2f} eval {sc['eval']:.2f} K  "
              f"opens {sc['opened']}  monthly bias " + " ".join(f"{m}:{v:+.2f}" for m, v in sc["month"].items()))
        if len(summer):
            gauge = day["Q"].reindex(summer.index, method="nearest")
            print(f"{'':28s} JJAS lake {summer.Tw.mean() - 273.15:.2f} C, heat {heat.mean() / 1e6:.2f} MW, "
                  f"warming the gauge flow {np.nanmean(heat / (RHOC * gauge)):.2f} K")

    img = lake_imagery(lake_dir)
    area = {}
    for label in AREA_RUNS:
        wet = res[label]["wet"]
        jja = wet[wet.index.month.isin([7, 8])]
        area[label] = jja.area.groupby(jja.index.year).median() / 1e6
    print("\nJul-Aug lake area (km2): year " + " ".join(AREA_RUNS) + " imagery")
    for y in sorted(set(area["lake"].index) | set(img.index)):
        print(f"  {y} " + " ".join(f"{area[k].get(y, np.nan):.4f}" for k in AREA_RUNS) + f" {img.get(y, np.nan):.4f}")

    with open(tab_out, "w") as f:
        for label, name in RUNS:
            sc = res[label]
            f.write(f"{name:<34s} & {sc['kge']:.2f} & {sc['cal']:.2f} & {sc['eval']:.2f} & "
                    + " & ".join(f"${v:+.2f}$".replace("+", "+") for v in sc["month"].values).replace("-", "$-$").replace("$$-$", "$-")
                    + " \\\\\n")
    print("wrote", tab_out)

    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5.2))
    w = 0.16
    for k, (label, name) in enumerate(RUNS):
        m = res[label]["month"]
        a.bar(np.arange(len(MONTHS)) + (k - 2) * w, m.values, w * 0.92, color=COLORS[k],
              label=f"{name}: RMSE {res[label]['cal']:.2f} / {res[label]['eval']:.2f} K")
    a.axhline(0, color="k", lw=0.6)
    a.set_xticks(np.arange(len(MONTHS)), ["May", "Jun", "Jul", "Aug", "Sep", "Oct"])
    a.set_ylabel("water temperature, model $-$ gauge (K)")
    a.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False,
             title="RMSE WY2016–19 / WY2020–26", title_fontsize=8)
    a.set_title("(a) mean error by month, 2016–2026", fontsize=10)
    years = np.arange(2004, 2027)
    b.plot(img.index, img.values, "o", color="k", ms=5, label="imagery, Jul–Aug median (from 2013)")
    for label in AREA_RUNS:
        k = [r[0] for r in RUNS].index(label)
        b.plot(area[label].index, area[label].values, "-", color=COLORS[k], lw=1.8, label=RUNS[k][1])
    b.set_xlim(years[0] + 0.5, years[-1] + 0.5); b.set_ylim(0, 0.07)
    b.set_xticks(range(2005, 2027, 3))
    b.set_ylabel("lake area (km$^2$)"); b.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    b.set_title("(b) July–August lake area, model from October 2004", fontsize=10)
    for ax in (a, b):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(fig_out, bbox_inches="tight"); print("wrote", fig_out)


if __name__ == "__main__":
    main()
