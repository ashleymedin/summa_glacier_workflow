#!/usr/bin/env python3
"""Fetch hourly weather from a NOAA ISD station or a USGS NWIS weather station into a domain's station folder.

Writes <stations>/<elevation>/LVL2/<name>_hourly_LVL2_<year>.csv, the layout of the USGS Benchmark Glacier station
records that correct_forcing_to_station.py reads, one row an hour, stamped at the hour's end (UTC_time):

  site_temp                    air temperature, degC
  RelHum                       relative humidity, %
  Barom                        station pressure, kPa
  WindSpeed                    wind speed, m s-1, at the sensor's own height (ISD: 10 m)
  Precip_Incremental           precipitation in the hour, mm

  isd   NOAA Integrated Surface Database (www.ncei.noaa.gov access API, no key), the routine hourly METARs (FM-15) only.
        Their precipitation is the hour to the report (at :53); a report without one, and without a PNO remark (sensor
        out), is a dry hour. Values failing ISD's quality check are dropped.
  nwis  USGS instantaneous values (waterservices.usgs.gov) of a weather station, hourly means; precipitation the rise over
        the hour of the cumulative gauge's running maximum, so its jitter is not counted, the hour of an emptying (a fall
        of more than RESET_MM) left out.

    ./acquire_station_weather.py isd 70381025309 juneau_airport 2004-10 2026-09 data/domain_LemonCreek/observations/stations
    ./acquire_station_weather.py nwis 582202134215701 lemoncreek1280 2026-07 2026-11 data/domain_LemonCreek/observations/stations
"""

import argparse
import csv
import io
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

ISD = "https://www.ncei.noaa.gov/access/services/data/v1"
NWIS = "https://waterservices.usgs.gov/nwis/iv/"
NWIS_SITE = "https://waterservices.usgs.gov/nwis/site/"
ISD_BAD = set("2367")  # ISD quality codes of suspect or erroneous values
COLUMNS = ("site_temp", "RelHum", "Barom", "WindSpeed", "Precip_Incremental")
FT = 0.3048
RESET_MM = 10.0  # a fall of the cumulative gauge larger than this is an emptying, mm


def relative_humidity(t, td):
    """Relative humidity (%) from temperature and dew point (degC), Bolton (1980)."""
    e = lambda x: np.exp(17.67 * x / (x + 243.5))
    return 100.0 * e(td) / e(t)


def isd_value(field, scale, missing):
    """An ISD 'value,quality' field as a float over scale, NaN where missing or failing quality."""
    if not isinstance(field, str) or "," not in field:
        return np.nan
    parts = field.split(",")
    value, quality = parts[0], parts[1]
    if value.lstrip("+-") == missing or quality in ISD_BAD:
        return np.nan
    return float(value) / scale


def isd_year(station, first, last):
    q = urllib.parse.urlencode({"dataset": "global-hourly", "stations": station, "format": "csv",
                                "startDate": first.strftime("%Y-%m-%dT%H:%M:%S"), "endDate": last.strftime("%Y-%m-%dT%H:%M:%S"),
                                "dataTypes": "REPORT_TYPE,TMP,DEW,WND,MA1,AA1,REM", "includeStationLocation": "true"})
    with urllib.request.urlopen(f"{ISD}?{q}", timeout=600) as r:
        return pd.read_csv(io.StringIO(r.read().decode()), dtype=str)


def from_isd(station, first, last):
    """Hourly table (UTC hour end index) of one ISD station, and its elevation (m)."""
    frames, elevation = [], None
    for year in range(first.year, last.year + 1):
        t0, t1 = max(first, datetime(year, 1, 1)), min(last, datetime(year, 12, 31, 23, 59))
        raw = isd_year(station, t0, t1)
        if raw.empty:
            continue
        elevation = float(raw["ELEVATION"].iloc[0])
        raw = raw[raw["REPORT_TYPE"].str.strip() == "FM-15"]
        out = pd.DataFrame(index=pd.to_datetime(raw["DATE"]).dt.ceil("h"))
        t = np.array([isd_value(v, 10.0, "9999") for v in raw["TMP"]])
        td = np.array([isd_value(v, 10.0, "9999") for v in raw["DEW"]])
        out["site_temp"] = t
        out["RelHum"] = relative_humidity(t, td)
        out["Barom"] = [isd_value(",".join(v.split(",")[2:4]), 100.0, "99999") if isinstance(v, str) else np.nan for v in raw["MA1"]]
        out["WindSpeed"] = [isd_value(",".join(v.split(",")[3:5]), 10.0, "9999") if isinstance(v, str) else np.nan for v in raw["WND"]]
        pr = []
        for aa, rem in zip(raw["AA1"], raw.get("REM", pd.Series([""] * len(raw)))):
            if isinstance(aa, str) and aa.split(",")[0] == "01":
                p = aa.split(",")
                pr.append(np.nan if p[1] == "9999" or p[3] in ISD_BAD else float(p[1]) / 10.0)
            else:
                pr.append(np.nan if isinstance(rem, str) and " PNO" in rem else 0.0)
        out["Precip_Incremental"] = pr
        frames.append(out[~out.index.duplicated(keep="last")])
        print(f"{station} {year}: {len(frames[-1])} hourly reports", flush=True)
    return pd.concat(frames), elevation


