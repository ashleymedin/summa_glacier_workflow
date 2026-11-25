import sys,numpy as np,netCDF4 as n
S=sys.argv[1]
a,b=[n.Dataset(f'{S}/out_{v}/GulkanaWolverine_timestep.nc') for v in('base','nocm')]
print(a['time'].shape,[d for d in a.variables if 'om' in d][:8])
g=lambda d,k:np.ma.filled(d[k][:].astype(float),np.nan)
A,B=g(a,'mLayerTemp'),g(b,'mLayerTemp'); ns=g(a,'nSnow');nsb=g(b,'nSnow');so=g(a,'nSoil');nl=g(a,'nLake')
def pick(X,sn,h,d,m):  # soil layers
    t=np.arange(X.shape[0])[:,None]; s=(np.where(sn[:,h,d]>=0,sn[:,h,d],0)).astype(int)[:,None]+np.arange(m)
    return X[:,:,h,d][t,s]
for h in range(A.shape[2]):
  for d in range(A.shape[3]):
    m=int(np.nanmax(np.where(so[:,h,d]>0,so[:,h,d],0)))
    if m==0: continue
    x,y=pick(A,ns,h,d,m),pick(B,nsb,h,d,m); z=np.where((x>200)&(y>200),y-x,np.nan)
    if np.isnan(z).all(): continue
    print('hru',h,'dom',d,'m',m,'mean dT/layer',np.round(np.nanmean(z,0),3),'max|dT|',np.round(np.nanmax(abs(z),0),2),'rms %.3f'%np.sqrt(np.nanmean(z**2)))
for k in('averageRoutedRunoff','scalarTotalET','scalarSoilDrainage','scalarSWE','basin__GlacierArea'):
    p,q=g(a,k),g(b,k); bad=(p<-9000)|(q<-9000); p[bad]=np.nan;q[bad]=np.nan
    P,Q=np.nanmean(p,0),np.nanmean(q,0); print(k,np.round(100*(Q-P)/np.where(P==0,np.nan,P),3).tolist())
