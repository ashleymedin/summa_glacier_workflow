from load import *
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
OUT = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs/gulkana_timing_diagnosis"
C = {"obs": "#0b0b0b", "s1": "#2a78d6", "s2": "#eb6834", "s3": "#1baf7a", "s4": "#eda100", "grid": "#e4e3df", "muted": "#52514e"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": C["muted"],
                     "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.6, "lines.linewidth": 2})
AF = 30.77 / 26.62
r = pd.read_pickle(f"{OUT}/r_451.pkl"); mo = r.groupby(r.index.month).mean()
fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
m = mo.index
a = ax[0]
a.plot(m, mo.obs, color=C["obs"], label="gauge")
a.plot(m, mo.sim * AF, color=C["s1"], label="sim x area fix (30.77/26.62)")
a.stackplot(m, mo.glacRouted * AF, mo.nonGlac * AF, colors=[C["s1"], C["s3"]], alpha=0.25, labels=["glacier routed", "upland (routed)"])
a.set_xticks(range(1, 13)); a.set_ylabel("m$^3$ s$^{-1}$"); a.set_title("(a) Trial 451, monthly means over gauged days 2009-2022", loc="left")
a.legend(frameon=False, fontsize=8)
b = ax[1]
w = 0.2
b.bar(m - 1.5 * w, mo.glacMelt_snow * AF, w, color=C["s1"], label="glacier, snow-covered domains")
b.bar(m - 0.5 * w, mo.glacMelt_bare * AF, w, color=C["s2"], label="glacier, bare domains")
b.bar(m + 0.5 * w, mo.uplMelt * AF, w, color=C["s3"], label="upland snowmelt (est.)")
b.bar(m + 1.5 * w, (mo.rainGlac + mo.rainUpl) * AF, w, color=C["s4"], label="rain, whole basin")
b.plot(m, (mo.obs - mo.sim * AF).clip(lower=0), color=C["obs"], ls="--", lw=1.5, label="gauge minus sim (area-fixed)")
b.set_xticks(range(1, 13)); b.set_title("(b) Unrouted inputs to runoff, trial 451", loc="left"); b.legend(frameon=False, fontsize=7.5)
fig.tight_layout(); fig.savefig(f"{OUT}/monthly_sources_451.png", dpi=150)

# Aug 2018 event
W = pd.read_csv(f"{DATA}/observations/storage/mass_balance/Input_Gulkana_Daily_Weather.csv", parse_dates=["Date"], index_col="Date").sort_index()
cor = pd.read_pickle(f"{OUT}/forc_corr.pkl").resample("1D").sum(); cor.index = cor.index.normalize()
s, e = "2018-07-25", "2018-08-31"
fig, ax = plt.subplots(2, 1, figsize=(9, 5), sharex=True)
for el, col in [(1480, C["s2"]), (1725, C["s4"])]:
    x = W[W.Elevation == el].Precip_TPG.loc[s:e]; ax[0].plot(x.index, x, color=col, label=f"station {el} m")
ax[0].plot(cor.loc[s:e].index, cor.P3.loc[s:e], color=C["s1"], label="forcing HRU 3 (1787 m), raw = corrected in summer")
ax[0].set_ylabel("mm d$^{-1}$"); ax[0].legend(frameon=False, fontsize=8); ax[0].set_title("(a) Daily precipitation", loc="left")
for tr, col in [("451", C["s1"]), ("189", C["s3"])]:
    rr = pd.read_pickle(f"{OUT}/r_{tr}.pkl").loc[s:e]; ax[1].plot(rr.index, rr.sim * AF, color=col, label=f"sim {tr} x area fix")
ax[1].plot(r.loc[s:e].index, r.obs.loc[s:e], color=C["obs"], label="gauge")
ax[1].set_ylabel("m$^3$ s$^{-1}$"); ax[1].legend(frameon=False, fontsize=8); ax[1].set_title("(b) Discharge, USGS 15478040", loc="left")
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(f"{OUT}/aug2018_event.png", dpi=150)

# debris area growth
fig, a = plt.subplots(figsize=(6, 3))
for tr, col in [("451", C["s1"]), ("411", C["s2"]), ("189", C["s3"])]:
    df, dom, idx = sim(tr); A = np.nan_to_num(dom["DOMarea"]); ty = dom["domType"]
    dbr = np.where(ty[None] == 4, A, 0).sum((1, 2)) / 1e6; gl = np.where(ty[None] >= 2, A, 0).sum((1, 2)) / 1e6
    a.plot(idx, dbr / gl * 100, color=col, label=f"trial {tr}")
a.axhline(1.76 / 17.67 * 100, color=C["muted"], lw=1, ls=":"); a.text(idx[1500], 5, "mapped debris (start)", color=C["muted"], fontsize=8)
a.set_ylabel("debris domain, % of glacier"); a.legend(frameon=False, fontsize=8); a.set_title("Debris-domain share of the model glacier", loc="left")
fig.tight_layout(); fig.savefig(f"{OUT}/debris_area.png", dpi=150)
print("ok")
