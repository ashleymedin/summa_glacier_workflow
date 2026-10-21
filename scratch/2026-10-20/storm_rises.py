"""Wolverine August-September storm rises: each run's rise from the pre-storm low to the peak over the gauge's,
and its pre-storm flow over the gauge's (daily means, 2009-2022).

    storm_rises.py <label> [<label> ...]     labels of calibration_paper1_rerun/sample_469_<label> ('' for sample_469)
"""
import sys, glob
import numpy as np, pandas as pd, netCDF4 as nc

WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
R = f'{WF}/runs/wolverine_corrected/calibration_paper1_rerun'
o = nc.Dataset(f'{WF}/data/domain_Wolverine/observations/calibration/USGS_15236900_daily_flow.nc')
obs = pd.Series(np.asarray(o['q_obs'][:], float),
                index=pd.DatetimeIndex(nc.num2date(o['time'][:], o['time'].units, only_use_cftime_datetimes=False)).normalize())
obs = obs[(obs.index.year >= 2009) & (obs.index.month.isin([8, 9]))].dropna()

events = []
for d in obs.index:
    w = obs[d - pd.Timedelta(days=3): d + pd.Timedelta(days=3)]
    pre = obs[d - pd.Timedelta(days=3): d - pd.Timedelta(days=1)]
    if len(pre) == 3 and obs[d] == w.max() and obs[d] >= 1.4 * pre.min():
        events.append((pre.idxmin(), d))


def simulated(label):
    run = f'{R}/sample_469' + (f'_{label}' if label else '')
    area = float(np.sum(nc.Dataset(run + '_settings/attributes.nc' if label else f'{R}/sample_469_settings/attributes.nc')['HRUarea'][:]))
    d = nc.Dataset(glob.glob(f'{run}/output/*sample*_timestep.nc')[0])
    t = pd.DatetimeIndex(nc.num2date(d['time'][:], d['time'].units, only_use_cftime_datetimes=False))
    q = pd.Series(np.asarray(d['averageRoutedRunoff'][:, 0], float) * area, index=t)
    return q.resample('D').mean()


rows = []
for label in sys.argv[1:] or ['']:
    s = simulated(label)
    for p, d in events:
        if d not in s.index:
            continue
        peak = s[d - pd.Timedelta(days=1): d + pd.Timedelta(days=1)].max()
        rows.append({'run': label or 'base', 'storm': d.date(), 'obs_pre': obs[p], 'obs_rise': obs[d] - obs[p],
                     'pre_ratio': s[p] / obs[p], 'rise_ratio': (peak - s[p]) / (obs[d] - obs[p])})
r = pd.DataFrame(rows)
print(r.pivot(index='storm', columns='run', values='rise_ratio').round(2).to_string())
print(r.groupby('run').agg(storms=('storm', 'size'), pre_ratio=('pre_ratio', 'median'), rise_ratio=('rise_ratio', 'median')).round(2).to_string())
