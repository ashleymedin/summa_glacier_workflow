from load import *
import xarray as xr
W = pd.read_csv(f"{DATA}/observations/storage/mass_balance/Input_Gulkana_Daily_Weather.csv", parse_dates=["Date"], index_col="Date")
def forc(kind):
    p = f"{DATA}/forcing/SUMMA_input/" + ("station_corrected/" if kind == "corr" else "")
    fs = sorted(glob.glob(p + "*20[0-2][0-9]*.nc"))
    ds = xr.open_mfdataset(fs, combine="by_coords")[["pptrate", "airtemp"]].load()
    df = {}
    for h in range(3):
        df[f"P{h+1}"] = ds.pptrate.isel(hru=h).to_series() * 3600  # mm/h
        df[f"T{h+1}"] = ds.airtemp.isel(hru=h).to_series() - 273.15
    df = pd.DataFrame(df); df.index = df.index - pd.Timedelta("9h")  # to AKST days
    return df
if __name__ == "__main__":
    pd.set_option("display.width", 220)
    raw, cor = forc("raw"), forc("corr")
    raw.to_pickle("../forc_raw.pkl"); cor.to_pickle("../forc_corr.pkl")
    print(W.loc["2009":"2022"].describe().T)
