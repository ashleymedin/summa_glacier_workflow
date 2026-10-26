"""Area change per 100 m band (USGS heights, each year's own surface) split into cells newly iced, cells melted out, and iced cells moving band."""
import glob, sys
import numpy as np, netCDF4 as nc4
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
CASES = dict(gulkana=('gulkana_corrected', 384, -16.1, 2021), wolverine=('wolverine_corrected', 469, -14.0, 2020))
for name, (case, trial, dz, yend) in CASES.items():
    for label in tuple(sys.argv[1:]):
        r = f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_{label}'
        with nc4.Dataset(r + '_settings/attributes.nc') as d:
            nx, ny = np.asarray(d['nx'][:, 0]).astype(int), np.asarray(d['ny'][:, 0]).astype(int)
            G = [g for g in range(len(nx))]
            bed = [np.asarray(d['bed_elev'][:ny[g], :nx[g], g, 0], float) for g in G]
            dx = float(np.asarray(d['dx'][:]).flat[0])
        with nc4.Dataset(r + '_settings/coldState.nc') as d:
            S0 = [np.asarray(d['surface_elev'][:ny[g], :nx[g], g, 0], float) for g in G]
        S1, yrs = None, []
        for p in sorted(glob.glob(f'{r}/output/*sample*_annual.nc')):
            with nc4.Dataset(p) as d:
                tt = nc4.num2date(d['time'][:], d['time'].units)
                yrs = [x.year - 1 if (x.month, x.day) == (1, 1) else x.year for x in tt]
                i = yrs.index(yend)
                S1 = [np.asarray(d['surface_elev'][i, :ny[g], :nx[g], g, 0], float) for g in G]
                Sall = [np.asarray(d['surface_elev'][:, :ny[g], :nx[g], g, 0], float) for g in G]
        a = dx * dx / 1e6
        rows = {}
        new_ever = 0
        for g in G:
            h0, h1 = S0[g] - bed[g] > 0.1, S1[g] - bed[g] > 0.1
            new_ever += ((Sall[g] - bed[g] > 0.1).any(0) & ~h0).sum()
            z0, z1 = np.floor((S0[g] - dz) / 100) * 100, np.floor((S1[g] - dz) / 100) * 100
            for z in np.unique(np.r_[z0[h0], z1[h1]]):
                k = rows.setdefault(z, np.zeros(4))
                k[0] += ((z1 == z) & h1 & ~h0).sum() * a                    # newly iced
                k[1] -= ((z0 == z) & h0 & ~h1).sum() * a                    # melted out
                k[2] += (((z1 == z) & h1 & h0).sum() - ((z0 == z) & h0 & h1).sum()) * a  # moved band
                k[3] += ((z1 == z) & h1).sum() * a - ((z0 == z) & h0).sum() * a
        print(f'\n{name} {label} cold state -> {yend}; cells ever iced outside the start ice: {new_ever}')
        print(' band  new  melted  moved  total (km2)')
        for z in sorted(rows):
            if np.abs(rows[z]).max() >= 0.01: print(f' {z:5.0f} ' + ' '.join(f'{v:6.2f}' for v in rows[z]))
