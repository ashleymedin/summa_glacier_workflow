"""Main-glacier area (ice > 0.1 m) and mean thickness by year, per run label."""
import glob, sys
import numpy as np, netCDF4 as nc4
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
CASES = dict(gulkana=('gulkana_corrected', 384), wolverine=('wolverine_corrected', 469))
for name, (case, trial) in CASES.items():
    for label in sys.argv[1:]:
        r = f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_{label}'
        with nc4.Dataset(r + '_settings/attributes.nc') as d:
            nx, ny = np.asarray(d['nx'][:, 0]).astype(int), np.asarray(d['ny'][:, 0]).astype(int)
            g = int(np.argmax(nx * ny)); bed = np.asarray(d['bed_elev'][:ny[g], :nx[g], g, 0], float)
            dx = float(np.asarray(d['dx'][:]).flat[0])
        with nc4.Dataset(r + '_settings/coldState.nc') as d:
            S = [np.asarray(d['surface_elev'][:ny[g], :nx[g], g, 0], float)]; yrs = ['cold']
        for p in sorted(glob.glob(f'{r}/output/*spinup_rank0001_annual.nc')) + sorted(glob.glob(f'{r}/output/*sample*_annual.nc')):
            with nc4.Dataset(p) as d:
                tt = nc4.num2date(d['time'][:], d['time'].units)
                S += list(np.asarray(d['surface_elev'][:, :ny[g], :nx[g], g, 0], float))
                yrs += [x.year - 1 if (x.month, x.day) == (1, 1) else x.year for x in tt]
        H = np.array(S) - bed
        ice = H > 0.1
        print(f'{name} {label}: ' + ' '.join(f'{y}:{i.sum() * dx * dx / 1e6:.2f}/{h[i].mean():.0f}' for y, i, h in zip(yrs, ice, H)))
