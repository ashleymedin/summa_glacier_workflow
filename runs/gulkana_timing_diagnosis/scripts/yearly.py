from load import *
pd.set_option("display.width", 220)
for tr in ["451", "189"]:
    r = pd.read_pickle(f"../r_{tr}.pkl")
    df, dom, idx = sim(tr)
    A = np.nan_to_num(dom["DOMarea"]); ty = dom["domType"]
    gm = np.nan_to_num(dom["scalarGlacierMelt"])
    rows = []
    for y in range(2009, 2023):
        s = r[r.index.year == y]
        jun = s[s.index.month == 6]; ja = s[s.index.month.isin([7, 8])]
        sel = (idx.year == y) & idx.month.isin([7, 8])
        row = {"year": y, "Jun s/o": jun.sim.sum() / jun.obs.sum(), "JA s/o": ja.sim.sum() / ja.obs.sum(), "yr s/o": s.sim.sum() / s.obs.sum()}
        for k, nm in [(2, "acc"), (3, "cln"), (4, "dbr")]:
            mask = (ty == k)[None] & sel[:, None, None]
            area = np.where(mask, A, 0).sum((1, 2)); flux = np.where(mask, gm * A, 0).sum((1, 2))
            row[f"A_{nm} km2"] = area[sel].mean() / 1e6
            row[f"JA melt {nm} mm/d"] = flux[sel].sum() / max(area[sel].sum(), 1) * 86400 * 1000
        rows.append(row)
    print(f"\n== trial {tr}"); print(pd.DataFrame(rows).set_index("year").round(2).to_string())
