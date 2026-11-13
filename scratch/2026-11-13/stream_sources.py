"""Monthly stream, lateral inflow, lake and delta temperatures and flows of a wolverine_stream_delta rerun (held-out years)."""
import sys, os, glob; sys.path.insert(0,'.')
import plot_setup_runs as p, numpy as np, pandas as pd, netCDF4 as nc
out="runs/wolverine_stream_delta/calibration_added_rerun/sample_459_aqT/output"
with nc.Dataset(glob.glob(out+"/*sample000001_day.nc")[0]) as d:
    t=(pd.Timestamp("1990-01-01")+pd.to_timedelta(np.round(np.array(d["time"][:],float)),unit="s")).normalize()
    g=lambda v,h,k: pd.Series(np.ma.filled(d[v][:,h,k].astype(float),np.nan),index=t)
    x=pd.DataFrame({"Tstream":g("scalarStreamTemp_mean",3,1)-273.15,"Qout":g("scalarStreamOutflow_mean",3,1),
       "latQ":g("scalarStreamLatInflow_mean",3,1),"latT":g("scalarStreamLatInflowTemp_mean",3,1)-273.15,
       "lakeT":g("scalarStreamTemp_mean",0,3)-273.15,"lakeQ":g("scalarStreamOutflow_mean",0,3),
       "deltaT":g("scalarStreamTemp_mean",0,4)-273.15,"airT":np.nan})
    print({k:d[k].units if hasattr(d[k],'units') else '' for k in ["scalarStreamOutflow_mean","scalarStreamLatInflow_mean"]})
x=x[x.index>="2019-10-01"]
print(x.groupby(x.index.month).mean().round(3).to_string())
