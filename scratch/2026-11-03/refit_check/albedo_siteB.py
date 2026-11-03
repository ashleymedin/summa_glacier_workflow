"""Modelled daily albedo of Gulkana's HRU 2 domains vs Wilson Site B (1682 m), Apr-Aug 2024; usage: albedo_siteB.py <label>"""
import sys, warnings; warnings.filterwarnings('ignore')
import netCDF4 as nc, numpy as np, pandas as pd
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
d = nc.Dataset(f'{WF}/runs/gulkana_corrected/calibration_paper1_rerun/sample_384_{sys.argv[1]}/output/gulkana_corrected_rank0001_sample000001_day.nc')
t = pd.DatetimeIndex(nc.num2date(d['time'][:], d['time'].units, only_use_cftime_datetimes=False)).normalize()
obs = pd.read_csv(f'{WF}/data/domain_Gulkana/observations/campaigns/wilson_2024/5_albedo/gulkanaB_daily_albedo_2024.csv', index_col=0, parse_dates=True).albedo
print('vars', [v for v in d.variables if 'lbedo' in v])
for v in ('scalarGroundAlbedo_mean', 'scalarSnowAlbedo_mean'):
    if v not in d.variables: continue
    a = np.ma.filled(d[v][:], np.nan); a[a < -1] = np.nan; print(v, a.shape)
    for h in range(a.shape[1]):
        for j in range(a.shape[2]):
            s = pd.Series(a[:, h, j], t)
            if np.isnan(s).all(): continue
            m = pd.concat([s, obs], axis=1, keys=['m', 'o']).dropna()
            if len(m) < 20: continue
            mo = m.groupby(m.index.month).mean().round(2)
            print(f' hru{h+1} dom{j+1}: n={len(m)} bias {np.mean(m.m-m.o):+.3f} rmse {np.sqrt(np.mean((m.m-m.o)**2)):.3f} r {m.m.corr(m.o):.2f} | monthly mod/obs', ' '.join(f'{k}:{r.m}/{r.o}' for k, r in mo.iterrows()))
