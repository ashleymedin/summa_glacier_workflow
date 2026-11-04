import sys, glob, os, numpy as np, netCDF4 as nc
# exact comparison of every variable in head vs new output pairs for one solver
out, solver, ta, tb = sys.argv[1:5]
skip = {'wallClockTime','numSteps','meanStepSize','numIter'} if False else {'wallClockTime'}
ndiff = 0; npair = 0
for h in sorted(glob.glob(f'{out}/*/*_{solver}_double_{ta}_*.nc')):
    n = h.replace(f'_{ta}_', f'_{tb}_')
    if not os.path.exists(n): print('MISSING', n); ndiff += 1; continue
    npair += 1
    a, b = nc.Dataset(h), nc.Dataset(n)
    bad = []
    for v in a.variables:
        if v in skip: continue
        a.set_auto_mask(False); b.set_auto_mask(False); x, y = a[v][:], b[v][:]
        if x.shape != y.shape: bad.append(v+'(shape)'); continue
        if x.dtype.kind in 'fc':
            if not np.array_equal(x, y, equal_nan=True): bad.append(v)
        elif not np.array_equal(x, y): bad.append(v)
    if bad: ndiff += 1; print(os.path.basename(h), 'DIFF', bad[:8], len(bad))
print(f'{solver} {ta} vs {tb}: {npair} pairs, {ndiff} differ')
