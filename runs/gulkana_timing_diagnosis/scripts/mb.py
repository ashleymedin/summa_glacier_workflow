from load import *
d = nc.Dataset(f"{DATA}/observations/calibration/gulkana_mass_balance_seasonal.nc")
b = np.array(d["time_bnds"][:]); v = np.array(d["mb_obs"][:]); t0 = pd.Timestamp("1950-01-01")
seas = pd.DataFrame({"start": [t0 + pd.Timedelta(minutes=int(x)) for x in b[:, 0]], "end": [t0 + pd.Timedelta(minutes=int(x)) for x in b[:, 1]], "obs": v})
seas = seas[(seas.start >= "2009-01-01") & (seas.end <= "2022-12-31")]
out = {}
for tr in TRIALS:
    df, dom, idx = sim(tr)
    cum = (df.basin__GlacierMassChange * 86400).cumsum()
    out[tr] = [cum[e - pd.Timedelta("1D")] - cum[s - pd.Timedelta("1D")] for s, e in zip(seas.start, seas.end)]
    # monthly glacier mass change climatology (mm w.e. per month)
    m = (df.basin__GlacierMassChange * 86400).loc["2009":"2022"]
    print(tr, "mean monthly glacier mass change (mm w.e.):", m.groupby(m.index.month).sum().div(14).round(0).to_dict())
for tr in TRIALS: seas[tr] = np.round(out[tr])
seas["season"] = np.where(seas.obs > 0, "winter", "summer")
pd.set_option("display.width", 200)
print(seas.to_string())
print(seas.groupby("season")[["obs"] + list(TRIALS)].mean().round(0))
