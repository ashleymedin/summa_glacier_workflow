import pandas as pd, numpy as np, json
d=pd.read_csv('all.csv',names=['s','t','q'],dtype={'s':str}); d['q']=pd.to_numeric(d.q,errors='coerce')/35.3147; p=d.groupby(['t','s']).q.mean().unstack(); p.index=pd.to_datetime(p.index); wy=p.index.year+(p.index.month>=10)
L='15052000'; M='15052500'
# outburst days: Mendenhall rises over 3x its 21-day median, padded; only days when Lemon is not itself high
med=p[M].rolling(31,center=True,min_periods=10).median(); lmed=p[L].rolling(31,center=True,min_periods=10).median()
hi=(p[M]>1.5*med)&(p[M]/med>1.5*p[L]/lmed); ob=hi.rolling(9,center=True,min_periods=1).max().astype(bool)
jn=p.index.month.isin([5,6,7,8,9])
for name,mask in (('all May-Sep',jn),('May-Sep, outbursts removed',jn&~ob),('May-Jun only',p.index.month.isin([5,6])),('Oct, Nov',p.index.month.isin([10,11]))):
    r={}
    for s in p.columns:
        if s==L: continue
        x=p.loc[mask,[L,s]].dropna(); g=x.groupby(wy[p.index.get_indexer(x.index)]).agg(['mean','count']); r[s]=(g[L]['mean']/g[s]['mean']).where(g[L]['count']>25)
    print(name); print(pd.DataFrame(r).loc[2003:].round(3).to_string())
print(p.notna().groupby(wy).sum().loc[2003:].to_string())
print('outburst days/yr',pd.Series(ob&jn).groupby(wy).sum().to_dict())
fm=json.load(open('fm.json'))['features']; a=pd.DataFrame([(x['properties']['time'][:16],x['properties']['parameter_code'],x['properties']['value']) for x in fm],columns=list('tpv')); a['v']=pd.to_numeric(a.v); a['d']=a.t.str[:10]; m=a.pivot_table(index='d',columns='p',values='v'); print(m.dropna(subset=['00060','00065'])[['00060','00065']].loc['2003':].to_string())
# Lemon rises unmatched elsewhere: daily rise over 2x the 15-day median with no wet forcing and no rise at the non-outburst gauges
import glob, xarray as xr
P=pd.concat([xr.open_dataset(f).pptrate.mean('hru').to_series() for f in sorted(glob.glob('/Users/amedin/Research/SummaSundials/summa_glacier_workflow/data/domain_LemonCreek_grus/forcing/SUMMA_input/station_corrected/*.nc'))]).resample('D').sum()*3600
P.index=P.index.normalize(); p3=P.rolling(3).sum().reindex(p.index)
r=p/p.rolling(15,center=True,min_periods=8).median()
c=p[(r[L]>1.6)&(p[L]>8)&(p3<15)&(r['15101490']<1.3)]; print('Lemon rises with dry 3-day forcing and no Greens Creek rise'); print(pd.concat([c.round(1),r.loc[c.index,[L]].round(2).rename(columns={L:'xmed'}),p3.loc[c.index].round(1).rename('P3')],axis=1).to_string())
