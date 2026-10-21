"""Write the main glacier's start surface, bed and glacierMask as raw float64 (Fortran order, x fastest) for real_grid."""
import numpy as np, netCDF4 as nc4
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
for case in ('gulkana_corrected', 'wolverine_corrected'):
    ins = f'{WF}/runs/{case}/summa_inputs_flow'
    with nc4.Dataset(f'{ins}/attributes.nc') as d:
        bed = np.asarray(d['bed_elev'][:, :, :, 0], float); gm = np.asarray(d['glacierMask'][:, :, :, 0], float)
        nx = np.asarray(d['nx'][:, 0]).astype(int); ny = np.asarray(d['ny'][:, 0]).astype(int); dx = float(np.asarray(d['dx'][:]).flat[0])
    g = int(np.argmax(nx * ny))
    with nc4.Dataset(f'{ins}/coldState.nc') as d:
        s0 = np.asarray(d['surface_elev'][:, :, g, 0], float)[:ny[g], :nx[g]]
    b = bed[:ny[g], :nx[g], g]; m = gm[:ny[g], :nx[g], g]
    # arrays are (y, x); Fortran S(nx,ny) with x fastest is the C-order (y, x) buffer
    np.stack([s0, b, m]).astype('<f8').tofile(f'{case}.bin')
    open(f'{case}.txt', 'w').write(f'{nx[g]} {ny[g]} {dx}\n')
    print(case, nx[g], ny[g], dx, (s0 - b > 0.1).sum())
