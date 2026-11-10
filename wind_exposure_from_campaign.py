#!/usr/bin/env python3
"""windExposure from an on-ice campaign: glacier-surface wind as a fraction of the forcing's reference station wind.

The on-ice station and the reference station need not overlap in time.  They are linked through a bridge station
that overlaps both:

  ratio(month) = [U_ice / U_bridge]_campaign * [U_bridge / U_ref]_bridge-years

Two summaries are written.  The monthly ratio compares mean winds.  The heat-weighted ratio compares
sum(U * max(T_ice, 0)) instead, because over melting ice the sensible heat scales with wind times air temperature
above 0 degC.  It is the single windExposure that gives the campaign's sensible heat from the reference
station's wind.

The on-ice file is a Campbell logger table (TIMESTAMP, WS_ms_Avg, AirTC_Avg), as in Wilson et al.'s 2026
Gulkana Site B release.  Its clock is shifted by whichever of --lags correlates best with the bridge station.
Station files are the USGS benchmark-glacier LVL2 tables (UTC_time, WindSpeed).

    ./wind_exposure_from_campaign.py $O/campaigns/wilson_2024/1_meteo/gulkanaB_AWS_2024.csv \\
        "$O/stations/1725/LVL2/gulkana1725_hourly_LVL2_*.csv" "$O/stations/1480/LVL2/gulkana1480_hourly_LVL2_*.csv" \\
        $S/domain_Gulkana/forcing/wind_exposure_wilson2024.csv
"""

import argparse
import glob

import numpy as np
import pandas as pd


def read_station(pattern, years):
    """Hourly wind (m s-1) on UTC, from USGS LVL2 files for the given years."""
    files = [f for f in sorted(glob.glob(pattern)) if int(f.rsplit("_", 1)[1][:4]) in years]
    d = pd.concat(pd.read_csv(f, usecols=["UTC_time", "WindSpeed"]) for f in files)
    s = pd.Series(d.WindSpeed.astype(float).values, index=pd.to_datetime(d.UTC_time))
    return s[~s.index.duplicated()].resample("h").mean()


def read_campaign(path):
    """Hourly wind (m s-1) and air temperature (degC) on the logger clock."""
    d = pd.read_csv(path, skiprows=[1, 2], parse_dates=["TIMESTAMP"], date_format="%m/%d/%Y %H:%M")
    d = d.set_index("TIMESTAMP")[["WS_ms_Avg", "AirTC_Avg"]].apply(pd.to_numeric, errors="coerce")
    return d.resample("h").mean().rename(columns={"WS_ms_Avg": "u", "AirTC_Avg": "t"})


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("campaign", help="on-ice logger table")
    p.add_argument("bridge", help="glob of the bridge station's LVL2 files")
    p.add_argument("reference", help="glob of the forcing reference station's LVL2 files")
    p.add_argument("output", help="CSV of month, ratio, heat-weighted ratio")
    p.add_argument("--bridge-years", default="2012-2022", help="years, first-last, for bridge over reference")
    p.add_argument("--lags", default="0,8,9", help="hours added to the campaign clock to try for UTC")
    p.add_argument("--min-days", type=float, default=10.0, help="fewest campaign days for a month's ratio")
    a = p.parse_args()

    camp = read_campaign(a.campaign)
    years = set(camp.index.year)
    near = read_station(a.bridge, years)
    best = None
    for lag in (int(x) for x in a.lags.split(",")):
        c = camp.copy()
        c.index = c.index + pd.Timedelta(hours=lag)
        j = pd.concat([c, near.rename("ub")], axis=1, sort=True).dropna()
        r = j.u.corr(j.ub)
        print(f"campaign clock +{lag} h: correlation with bridge wind {r:.2f}")
        if best is None or r > best[0]:
            best = (r, lag, j)
    _, lag, j = best
    print(f"using +{lag} h, {len(j)} overlapping hours")

    y0, y1 = (int(y) for y in a.bridge_years.split("-"))
    yrs = set(range(y0, y1 + 1))
    k = pd.concat([read_station(a.bridge, yrs).rename("b"), read_station(a.reference, yrs).rename("r")],
                  axis=1, sort=True).dropna()
    link = k.b.groupby(k.index.month).mean() / k.r.groupby(k.index.month).mean()

    j["heat"] = j.u * j.t.clip(lower=0.0)
    j["heat_b"] = j.ub * j.t.clip(lower=0.0)
    rows, num, den = [], 0.0, 0.0
    for m, g in j.groupby(j.index.month):
        if len(g) < 24 * a.min_days or m not in link:
            continue
        plain = g.u.mean() / g.ub.mean() * link[m]
        hw = g.heat.sum() / g.heat_b.sum() * link[m] if g.heat_b.sum() > 0 else np.nan
        if np.isfinite(hw):
            num += g.heat.sum()
            den += g.heat_b.sum() / link[m]
        rows.append((m, plain, hw, link[m], len(g), g.t.mean()))
        print(f"month {m:2d}: {len(g):4d} h, mean T {g.t.mean():5.1f} C, bridge/ref {link[m]:.2f}, "
              f"ratio {plain:.2f}, heat-weighted {hw:.2f}")
    season = num / den
    print(f"heat-weighted over the campaign: {season:.3f}")
    with open(a.output, "w") as fh:
        fh.write("month,ratio,heat_weighted_ratio,bridge_over_reference,campaign_hours,mean_airtemp_C\n")
        for m, plain, hw, lk, n, t in rows:
            fh.write(f"{m},{plain:.4f},{hw:.4f},{lk:.4f},{n},{t:.2f}\n")
        fh.write(f"all,,{season:.4f},,,\n")
    print(f"written {a.output}")


if __name__ == "__main__":
    main()
