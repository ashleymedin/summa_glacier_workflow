import numpy as np
f = np.load('/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/0145f8cb-2306-44c4-a47c-a55707ead47a/scratchpad/seam.npz')
dem, gl, zz, cov, w, ice = (f[k] for k in ['dem','gl','zz','cov','w','ice'])
d = gl - dem
cv = np.isfinite(zz) & w
for lo,hi in [(0,.25),(.25,.5),(.5,.75),(.75,.99),(.99,1.01)]:
    m = cv & (cov>=lo)&(cov<hi)
    print(f'cov {lo}-{hi}: n={m.sum()} d pct', np.round(np.nanpercentile(d[m],[5,50,95]),1) if m.sum() else '')
def pairs(z, mask, cvmask):
    out=[]
    for a,b in [((slice(None,-1),slice(None)),(slice(1,None),slice(None))),((slice(None),slice(None,-1)),(slice(None),slice(1,None)))]:
        both = mask[a]&mask[b]; edge = both & (cvmask[a]!=cvmask[b])
        dz = np.abs(z[a]-z[b])
        out.append((dz[both&edge], dz[both&~edge]))
    e = np.concatenate([o[0] for o in out]); n = np.concatenate([o[1] for o in out])
    return e, n
e,n = pairs(gl, w, cv)
print('edge pairs', len(e), 'median', np.median(e), '>50', (e>50).sum(), 'max', e.max(), '| others median', np.median(n), '>50', (n>50).sum())
# d near the edge on the covered side
from scipy.ndimage import binary_dilation
edge_cov = cv & binary_dilation(w & ~cv)
print('d on covered edge cells pct', np.round(np.percentile(d[edge_cov],[5,25,50,75,95]),1), 'cov there', np.round(np.percentile(cov[edge_cov],[5,50,95]),2))
