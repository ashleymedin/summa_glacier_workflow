"""Yearly ice budget of each glacier's tongue (start-ice cells below a USGS height): dV = B + F, F the ice flux in (1e3 m3 ice)."""
import sys
import numpy as np
exec(open('terminus_budget.py').read().split('def run(')[0])
import netCDF4 as nc4

ZT = dict(gulkana=1400, wolverine=700)

def tongue(name, label):
    case, trial, cap, dz = CASES[name]
    r = f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_{label}'
    with nc4.Dataset(r + '_settings/attributes.nc') as d:
        nx, ny = np.asarray(d['nx'][:, 0]).astype(int), np.asarray(d['ny'][:, 0]).astype(int)
        g = int(np.argmax(nx * ny))
        bed = np.asarray(d['bed_elev'][:ny[g], :nx[g], g, 0], float)
        mask = np.asarray(d['glacierMask'][:ny[g], :nx[g], g, 0]) == 1
        dx = float(np.asarray(d['dx'][:]).flat[0])
    with nc4.Dataset(r + '_settings/coldState.nc') as d:
        S = [np.asarray(d['surface_elev'][:ny[g], :nx[g], g, 0], float)]; D = [np.asarray(d['debris_thick'][:ny[g], :nx[g], g, 0], float)]
    years = []
    for p in sorted(glob.glob(f'{r}/output/*spinup_rank0001_annual.nc')) + sorted(glob.glob(f'{r}/output/*sample*_annual.nc')):
        with nc4.Dataset(p) as d:
            tt = nc4.num2date(d['time'][:], d['time'].units)
            S += list(np.asarray(d['surface_elev'][:, :ny[g], :nx[g], g, 0], float)); D += list(np.asarray(d['debris_thick'][:, :ny[g], :nx[g], g, 0], float))
            years += [x.year - 1 if (x.month, x.day) == (1, 1) else x.year for x in tt]
    S, D = np.array(S), np.array(D)
    H = np.where(mask, np.maximum(S - bed, 0), 0)
    P = profiles(f'{WF}/data/domain_{cap}/observations/storage/mass_balance/{name}_balance_profile.txt')
    T = (H[0] > THK) & (S[0] - dz < ZT[name])
    a = dx * dx; A = T.sum() * a
    print(f'\n{name} {label}: tongue below {ZT[name]} m USGS, {A / 1e6:.2f} km2, start H median {np.median(H[0][T]):.0f} m, '
          f'debris-covered {(D[0][T] >= 0.02).mean() * 100:.0f}%')
    print(' year  dV    B     F   (m ice over the tongue)  iced km2  H med')
    tot = np.zeros(3)
    for i, y in enumerate(years):
        if y > 2022: break
        b = balance(P, y, 0.5 * (S[i] + S[i + 1]), D[i])
        ice = T & ((H[i] > THK) | (H[i + 1] > THK))
        dV = (H[i + 1] - H[i])[T].sum() * a
        B = np.maximum(b[ice], -H[i][ice] - np.maximum(H[i + 1][ice] - H[i][ice], 0) * 0).sum() * a  # melt capped at the year-start ice
        tot += [dV, B, dV - B]
        print(f' {y} {dV / A:5.1f} {B / A:5.1f} {(dV - B) / A:5.1f}   {(H[i + 1] > THK)[T].sum() * a / 1e6:20.2f} {np.median(H[i + 1][T]):5.0f}')
    print(' all  ' + ' '.join(f'{v / A:5.1f}' for v in tot))

for name in ('gulkana', 'wolverine'):
    for label in ('usgsmb2_A1', 'usgsmb2_A0.25'):
        tongue(name, label)
