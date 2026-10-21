# 1D replica of glacAreaChange advection_MUSCL (l direction), clamped index ends like run_flowModel
import numpy as np
def sb(r): return np.maximum(0, np.maximum(np.minimum(2*r,1), np.minimum(r,2)))
def pluss(Hm,H,Hp):
    m=(Hp!=H)&(Hp!=Hm)&(H!=Hm); d=np.where(m,Hp-H,1.0)
    return np.where(m, H-0.5*sb(abs((H-Hm)/d))*(Hp-H), H)
def minus(Hm,H,Hp):
    m=(Hp!=H)&(Hp!=Hm)&(H!=Hm); d=np.where(m,H-Hm,1.0)
    return np.where(m, H+0.5*sb(abs((Hp-H)/d))*(H-Hm), H)
def run(u, D, mask, dt, nstep, dy=100.):
    n=len(D); l=np.arange(n); lp=np.minimum(l+1,n-1); lm=np.maximum(l-1,0)
    for _ in range(nstep):
        Dup=pluss(D[lm],D,D[lp]); Ddn=minus(D[lm],D,D[lp])
        uup=pluss(u[lm],u,u[lp]); udn=minus(u[lm],u,u[lp])
        div=(udn*Ddn-uup*Dup)/dy; div[mask==0]=0
        D=np.maximum(D+div*dt,0)
    return D
n=60; x=np.arange(n)
# interior: uniform u, debris bump well inside the ice, ice everywhere
u=np.full(n,-1e-6); mask=np.ones(n,int)   # u<0 = ice flows toward +l (u carries the slope sign)
D0=np.where((x>10)&(x<20),1.0,0.0)+np.where((x>=20)&(x<25),1-0.16*(x-20),0)
D=run(u,D0,mask,2e7,100); print('interior, uniform u: debris sum %.4f -> %.4f'%(D0.sum(),D.sum()))
# varying u inside ice (compressive toward the terminus)
u2=-1e-6*np.linspace(1,0.3,n); D=run(u2,D0,mask,2e7,100); print('interior, varying u: %.4f -> %.4f'%(D0.sum(),D.sum()))
# edge: ice ends at cell 40, u=0 outside (H=0)
u3=np.where(x<40,-1e-6,0.0); m3=(x<40).astype(int)
D0e=np.where((x>28)&(x<38),1.0,0.0); D=run(u3,D0e,m3,2e7,100)
print('edge: %.4f -> %.4f inside ice, %.4f on ice-free cells'%(D0e.sum(),D[m3==1].sum(),D[m3==0].sum()))
np.set_printoptions(precision=2, linewidth=200)
D=run(u,D0,mask,2e7,100); print('uniform, centroid %.1f -> %.1f'%((x*D0).sum()/D0.sum(),(x*D).sum()/D.sum())); print(D)
D=run(u3,D0e,m3,2e7,100); print(D)
for s in [1,-1]:
    u4=np.where(x<40,s*1e-6,0.0); D=run(u4,D0e,m3,2e7,100)
    print('edge, u sign %+d: inside %.4f, centroid %.1f'%(s,D[m3==1].sum(),(x*D).sum()/max(D.sum(),1e-12)))
