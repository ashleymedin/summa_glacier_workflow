#!/usr/bin/env python3
"""Gate before the paper calibrations: the 10 Nov balanced trial of each added case rerun with the Andreas (1987) and
the z0/100 heat roughness, scored on discharge KGE and the seasonal stake balances over the calibration and evaluation
years. Discharge is the GRU's routed runoff times its area, so the evaluation scores check it against the driver's.

    python scratch/2026-11-10/gate_roughness.py
"""
import datetime
import os

import netCDF4 as nc4
import numpy as np

WF = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CASES = {"wolverine_added": (298, "data/domain_Wolverine/observations/calibration", "USGS_15236900_daily_flow.nc",
                             "wolverine_mass_balance_seasonal.nc"),
         "gulkana_added": (194, "data/domain_Gulkana/observations/calibration", "USGS_15478040_daily_flow.nc",
                           "gulkana_mass_balance_seasonal.nc")}
LABELS = ["andreas", "z0h100"]
PERIODS = {"WY2006-15": (datetime.datetime(2005, 10, 1), datetime.datetime(2015, 10, 1)),
           "WY2016-26": (datetime.datetime(2015, 10, 1), datetime.datetime(2026, 10, 1))}


def times(d, name="time"):
    v = d[name]
    return np.array(nc4.num2date(v[:], v.units, getattr(v, "calendar", "standard"), only_use_cftime_datetimes=False,
                                 only_use_python_datetimes=True))


def kge(sim, obs):
    ok = np.isfinite(sim) & np.isfinite(obs)
    s, o = sim[ok], obs[ok]
    r = np.corrcoef(s, o)[0, 1]
    return 1 - np.sqrt((r - 1) ** 2 + (s.std() / o.std() - 1) ** 2 + (s.mean() / o.mean() - 1) ** 2)


def main():
    for case, (sample, obs_dir, flow, mb) in CASES.items():
        with nc4.Dataset(os.path.join(WF, obs_dir, flow)) as d:
            qt, qo = times(d), np.ma.filled(d["q_obs"][:].astype(float), np.nan)
        qobs = {t.date(): q for t, q in zip(qt, qo)}
        with nc4.Dataset(os.path.join(WF, obs_dir, mb)) as d:
            b = d["time_bnds"]
            b0 = nc4.num2date(b[:, 0], b.units, only_use_cftime_datetimes=False, only_use_python_datetimes=True)
            b1 = nc4.num2date(b[:, 1], b.units, only_use_cftime_datetimes=False, only_use_python_datetimes=True)
            mbo = np.ma.filled(d["mb_obs"][:].astype(float), np.nan)
        for label in LABELS:
            out = os.path.join(WF, "runs", case, "calibration_rerun_nov10", f"sample_{sample}_gate_{label}", "output")
            with nc4.Dataset(os.path.join(out, f"{case}_rank0001_sample000001_day.nc")) as d:
                dt = times(d)
                dmb = np.asarray(d["basin__GlacierMassChange_mean"][:, 0]) * 86400.0  # mm d-1
            with nc4.Dataset(os.path.join(WF, "runs", case, "summa_inputs", "attributes.nc")) as d:
                area = float(np.sum(d["HRUarea"][:]))
            with nc4.Dataset(os.path.join(out, f"{case}_rank0001_sample000001_timestep.nc")) as d:
                ht = times(d)
                q = np.asarray(d["averageRoutedRunoff"][:, 0]) * area
            days = np.array([t.date() for t in ht])
            ud, inv = np.unique(days, return_inverse=True)
            qd = np.bincount(inv, q) / np.bincount(inv)
            qo_d = np.array([qobs.get(u, np.nan) for u in ud])
            cum = np.concatenate([[0.0], np.cumsum(dmb)])
            day_ix = {t.date(): i for i, t in enumerate(dt)}
            for pname, (p0, p1) in PERIODS.items():
                sel = np.array([(u >= p0.date()) & (u < p1.date()) for u in ud])
                k = kge(qd[sel], qo_d[sel])
                rows = []
                for s0, s1, o in zip(b0, b1, mbo):
                    if not (np.isfinite(o) and s0 >= p0 and s1 <= p1 and s0.date() in day_ix and s1.date() in day_ix):
                        continue
                    sim = cum[day_ix[s1.date()] + 1] - cum[day_ix[s0.date()] + 1]
                    rows.append((s0, s1, o, sim))
                rows = np.array([(r[2], r[3], r[2] < 0) for r in rows])
                rmse = np.sqrt(np.mean((rows[:, 1] - rows[:, 0]) ** 2))
                summ = rows[rows[:, 2] == 1]
                wint = rows[rows[:, 2] == 0]
                print(f"{case:16s} {label:8s} {pname}: KGE {k:5.3f}  seasonal RMSE {rmse:4.0f} mm  "
                      f"summer obs {summ[:, 0].mean() / 1e3:+.2f} sim {summ[:, 1].mean() / 1e3:+.2f} m w.e. "
                      f"(range obs {summ[:, 0].min() / 1e3:+.2f}..{summ[:, 0].max() / 1e3:+.2f}, "
                      f"sim {summ[:, 1].min() / 1e3:+.2f}..{summ[:, 1].max() / 1e3:+.2f})  "
                      f"winter obs {wint[:, 0].mean() / 1e3:+.2f} sim {wint[:, 1].mean() / 1e3:+.2f}")
            with nc4.Dataset(os.path.join(out, f"{case}_run0001_calibration.nc")) as d:
                print(f"{'':16s} {label:8s} driver WY2016-26: KGE {float(d['objective'][:].ravel()[0]):5.3f}  "
                      f"seasonal RMSE {float(d['objective'][:].ravel()[1]):4.0f} mm")


if __name__ == "__main__":
    main()
