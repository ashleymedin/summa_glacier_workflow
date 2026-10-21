import numpy as np
for case in ('wolverine_corrected', 'gulkana_corrected'):
    nx, ny, dx = open(f'{case}.txt').read().split(); nx, ny = int(nx), int(ny)
    s0, b, m = np.fromfile(f'{case}.bin').reshape(3, ny, nx)
    s1 = np.fromfile(f'{case}_1yr.bin').reshape(ny, nx)
    s0 = np.where(m > 0, s0, b); H0 = s0 - b; d = s1 - s0; ice = H0 > 0.1
    out = np.pad(m == 0, 1, constant_values=True)
    edge = (m > 0) & (out[:-2, 1:-1] | out[2:, 1:-1] | out[1:-1, :-2] | out[1:-1, 2:])
    print(case, f'edge ice cells {(edge&ice).sum()}: mean dS {d[edge&ice].mean():.2f} m (sum {d[edge&ice].sum()*float(dx)**2:.3g} m3); interior {d[~edge&ice].mean():.3f} m')
    for i in np.argsort(-np.abs(d), axis=None)[:6]:
        y, x = divmod(i, nx)
        nb = [(s0[y+a, x+c] if 0 <= y+a < ny and 0 <= x+c < nx else np.nan) for a, c in ((-1,0),(1,0),(0,-1),(0,1))]
        print(f'   cell ({x},{y}) S0 {s0[y,x]:.0f} H0 {H0[y,x]:.0f} dS {d[y,x]:+.0f} edge {edge[y,x]}  neighbour S0 {np.round(nb).tolist()}  mask {[int(m[y+a,x+c]) if 0<=y+a<ny and 0<=x+c<nx else -1 for a,c in ((-1,0),(1,0),(0,-1),(0,1))]}')
    zq = np.percentile(s0[ice], 10); low = ice & (s0 < zq)
    print(f'   lowest 10% (below {zq:.0f} m): mean dS {d[low].mean():+.2f}, H0 {np.median(H0[low]):.0f} m')
