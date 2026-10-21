"""Late-September Wolverine storms: forcing temperature and phase on the upper glacier against the stations."""
import sys, glob, os
import numpy as np, pandas as pd, netCDF4 as nc
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
sys.path.insert(0, WF)
from correct_forcing_to_station import read_station, wet_bulb, specific_humidity, EPOCH

D = f'{WF}/data/domain_Wolverine'
st = {z: read_station(f'{D}/USGSweatherData/{z}') for z in (990, 1420)}
LAPSE_SEP = -7.51e-3
TRED, TCRIT, TRANGE, SUMMA_LAPSE = 1.0302, 273.1688, 0.6113, 0.006871   # trial 469


def summa_frac_snow(tw):
    lo, hi = tw - TRANGE / 2, tw + TRANGE / 2
    return np.clip((TCRIT - lo) / (hi - lo), 0, 1)


def forcing(month, sub):
    f = glob.glob(f'{D}/forcing/SUMMA_input/{sub}*{month}.nc')[0]
    d = nc.Dataset(f)
    out = {v: np.array(d[v][:], float) for v in ('airtemp', 'spechum', 'airpres', 'pptrate')}
    out['hour'] = np.array(d['time'][:]).astype(int)
    return out


rain_dom = {}
for start in ('2014-09-16', '2020-09-23', '2022-09-28'):
    t0 = pd.Timestamp(start, tz='UTC'); t1 = t0 + pd.Timedelta(days=3)
    m = t0.strftime('%Y%m')
    fc = forcing(m, 'station_corrected/Wolverine_ERA5_remapped_domain_Wolverine_ERA5_merged_')
    hrs = fc['hour']
    times = pd.to_datetime([EPOCH + pd.Timedelta(hours=int(h)) for h in hrs])
    sel = (times > t0) & (times <= t1)
    h = hrs[sel]
    pr990 = np.array([st[990]['PR'].get(x, np.nan) for x in h])
    t990 = np.array([st[990]['T'].get(x, np.nan) for x in h])
    t1420 = np.array([st[1420].get('T', {}).get(x, np.nan) for x in h])
    rh990 = np.array([st[990].get('RH', {}).get(x, np.nan) for x in h])
    T3 = fc['airtemp'][sel, 2] - 273.15  # HRU 3, 1410 m
    T2 = fc['airtemp'][sel, 1] - 273.15
    P3 = fc['pptrate'][sel, 2] * 3600; P2 = fc['pptrate'][sel, 1] * 3600; P1 = fc['pptrate'][sel, 0] * 3600
    # station 990 lapsed to 1369 m (upper clean-ice domain) and 1410 m
    t990_1410 = t990 + LAPSE_SEP * (1410 - 990)
    # model temperature on the upper glacier domain (1369 m)
    Tdom = T3 + 273.15 - (1369 - 1410) * SUMMA_LAPSE
    Tdom = np.where(Tdom > 273.15, Tdom - TRED, Tdom)
    q3 = fc['spechum'][sel, 2]; p3 = fc['airpres'][sel, 2]
    fs_model = summa_frac_snow(wet_bulb(Tdom, q3, p3))
    # wet bulb from the station: 990 RH (if any) carried at constant q is not available; use the forcing q
    fs_station = summa_frac_snow(wet_bulb(t990_1410 + 273.15 + 41 * SUMMA_LAPSE, q3, p3))
    wet = P3 > 0.1
    print(f'\n{start} +3 d: precipitation HRU1/2/3 {P1.sum():.0f}/{P2.sum():.0f}/{P3.sum():.0f} mm, 990 gauge {np.nansum(pr990):.0f} mm '
          f'({np.isfinite(pr990).sum()} h)')
    print(f'  wet hours, mean T (degC): forcing HRU3 1410 m {T3[wet].mean():+.2f}, 990 station lapsed to 1410 {np.nanmean(t990_1410[wet]):+.2f}, '
          f'1420 station {np.nanmean(t1420[wet]) if np.isfinite(t1420[wet]).any() else float("nan"):+.2f}, 990 station {np.nanmean(t990[wet]):+.2f}')
    print(f'  model upper ice domain (1369 m) T on wet hours {np.mean(Tdom[wet]) - 273.15:+.2f} (after -{TRED} K above 0)')
    print(f'  snow share of HRU3 precipitation: model {np.sum(fs_model * P3) / P3.sum():.2f}, with 990 station lapsed {np.nansum(fs_station * P3) / P3.sum():.2f}')
    # by hour table, 6-hourly
    df = pd.DataFrame({'P3': P3, 'g990': pr990, 'T3': T3, 'T990@1410': t990_1410, 'T1420': t1420, 'Tdom': Tdom - 273.15, 'fsnow': fs_model},
                      index=times[sel]).resample('6h').agg({'P3': 'sum', 'g990': 'sum', 'T3': 'mean', 'T990@1410': 'mean', 'T1420': 'mean', 'Tdom': 'mean', 'fsnow': 'mean'})
    print(df.round(1).to_string())
