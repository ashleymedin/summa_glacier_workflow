import pandas as pd, numpy as np, glob, json
L=[]
for f in sorted(glob.glob('gauge/iv_15052000.*')):
    rows=[r.rstrip('\n').split('\t') for r in open(f) if r.startswith('USGS')]
    hdr=[r for r in open(f) if r.startswith('agency_cd')]
    if not rows or not hdr: continue
    h=hdr[0].rstrip('\n').split('\t'); d=pd.DataFrame(rows,columns=h); qc=[c for c in h if c.endswith('00060')][0]; sc=[c for c in h if c.endswith('00065')][0]
    d=d.assign(t=pd.to_datetime(d.datetime),q=pd.to_numeric(d[qc],errors='coerce'),s=pd.to_numeric(d[sc],errors='coerce'))[['t','q','s']]; print(f[-4:],len(d),d.q.notna().sum(),d.s.notna().sum()); L.append(d)
d=pd.concat(L).drop_duplicates('t').set_index('t').sort_index(); d.to_pickle('iv.pkl'); d['y']=d.index.year
print('stage (ft) at published flow, by half year'); 
b=[30,60,120,200,300,450,700,1000,1500,2500]
for y,g in d.groupby([d.y,np.where(d.index.month<8,'a','b')]):
    print(y,[ (round(g.s[(g.q>.95*x)&(g.q<1.05*x)].median(),2)) for x in b],'maxQ',g.q.max(),'maxS',g.s.max())
# published rating slope: ft rise 100->1000 cfs
jn=d[d.index.month.isin([7,8])]; day=jn.index.normalize()
g=jn.groupby(day); amp=pd.DataFrame({'ds':g.s.quantile(.97)-g.s.quantile(.03),'dq':g.q.max()-g.q.min(),'sm':g.s.mean(),'qm':g.q.mean(),'n':g.s.count()}); amp=amp[amp.n>80]
import xarray as xr
P=pd.concat([xr.open_dataset(f).pptrate.mean('hru').to_series() for f in sorted(glob.glob('/Users/amedin/Research/SummaSundials/summa_glacier_workflow/data/domain_LemonCreek_grus/forcing/SUMMA_input/station_corrected/*.nc'))]).resample('D').sum()*3600
T=pd.concat([xr.open_dataset(f).airtemp.mean('hru').to_series()-273.15 for f in sorted(glob.glob('/Users/amedin/Research/SummaSundials/summa_glacier_workflow/data/domain_LemonCreek_grus/forcing/SUMMA_input/station_corrected/*.nc'))]).resample('D').mean()
amp['p']=P.rolling(3).sum().reindex(amp.index); amp['T']=T.reindex(amp.index); dry=amp[amp.p<4]
print('dry Jul-Aug days: daily stage range ft, flow range cfs, mean flow, T'); print(dry.groupby(dry.index.year).agg(n=('ds','count'),ds=('ds','median'),dq=('dq','median'),qm=('qm','median'),T=('T','median')).round(2).to_string())
# event rises in stage vs rain
D=pd.DataFrame({'s':d.s.resample('D').max(),'q':d.q.resample('D').max(),'base':d.s.resample('D').min().rolling(7,min_periods=3).min(),'p2':P.rolling(2).sum()}).dropna(); D=D[D.index.month.isin([7,8,9,10])]; D['rise']=D.s-D.base
for a,b2 in((2008,2019),(2020,2021),(2022,2022),(2023,2026)):
    k=D[(D.index.year>=a)&(D.index.year<=b2)]; print(a,b2,[(lo,len(x),round(x.rise.mean(),2),round(x.q.mean()),round(x.q.max())) for lo,x in((l,k[(k.p2>=l)&(k.p2<h)]) for l,h in((0,10),(10,25),(25,50),(50,80),(80,200)))])
