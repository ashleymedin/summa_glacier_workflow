#!/usr/bin/env python3
"""Write a USGS Benchmark Glacier's yearly balance profiles as a SUMMA glacierMassBalFile.

Each balance year's point annual balances (Input_<Glacier>_Glaciological_Data.csv) are fitted with the USGS
profile: continuous piecewise-linear in elevation with one breakpoint, at the median of USGS's yearly ELAs, a
straight line when every stake lies to one side of it.  Each profile is then shifted at every elevation so it integrates over that year's USGS
hypsometry to the published, geodetically calibrated Ba (Output_<Glacier>_Glacier_Wide_solutions_calibrated.csv),
as the calibration is a shift of the glacier-wide balance.  The profile is written at every
--step metres over --range, so SUMMA's flow model interpolates it rather than extrapolating.

The shift is printed beside USGS's own calibration; the two differ by the profile method.

USGS elevations are WGS84 ellipsoid heights; --datum (m) is added to them to put the profile in the model DEM's
heights (Gulkana -16.1, Wolverine -14.0: the setup's surface less the survey DEM on the glacier).

    ./acquire_balance_profile.py data/domain_Gulkana/observations/storage/mass_balance gulkana_balance_profile.txt --datum -16.1
"""

import argparse
import os

import numpy as np
import pandas as pd


def fit_profile(z, b, zk):
    """The profile's knots (elevations, balances), least squares with its breakpoint at zk, a line if no stakes lie on one side."""
    z, b = np.asarray(z, float), np.asarray(b, float)
    ends = np.array([z.min(), z.max()])
    if len(z) < 3 or not (z.min() < zk < z.max()):
        return ends, np.polyval(np.polyfit(z, b, 1), ends)
    X = np.column_stack([np.ones_like(z), z - zk, np.maximum(z - zk, 0)])
    c, *_ = np.linalg.lstsq(X, b, rcond=None)
    knots = np.array([ends[0], zk, ends[1]])
    return knots, c[0] + c[1] * (knots - zk) + c[2] * np.maximum(knots - zk, 0)


def profile_at(knots_z, knots_b, z):
    """The profile at z, extended linearly past its end knots."""
    z = np.asarray(z, float)
    lo = knots_b[0] + (knots_b[1] - knots_b[0]) / (knots_z[1] - knots_z[0]) * (z - knots_z[0])
    hi = knots_b[-1] + (knots_b[-1] - knots_b[-2]) / (knots_z[-1] - knots_z[-2]) * (z - knots_z[-1])
    return np.where(z < knots_z[0], lo, np.where(z > knots_z[-1], hi, np.interp(z, knots_z, knots_b)))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("usgs_dir", help="folder with the USGS Input_* and Output_* tables of one glacier")
    p.add_argument("output", help="glacierMassBalFile to write")
    p.add_argument("--first", type=int, default=2000, help="first balance year written")
    p.add_argument("--range", type=float, nargs=2, default=(0, 3000), metavar=("LOW", "HIGH"),
                   help="elevations the profile is written over (m)")
    p.add_argument("--datum", type=float, default=0, help="added to the USGS ellipsoid heights (m)")
    p.add_argument("--step", type=float, default=25, help="elevation step of the written profile (m)")
    a = p.parse_args()

    name = os.path.basename(os.path.normpath(a.usgs_dir))
    table = lambda kind: pd.read_csv(os.path.join(a.usgs_dir, kind.format(name)))
    stakes = table("Input_{}_Glaciological_Data.csv").dropna(subset=["ba"])
    wide = table("Output_{}_Glacier_Wide_solutions_calibrated.csv").set_index("Year")
    aad = table("Input_{}_Area_Altitude_Distribution.csv").set_index("Year")
    bands = aad.columns.astype(float)
    zk = wide.ELA.median()
    grid = np.arange(a.range[0], a.range[1] + a.step / 2, a.step)

    lines = ["! USGS Benchmark Glacier balance profiles: piecewise linear in elevation, shifted to the calibrated Ba",
             f"! from {os.path.abspath(a.usgs_dir)}, USGS ellipsoid heights {a.datum:+.1f} m",
             "! year  debris(0 clean, 1 covered)  elevation (m)  annual balance (m w.e.)"]
    print(f"breakpoint {zk:.0f} m\n year  stakes     Ba  shift  calibration (m w.e.)")
    for year, s in stakes[stakes.Year >= a.first].groupby("Year"):
        if len(s) < 2 or year not in wide.index:
            continue
        kz, kb = fit_profile(s.elevation, s.ba, zk)
        area = aad.loc[year].to_numpy(float) if year in aad.index else aad.iloc[-1].to_numpy(float)
        shift = wide.loc[year, "Ba"] - np.sum(profile_at(kz, kb, bands) * area) / area.sum()
        print(f" {year}  {len(s):6d}  {wide.loc[year, 'Ba']:5.2f}  {shift:5.2f}  {wide.loc[year, 'Calibration']:11.2f}")
        lines += [f"{year} 0 {z:7.1f} {v:8.3f}" for z, v in zip(grid, profile_at(kz, kb, grid - a.datum) + shift)]
    with open(a.output, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
