"""Yearly ice budget of the cells each run advances onto, and of the start-ice margin band behind them.
dV = B + F: dV volume change, B the prescribed balance on the iced cells (m ice), F the ice flux in.
B is bracketed: cells iced the whole year (lo) and cells iced at either end (hi)."""
import glob, sys
import numpy as np, netCDF4 as nc4
from scipy.ndimage import binary_dilation
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
RW, RI, THK = 1000.0, 917.0, 0.1

CASES = dict(gulkana=('gulkana_corrected', 384, 'Gulkana', -16.1), wolverine=('wolverine_corrected', 469, 'Wolverine', -14.0))


def profiles(path):
    a = np.loadtxt(path, comments='!')
    return {(int(y), int(f)): (a[(a[:, 0] == y) & (a[:, 1] == f), 2], a[(a[:, 0] == y) & (a[:, 1] == f), 3])
            for y, f in {(r[0], r[1]) for r in a}}


def balance(P, year, S, debris):
    clean = P[(year, 0)]; dbr = P.get((year, 1), clean)
    b = np.where(debris >= 0.02, np.interp(S, *dbr), np.interp(S, *clean))
    return b * RW / RI  # m ice per year


def run(name, label, band_cells=3):
    case, trial, cap, dz = CASES[name]
    r = f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_{label}'
    with nc4.Dataset(r + '_settings/attributes.nc') as d:
        nx, ny = np.asarray(d['nx'][:, 0]).astype(int), np.asarray(d['ny'][:, 0]).astype(int)
        g = int(np.argmax(nx * ny))
        bed = np.asarray(d['bed_elev'][:ny[g], :nx[g], g, 0], float)
        mask = np.asarray(d['glacierMask'][:ny[g], :nx[g], g, 0]) == 1
        dx = float(np.asarray(d['dx'][:]).flat[0])
    with nc4.Dataset(r + '_settings/coldState.nc') as d:
        S = [np.asarray(d['surface_elev'][:ny[g], :nx[g], g, 0], float)]
        D = [np.asarray(d['debris_thick'][:ny[g], :nx[g], g, 0], float)]
    files = sorted(glob.glob(f'{r}/output/*spinup_rank0001_annual.nc')) + sorted(glob.glob(f'{r}/output/*sample*_annual.nc'))
    years = []
    for p in files:
        with nc4.Dataset(p) as d:
            tt = nc4.num2date(d['time'][:], d['time'].units)
            S += list(np.asarray(d['surface_elev'][:, :ny[g], :nx[g], g, 0], float))
            D += list(np.asarray(d['debris_thick'][:, :ny[g], :nx[g], g, 0], float))
            years += [x.year - 1 if (x.month, x.day) == (1, 1) else x.year for x in tt]
    S, D = np.array(S), np.array(D)
    H = np.where(mask, np.maximum(S - bed, 0), 0)
    P = profiles(f'{WF}/data/domain_{cap}/observations/storage/mass_balance/{name}_balance_profile.txt')
    ice0 = H[0] > THK
    adv = mask & ~ice0 & (H[1:] > THK).any(0)
    band = ice0 & binary_dilation(adv, iterations=band_cells)
    a = dx * dx
    print(f'\n{name} {label}: advance cells {adv.sum()} ({adv.sum() * a / 1e6:.2f} km2, bed {np.percentile(bed[adv] - dz, 5):.0f}-'
          f'{np.percentile(bed[adv] - dz, 95):.0f} m USGS), margin band {band.sum()} cells, start {np.median(H[0][band]):.0f} m median')
    print(' year | advance: iced km2  dV  B_lo  B_hi  F_lo  F_hi (1e3 m3) | band: dV  B  F (1e3 m3), band H med (m)')
    tot = np.zeros(5)
    for i, y in enumerate(years):
        Ha, Hb = H[i], H[i + 1]
        b = balance(P, y, 0.5 * (S[i] + S[i + 1]), D[i])  # profiles are already in model heights
        both, either = (Ha > THK) & (Hb > THK), (Ha > THK) | (Hb > THK)
        dV = (Hb - Ha)[adv].sum() * a / 1e3
        Blo, Bhi = b[adv & both].sum() * a / 1e3, b[adv & either].sum() * a / 1e3
        dVb, Bb = (Hb - Ha)[band].sum() * a / 1e3, b[band & either].sum() * a / 1e3
        tot += [dV, Blo, Bhi, dVb, Bb]
        print(f' {y} | {(Hb > THK)[adv].sum() * a / 1e6:5.2f} {dV:7.0f} {Blo:6.0f} {Bhi:6.0f} {dV - Blo:6.0f} {dV - Bhi:6.0f} |'
              f' {dVb:7.0f} {Bb:7.0f} {dVb - Bb:7.0f}  {np.median(Hb[band]):5.0f}')
    dV, Blo, Bhi, dVb, Bb = tot
    print(f' all  |       {dV:7.0f} {Blo:6.0f} {Bhi:6.0f} {dV - Blo:6.0f} {dV - Bhi:6.0f} | {dVb:7.0f} {Bb:7.0f} {dVb - Bb:7.0f}')
    return dict(years=years, H=H, adv=adv, band=band, bed=bed, dz=dz, a=a)


if __name__ == '__main__':
    for name in sys.argv[1:] or ('gulkana', 'wolverine'):
        for label in ('usgsmb2_A1', 'usgsmb2_A0.25'):
            run(name, label)
