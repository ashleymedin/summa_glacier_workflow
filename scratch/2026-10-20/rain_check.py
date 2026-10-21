"""Aug-Sep rain storms at Wolverine: gauge vs trial 469 discharge, 990 m gauge precip vs forcing precip."""
import sys, glob
import numpy as np, pandas as pd, xarray as xr
W = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow"
sys.path.insert(0, W)
from correct_forcing_to_station import read_station, EPOCH

run = sys.argv[1] if len(sys.argv) > 1 else f"{W}/runs/wolverine_corrected/calibration_paper1_rerun/sample_469"
forc = sys.argv[2] if len(sys.argv) > 2 else f"{W}/data/domain_Wolverine/forcing/SUMMA_input/station_corrected"

att = xr.open_dataset(f"{run}_settings/attributes.nc")
area = float(att.HRUarea.sum())
sim = xr.open_dataset(glob.glob(f"{run}/output/*sample000001_timestep.nc")[0])
qs = pd.Series(sim.averageRoutedRunoff.isel(gru=0).values * area, index=pd.to_datetime(sim.time.values).round("h"))
ob = pd.read_csv(f"{W}/data/domain_Wolverine/observations/streamflow/preprocessed/Wolverine_streamflow_processed.csv",
                 index_col=0, parse_dates=True).discharge_cms

st = read_station(f"{W}/data/domain_Wolverine/USGSweatherData/990")["PR"]
ps = pd.Series(st.values(), index=pd.to_datetime([EPOCH + pd.Timedelta(hours=h) for h in st]).tz_localize(None)).sort_index()

w = att.HRUarea.values / area
def basin_ppt(folder):
    fs = []
    for f in sorted(glob.glob(f"{folder}/*.nc")):
        d = xr.open_dataset(f)
        if pd.Timestamp(d.time.values[-1]).year < 2009:
            continue
        fs.append(pd.Series((d.pptrate.values * w).sum(1) * 3600, index=pd.to_datetime(d.time.values).round("h")))
    p = pd.concat(fs).sort_index()
    return p[~p.index.duplicated()]
pf = basin_ppt(forc)
pr = basin_ppt(f"{W}/data/domain_Wolverine/forcing/SUMMA_input")

dd = xr.open_dataset(glob.glob(f"{run}/output/*sample000001_day.nc")[0])
a = dd.DOMarea_mean.fillna(0)
rf = pd.Series(((dd.scalarRainfall_mean.fillna(0) * a).sum(["hru", "dom"]) / a.sum(["hru", "dom"])).values * 86400,
               index=pd.to_datetime(dd.time.values).normalize() - pd.Timedelta(days=1))
sf = pd.Series(((dd.scalarSnowfall_mean.fillna(0) * a).sum(["hru", "dom"]) / a.sum(["hru", "dom"])).values * 86400,
               index=rf.index)

df = pd.DataFrame({"qo": ob, "qs": qs, "ps": ps, "pf": pf, "pr": pr}).loc["2009":"2022"]
day = df.resample("D").agg({"qo": "mean", "qs": "mean", "ps": lambda x: x.sum(min_count=20), "pf": "sum", "pr": "sum"})
day["rain"], day["snow"] = rf[~rf.index.duplicated(keep="last")], sf[~sf.index.duplicated(keep="last")]
day = day[day.index.month.isin([8, 9])]
print(f"Aug-Sep days with all data: {day.dropna().shape[0]}")
print("Aug-Sep means  obs Q %.2f  sim Q %.2f m3/s" % (day.qo.mean(), day.qs.mean()))
print("Aug-Sep totals all days: corrected %.0f raw %.0f mm" % (day.pf.sum(), day.pr.sum()))
print("Aug-Sep totals where station has data: station %.0f mm, forcing basin %.0f mm" %
      (day.dropna().ps.sum(), day.dropna().pf.sum()))

# storms: 3-day station precip >= 40 mm; peak in the 5 days after its first day vs the day before
rain3 = day.ps.rolling("3D").sum()
ev, last = [], None
for t, r in rain3.items():
    if r >= 40 and (last is None or (t - last).days > 6):
        t0 = t - pd.Timedelta(days=2)
        h = df.loc[t0 - pd.Timedelta(days=1): t0 + pd.Timedelta(days=5)]
        base = df.loc[t0 - pd.Timedelta(days=1): t0, ["qo", "qs"]].min()
        pk = h[["qo", "qs"]].max()
        ev.append(dict(start=t0.date(), st_mm=day.ps.loc[t0:t].sum(), fo_mm=day.pf.loc[t0:t].sum(), raw_mm=day.pr.loc[t0:t].sum(),
                       snow_pct=100 * day.snow.loc[t0:t].sum() / (day.snow.loc[t0:t].sum() + day.rain.loc[t0:t].sum()),
                       qo_base=base.qo, qo_pk=pk.qo, qs_base=base.qs, qs_pk=pk.qs,
                       rise_ratio=(pk.qs - base.qs) / (pk.qo - base.qo)))
        last = t
e = pd.DataFrame(ev)
pd.set_option("display.width", 200)
print(e.round(2).to_string(index=False))
print("median rise ratio sim/obs %.2f, peak ratio %.2f, forcing/station precip %.2f" %
      (e.rise_ratio.median(), (e.qs_pk / e.qo_pk).median(), e.fo_mm.sum() / e.st_mm.sum()))
