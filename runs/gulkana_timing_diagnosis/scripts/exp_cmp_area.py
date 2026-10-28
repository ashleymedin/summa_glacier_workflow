import sys
import load_area as load
from load_area import *
EXP = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs/gulkana_timing_diagnosis/exp"
names = sys.argv[1:]
q = obs(); rows = {}; mb = {}
d = nc.Dataset(f"{DATA}/observations/calibration/gulkana_mass_balance_seasonal.nc")
b = np.array(d["time_bnds"][:]); v = np.array(d["mb_obs"][:]); t0 = pd.Timestamp("1950-01-01")
S = [(t0 + pd.Timedelta(minutes=int(x)), t0 + pd.Timedelta(minutes=int(y)), o) for (x, y), o in zip(b, v)]
S = [s for s in S if s[0] >= pd.Timestamp("2010-01-01") and s[1] <= pd.Timestamp("2014-12-31")]
for n in names:
    load.TRIALS[n] = f"{EXP}/{n}"
    df, dom, idx = sim(n)
    s = (df.averageRoutedRunoff * TOTAREA).loc["2010":"2014"]; o = q.reindex(s.index)
    mo = s.groupby(s.index.month).mean() / o.groupby(o.index.month).mean()
    A = np.nan_to_num(dom["DOMarea"]); ty = dom["domType"]
    dbr = np.where(ty[None] == 4, A, 0).sum((1, 2))[-1] / np.where(ty[None] >= 2, A, 0).sum((1, 2))[-1]
    cum = (df.basin__GlacierMassChange * 86400).cumsum()
    bal = [(cum[e - pd.Timedelta("1D")] - cum[st - pd.Timedelta("1D")], ob) for st, e, ob in S]
    win = np.mean([x for x, ob in bal if ob > 0]); summ = np.mean([x for x, ob in bal if ob < 0])
    kge_r = s.corr(o); alpha = s.std() / o.std(); beta = s.mean() / o.mean()
    rows[n] = {"all": beta, **{m: mo[m] for m in [5, 6, 7, 8, 9]}, "Jun/JA": mo[6] / ((mo[7] + mo[8]) / 2),
               "KGE": 1 - np.sqrt((kge_r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2), "r": kge_r,
               "Bw mm": win, "Bs mm": summ, "debris% end": dbr * 100}
obsw = np.mean([ob for _, _, ob in S if ob > 0]); obss = np.mean([ob for _, _, ob in S if ob < 0])
print(pd.DataFrame(rows).T.round(2).to_string()); print(f"obs Bw {obsw:.0f}  Bs {obss:.0f}")
