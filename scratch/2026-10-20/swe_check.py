import sys, netCDF4 as nc, numpy as np, pandas as pd
WF='/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs'
lab=sys.argv[1]
for case,tr in (('gulkana_corrected',384),('wolverine_corrected',469)):
    d=nc.Dataset(f'{WF}/{case}/calibration_paper1_rerun/sample_{tr}_{lab}/output/{case}_rank0001_sample000001_day.nc')
    t=pd.DatetimeIndex(nc.num2date(d['time'][:],d['time'].units,only_use_cftime_datetimes=False))
    swe=d['scalarSWE_mean'][:]; m=d['glacMass4AreaChange_mean'][:]; typ=d['domType'][:]; z=d['DOMelev_mean'][:]
    print(case)
    for h in range(typ.shape[0]):
        for k in range(typ.shape[1]):
            if typ[h,k]<2: continue
            i=[j for j in range(len(t)) if t[j].month==9 and t[j].day==30]
            print(f' hru{h+1} type{typ[h,k]} z{z[0,h,k]:.0f}  SWE 30Sep:', ' '.join(f'{swe[j,h,k]:.0f}' for j in i), '| mass:', ' '.join(f'{m[j,h,k]:.0f}' for j in i))
