#!/usr/bin/env python3
"""One GRU against three (one k, k by length): gauge discharge, glacier runoff, balance and area (runs of lemon_grus_test.py)."""
import os, numpy as np, netCDF4 as nc, glob
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def load(name):
    d = nc.Dataset(glob.glob(f"runs/lemon_grus/test/{name}/output/*_day.nc")[0]); a = nc.Dataset(f"runs/lemon_grus/test/{name}/settings/attributes.nc")
    g = np.array(a["hru2gruId"][:]); A = np.array([np.array(a["HRUarea"][:])[g == k].sum() for k in np.array(a["gruId"][:])])
    t = nc.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)
    get = lambda v: np.ma.filled(d[v][:], 0).reshape(len(t), -1).astype(float)
    e = nc.Dataset(glob.glob(f"runs/lemon_grus/test/{name}/output/*_timestep.nc")[0]); h = np.array([np.datetime64(x, "h") for x in nc.num2date(e["time"][:], e["time"].units, only_use_cftime_datetimes=False)])
    u, i = np.unique((h - np.timedelta64(1, "h")).astype("datetime64[D]"), return_inverse=True); q = np.ma.filled(e["averageRoutedRunoff"][:], 0).reshape(len(h), -1) @ A; avg = np.bincount(i, q) / np.bincount(i)
    ga = get("basin__GlacierArea_mean"); mc = get("basin__GlacierMassChange_mean") if "basin__GlacierMassChange_mean" in d.variables else None
    return dict(t=np.array([np.datetime64(x, "D") for x in t]), q_t=u, avg=avg, glac=get("glacierRoutedRunoff_mean") @ A, ga=ga, mc=mc, A=A, vars=list(d.variables))
R = {n: load(n) for n in ("one", "equal", "length")}
def nse(x, y): return 1 - ((x - y) ** 2).sum() / ((y - y.mean()) ** 2).sum()
def kge(s, o):
    r = np.corrcoef(s, o)[0, 1]; return 1 - np.sqrt((r - 1) ** 2 + (s.std() / o.std() - 1) ** 2 + (s.mean() / o.mean() - 1) ** 2), r, s.mean() / o.mean(), s.std() / o.std()
obs = nc.Dataset(glob.glob("data/domain_LemonCreek/observations/calibration/USGS_15052000_daily_flow.nc")[0]); ov = [v for v in obs.variables if obs[v].ndim >= 1 and v not in ("time", "time_bnds", "gruId", "segId", "reachId")][0]
ot = np.array([(np.datetime64(x, "h") - np.timedelta64(1, "h")).astype("datetime64[D]") for x in nc.num2date(obs["time"][:], obs["time"].units, only_use_cftime_datetimes=False)])
od = dict(zip(ot, np.ma.filled(obs[ov][:].astype(float), np.nan).ravel())); print("obs", ov)
t = R["one"]["q_t"]; o = np.array([od.get(x, np.nan) for x in t]); ok = np.isfinite(o)
for n, r in R.items():
    for lab, q in (("averageRoutedRunoff_mean", r["avg"]),):
        print(n, lab, "KGE r bias var %.3f %.3f %.3f %.3f" % kge(q[ok], o[ok]), end="; ")
    yr = np.array([x.astype("datetime64[Y]").astype(int) + 1970 for x in r["t"]])
    print("area start/end %.2f %.2f" % (r["ga"].sum(1)[30] / 1e6, r["ga"].sum(1)[-30] / 1e6), "per GRU end", (r["ga"][-30] / 1e6).round(2), "glacier runoff mean %.3f" % r["glac"].mean())
for a, b in (("equal", "one"), ("length", "equal"), ("length", "one")):
    x, y = R[a], R[b]; print(f"{a} vs {b}: glacier runoff NSE {nse(x['glac'], y['glac']):.4f}, rms {np.sqrt(((x['glac'] - y['glac']) ** 2).mean()) / y['glac'].mean():.1%}; routed discharge NSE {nse(x['avg'], y['avg']):.4f}, rms {np.sqrt(((x['avg'] - y['avg']) ** 2).mean()) / y['avg'].mean():.1%}")
