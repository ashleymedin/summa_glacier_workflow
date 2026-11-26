import pandas as pd, numpy as np, json
fm=json.load(open('fm.json'))['features']; a=pd.DataFrame([(x['properties']['time'],x['properties']['value'],x['properties'].get('qualifier')) for x in fm if x['properties']['parameter_code']=='00060'],columns=['t','v','q']); a['v']=pd.to_numeric(a.v)/35.3147; a['d']=(pd.to_datetime(a.t,utc=True)-pd.Timedelta(hours=9)).dt.tz_localize(None).dt.normalize()
d=pd.read_csv('all.csv',names=['s','t','q'],dtype={'s':str}); d['q']=pd.to_numeric(d.q,errors='coerce')/35.3147; p=d.groupby(['t','s']).q.mean().unstack(); p.index=pd.to_datetime(p.index)
f=a.groupby('d').v.mean().to_frame('field').join(p,how='inner').rename(columns={'15052000':'pub','15055500':'Ant','15052500':'Men','15101490':'Gre'}); f['pub/field']=f['pub']/f.field
for n in('Ant','Men','Gre'): f['f/'+n]=f.field/f[n]
f['m']=f.index.month; print(f[f.index>='2017'].round(3).to_string())
x=f[f.m.isin([5,6,7,8,9,10])]
for n in('Ant','Men','Gre'):
    for a0,b0 in(('2003','2019'),('2023','2026')): y=x.loc[a0:b0]; print(n,a0,b0,len(y),'median field/'+n,y['f/'+n].median().round(3),y['f/'+n].quantile([.25,.75]).round(3).tolist(),'pub/field',y['pub/field'].median().round(3))
for mo in ([5,6],[7,8,9]):
    y=f[f.m.isin(mo)]; print(mo,y.loc[:'2019','f/Ant'].describe()[['count','25%','50%','75%']].round(2).to_dict(),y.loc['2023':,'f/Ant'].describe()[['count','25%','50%','75%']].round(2).to_dict())
