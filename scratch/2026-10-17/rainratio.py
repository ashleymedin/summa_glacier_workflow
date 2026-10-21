"""Monthly 990 m gauge catch (raw and SA undercatch-corrected) against raw ERA5 precipitation at 990 m."""
import sys, glob, os
sys.path.insert(0, '/Users/amedin/Research/SummaSundials/summa_glacier_workflow')
import numpy as np
from netCDF4 import Dataset
from datetime import timedelta
from correct_forcing_to_station import read_station, catch_efficiency, along_elevation, EPOCH
D = '/Users/amedin/Research/Symfluence/SYMFLUENCE_data/domain_Wolverine'
st = read_station(f'{D}/USGSweatherData/990')
with Dataset(f'{D}/settings/SUMMA/attributes.nc') as d:
    elev = dict(zip(np.array(d['hruId'][:]).astype(int), np.array(d['elevation'][:], float)))
hours, pp, ids = [], [], None
for f in sorted(glob.glob(f'{D}/forcing/SUMMA_input/*.nc')):
    with Dataset(f) as d:
        hours.append(np.array(d['time'][:]).astype(int)); pp.append(np.array(d['pptrate'][:], float)); ids = np.array(d['hruId'][:]).astype(int)
hours = np.concatenate(hours); pp = np.concatenate(pp)
z = np.array([elev[h] for h in ids])
on = lambda s: np.array([s.get(h, np.nan) for h in hours])
pr, u, t = on(st['PR']), on(st['U']), on(st['T'])
ok = np.isfinite(pr) & np.isfinite(u) & np.isfinite(t)
era = along_elevation(z, np.maximum(pp, 0) * 3600, 990)
cor = np.where(ok, pr / np.where(ok, catch_efficiency(np.where(ok, u, 0), np.where(ok, t, 0), 'SA'), 1), np.nan)
mon = np.array([(EPOCH + timedelta(hours=int(h))).month for h in hours])
yrs = len(set((EPOCH + timedelta(hours=int(h))).year for h in hours[ok]))
print(f'990 m gauge, {ok.sum()} h with gauge, wind and T')
print('mon  gauge  gauge_SA   ERA5   ratio_raw ratio_SA  wind  T>2C share  catch')
for m in list(range(1, 13)) + [0]:
    s = ok & ((mon == m) if m else True)
    sel = s
    g, c, e = pr[sel].sum(), cor[sel].sum(), era[sel].sum()
    w = (u[sel] * pr[sel]).sum() / max(pr[sel].sum(), 1e-9)
    warm = pr[sel & (t > 2)].sum() / max(g, 1e-9)
    print(f'{m if m else "all":>3} {g:7.0f} {c:8.0f} {e:7.0f}   {g/e:6.2f}   {c/e:6.2f}  {w:5.1f}  {warm:6.2f}  {g/c:5.2f}')
