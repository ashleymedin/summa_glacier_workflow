"""The lake snow and surface energy budget each day of lake_snow_run.sh, and its November-March means."""
import glob, numpy as np, pandas as pd, netCDF4 as nc
out="runs/wolverine_stream_delta/calibration_added_rerun/sample_459_lakesnow/output"
with nc.Dataset(glob.glob(out+"/*sample000001_day.nc")[0]) as d:
    t=(pd.Timestamp("1990-01-01")+pd.to_timedelta(np.round(np.array(d["time"][:],float)),unit="s")).normalize()
    def g(v,k=3,s=1.0):
        return np.ma.filled(d[v+"_mean"][:,0,k].astype(float),np.nan)*s
    x=pd.DataFrame({"swe":g("scalarSWE"),"sweUp":g("scalarSWE",0),"ice":g("scalarLakeIceThick"),
      "subl":g("scalarGroundSublimation",3,86400),"sublUp":g("scalarGroundSublimation",0,86400),
      "drain":g("scalarSnowDrainage",3,86400*1000),"pond":g("scalarSfcMeltPond"),"snowf":g("scalarSnowfall",3,86400),
      "rain":g("scalarRainfall",3,86400),"Ts":g("scalarSurfaceTemp")-273.15,"Ta":np.ma.filled(d["airtemp_mean"][:,0].astype(float),np.nan)-273.15,"u":np.ma.filled(d["windspd_mean"][:,0].astype(float),np.nan),
      "H":g("scalarSenHeatTotal"),"LE":g("scalarLatHeatTotal"),"G":g("scalarGroundNetNrgFlux"),"SW":g("scalarGroundAbsorbedSolar"),"LW":g("scalarLWNetGround")},index=t)
pd.set_option("display.width",250)
print(x["2021-12-18":"2022-01-02"].round(2).to_string())
w=x[(x.index>="2019-10-01")&x.index.month.isin([11,12,1,2,3])]
print(w[["subl","sublUp","drain","snowf","rain","H","LE","G"]].mean().round(3))
