import numpy as np, sys
from scipy import ndimage
def load(fn):
    h=open(fn).readline().split(); nx,ny,ela=int(h[0]),int(h[1]),float(h[2])
    a=np.loadtxt(fn,skiprows=1); S,B,D,H=[a[:,k].reshape(ny,nx) for k in range(4)]
    return S,B,D,H.astype(int),ela
dA=50.516**2/1e6
for fn in sys.argv[1:]:
    S,B,D,H,ela=load(fn); g=(S-B)>1.0
    dist=ndimage.distance_transform_edt(g)*50.516
    d=g&(D>=0.02)
    print(fn.split('/')[-3], fn.split('_')[-1][:3], 'deb %.2f km2;'%(d.sum()*dA), 'by edge distance (m): '+' '.join('%d-%d:%.2f/%.2f'%(lo,hi,(d&(dist>lo)&(dist<=hi)).sum()*dA,(g&(dist>lo)&(dist<=hi)).sum()*dA) for lo,hi in [(0,60),(60,160),(160,300),(300,3000)]),
          '| by HRU:',' '.join('%d:%.2f'%(h,(d&(H==h)).sum()*dA) for h in (1,2,3)),
          '| D(new deb) p10/50/90 %.3f %.3f %.3f'%tuple(np.percentile(D[d&(H!=1)],[10,50,90])) if (d&(H!=1)).any() else '')
