#!/usr/bin/env python3
"""glacierTempReduction from an on-ice campaign: glacier-surface air temperature above 0 degC as a fraction of the
station air's at the same elevation.

Over melting ice the air is cooled in proportion to its temperature above freezing.  The factor is the least-squares
slope through 0 degC of T_ice on T_off over the hours with T_off above 0 degC, T_off the station's air lapsed to the
campaign's elevation.  The mean gap by 2 K bin of T_off and the ratio of positive degrees,
sum(max(T_ice, 0)) / sum(max(T_off, 0)), are printed as checks on the form.

The on-ice file is a Campbell logger table (TIMESTAMP, WS_ms_Avg, AirTC_Avg), as in Wilson et al.'s 2026 Gulkana Site B
release; the station files are the USGS benchmark-glacier LVL2 tables (UTC_time, site_temp_USGS).

    ./air_cooling_from_campaign.py $O/campaigns/wilson_2024/1_meteo/gulkanaB_AWS_2024.csv 1682 \\
        "$O/stations/1725/LVL2/gulkana1725_hourly_LVL2_*.csv" 1725 $S/domain_Gulkana/forcing/air_cooling_wilson2024.csv
"""

import argparse
import glob

import numpy as np
import pandas as pd

from wind_exposure_from_campaign import read_campaign


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("campaign", help="on-ice logger table")
    p.add_argument("campaign_elev", type=float, help="its elevation (m)")
    p.add_argument("station", help="glob of the station's LVL2 files")
    p.add_argument("station_elev", type=float, help="its elevation (m)")
    p.add_argument("output", help="CSV of month, factor")
    p.add_argument("--lapse", type=float, default=7.3, help="air temperature decrease with height (K km-1)")
    p.add_argument("--min-days", type=float, default=10.0, help="fewest thawed days for a month's factor")
    p.add_argument("--lag", type=int, default=8, help="hours added to the campaign clock for UTC")
    a = p.parse_args()

    camp = read_campaign(a.campaign)
    camp.index = camp.index + pd.Timedelta(hours=a.lag)
    d = pd.concat(pd.read_csv(f, usecols=["UTC_time", "site_temp_USGS"]) for f in sorted(glob.glob(a.station))
                  if int(f.rsplit("_", 1)[1][:4]) in set(camp.index.year))
    s = pd.Series(d.site_temp_USGS.astype(float).values, index=pd.to_datetime(d.UTC_time))
    s = s[~s.index.duplicated()].resample("h").mean() + a.lapse * 1e-3 * (a.station_elev - a.campaign_elev)
    j = pd.concat([camp.t.rename("ice"), s.rename("off")], axis=1, sort=True).dropna()

    print("off-ice T (C)  hours  off minus ice (K)")
    for lo in range(-10, 16, 2):
        g = j[(j.off > lo) & (j.off <= lo + 2)]
        if len(g) >= 48:
            print(f"{lo:5d}..{lo + 2:<5d} {len(g):6d} {(g.off - g.ice).mean():7.2f}")
    print(f"ratio of positive degrees {j.ice.clip(lower=0).sum() / j.off.clip(lower=0).sum():.3f}")

    def slope(g):
        return (g.ice * g.off).sum() / (g.off ** 2).sum()

    t = j[j.off > 0]
    rows = [(m, slope(g), len(g)) for m, g in t.groupby(t.index.month) if len(g) >= 24 * a.min_days]
    for m, f, n in rows:
        print(f"month {m:2d}: {n:4d} thawed h, factor {f:.2f}")
    season = slope(t)
    print(f"over the campaign's {len(t)} thawed hours: {season:.3f}")
    with open(a.output, "w") as fh:
        fh.write("month,factor,thawed_hours\n")
        for m, f, n in rows:
            fh.write(f"{m},{f:.4f},{n}\n")
        fh.write(f"all,{season:.4f},{len(t)}\n")
    print(f"written {a.output}")


if __name__ == "__main__":
    main()
