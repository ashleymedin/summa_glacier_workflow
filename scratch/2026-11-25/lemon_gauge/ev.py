# volume & stage-integral test, May-Oct; recession constants; and stage-flow conversion with one common shape
import pandas as pd, numpy as np
d=pd.read_pickle('iv.pkl'); 
pub=pd.read_csv('all.csv',names=['s','t','q'],dtype={'s':str}); pub['q']=pd.to_numeric(pub.q,errors='coerce')/35.3147; p=pub.groupby(['t','s']).q.mean().unstack(); p.index=pd.to_datetime(p.index); l=p['15052000']
m=np.log(l).diff(); 
for a,b in((2003,2012),(2013,2021),(2022,2022),(2023,2026)):
    k=(l.index.year>=a)&(l.index.year<=b)&l.index.month.isin([7,8,9,10]); r=m[k&(m<-.03)&(l.shift(1)>12)]; print('recession from >12 m3/s, median dlnq/day',a,b,round(r.median(),2),len(r)); 
    k2=k&(l.shift(1)<12)&(l.shift(1)>5); print('   5-12',round(m[k2&(m<-.03)].median(),2))
# stage variability normalised: convert stage to equivalent flow by the pre-2021 shape, shifted by the drop at measured flows (field measurements only)
fm=[]
import json
a=pd.DataFrame([(x['properties']['time'][:10],x['properties']['parameter_code'],float(x['properties']['value'])) for x in json.load(open('fm.json'))['features']],columns=list('tpv')).pivot_table(index='t',columns='p',values='v').dropna(subset=['00060','00065'])
pre=a.loc['2008':'2019']; pre=pre[pre['00060']>100]; post=a.loc['2023':]; post=post[post['00060']>100]
for n,x in(('pre >100cfs',pre),('post >100cfs',post)):
    c=np.polyfit(np.log(x['00060']),x['00065'],1); print(n,len(x),'ft per ln-cfs',c.round(3),'max measured',x['00060'].max())
x=pre[pre['00060']<360]; print('pre, 100-360 only',len(x),np.polyfit(np.log(x['00060']),x['00065'],1).round(3))
# control shape from the measurements: stage needed at 1000 cfs
print(post[['00060','00065']].sort_values('00060').to_string())
for lab,yrs in (('published rating 2023-26',(2023,2026)),('published rating 2017-19',(2017,2019))):
    g=d[(d.index.year>=yrs[0])&(d.index.year<=yrs[1])]; print(lab,[(q,round(g.s[(g.q>.97*q)&(g.q<1.03*q)].median(),2)) for q in (100,150,200,300,400,600,800,1000,1300)])
