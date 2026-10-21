"""Model SIA surface speed (no sliding) against ITS_LIVE annual speed, by 100 m band of each year's surface (USGS heights).
f_A implied = run's f_A x median(obs) / median(model) over the band's cells, since deformation speed is linear in A at fixed geometry."""
import glob, sys
import numpy as np, netCDF4 as nc4
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
A0, N, RHO, G, YR = 2.4e-24, 3, 917.0, 9.80616, 365.25 * 86400
CASES = dict(gulkana=('gulkana_corrected', 384, 'Gulkana', -16.1), wolverine=('wolverine_corrected', 469, 'Wolverine', -14.0))
MAXERR, MINV, MINH = 10.0, 0.0, 20.0  # m/yr ITS_LIVE error cap, slowest speed used, thinnest model ice (m)


def model(name, label):
    case, trial, cap, dz = CASES[name]
    r = f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_{label}'
    with nc4.Dataset(r + '_settings/attributes.nc') as d:
        nx, ny = np.asarray(d['nx'][:, 0]).astype(int), np.asarray(d['ny'][:, 0]).astype(int)
        g = int(np.argmax(nx * ny))
        bed = np.asarray(d['bed_elev'][:ny[g], :nx[g], g, 0], float)
        mask = np.asarray(d['glacierMask'][:ny[g], :nx[g], g, 0]) == 1
        dx = float(np.asarray(d['dx'][:]).flat[0])
    S, D, years = [], [], []
    for p in sorted(glob.glob(f'{r}/output/*sample*_annual.nc')):
        with nc4.Dataset(p) as d:
            tt = nc4.num2date(d['time'][:], d['time'].units)
            S += list(np.asarray(d['surface_elev'][:, :ny[g], :nx[g], g, 0], float))
            D += list(np.asarray(d['debris_thick'][:, :ny[g], :nx[g], g, 0], float))
            years += [x.year - 1 if (x.month, x.day) == (1, 1) else x.year for x in tt]
    S, D = np.array(S), np.array(D)
    H = np.where(mask, np.maximum(S - D - bed, 0), 0)
    gy, gx = np.gradient(S, dx, axis=(1, 2))
    u = 2 * A0 * float(label.split('_A')[-1]) / (N + 1) * (RHO * G) ** N * H ** (N + 1) * np.hypot(gx, gy) ** N * YR
    return dict(zip(years, zip(u, H, S - dz)))


def compare(name, years=range(2013, 2021)):
    cap = CASES[name][2]
    o = np.load(f'{WF}/data/domain_{cap}/observations/storage/velocity/itslive_annual.npz')
    runs = {lab: model(name, lab) for lab in ('usgsmb2_A1', 'usgsmb2_A0.25')}
    print(f'\n{name}, {min(years)}-{max(years)}: median speed (m/yr) and implied f_A by band; n = cell-years')
    print(' band   n  ITS_LIVE  A1 model  f_A(A1)  A0.25 model  f_A(A0.25)')
    rows = {}
    for y in years:
        i = list(o['years']).index(y)
        v, e = o['v'][i], o['v_error'][i]
        u1, H1, Z = runs['usgsmb2_A1'][y]; u4, H4, _ = runs['usgsmb2_A0.25'][y]
        ok = (H1 > MINH) & (H4 > MINH) & np.isfinite(v) & (e < MAXERR) & (v > MINV)
        for z in np.unique(np.floor(Z[ok] / 100) * 100):
            k = ok & (np.floor(Z / 100) * 100 == z)
            rows.setdefault(z, []).append(np.c_[v[k], u1[k], u4[k]])
    allr = []
    for z in sorted(rows):
        a = np.vstack(rows[z]); allr.append(a)
        if len(a) < 20: continue
        print(f' {z:5.0f} {len(a):4d} {np.median(a[:, 0]):8.1f} {np.median(a[:, 1]):9.1f} {np.median(a[:, 0]) / np.median(a[:, 1]):8.2f}'
              f' {np.median(a[:, 2]):11.1f} {0.25 * np.median(a[:, 0]) / np.median(a[:, 2]):10.2f}')
    a = np.vstack(allr)
    print(f'   all {len(a):4d} {np.median(a[:, 0]):8.1f} {np.median(a[:, 1]):9.1f} {np.median(a[:, 0]) / np.median(a[:, 1]):8.2f}'
          f' {np.median(a[:, 2]):11.1f} {0.25 * np.median(a[:, 0]) / np.median(a[:, 2]):10.2f}')


if __name__ == '__main__':
    for name in sys.argv[1:] or CASES:
        compare(name, range(2009, 2012))
        compare(name)
