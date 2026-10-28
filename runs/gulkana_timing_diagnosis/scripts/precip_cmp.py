from load import *
pd.set_option("display.width", 220)
W = pd.read_csv(f"{DATA}/observations/storage/mass_balance/Input_Gulkana_Daily_Weather.csv", parse_dates=["Date"], index_col="Date").sort_index()
st = {e: W[W.Elevation == e].Precip_TPG for e in [1480, 1725]}
st = pd.DataFrame(st); st = st[~st.index.duplicated()]
raw = pd.read_pickle("../forc_raw.pkl").resample("1D").sum(); cor = pd.read_pickle("../forc_corr.pkl").resample("1D").sum()
raw.index = raw.index.normalize(); cor.index = cor.index.normalize()
Traw = pd.read_pickle("../forc_raw.pkl")
both = st.dropna().index.intersection(raw.index)
d = pd.DataFrame({"st1480": st[1480], "st1725": st[1725], "rawH1": raw.P1, "rawH3": raw.P3, "rawH2": raw.P2, "corH1": cor.P1, "corH3": cor.P3, "corH2": cor.P2}).loc[both]
d = d.loc["2011":"2022"]
for lab, months in [("Jun-Sep", [6, 7, 8, 9]), ("Jul-Aug", [7, 8]), ("Oct-May", [10, 11, 12, 1, 2, 3, 4, 5])]:
    s = d[d.index.month.isin(months)]
    print(lab, "days", len(s), "totals mm/yr-equivalent per season:", (s.groupby(s.index.year).sum().mean()).round(0).to_dict())
s = d[d.index.month.isin([6, 7, 8, 9])]
print("\nJun-Sep by year (mm):"); print(s.groupby(s.index.year).agg(["sum"]).round(0).droplevel(1, axis=1).assign(n=s.groupby(s.index.year).size()).to_string())
# daily extremes
print("\nwettest station days (1725) Jun-Sep vs forcing:")
top = s.st1725.sort_values(ascending=False).head(12)
print(d.loc[top.index].round(1).sort_index().to_string())
# daily correlation and quantiles
print("\nJJAS daily correlation st1480 vs corH1:", round(s.st1480.corr(s.corH1), 2), " st1725 vs corH3:", round(s.st1725.corr(s.corH3), 2))
print("JJAS 99th pct daily mm: ", s.quantile(0.99).round(1).to_dict())
for ev in [("2018-08-02", "2018-08-07"), ("2018-08-12", "2018-08-16"), ("2018-08-20", "2018-08-24"), ("2013-08-18", "2013-08-21"), ("2022-07-16", "2022-07-19"), ("2016-07-22", "2016-07-25")]:
    e = pd.DataFrame({"st1480": st[1480], "st1725": st[1725], "rawH3": raw.P3, "corH3": cor.P3, "corH2": cor.P2, "corH1": cor.P1}).loc[ev[0]:ev[1]].sum().round(0)
    print(ev, e.to_dict())
# rain/snow partition: hourly air temp at HRU2/3 during event
T = pd.read_pickle("../forc_corr.pkl")
print("\nAug 2-6 2018 corrected hourly air temp at HRUs (mean, min):", T.loc["2018-08-02":"2018-08-06", ["T1", "T2", "T3"]].agg(["mean", "min"]).round(1).to_dict())
