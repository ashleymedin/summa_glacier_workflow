import sys, glob, numpy as np
sys.path.insert(0, ".")
from correct_forcing_to_station import read_station, catch_efficiency, along_elevation, EPOCH, snow_fraction
from datetime import timedelta
from netCDF4 import Dataset
d = sys.argv[1]; P = f"data/domain_{d}"
with Dataset(f"{P}/settings/SUMMA/attributes.nc") as a:
    elev = dict(zip(a["hruId"][:].astype(int), a["elevation"][:]))
files = sorted(glob.glob(f"{P}/forcing/SUMMA_input/*.nc"))
H, PR, T = [], [], []
for f in files:
    with Dataset(f) as s:
        H.append(s["time"][:].astype(int)); PR.append(np.array(s["pptrate"][:])*3600); T.append(np.array(s["airtemp"][:]))
        ids = s["hruId"][:].astype(int)
H = np.concatenate(H); PR = np.maximum(np.concatenate(PR), 0); T = np.concatenate(T)
z = np.array([elev[i] for i in ids])
dt = [EPOCH + timedelta(hours=int(h)) for h in H]
mon = np.array([x.month for x in dt]); yr = np.array([x.year for x in dt])
for g in sorted(int(x.split("/")[-1]) for x in glob.glob(f"{P}/USGSweatherData/*") if x.split("/")[-1].isdigit()):
    st = read_station(f"{P}/USGSweatherData/{g}")
    pr = np.array([st.get("PR", {}).get(h, np.nan) for h in H]); u = np.array([st.get("U", {}).get(h, np.nan) for h in H]); t = np.array([st.get("T", {}).get(h, np.nan) for h in H])
    ok = np.isfinite(pr) & np.isfinite(u) & np.isfinite(t)
    ce = np.where(ok, catch_efficiency(np.nan_to_num(u), np.nan_to_num(t), "SA"), np.nan)
    f = along_elevation(z, PR, g)
    print(f"gauge {g} m: valid hours {ok.sum()}")
    for y in range(2008, 2023):
        s = ok & (yr == y) & (mon >= 6) & (mon <= 9)
        if s.sum() < 24*60: continue
        print(f"  {y} JJAS {s.sum()/24:5.0f} d: gauge {pr[s].sum():6.0f} corr {np.sum(pr[s]/ce[s]):6.0f} forcing {f[s].sum():5.0f} ratio {np.sum(pr[s]/ce[s])/f[s].sum():.2f}")
    for m in range(1, 13):
        s = ok & (mon == m)
        if s.sum() < 24*30: continue
        print(f"  month {m:2d}: {s.sum()/24:5.0f} d ratio {np.sum(pr[s]/ce[s])/max(f[s].sum(),1e-9):.2f}  catch {pr[s].sum()/np.sum(pr[s]/ce[s]):.2f}")
