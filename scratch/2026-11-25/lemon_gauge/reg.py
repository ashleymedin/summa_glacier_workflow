# Lemon daily flow predicted from the neighbours (trained May-Oct 2003-2019); residual of published and of field-measured flow
import pandas as pd, numpy as np, json
from sklearn.ensemble import RandomForestRegressor
d=pd.read_csv('all.csv',names=['s','t','q'],dtype={'s':str}); d['q']=pd.to_numeric(d.q,errors='coerce')/35.3147; p=d.groupby(['t','s']).q.mean().unstack(); p.index=pd.to_datetime(p.index)
N={'15052000':'L','15055500':'A','15052500':'M','15041200':'T'}; p=p.rename(columns=N); l=np.log(p[['A','M','T','15101490']].clip(lower=.05)); l=l.rename(columns={'15101490':'G'})
for use in (['A','T'],['A','M','T'],['A','T','G']):
    X=pd.concat([l[use],l[use].shift(1).add_suffix('1')],axis=1); w=2*np.pi*p.index.dayofyear/365.25; X['s']=np.sin(w); X['c']=np.cos(w); X['s2']=np.sin(2*w); X['c2']=np.cos(2*w)
    ok=X.notna().all(axis=1)&p.L.notna()&p.index.month.isin([5,6,7,8,9,10]); Y=np.log(p.L); yr=p.index.year
    tr=ok&(yr<=2019); 
    from sklearn.preprocessing import PolynomialFeatures; from sklearn.linear_model import LinearRegression; from sklearn.pipeline import make_pipeline
    m=make_pipeline(PolynomialFeatures(2),LinearRegression())
    # leave-one-year-out for training years
    pr=pd.Series(np.nan,p.index)
    for y in range(2003,2020): k=tr&(yr!=y); m.fit(X[k],Y[k]); z=ok&(yr==y); pr[z]=m.predict(X[z])
    m.fit(X[tr],Y[tr]); z=ok&(yr>2019); pr[z]=m.predict(X[z])
    e=np.exp(pr); r=pd.DataFrame({'L':p.L,'E':e}).dropna(); r['per']=np.where(r.index.month<=6,'MayJun',np.where(r.index.month<=9,'JulSep','Oct'))
    g=r.groupby([r.index.year,'per']).sum(); g=(g.L/g.E).unstack(); g['all']=r.L.groupby(r.index.year).sum()/r.E.groupby(r.index.year).sum(); print(use); print(g.round(2).to_string())
    fm=json.load(open('fm.json'))['features']; a=pd.DataFrame([(x['properties']['time'],x['properties']['value']) for x in fm if x['properties']['parameter_code']=='00060'],columns=['t','v']); a['v']=pd.to_numeric(a.v)/35.3147; a.index=(pd.to_datetime(a.t,utc=True)-pd.Timedelta(hours=9)).dt.tz_localize(None).dt.normalize(); f=a.v.groupby(level=0).mean().to_frame('F').join(r,how='inner'); f['F/E']=f.F/f.E; f['P/E']=f.L/f.E
    for A,B in ((2003,2012),(2013,2019),(2023,2026)): k=f[(f.index.year>=A)&(f.index.year<=B)]; print('field/expected',A,B,len(k),np.exp(np.log(k['F/E']).mean()).round(2),'sd',np.log(k['F/E']).std().round(2),'| published same days',np.exp(np.log(k['P/E']).mean()).round(2))
    j=f[f.index.month.isin([7,8,9])]
    for A,B in ((2003,2012),(2013,2019),(2023,2026)): k=j[(j.index.year>=A)&(j.index.year<=B)]; print('  Jul-Sep',A,B,len(k),np.exp(np.log(k['F/E']).mean()).round(2),np.round(k['F/E'].values,2))
# monthly 2020-2026 ratio
    if use==['A','M','T']:
        q=r[r.index.year>=2019]; h=q.groupby([q.index.year,q.index.month])[['L','E']].sum(); print((h.L/h.E).unstack().round(2).to_string())
        for A,B in ((2003,2019),(2023,2026)):
            k=r[(r.index.year>=A)&(r.index.year<=B)&r.index.month.isin([7,8,9])]; b=pd.cut(k.E,[0,5,8,11,14,20,100]); print(A,B,(k.L.groupby(b,observed=True).sum()/k.E.groupby(b,observed=True).sum()).round(2).to_dict())
