"""Glacier area (cells with ice > 0.1 m, all grids) at the last survey year, per run label."""
import glob, sys
import numpy as np, netCDF4 as nc4
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
CASES = dict(gulkana=('gulkana_corrected', 384, 2021, 15.49), wolverine=('wolverine_corrected', 469, 2020, 15.41))
for name, (case, trial, yend, usgs) in CASES.items():
    out = []
    for label in sys.argv[1:]:
        r = f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_{label}'
        with nc4.Dataset(r + '_settings/attributes.nc') as d:
            nx, ny = np.asarray(d['nx'][:, 0]).astype(int), np.asarray(d['ny'][:, 0]).astype(int)
            bed = np.asarray(d['bed_elev'][:, :, :, 0], float); dx = float(np.asarray(d['dx'][:]).flat[0])
        p = sorted(glob.glob(f'{r}/output/*sample*_annual.nc'))[0]
        with nc4.Dataset(p) as d:
            tt = nc4.num2date(d['time'][:], d['time'].units)
            yrs = [x.year - 1 if (x.month, x.day) == (1, 1) else x.year for x in tt]
            S = np.asarray(d['surface_elev'][yrs.index(yend), :, :, :, 0], float)
        a = sum(((S[:ny[g], :nx[g], g] - bed[:ny[g], :nx[g], g]) > 0.1).sum() for g in range(len(nx))) * dx * dx / 1e6
        out.append(f'{label} {a:.2f}')
    print(f'{name} {yend} (USGS {usgs}): ' + ', '.join(out))
