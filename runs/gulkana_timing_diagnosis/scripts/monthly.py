from load import *
q = obs()
pd.set_option("display.width", 220); pd.set_option("display.precision", 2)
for tr in TRIALS:
    df, dom, idx = sim(tr)
    A = np.nan_to_num(dom["DOMarea"]); ty = dom["domType"]
    m3 = lambda x: x * TOTAREA
    r = pd.DataFrame(index=idx)
    r["obs"] = q.reindex(idx)
    r["sim"] = m3(df.averageRoutedRunoff)
    r["glacRouted"] = m3(df.glacierRoutedRunoff)
    r["nonGlac"] = r.sim - r.glacRouted
    r["surfInst"] = m3(df.basin__SurfaceRunoff); r["aqInst"] = m3(df.basin__AquiferBaseflow)
    gm = np.nan_to_num(dom["scalarGlacierMelt"]) * A  # m3/s per domain
    swe = np.nan_to_num(dom["scalarSWE"])
    rain = np.nan_to_num(dom["scalarRainfall"]) * A / 1000.
    snow = np.nan_to_num(dom["scalarSnowfall"]) * A / 1000.
    glac = (ty >= 2)[None, :, :] & np.ones_like(A, bool)
    r["glacMelt_snow"] = np.where(glac & (swe > 0), gm, 0).sum((1, 2))
    r["glacMelt_bare"] = np.where(glac & (swe <= 0), gm, 0).sum((1, 2))
    for k, nm in [(2, "acc"), (3, "cln"), (4, "dbr")]:
        r["gm_" + nm] = np.where(ty[None] == k, gm, 0).sum((1, 2))
    r["rainGlac"] = np.where(glac, rain, 0).sum((1, 2)); r["rainUpl"] = np.where(ty[None] == 1, rain, 0).sum((1, 2))
    r["snowGlac"] = np.where(glac, snow, 0).sum((1, 2)); r["snowUpl"] = np.where(ty[None] == 1, snow, 0).sum((1, 2))
    swV = swe * A / 1000.
    r["sweUpl"] = np.where(ty[None] == 1, swV, 0).sum((1, 2)); r["sweGlac"] = np.where(glac, swV, 0).sum((1, 2))
    # upland snowmelt estimate (m3/s) = snowfall - dSWE/dt (ignores sublimation)
    r["uplMelt"] = (r.snowUpl - r.sweUpl.diff() / 86400.).clip(lower=0)
    r = r.loc["2009-01-01":"2022-12-31"].dropna(subset=["obs"])
    mo = r.groupby(r.index.month).mean()
    print(f"\n=== trial {tr}  (monthly mean m3/s over gauged days 2009-2022)")
    cols = ["obs", "sim", "glacRouted", "nonGlac", "surfInst", "aqInst", "glacMelt_snow", "glacMelt_bare", "gm_acc", "gm_cln", "gm_dbr", "rainGlac", "rainUpl", "snowGlac", "snowUpl", "uplMelt"]
    print(mo[cols].round(2).to_string())
    print("ratio sim/obs:", (mo.sim / mo.obs).round(2).to_dict())
    tot = r[cols].mean(); print("annual mean:", tot.round(3).to_dict())
    r.to_pickle(f"../r_{tr}.pkl")
