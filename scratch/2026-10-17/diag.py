"""Monthly water-temperature bias (sim - obs, degC) and scores of each rerun, 2017-2019."""
import sys, os
sys.path.insert(0, '/Users/amedin/Research/USask/Writeups/summa_sundials_svn/streamtemp/figs')
from plotlib import *

t = obs('USGS_15236900_daily_temperature.nc', 't_obs'); q = obs('USGS_15236900_daily_flow.nc', 'q_obs')
runs = sorted(r for r in os.listdir(f'{S}/runs') if os.path.exists(f'{S}/runs/{r}/output/wolverine_timestep.nc'))
print(f'{"run":16s} {"KGE":>6s} {"Trmse":>6s} ' + ' '.join(f'{m:>6s}' for m in ('May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'JJAS')))
for r in sys.argv[1:] or runs:
    try:
        dd = daily(sim(r))
    except Exception as e:
        print(r, 'unreadable', e); continue
    dd = dd[(dd.index >= '2017-01-01') & (dd.index < '2020-01-01')]
    T = dd['T'] - 273.15 if dd['T'].mean() > 100 else dd['T']
    j = pd.concat([T.rename('s'), t.rename('o')], axis=1, sort=True).dropna()
    b = (j.s - j.o).groupby(j.index.month).mean()
    jj = j[j.index.month.isin([6, 7, 8, 9])]
    k = pd.concat([dd['Q'].rename('s'), q.rename('o')], axis=1, sort=True).dropna()
    r_ = k.s.corr(k.o); a = k.s.std() / k.o.std(); be = k.s.mean() / k.o.mean()
    kge = 1 - np.sqrt((r_ - 1) ** 2 + (a - 1) ** 2 + (be - 1) ** 2)
    rm = np.sqrt(((j.s - j.o) ** 2).mean())
    print(f'{r:16s} {kge:6.3f} {rm:6.3f} ' + ' '.join(f'{b.get(m, np.nan):+6.2f}' for m in (5, 6, 7, 8, 9, 10)) + f' {(jj.s - jj.o).mean():+6.2f}')
    d = nc.Dataset(f'{S}/runs/{r}/output/wolverine_timestep.nc')
    if 'glacierRoutedRunoff' not in d.variables: continue
    # glacier GRU 1 runoff: total, glacier part, aquifer part; non-glacier water temperature with the glacier part at 0 degC
    idx = pd.Timestamp('1990-01-01') + pd.to_timedelta(np.round(np.array(d['time'][:])), unit='s')
    g = int(np.where(np.array(d['gruId'][:]) == 1)[0][0])
    x = pd.DataFrame({k: np.array(d[v][:, g]) for k, v in (('tot', 'averageRoutedRunoff'), ('gl', 'glacierRoutedRunoff'), ('T', 'averageRoutedRunoffTemp'))}, index=idx)
    x = x[(x.index >= '2017-01-01') & (x.index < '2020-01-01')]
    x['Th'] = (x['T'] - 273.15) * x['tot']
    m = x.groupby(x.index.month).sum()
    print(f'{"":16s} glacier share  ' + ' '.join(f'{100 * m.gl[k] / m.tot[k]:5.0f}%' for k in (5, 6, 7, 8, 9, 10)))
    print(f'{"":16s} non-glacier T  ' + ' '.join(f'{m.Th[k] / (m.tot[k] - m.gl[k]):6.2f}' for k in (5, 6, 7, 8, 9, 10)))
