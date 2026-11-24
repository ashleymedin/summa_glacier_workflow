#!/usr/bin/env python3
"""Gauge water temperature and discharge of lemon_stream and lemon_stream_grus (mizuRoute's reach at the gauge, daily means on UTC-9 days)
against USGS 15052000, with the temperature of each GRU's runoff into its reach."""
import os, numpy as np, netCDF4 as nc
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
O = "data/domain_LemonCreek/observations/calibration/"
def times(d): return np.array([np.datetime64(x, "h") for x in nc.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)])
def obs(f, v):  # each value is stamped at the end of its day
    d = nc.Dataset(f); return dict(zip((times(d) - np.timedelta64(1, "h")).astype("datetime64[D]"), np.ma.filled(d[v][:].astype(float), np.nan).ravel()))
To, Qo = obs(O + "USGS_15052000_daily_temperature.nc", "t_obs"), obs(O + "USGS_15052000_daily_flow.nc", "q_obs")
def kge(s, o):
    r = np.corrcoef(s, o)[0, 1]; return 1 - np.sqrt((r - 1) ** 2 + (s.std() / o.std() - 1) ** 2 + (s.mean() / o.mean() - 1) ** 2)
daily = {}
for case, g in (("lemon_stream", 0), ("lemon_stream_grus", 2)):
    d = nc.Dataset(f"runs/{case}/test/output/{case}_timestep.nc"); t = times(d)
    h = (t - np.timedelta64(1, "h")).astype("datetime64[D]")  # the stamps of an observed day
    Q = np.ma.filled(d["Q_reach"][:], np.nan)[:, g, 0]; T = np.ma.filled(d["T_reach"][:], np.nan)[:, g]
    T = np.where((T > 200) & (T < 330), T - 273.16, np.nan)
    u, i = np.unique(h, return_inverse=True); n = np.bincount(i)
    q = np.bincount(i, Q) / n; tw = np.bincount(i, np.nan_to_num(T)) / np.maximum(np.bincount(i, np.isfinite(T)), 1)
    mon = u.astype("datetime64[M]").astype(int) % 12 + 1
    o, qo = np.array([To.get(x, np.nan) for x in u]), np.array([Qo.get(x, np.nan) for x in u])
    daily[case] = (u, tw, q)
    print(case)
    for nm, m in (("Jun-Sep", (mon > 5) & (mon < 10)), ("May-Oct", (mon > 4) & (mon < 11))):
        ok = m & np.isfinite(o); e = tw[ok] - o[ok]
        print(f"  {nm}: n {ok.sum()}, model {tw[ok].mean():.2f} obs {o[ok].mean():.2f} bias {e.mean():+.2f} rmse {np.sqrt((e**2).mean()):.2f} r {np.corrcoef(tw[ok], o[ok])[0, 1]:.2f}")
    print("  monthly bias", {int(k): round(float(np.nanmean((tw - o)[mon == k])), 2) for k in range(4, 12)})
    ok = np.isfinite(qo); print(f"  discharge KGE {kge(q[ok], qo[ok]):.3f}, share {q[ok].mean() / qo[ok].mean():.2f}")
    dd = nc.Dataset(f"runs/{case}/test/output/{case}_day.nc"); R = np.ma.filled(dd["averageRoutedRunoffTemp_mean"][:], np.nan) - 273.16
    md = times(dd).astype("datetime64[M]").astype(int) % 12 + 1
    print("  runoff temperature of each GRU into its reach, Jun-Sep:", R[(md > 5) & (md < 10)].mean(axis=0).round(2), " reaches", (np.ma.filled(d["T_reach"][:], np.nan)[np.isin(t.astype("datetime64[M]").astype(int) % 12 + 1, (6, 7, 8, 9))].mean(axis=0) - 273.16).round(2))
a, b = daily["lemon_stream"], daily["lemon_stream_grus"]; m = np.isin(a[0].astype("datetime64[M]").astype(int) % 12 + 1, (6, 7, 8, 9))
print(f"gauge Jun-Sep, split less one GRU: {(b[1] - a[1])[m].mean():+.2f} K, rms {np.sqrt(((b[1] - a[1])[m] ** 2).mean()):.2f}; largest day {np.abs(b[1] - a[1])[m].max():.2f}")
