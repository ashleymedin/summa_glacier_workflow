#!/usr/bin/env python3
"""Does CHELSA's 1 km monthly wind climatology carry the stations' wind? CHELSA sfcWind at each wind station's pixel
against the station-over-ERA5 ratio of the station correction (corrections.csv) and the ERA5 wind it was taken against.

    python scratch/2026-11-11/lapse/chelsa_wind.py
"""
import csv
import glob
import os

import numpy as np
import rasterio
from netCDF4 import Dataset, num2date

WF = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
URL = "/vsicurl/https://os.zhdk.cloud.switch.ch/chelsav2/GLOBAL/climatologies/1981-2010/sfcWind/CHELSA_sfcWind_{m:02d}_1981-2010_V.2.1.tif"
STATIONS = {"Wolverine": (990, 60.381923, -148.939662), "Gulkana": (1480, 63.261373, -145.41021)}


def main():
    for dom, (z, la, lo) in STATIONS.items():
        rows = {r[0]: r[1:] for r in csv.reader(open(os.path.join(WF, "data", f"domain_{dom}", "forcing", "SUMMA_input",
                                                                    "station_corrected", "corrections.csv"))) if r}
        ratio = np.array([float(x) for x in rows["windspd_ratio"][:12]])
        hz = np.array([float(r[1]) for k, r in rows.items() if k.isdigit()])
        j = int(np.argmin(abs(hz - z)))  # the HRU nearest the station's height, whose ERA5 wind the ratio was taken against
        era = np.zeros(12)
        n = np.zeros(12)
        for f in sorted(glob.glob(os.path.join(WF, "data", f"domain_{dom}", "forcing", "SUMMA_input", "*_20[01]*.nc"))):
            with Dataset(f) as d:
                m = num2date(d["time"][0], d["time"].units).month
                era[m - 1] += float(np.mean(d["windspd"][:, j])); n[m - 1] += 1
        era /= n
        chelsa = []
        for m in range(1, 13):
            with rasterio.open(URL.format(m=m)) as r:
                row, col = r.index(lo, la)
                v = r.read(1, window=((row, row + 1), (col, col + 1)))[0, 0]
                chelsa.append(v * r.scales[0] + r.offsets[0])
        chelsa = np.array(chelsa)
        print(f"{dom} station {z} m (HRU {j + 1}):")
        print("  ERA5 m/s     " + " ".join(f"{x:5.2f}" for x in era))
        print("  station m/s  " + " ".join(f"{x:5.2f}" for x in era * ratio))
        print("  CHELSA m/s   " + " ".join(f"{x:5.2f}" for x in chelsa))
        print("  station/ERA5 " + " ".join(f"{x:5.2f}" for x in ratio))
        print("  CHELSA/ERA5  " + " ".join(f"{x:5.2f}" for x in chelsa / era))


if __name__ == "__main__":
    main()
