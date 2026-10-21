# 1D replica of advection_upwind: face velocities, one flux per face, closed faces beside no ice
import numpy as np
def run(uf, D, dt, nstep, dy=100.):
    out=(np.maximum(uf,0)+np.maximum(-np.r_[0,uf[:-1]],0))/dy
    assert dt*out.max()<=0.5+1e-12
    for _ in range(nstep):
        f=np.where(uf>0, uf*D, uf*np.r_[D[1:],0])
        D=np.maximum(D+dt*(-f/dy+np.r_[0,f[:-1]]/dy),0)
    return D
n=60; x=np.arange(n)
D0=np.where((x>10)&(x<20),1.0,0.0)+np.where((x>=20)&(x<25),1-0.16*(x-20),0)
uf=np.full(n,1e-6); uf[-1]=0
D=run(uf,D0,2e7,100); print('uniform: sum %.4f -> %.4f, centroid %.1f -> %.1f (expect +20)'%(D0.sum(),D.sum(),(x*D0).sum()/D0.sum(),(x*D).sum()/D.sum()))
uc=1e-6*np.linspace(1,0.3,n); uf2=0.5*(uc[:-1]+uc[1:]); uf2=np.r_[uf2,0]
D=run(uf2,D0,2e7,100); print('compressive: sum %.4f -> %.4f, max %.2f'%(D0.sum(),D.sum(),D.max()))
uf3=np.where(x<39,1e-6,0.0); D0e=np.where((x>28)&(x<38),1.0,0.0)
D=run(uf3,D0e,2e7,100); print('edge: sum %.4f -> %.4f, piled in last ice cell %.2f'%(D0e.sum(),D.sum(),D[39]))
