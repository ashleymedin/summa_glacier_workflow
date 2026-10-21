"""Main glacier's starting area, volume and thickness by ring in from the margin, per domain build."""
import sys
import netCDF4 as nc, numpy as np
from scipy.ndimage import binary_erosion

for tag, root in [a.split('=') for a in sys.argv[1:]]:
    d = nc.Dataset(root + '/settings/SUMMA/attributes_glac.nc'); c = nc.Dataset(root + '/settings/SUMMA/coldstate_glac.nc')
    nx, ny = np.asarray(d['nx'][:]).ravel(), np.asarray(d['ny'][:]).ravel()
    g = int(np.argmax(nx * ny))
    bed = np.asarray(d['bed_elev'][:ny[g], :nx[g], g, 0]); S = np.asarray(c['surface_elev'][:ny[g], :nx[g], g, 0])
    dx = float(np.asarray(d['dx'][:]).flat[0]); a = dx * dx / 1e6
    h = S - bed; ice = h > 0.1
    rings, inner = [], ice
    for k in range(4):
        nxt = binary_erosion(inner)
        rings.append(np.median(h[inner & ~nxt])); inner = nxt
    print(f'{tag:14s} area {ice.sum()*a:6.2f} km2  volume {h[ice].sum()*dx*dx/1e9:.3f} km3  mean {h[ice].mean():5.0f} m  '
          f'rings 1-4 median ' + ' '.join(f'{r:5.1f}' for r in rings) + f' m  min surface {S[ice].min():.0f} m')
