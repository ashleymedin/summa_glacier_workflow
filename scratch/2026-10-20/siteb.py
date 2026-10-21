import sys, numpy as np, pandas as pd
sys.path.insert(0,'/Users/amedin/Research/SummaSundials/summa_glacier_workflow')
D='/Users/amedin/Research/SummaSundials/summa_glacier_workflow/data/domain_Gulkana'
b=pd.read_csv(f'{D}/Wilson_gulkana_2024_data/1_meteo/gulkanaB_AWS_2024.csv',skiprows=[1,2])
b['t']=pd.to_datetime(b.TIMESTAMP,format='%m/%d/%Y %H:%M')
b=b.set_index('t')[['AirTC_Avg','WS_ms_Avg','SWUpper_Avg']].apply(pd.to_numeric,errors='coerce').resample('1h',label='right',closed='right').mean()
s=pd.read_csv(f'{D}/USGSweatherData/1725/LVL2/gulkana1725_15min_LVL2_2024.csv')
s['t']=pd.to_datetime(s.UTC_time,format='%Y/%m/%d %H:%M')
s=s.set_index('t')[['site_temp','Precip_Disdrometer_Incremental','WindSpeed','ShortwaveIn']].apply(pd.to_numeric,errors='coerce')
sh=s.resample('1h',label='right',closed='right').agg({'site_temp':'mean','Precip_Disdrometer_Incremental':'sum','WindSpeed':'mean','ShortwaveIn':'mean'})
x=b.join(sh,how='inner').dropna(subset=['AirTC_Avg','site_temp'])
lapse={5:-7.07,6:-7.29,7:-7.85,8:-7.76,9:-7.25}
x['Toff']=x.site_temp+x.index.month.map(lapse).fillna(-7.5).values*1e-3*(1682-1725)
x['gap']=x.Toff-x.AirTC_Avg
x=x[(x.index.month>=6)&(x.index.month<=8)]
x['wet']=x.Precip_Disdrometer_Incremental>0.1
x['bin']=pd.cut(x.Toff,[-10,0,2,4,6,8,10,12,14,25])
print('JJA 2024 hours',len(x),'wet',x.wet.sum(), 'mean gap', round(x.gap.mean(),2))
print(x.groupby(['bin','wet'],observed=True).gap.agg(['mean','count']).round(2).unstack().to_string())
# linear fit gap vs Toff, dry only
for w in (False,True):
    y=x[x.wet==w]; c=np.polyfit(y.Toff,y.gap,1); print('wet' if w else 'dry','fit gap = %.3f*T %+.2f'%(c[0],c[1]), ' zero at %.1f C'%(-c[1]/c[0]))
c=np.polyfit(x.Toff,x.gap,1); print('all fit gap = %.3f*T %+.2f, zero at %.1f'%(c[0],c[1],-c[1]/c[0]))
# daytime vs night
x['day']=x.ShortwaveIn>50
print(x[~x.wet].groupby(['bin','day'],observed=True).gap.mean().round(2).unstack().to_string())
