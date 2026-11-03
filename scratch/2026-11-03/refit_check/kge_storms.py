"""Daily discharge KGE and Aug-Sep storm rise ratio of trials 384/469 reruns; usage: kge_storms.py <label> [<label> ...]"""
import sys
import warnings; warnings.filterwarnings('ignore')
import netCDF4 as nc, numpy as np, pandas as pd, xarray as xr
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
CASES = {'Gulkana': ('gulkana_corrected', 384, 'Gulkana', 'USGS_15478040_daily_flow.nc'), 'Wolverine': ('wolverine_corrected', 469, 'Wolverine', 'USGS_15236900_daily_flow.nc')}
def kge(s, o):
    r = np.corrcoef(s, o)[0, 1]; return 1 - np.sqrt((r - 1) ** 2 + (s.std() / o.std() - 1) ** 2 + (s.mean() / o.mean() - 1) ** 2)
for lab in sys.argv[1:]:
    for name, (case, tr, dom, f) in CASES.items():
        d = nc.Dataset(f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{tr}_{lab}/output/{case}_rank0001_sample000001_timestep.nc')
        t = pd.DatetimeIndex(nc.num2date(d['time'][:], d['time'].units, only_use_cftime_datetimes=False)).normalize()
        area = float(xr.open_dataset(f'{WF}/runs/{case.split("_")[0]}_added/summa_inputs/attributes.nc').HRUarea.sum()); q = area * pd.Series(np.ma.filled(d['averageRoutedRunoff'][:], np.nan).reshape(len(t), -1)[:, 0], t).resample('D', offset='9h').mean()
        o = xr.open_dataset(f'{WF}/data/domain_{dom}/observations/calibration/{f}'); ov = o['q_obs']
        obs = pd.Series(np.asarray(ov.values).ravel(), pd.DatetimeIndex(o.time.values))
        j = pd.concat([q, obs], axis=1, keys=['m', 'o']).dropna(); j.index = j.index.normalize()
        out = [f'{name} {lab}']
        for a, b in (('2009', '2015'), ('2016', '2022')):
            x = j[a:b]; out.append(f'{a}-{b[2:]} KGE {kge(x.m.values, x.o.values):.3f} n={len(x)}')
        # storms: Aug15-Sep30, obs rise >=40% in 3 days; rise ratio model/obs above pre-storm flow
        rr = []
        for dt in j.index:
            if dt.month not in (8, 9) or (dt.month == 8 and dt.day < 15): continue
            p = dt - pd.Timedelta(days=3)
            if p in j.index and j.o[dt] >= 1.4 * j.o[p] and j.o[dt] > j.o[p]:
                rr.append((j.m[dt] - j.m[p]) / (j.o[dt] - j.o[p]))
        out.append(f'storms {len(rr)} median rise ratio {np.median(rr):.2f}' if rr else 'no storms')
        print('  '.join(out))
