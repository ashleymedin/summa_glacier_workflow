"""Each upland domain's runoff by path (surface runoff at the top layer's temperature, aquifer baseflow at the soil base's) by month, from soil_water_run.sh."""
import glob, numpy as np, pandas as pd, netCDF4 as nc
out="runs/wolverine_stream_delta/calibration_added_rerun/sample_459_soilwater/output"
d=nc.Dataset(glob.glob(out+"/*sample000001_day.nc")[0])
t=(pd.Timestamp("1990-01-01")+pd.to_timedelta(np.round(np.array(d["time"][:],float)),unit="s")).normalize()
typ=np.asarray(d["domType"][:]); area=np.ma.filled(d["DOMarea_mean"][-1].astype(float),0)
print("domType",typ.tolist()); print("area km2",np.round(area/1e6,3).tolist())
print({k:d[k].dimensions for k in ("mLayerColumnOutflow","mLayerTemp","scalarSurfaceRunoff_mean") if k in d.variables})
print([k for k in d.variables])
print(d["mLayerColumnOutflow"].units, d["scalarSurfaceRunoff_mean"].units, d["scalarSoilDrainage_mean"].units)
sel=(t>=pd.Timestamp("2019-10-01"))
rows=[]
for h in range(3):
    A=area[h,0]
    q=np.ma.filled(d["mLayerColumnOutflow"][:, :, h, 0].astype(float),np.nan)[sel]
    T=np.ma.filled(d["mLayerTemp"][:, :, h, 0].astype(float),np.nan)[sel]
    z=np.ma.filled(d["mLayerDepth"][:, :, h, 0].astype(float),np.nan)[sel]
    nS=np.sum(np.isfinite(q)&(np.abs(q)<1e10),axis=1)
    nL=np.sum(np.isfinite(T)&(T>100),axis=1)
    Tsoil=np.array([T[i,nL[i]-nS[i]:nL[i]] for i in range(len(nS))]); qq=np.where(np.abs(q)<1e10,q,0)[:, :Tsoil.shape[1]]
    qcol=qq.sum(1); Tcol=np.where(qcol>0,(qq*np.maximum(Tsoil,273.15)).sum(1)/np.where(qcol>0,qcol,1),np.nan)-273.15
    sr=np.ma.filled(d["scalarSurfaceRunoff_mean"][:,h,0].astype(float),np.nan)[sel]*A
    dr=np.ma.filled(d["scalarSoilDrainage_mean"][:,h,0].astype(float),np.nan)[sel]*A
    bf=np.ma.filled(d["scalarAquiferBaseflow_mean"][:,h,0].astype(float),np.nan)[sel]*A
    top=np.maximum(T[:,0],273.15)-273.15
    df=pd.DataFrame({"sr":sr,"Ttop":top,"col":qcol,"Tcol":Tcol,"drain":dr,"bf":bf,"T1":Tsoil[:,0]-273.15,"Tbot":Tsoil[:,-1]-273.15},index=t[sel])
    m=df.groupby(df.index.month).mean()
    print(f"\nupland HRU{h} {A/1e6:.2f} km2, nSoil {nS.max()}"); print(m.loc[[4,5,6,9,10,11]].round(3).to_string())
