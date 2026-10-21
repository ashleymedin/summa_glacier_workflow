import sys, netCDF4 as nc, numpy as np, pandas as pd
WF='/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs'
lab=sys.argv[1]
V=['airtemp','windspd','scalarSnowAlbedo','scalarGroundAbsorbedSolar','scalarLWNetGround','scalarSenHeatGround','scalarLatHeatGround','scalarSurfaceTemp','scalarSWE','scalarSnowfall_mean','scalarRainfall_mean']
for case,tr in (('gulkana_corrected',384),('wolverine_corrected',469)):
    d=nc.Dataset(f'{WF}/{case}/calibration_paper1_rerun/sample_{tr}_{lab}/output/{case}_rank0001_sample000001_day.nc')
    t=pd.DatetimeIndex(nc.num2date(d['time'][:],d['time'].units,only_use_cftime_datetimes=False))
    typ=np.ma.filled(d['domType'][:],-1); z=np.ma.filled(d['DOMelev_mean'][:],np.nan)
    jja=(t.month>=6)&(t.month<=8)
    print(case, lab, 'JJA means 2009-2022')
    rows=[]
    for h in range(typ.shape[0]):
        for k in range(typ.shape[1]):
            if typ[h,k]<1 or typ[h,k]>4: continue
            r={'hru':h+1,'type':int(typ[h,k]),'z':np.nanmean(z[jja,h,k])}
            for v in V:
                name=v if v.endswith('_mean') else v+'_mean'
                x=np.ma.filled(d[name][:],np.nan)
                x=x[:,h,k] if x.ndim==3 else x[:,h]
                val=np.nanmean(x[jja])
                if v=='airtemp' or v=='scalarSurfaceTemp': val-=273.15
                if v.endswith('fall_mean'): val*=86400*92
                r[v.replace('scalar','').replace('_mean','').replace('Ground','')]=val
            r['snowfree']=np.mean(np.ma.filled(d['scalarSWE_mean'][:],np.nan)[jja,h,k]<1)
            rows.append(r)
    print(pd.DataFrame(rows).round(2).to_string())
