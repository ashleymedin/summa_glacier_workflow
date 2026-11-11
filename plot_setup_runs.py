#!/usr/bin/env python3
"""Plot the balanced trials of the WY2006-2026 glacier runs against the gauge, the stakes and the WGMS estimates.

    plot_setup_runs.py <basin> <out.pdf> <case>:<name>:<sample>:<label> [...]

    ./plot_setup_runs.py wolverine figs/wolverine_best.pdf wolverine_added:calibration:459:added wolverine_general:calibration_rerun_nov11:396:general

Each trial is the output of runs/rerun_trials.py --aligned, with and without --calibration-years (see trial), so every
score and every simulated balance is the calibration driver's own (its evaluation group in the timestep file). Rows:
(a) daily discharge, with each trial's KGE; (b) its mean annual cycle on gauged days, each trial's glacier ice melt
shaded; (c) the seasonal glacier-wide balances the driver scored against the USGS stakes; (d) the annual balances it
scored against the WGMS annual mass-change estimates. Scores are calibration / held out.
"""
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import netCDF4 as nc
import numpy as np
import pandas as pd

WORKFLOW = os.path.dirname(os.path.abspath(__file__))
OBS = {"gulkana": ("data/domain_Gulkana/observations/calibration", "USGS_15478040_daily_flow.nc"),
       "wolverine": ("data/domain_Wolverine/observations/calibration", "USGS_15236900_daily_flow.nc")}
COLORS = ["#1b6ca8", "#e07b39", "#3a923a", "#9b59b6"]
START, HELD, END = "2005-10-01", "2015-10-01", "2026-09-30"  # run, held-out and end dates


def dates(d):
    """The time coordinate as dates, the time rounded to the hour first (SUMMA's stamps carry rounding)."""
    t = nc.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False, only_use_python_datetimes=True)
    return pd.DatetimeIndex(pd.to_datetime(list(t)).round("h").strftime("%Y-%m-%d"))


def series(path, var):
    d = nc.Dataset(path)
    return pd.Series(np.ma.filled(d[var][:].astype(float), np.nan).squeeze(), index=dates(d))


def aligned(out):
    """The driver's aligned obs and sim of each target in a rerun's timestep file, the pairs it scored."""
    h = nc.Dataset([f for f in glob.glob(os.path.join(out, "*_timestep.nc")) if "spinup" not in f][0])
    ev = {}
    for t, g in h["evaluation"].groups.items():
        ev[t] = pd.DataFrame({"obs": np.ma.filled(g["obs"][:].astype(float), np.nan),
                              "sim": np.ma.filled(g["sim"][:].astype(float), np.nan)}, index=dates(g)).dropna()
    return ev


def trial(case, name, sample):
    """Daily discharge and glacier ice melt (m3 s-1), and the scored pairs of each target: the calibration years'
    from the rerun over those years alone (sample_<n>_aligned_cal), as the search ran it, and the held-out years'
    from the rerun through them (sample_<n>_aligned), as calibrate.py evaluate ran it."""
    rerun = os.path.join(WORKFLOW, "runs", case, name if "_rerun" in name else f"{name}_rerun")  # a rerun folder, or its calibration
    out = os.path.join(rerun, f"sample_{sample}_aligned", "output")
    path = [f for f in glob.glob(os.path.join(out, "*_day.nc")) if "spinup" not in f][0]
    d = nc.Dataset(path)
    melt = np.ma.filled(d["scalarGlceMelt_mean"][:].astype(float), 0.0)  # m s-1 by HRU and domain, negative melting
    area = np.ma.filled(d["DOMarea_mean"][:].astype(float), 0.0)         # m2
    used = (melt > -9000) & (area > 0)                                   # -9999 marks a domain an HRU lacks
    melt, area = np.where(used, np.abs(melt), 0.0), np.where(used, area, 0.0)
    daily = pd.DataFrame({"Qice": (melt * area).sum((1, 2))}, index=dates(d))
    daily = daily[~daily.index.duplicated()]  # the run's last, partial day repeats the last date
    h = nc.Dataset(path.replace("_day.nc", "_timestep.nc"))
    th = pd.to_datetime(nc.num2date(h["time"][:], h["time"].units, only_use_cftime_datetimes=False,
                                    only_use_python_datetimes=True))
    hru_area = float(np.sum(nc.Dataset(os.path.join(WORKFLOW, "runs", case, "summa_inputs", "attributes.nc"))["HRUarea"][:]))
    q = pd.Series(np.ma.filled(h["averageRoutedRunoff"][:, 0].astype(float), np.nan) * hru_area, index=th.round("h"))
    q = q.resample("24h", offset="9h", label="right", closed="right").mean()  # the gauge's Alaska day, stamped at its end
    q.index = pd.to_datetime(q.index.strftime("%Y-%m-%d"))
    daily["Q"] = q.reindex(daily.index)
    cal, held = aligned(os.path.join(rerun, f"sample_{sample}_aligned_cal", "output")), aligned(out)
    ev = {t: pd.concat([cal[t][cal[t].index < HELD], held[t][held[t].index >= HELD]]) for t in held}
    return daily, ev


