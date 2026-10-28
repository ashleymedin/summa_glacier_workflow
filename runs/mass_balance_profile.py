#!/usr/bin/env python3
"""The glacier mass balance the flow model is given, against the USGS stakes: mass_balance_profile.py [label]

Each glacier domain's mass change over each area-update year (glacMass4AreaChange just before it resets), at the
domain's elevation (DOMelev), from trials 384 and 469 rerun by rerun_trials.py with --label (default mb); the
clean domains' ablation gradient each year against the stakes', and the stakes' mean balance against the clean
domains' curve at each stake's elevation, interpolated and extrapolated as fit_massBalanceCurve does.
"""
import sys
import netCDF4 as nc, numpy as np, pandas as pd

WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
LABEL = sys.argv[1] if len(sys.argv) > 1 else 'mb'
for name, case, trial in (('Gulkana', 'gulkana_corrected', 384), ('Wolverine', 'wolverine_corrected', 469)):
    d = nc.Dataset(f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_{LABEL}/output/{case}_rank0001_sample000001_day.nc')
    t = pd.DatetimeIndex(nc.num2date(d['time'][:], d['time'].units, only_use_cftime_datetimes=False))
    m = np.asarray(d['glacMass4AreaChange_mean'][:])   # (time, hru, dom) kg m-2
    z = np.asarray(d['DOMelev_mean'][:]); a = np.asarray(d['DOMarea_mean'][:]); typ = np.asarray(d['domType'][:])
    size = [np.nanmean(np.abs(m[i][typ > 1])) for i in range(len(t))]
    drop = [i for i in range(1, len(t)) if size[i - 1] > 100 and size[i] < 0.2 * size[i - 1]]  # the day after each reset
    ends = [i - 1 for i in drop]
    print(f'\n{name}: area updates after {sorted(set(t[i].strftime("%m-%d") for i in ends))}, {len(ends)} years')
    rows = []
    for i in ends:
        for h in range(typ.shape[0]):
            for k in range(typ.shape[1]):
                if typ[h, k] > 1 and a[i, h, k] > 0:
                    rows.append({'year': t[i].year, 'hru': h + 1, 'type': int(typ[h, k]), 'elev': z[i, h, k], 'b': m[i, h, k] / 1000})
    r = pd.DataFrame(rows)
    print(r.groupby(['hru', 'type']).agg(elev=('elev', 'mean'), b_mweq=('b', 'mean')).round(2).to_string())
    s = pd.read_csv(f'{WF}/data/domain_{name}/observations/storage/mass_balance/Input_{name}_Glaciological_Data.csv').dropna(subset=['ba'])
    out = []
    for y, g in r.groupby('year'):
        clean = g[g.type != 4].sort_values('elev')
        st = s[s.Year == y]
        if len(clean) < 2 or st.empty:
            continue
        abl = clean[clean.b < 0]
        grad = np.polyfit(abl.elev, abl.b, 1)[0] * 1000 if len(abl) >= 2 else np.nan
        mod = np.interp(st.elevation, clean.elev, clean.b, left=np.nan, right=np.nan)
        lo = clean.iloc[:2]; sl = (lo.b.iloc[1] - lo.b.iloc[0]) / (lo.elev.iloc[1] - lo.elev.iloc[0])
        mod = np.where(st.elevation < clean.elev.iloc[0], lo.b.iloc[0] + max(sl, 0) * (st.elevation - lo.elev.iloc[0]), mod)
        for (_, p), v in zip(st.iterrows(), mod):
            out.append({'year': y, 'site': p.site_name, 'elev': p.elevation, 'stake': p.ba, 'model': v})
        sabl = st[st.ba < 0]
        sg = np.polyfit(sabl.elevation, sabl.ba, 1)[0] * 1000 if len(sabl) >= 2 else np.nan
        print(f'  {y}: clean-domain ablation gradient {grad:5.2f}, stakes {sg:5.2f} mm w.e. per m')
    o = pd.DataFrame(out)
    print(o.groupby('site').agg(elev=('elev', 'median'), stake=('stake', 'mean'), model=('model', 'mean'), n=('stake', 'size'))
          .sort_values('elev').round(2).to_string())
