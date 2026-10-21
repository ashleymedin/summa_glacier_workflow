"""Model SIA surface speed (no sliding) at Wolverine's GNSS stakes against the stakes' measured speed."""
import glob, os, sys
import numpy as np, pandas as pd, netCDF4 as nc4
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
sys.path.insert(0, WF)
from domain_config import load_config
from glacier_cold_state import grid_transforms

A0, N, RHO, G = 2.4e-24, 3, 917.0, 9.80616
YR = 365.25 * 86400

g = pd.read_csv(f'{WF}/GlacierDEM/USGS_Glacier_GNSS.csv'); g['Date'] = pd.to_datetime(g.Date)
obs = []
for s, x in g.groupby('Stake_name'):
    x = x.sort_values('Date')
    for a, b in [(x.iloc[0], x.iloc[-1])]:
        dt = (b.Date - a.Date).days / 365.25
        if dt >= 0.9:  # whole years only: summer speeds run above annual
            obs.append(dict(site=a.Site, stake=s, year=a.Date.year + (b.Date - a.Date).days / 730.5,
                            E=(a.Easting + b.Easting) / 2, N=(a.Northing + b.Northing) / 2, z=a.Elevation,
                            speed=np.hypot(b.Easting - a.Easting, b.Northing - a.Northing) / dt))
obs = pd.DataFrame(obs)

if 'gulkana' in sys.argv[1]:  # WRI 00-4074 table 9, stake bottoms Oct 1994 to Sep 1995, local + (575000, 7011000) m
    obs = pd.DataFrame(dict(site=['A', 'B', 'D'], z=[1365, 1676, 1828], E=[578807, 579741, 581018],
                            N=[7015451, 7018393, 7018344], speed=[20.0, 47.3, 49.0]))
c = load_config(f'{WF}/domains/' + ('gulkana' if 'gulkana' in sys.argv[1] else 'wolverine') + '.yaml')
tr, _ = grid_transforms(c['project_dir'], c['domain'], c['utm_epsg'])
out = obs.groupby('site').agg(z=('z', 'mean'), E=('E', 'mean'), N=('N', 'mean'), n=('speed', 'size'),
                              obs=('speed', 'median')).sort_values('z')
for run in sys.argv[1:]:
    A = A0 * float(run.split('_A')[-1])
    with nc4.Dataset(f'{run}_settings/attributes.nc') as d:
        bed = np.asarray(d['bed_elev'][:, :, :, 0], float); ids = np.asarray(d['gridId'][:, 0]).astype(int)
        nx, ny = np.asarray(d['nx'][:, 0]).astype(int), np.asarray(d['ny'][:, 0]).astype(int)
        dx = float(np.asarray(d['dx'][:]).flat[0])
    m = int(np.argmax(nx * ny)); t = tr[int(ids[m])]
    S, years = [], []
    for p in sorted(glob.glob(f'{run}/output/*sample*_annual.nc')):
        with nc4.Dataset(p) as d:
            tt = nc4.num2date(d['time'][:], d['time'].units)
            S.append(np.asarray(d['surface_elev'][:, :ny[m], :nx[m], m, 0], float))
            years += [x.year - 1 if (x.month, x.day) == (1, 1) else x.year for x in tt]
    S, years = np.concatenate(S), np.array(years)
    S = S[(years >= 2015) & (years <= 2020)]
    if False:  # the cold state, A x 1
        with nc4.Dataset(f'{run}_settings/coldState.nc') as d:
            s0 = np.asarray(d['surface_elev'][:ny[m], :nx[m], m, 0], float)
        h0 = np.clip(s0 - bed[:ny[m], :nx[m], m], 0, None)
        g0y, g0x = np.gradient(s0, dx)
        u0 = np.where(h0 > 0.1, 2 * A0 / (N + 1) * (RHO * G) ** N * h0 ** (N + 1) * np.hypot(g0x, g0y) ** N * YR, np.nan)
        c0, r0 = (~t) * (out.E.values, out.N.values)
        out['start_A1'] = u0[np.floor(r0).astype(int), np.floor(c0).astype(int)].round(1)
        out['start_H'] = h0[np.floor(r0).astype(int), np.floor(c0).astype(int)].round(0)
        out['obs/start_A1'] = (out.obs / out.start_A1).round(2)
    H = np.clip(S - bed[None, :ny[m], :nx[m], m], 0, None)
    gy, gx = np.gradient(S, dx, axis=(1, 2))
    u = 2 * A / (N + 1) * (RHO * G) ** N * H ** (N + 1) * np.hypot(gx, gy) ** N * YR
    u = np.where(H > 0.1, u, np.nan).mean(0)
    col, row = (~t) * (out.E.values, out.N.values)
    r, k = np.floor(row).astype(int), np.floor(col).astype(int)
    out[os.path.basename(run)] = u[r, k].round(1)
    out[os.path.basename(run) + '_H'] = H.mean(0)[r, k].round(0)
print(out.drop(columns=['E', 'N']).round(1).to_string())
