from load import *
pd.set_option("display.width", 250)
names = {1: "upl", 2: "acc", 3: "cln", 4: "dbr"}
for tr in ["451", "411", "189"]:
    df, dom, idx = sim(tr)
    swe = dom["scalarSWE"]; ty = dom["domType"]; A = dom["DOMarea"]
    rows = []
    for y in range(2009, 2023):
        row = {"year": y}
        for h in range(3):
            for k in range(4):
                if ty[h, k] < 1: continue
                sel = (idx.year == y) & (idx.month >= 4) & (idx.month <= 10)
                s = swe[sel, h, k]; dd = idx[sel]
                if np.nanmean(A[sel, h, k]) < 1e5: row[f"H{h+1}{names[ty[h,k]]}"] = "-"; continue
                bare = np.where(s <= 0.01)[0]
                row[f"H{h+1}{names[ty[h,k]]}"] = dd[bare[0]].strftime("%m-%d") if len(bare) else "never"
        rows.append(row)
    print(f"\n== trial {tr}: first snow-free day (SWE<=0.01 kg m-2) Apr-Oct, '-' = domain under 0.1 km2")
    print(pd.DataFrame(rows).set_index("year").to_string())
    sel = (idx.month == 4) & (idx.day == 30)
    print("Apr-30 mean SWE (mm) by domain:\n", np.round(np.nanmean(swe[sel], 0)))
