import sys, netCDF4 as nc, numpy as np, pandas as pd
WF='/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs/wolverine_corrected/calibration_paper1_rerun'
for lab in sys.argv[1:]:
    d=nc.Dataset(f'{WF}/sample_469_{lab}/output/wolverine_corrected_rank0001_sample000001_day.nc')
    t=pd.DatetimeIndex(nc.num2date(d['time'][:],d['time'].units,only_use_cftime_datetimes=False)).normalize()
    r=np.ma.filled(d['scalarRainfall_mean'][:],0); s=np.ma.filled(d['scalarSnowfall_mean'][:],0); typ=np.ma.filled(d['domType'][:],-1); a=np.ma.filled(d['DOMarea_mean'][:],0)
    out=[]
    for st in ('2014-09-16','2020-09-23','2022-09-28'):
        sel=(t>=pd.Timestamp(st))&(t<pd.Timestamp(st)+pd.Timedelta(days=3))
        R=(r[sel]*a[sel]).sum(); S=(s[sel]*a[sel]).sum()
        up=(typ==2); up[:2]=False  # HRU3 clean ice
        Ru=r[sel][:,up].sum(); Su=s[sel][:,up].sum()
        out.append(f'{st}: basin snow {S/(R+S):.2f}, upper ice {Su/(Ru+Su):.2f}')
    print(lab,' | '.join(out))
