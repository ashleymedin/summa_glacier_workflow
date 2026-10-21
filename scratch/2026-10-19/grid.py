import numpy as np, sys, glob
def load(fn):
    h=open(fn).readline().split(); nx,ny,ela=int(h[0]),int(h[1]),float(h[2])
    a=np.loadtxt(fn,skiprows=1)
    S,B,D,H=[a[:,k].reshape(ny,nx) for k in range(4)]
    return S,B,D,H.astype(int),ela
for fn in sys.argv[1:]:
    S,B,D,H,ela=load(fn); g=(S-B)>1.0  # thick4area approx
    dA=50.516**2/1e6
    print(fn.split('/')[-1], 'ELA %.0f glac %.2f km2 deb>=2cm %.2f km2 deb>0 %.2f km2'%(ela,g.sum()*dA,(g&(D>=0.02)).sum()*dA,(g&(D>0)).sum()*dA))
    for h in np.unique(H[g]):
        m=g&(H==h); print('  hru',h,'area %.2f deb>=2cm %.2f meanD(deb) %.3f p50 %.3f p90 %.3f max %.2f'%(m.sum()*dA,(m&(D>=0.02)).sum()*dA,D[m&(D>=0.02)].mean() if (m&(D>=0.02)).any() else 0,*(np.percentile(D[m&(D>=0.02)],[50,90]) if (m&(D>=0.02)).any() else (0,0)),D[m].max()))
    e=np.arange(1200,2500,100)
    print('  elev band: glac km2 / deb km2:', ' '.join('%d:%.2f/%.2f'%(lo,(g&(S>=lo)&(S<lo+100)).sum()*dA,(g&(S>=lo)&(S<lo+100)&(D>=0.02)).sum()*dA) for lo in e))
