"""Trial 469's runoff parts at the Aug-Sep storms: pre-storm level and rise of each, in m3/s."""
import numpy as np, pandas as pd, netCDF4 as nc, glob
exec(open('storm_rises.py').read().split('def simulated')[0].split('"""',2)[2])
run = f'{R}/sample_469_' + __import__('os').environ.get('LAB','flow_A1')
area = float(np.sum(nc.Dataset(run + '_settings/attributes.nc')['HRUarea'][:]))
d = nc.Dataset(glob.glob(f'{run}/output/*sample*_day.nc')[0])
t = pd.DatetimeIndex(nc.num2date(d['time'][:], d['time'].units, only_use_cftime_datetimes=False)).normalize()
parts = {v: pd.Series(np.asarray(d[v + '_mean'][:, 0], float) * area, index=t)
         for v in ('basin__SurfaceRunoff', 'basin__AquiferBaseflow', 'glacierRoutedRunoff')}
dt = nc.Dataset(glob.glob(f'{run}/output/*sample*_timestep.nc')[0])
tt = pd.DatetimeIndex(nc.num2date(dt['time'][:], dt['time'].units, only_use_cftime_datetimes=False))
parts['total'] = pd.Series(np.asarray(dt['averageRoutedRunoff'][:, 0], float) * area, index=tt).resample('D').mean()
rows = []
for p, e in events:
    if e not in parts['total'].index: continue
    r = {'obs_pre': obs[p], 'obs_rise': obs[e] - obs[p]}
    for k, s in parts.items():
        r[k + '_pre'] = s[p]; r[k + '_rise'] = s[e - pd.Timedelta(days=1): e + pd.Timedelta(days=1)].max() - s[p]
    rows.append(r)
print(pd.DataFrame(rows).median().round(2).to_string())
