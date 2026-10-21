import netCDF4 as nc, glob, numpy as np, pandas as pd, sys
runs="/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs/"
for p in sys.argv[1:]:
    f=glob.glob(runs+p+"/output/*sample*_day.nc")[0]
    d=nc.Dataset(f); t=pd.DatetimeIndex(nc.num2date(d["time"][:],d["time"].units,only_use_cftime_datetimes=False))
    a=np.array(d["DOMarea_mean"][:]); a[a<-9000]=np.nan
    ty=np.array(d["domType"][:])
    # a dims time, dom, hru?
    print(p, a.shape, ty.shape)
    ar=a if a.shape[1]==ty.shape[0] else np.moveaxis(a,1,2)
    df={}
    for k,lab in [(4,'dbr'),(2,'cl2'),(3,'cl3')]:
        m=(ty==k)
        df[lab]=np.nansum(np.where(m[None], ar,0),axis=(1,2))/1e6
    # per hru debris
    for h in range(ty.shape[0]):
        df[f'dbr_h{h+1}']=np.nansum(np.where((ty[h]==4)[None],ar[:,h,:],0),axis=1)/1e6
    df=pd.DataFrame(df,index=t)
    df['glac']=df.dbr+df.cl2+df.cl3
    df['frac']=df.dbr/df.glac
    print(df.groupby(df.index.year).nth(10).round(2).to_string())
    print(df.iloc[-1:].round(2).to_string())