def from_nwis(site, first, last):
    """Hourly table (UTC hour end index) of a USGS weather station, and its elevation (m)."""
    with urllib.request.urlopen(f"{NWIS_SITE}?format=rdb&sites={site}&siteOutput=expanded") as r:
        rows = [l.split("\t") for l in r.read().decode().splitlines() if not l.startswith("#")]
    elevation = float(rows[2][rows[0].index("alt_va")]) * FT
    q = urllib.parse.urlencode({"format": "json", "sites": site, "startDT": first.strftime("%Y-%m-%d"),
                                "endDT": last.strftime("%Y-%m-%d")})
    with urllib.request.urlopen(f"{NWIS}?{q}", timeout=600) as r:
        series = json.load(r)["value"]["timeSeries"]
    convert = {"00020": ("site_temp", lambda x: x), "00021": ("site_temp", lambda x: (x - 32.0) / 1.8),
               "00052": ("RelHum", lambda x: x), "00025": ("Barom", lambda x: x * 0.1333224),  # mm Hg to kPa
               "00035": ("WindSpeed", lambda x: x * 0.44704), "82127": ("WindSpeed", lambda x: x * 0.3048),
               "72192": ("Precip_Incremental", lambda x: x * 25.4)}
    out = {}
    for s in series:
        code = s["variable"]["variableCode"][0]["value"]
        if code not in convert or not s["values"][0]["value"]:
            continue
        name, f = convert[code]
        v = pd.Series({pd.Timestamp(x["dateTime"]).tz_convert("UTC").tz_localize(None): f(float(x["value"]))
                       for x in s["values"][0]["value"]}).sort_index()
        if name == "Precip_Incremental":  # cumulative gauge: the rise of its running maximum, restarted at each emptying
            segment = (v.diff() < -RESET_MM).cumsum()
            envelope = v.groupby(segment).cummax()
            hourly = envelope.resample("h", label="right", closed="right").last()
            seg_hour = segment.resample("h", label="right", closed="right").last()
            rise = hourly.diff()
            out[name] = rise.where(seg_hour.diff() == 0)
        else:
            out[name] = v.resample("h", label="right", closed="right").mean()
    return pd.DataFrame(out), elevation


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("source", choices=("isd", "nwis"))
    p.add_argument("station", help="ISD station id (USAF+WBAN) or USGS site number")
    p.add_argument("name", help="file name prefix")
    p.add_argument("first", help="first month, YYYY-MM")
    p.add_argument("last", help="last month, YYYY-MM")
    p.add_argument("stations", help="the domain's station folder (observations/stations)")
    p.add_argument("--elevation", type=int, help="station folder name, m; default the source's elevation, rounded")
    a = p.parse_args()
    first = datetime.strptime(a.first, "%Y-%m")
    last = (datetime.strptime(a.last, "%Y-%m") + timedelta(days=32)).replace(day=1) - timedelta(minutes=1)
    table, elevation = (from_isd if a.source == "isd" else from_nwis)(a.station, first, last)
    table = table.reindex(columns=COLUMNS)
    z = a.elevation if a.elevation is not None else int(round(elevation))
    folder = os.path.join(a.stations, str(z), "LVL2")
    os.makedirs(folder, exist_ok=True)
    for year, part in table.groupby(table.index.year):
        path = os.path.join(folder, f"{a.name}_hourly_LVL2_{year}.csv")
        with open(path, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["UTC_time", "local_time", *COLUMNS])
            for t, r in part.iterrows():
                local = t.tz_localize(timezone.utc).tz_convert("America/Anchorage")
                w.writerow([t.strftime("%Y/%m/%d %H:%M"), local.strftime("%Y/%m/%d %H:%M"),
                            *("nan" if pd.isna(r[c]) else f"{r[c]:.3f}" for c in COLUMNS)])
    print(f"{a.name}: {len(table)} hours at {elevation:.0f} m into {folder}; "
          + ", ".join(f"{c} {int(table[c].notna().sum())}" for c in COLUMNS))


if __name__ == "__main__":
    main()
