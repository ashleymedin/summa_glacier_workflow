"""Held-out (WY2020-26) Wolverine water-temperature error at the gauge by month: bias, RMSE and share of the squared error, per rerun.

    run from the workflow root: ./scratch/2026-11-13/temp_error_months.py"""
import sys, os; sys.path.insert(0,'.')
import plot_setup_runs as p, numpy as np, pandas as pd
folder,_ = p.OBS["wolverine"]
to = p.series(os.path.join(p.WORKFLOW, folder, p.TEMP["wolverine"]), "t_obs").dropna()
for case,suf in (("wolverine_stream_delta","459_delta_drop"),("wolverine_stream_delta","459_aqT")):
    t = p.reach_temperature(case,"calibration_added_rerun",suf)
    d = pd.DataFrame({"s":t,"o":to}).dropna(); d=d[d.index>="2019-10-01"]; e=d.s-d.o
    print(f"\n{suf}: RMSE {np.sqrt((e**2).mean()):.2f} bias {e.mean():+.2f} n {len(e)}")
    g=e.groupby(d.index.month)
    m=pd.DataFrame({"n":g.size(),"bias":g.mean(),"rmse":np.sqrt(g.apply(lambda x:(x**2).mean())),"sd":g.std(),"obs":d.o.groupby(d.index.month).mean()})
    m["share_mse"]=(m.n*m.rmse**2)/(e**2).sum()
    m["bias_part"]=(m.n*m.bias**2)/(e**2).sum()
    print(m.round(2).to_string())
    # remove monthly bias -> rmse
    print("RMSE with each month's bias removed:", round(np.sqrt(((e-g.transform('mean'))**2).mean()),2))
    print("corr daily anomalies (30d highpass):", round(np.corrcoef(d.s-d.s.rolling(31,center=True,min_periods=5).mean(), d.o-d.o.rolling(31,center=True,min_periods=5).mean())[0,1],2) if len(d)>60 else None)
