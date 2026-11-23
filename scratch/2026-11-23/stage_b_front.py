"""Stage B (stream_b) Pareto front on wolverine_stream_delta: scores and the stream/lake parameters each trial chose."""
import glob, re
import numpy as np, pandas as pd, xarray as xr

RUN = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs/wolverine_stream_delta/stream_b"
ev = pd.read_csv(RUN + "_evaluation/evaluation.csv").set_index("sample")
rows = []
for f in glob.glob(RUN + "/output/*_sample*_trialParams.nc"):
    s = int(re.search(r"sample(\d+)_", f).group(1))
    if s not in ev.index:
        continue
    d = xr.open_dataset(f)
    rows.append(dict(sample=s,
                     snow_up=float(d.frozenPrecipMultip[0, 0]), snow_wet=float(d.frozenPrecipMultip[3, 0]),
                     lapse_wet=float(d.tempLapseRate[3, 0]), cool=float(d.wetlandAirCooling[0, 0]),
                     wind=float(d.wetlandWindFactor[0, 0]), K_h=float(d.wetlandStorageK[0, 0]) / 3600,
                     minD=float(d.wetlandMinDepth[3, 0]) if "dom" in d.wetlandMinDepth.dims else float(d.wetlandMinDepth[0]),
                     width=float(d.streamWidthMultip[0])))
p = pd.DataFrame(rows).set_index("sample")
t = ev.join(p).sort_values("cal_stream_temperature")
pd.set_option("display.width", 250)
print(t.round(3).to_string())
print("\nmedian\n", t.median().round(3).to_string())
