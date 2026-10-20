#!/usr/bin/env python3
"""Winter, summer and annual balance of each glacier domain against the stakes at its elevation: mass_balance_seasons.py [label]

From glacMass4AreaChange made continuous across its yearly resets, over each year's median stake dates (previous fall,
spring, fall); the stakes' bw and ba interpolated to the domain elevation (linear fit within 100 m beyond the stakes).
Stake bw excludes winter ablation, which the model's winter window holds.
"""
import sys
import netCDF4 as nc, numpy as np, pandas as pd

WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
LABEL = sys.argv[1] if len(sys.argv) > 1 else 'base'
CASES = {'Gulkana': ('gulkana_corrected', 384), 'Wolverine': ('wolverine_corrected', 469)}
pd.set_option('display.width', 200)


def load(name, label=LABEL):
    case, trial = CASES[name]
    d = nc.Dataset(f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_{label}/output/{case}_rank0001_sample000001_day.nc')
    t = pd.DatetimeIndex(nc.num2date(d['time'][:], d['time'].units, only_use_cftime_datetimes=False)).normalize()
    m = np.ma.filled(d['glacMass4AreaChange_mean'][:], np.nan)
    z = np.ma.filled(d['DOMelev_mean'][:], np.nan); a = np.ma.filled(d['DOMarea_mean'][:], np.nan)
    typ = np.asarray(d['domType'][:])
    # continuous cumulative mass: add back each reset
    dm = np.diff(m, axis=0, prepend=0 * m[:1])
    reset = (t.month == 10) & (t.day == 1)
    dm[reset] = m[reset]
    cum = np.nancumsum(dm, axis=0)
    return t, cum, z, a, typ


def stakes(name):
    s = pd.read_csv(f'{WF}/data/domain_{name}/USGSweatherData/{name}/Input_{name}_Glaciological_Data.csv')
    for c in ('spring_date', 'fall_date'):
        s[c] = pd.to_datetime(s[c], format='%Y/%m/%d', errors='coerce')
    return s[(s.Year >= 2009) & (s.Year <= 2022)]


def at(t, cum, date):
    i = t.searchsorted(date)
    return cum[min(i, len(t) - 1)]


def profile(name, label=LABEL, verbose=True):
    t, cum, z, a, typ = load(name, label)
    s = stakes(name)
    rows = []
    for y, g in s.groupby('Year'):
        prev = s[s.Year == y - 1]
        f0 = prev.fall_date.median() if prev.fall_date.notna().any() else pd.Timestamp(y - 1, 9, 30)
        f1 = g.fall_date.median() if g.fall_date.notna().any() else pd.Timestamp(y, 9, 30)
        sp = g.spring_date.median()
        if f0 < t[0]:
            continue
        mw = at(t, cum, sp) - at(t, cum, f0)
        ma = at(t, cum, f1) - at(t, cum, f0)
        iy = t.searchsorted(pd.Timestamp(y, 7, 1))
        for h in range(typ.shape[0]):
            for k in range(typ.shape[1]):
                if typ[h, k] < 2 or not (a[iy, h, k] > 0) or not (z[iy, h, k] > 0):
                    continue
                ze = z[iy, h, k]
                row = {'year': y, 'hru': h + 1, 'type': int(typ[h, k]), 'elev': ze,
                       'mw': mw[h, k] / 1000, 'ma': ma[h, k] / 1000}
                for col, key in (('bw', 'sw'), ('ba', 'sa')):
                    st = g.dropna(subset=[col]).sort_values('elevation')
                    if len(st) >= 3 and st.elevation.min() - 100 <= ze <= st.elevation.max() + 100:
                        row[key] = np.polyval(np.polyfit(st.elevation, st[col], 1), ze) if not (st.elevation.min() <= ze <= st.elevation.max()) \
                            else np.interp(ze, st.elevation, st[col])
                rows.append(row)
    r = pd.DataFrame(rows)
    r['ms'] = r.ma - r.mw
    r['ss'] = r.sa - r.sw
    out = r.groupby(['hru', 'type']).agg(elev=('elev', 'mean'), mw=('mw', 'mean'), sw=('sw', 'mean'), ms=('ms', 'mean'),
                                         ss=('ss', 'mean'), ma=('ma', 'mean'), sa=('sa', 'mean')).round(2)
    if verbose:
        print(f'\n{name} [{label}]  m = model, s = stakes at the domain elevation; w winter, s summer, a annual (m w.e.)')
        print(out.to_string())
    return r, out


if __name__ == '__main__':
    for n in CASES:
        profile(n)
