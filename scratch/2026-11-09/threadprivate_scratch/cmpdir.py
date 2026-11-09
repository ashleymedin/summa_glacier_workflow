import sys, glob, os, numpy as np, netCDF4 as nc
# exact comparison of every variable in the .nc files of two output directories
a_dir, b_dir = sys.argv[1:3]; nd = 0
for fa in sorted(glob.glob(f'{a_dir}/*.nc')):
    a, b = nc.Dataset(fa), nc.Dataset(fa.replace(a_dir, b_dir)); a.set_auto_mask(False); b.set_auto_mask(False); bad = []
    for v in a.variables:
        if v == 'wallClockTime': continue
        x, y = a[v][:], b[v][:]
        if x.shape != y.shape or not np.array_equal(x, y, equal_nan=x.dtype.kind in 'fc'): bad.append(v)
    nd += len(bad); print(os.path.basename(fa), 'identical' if not bad else f'DIFF {len(bad)}: {bad[:8]}')
sys.exit(1 if nd else 0)