def kge(df):
    r = np.corrcoef(df.sim, df.obs)[0, 1]
    return 1 - np.sqrt((r - 1) ** 2 + (df.sim.std() / df.obs.std() - 1) ** 2 + (df.sim.mean() / df.obs.mean() - 1) ** 2)


def rmse(df):
    return np.sqrt(np.mean((df.sim - df.obs) ** 2))


def split(df, score):
    """A score over the calibration years and over the held-out years."""
    return score(df[df.index < HELD]), score(df[df.index >= HELD])


def bars(ax, sims, target, obs_label, title):
    """Grouped bars by water year, observed black and each trial beside it, of the pairs the driver scored."""
    held = int(HELD[:4]) + 1
    wy = lambda idx: (idx - pd.Timedelta(days=1)).year + ((idx - pd.Timedelta(days=1)).month >= 10)  # a 1 Oct stamp ends its year
    first = min(wy(ev[target].index).min() for _, _, ev in sims)
    last = max(wy(ev[target].index).max() for _, _, ev in sims)
    ax.axvspan(held - 0.5, last + 0.5, color="0.93", zorder=0)
    w = 0.8 / (len(sims) + 1)
    off = lambda k: (k - len(sims) / 2) * w
    o = pd.concat([ev[target].obs for _, _, ev in sims]).groupby(level=0).first()  # every observation a trial scored
    ax.bar(wy(o.index) + off(0), o.values, w, color="k", label=obs_label)
    for k, ((label, _, ev), c) in enumerate(zip(sims, COLORS), start=1):
        e = ev[target]
        cal, hold = split(e, rmse)
        ax.bar(wy(e.index) + off(k), e.sim, w, color=c, label=f"{label}: RMSE {cal:.0f} / {hold:.0f} mm")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlim(first - 0.6, last + 0.6)
    ax.set_xticks(np.arange(first + first % 2, last + 1, 2))
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + 0.4 * (hi - lo))  # room for the legend
    ax.text(held - 0.35, 0.74, "held out", transform=ax.get_xaxis_transform(), color="grey", fontsize=8, va="top")
    ax.legend(fontsize=8, loc="upper center", ncol=len(sims) + 1, framealpha=0.9)
    ax.set_ylabel("Glacier-wide balance (mm w.e.)")
    ax.set_title(title, loc="left", fontsize=10)


def main():
    basin, pdf, specs = sys.argv[1], sys.argv[2], [x.split(":") for x in sys.argv[3:]]
    folder, flow = OBS[basin]
    q = series(os.path.join(WORKFLOW, folder, flow), "q_obs")[START:END]
    sims = [(label, *trial(case, name, sample)) for case, name, sample, label in specs]

    fig, ax = plt.subplots(4, 1, figsize=(10, 14), gridspec_kw={"height_ratios": [1.1, 1, 1, 1]})
    ax[0].plot(q.index, q.values, color="k", lw=0.8, label="USGS gauge")
    for (label, s, ev), c in zip(sims, COLORS):
        cal, hold = split(ev["discharge"], kge)
        ax[0].plot(s.index, s["Q"], color=c, lw=0.6, alpha=0.85, label=f"{label}: KGE {cal:.2f} / {hold:.2f}")
    ax[0].axvline(pd.Timestamp(HELD), color="grey", ls=":", lw=1)
    ax[0].text(pd.Timestamp(HELD) + pd.Timedelta(days=30), ax[0].get_ylim()[1] * 0.80, "held out", color="grey", fontsize=8)
    ax[0].set_ylabel("Discharge (m$^3$ s$^{-1}$)")
    ax[0].legend(fontsize=8, ncol=len(sims) + 1, loc="upper left")
    ax[0].set_title("(a) Daily discharge, WY2006–2026 (KGE calibration / held out)", loc="left", fontsize=10)

    doy = lambda x: x.groupby(x.index.day_of_year).mean()
    qo = doy(q)
    ax[1].plot(qo.index, qo.values, color="k", lw=1.5, label="USGS gauge")
    for (label, s, _), c in zip(sims, COLORS):
        s = s.loc[q.dropna().index.intersection(s.index)]
        g = doy(s["Qice"])
        ax[1].fill_between(g.index, 0, g.values, color=c, alpha=0.2, lw=0, label=f"{label}: glacier ice melt")
        ax[1].plot(doy(s["Q"]).index, doy(s["Q"]).values, color=c, lw=1.2, label=label)
    ticks = pd.date_range("2001-01-01", "2001-12-01", freq="MS")
    ax[1].set_xticks(ticks.day_of_year, ticks.strftime("%b"))
    ax[1].set_xlim(91, 334)
    ax[1].set_ylabel("Discharge (m$^3$ s$^{-1}$)")
    ax[1].legend(fontsize=8, loc="upper left")
    ax[1].set_title("(b) Mean annual cycle on gauged days, WY2006–2026", loc="left", fontsize=10)

    bars(ax[2], sims, "mass_balance", "USGS stakes",
         "(c) Seasonal balances by water year, winter up and summer down (RMSE calibration / held out)")
    bars(ax[3], sims, "wgms_amce", "WGMS estimate",
         "(d) Annual balances by water year (RMSE calibration / held out)")
    fig.tight_layout()
    fig.savefig(pdf)
    print(f"wrote {pdf}")


if __name__ == "__main__":
    main()
