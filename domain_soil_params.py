#!/usr/bin/env python3
"""Write the soil parameters that differ by domain type into a case's trialParams.nc.

Each parameter below becomes a (dom, hru) variable of trialParams.nc, by the domain types of the case's
coldState.nc: debris-covered ice (glacDbr) takes the debris value, every other domain the value of
localParamInfo.txt, unless the parameter holds one value for all. The calibration's name@domainType
parameters then override these per domain type.

  debris   rock density of Conway and Rasmussen (2000); porosity of Fontrodona-Bach et al. (2025); water retention and conductivity of the sand class
           of Carsel and Parrish (1988), since supraglacial debris has no measured hydraulic properties;
           wilting and transpiration points only kept in order below field capacity, as no plants grow
  upland   with --upland, the texture class of SoilGrids 2.0 (soilgrids_texture.py) with its Carsel and Parrish (1988)
           retention and conductivity, wilting point, transpiration point and field capacity from its curve (at
           least 0.011 apart), and the SoilGrids sand fraction
  all      frac_clay 0.1 in every domain, so frac_sand alone sets the conductivity of the solids under
           thCondSoil = funcSoilWet, 2.92 W m-1 K-1 at frac_sand 0 to 8.21 at 0.9; frac_silt is the remainder
           of sand and clay, which SUMMA requires to add to one with them

    ./domain_soil_params.py runs/gulkana_added/summa_inputs --upland loam 0.49
"""

import argparse
import os

import netCDF4 as nc4
import numpy as np

UPLAND, GLAC_DBR = 1, 4  # domain types of upland ground and debris-covered ice in coldState.nc

DEBRIS = {"soil_dens_intr": 2700.,     # kg m-3
          "theta_res": 0.045,          # -
          "critSoilWilting": 0.05,     # -
          "critSoilTranspire": 0.08,   # -
          "fieldCapacity": 0.10,       # -
          "vGn_alpha": -14.5,          # m-1
          "vGn_n": 2.68,               # -
          "k_soil": 8.25e-5,           # m s-1
          "k_macropore": 8.25e-5,      # m s-1, no macropores
          "theta_mp": 0.15,            # -
          "theta_sat": 0.30}           # -, the porosity most used for supraglacial debris (Fontrodona-Bach et al. 2025)
ALL = {"frac_clay": 0.1}
UPLAND_CLASS = {"sandy loam": {"theta_res": 0.065, "theta_sat": 0.41, "vGn_alpha": -7.5, "vGn_n": 1.89, "k_soil": 1.23e-5,
                               "critSoilWilting": 0.076, "critSoilTranspire": 0.087, "fieldCapacity": 0.098},
                "loam": {"theta_res": 0.078, "theta_sat": 0.43, "vGn_alpha": -3.6, "vGn_n": 1.56, "k_soil": 2.89e-6,
                         "critSoilWilting": 0.088, "critSoilTranspire": 0.127, "fieldCapacity": 0.165}}


def defaults(path):
    """Default value of each parameter in localParamInfo.txt."""
    out = {}
    for line in open(path):
        if "|" in line and not line.lstrip().startswith(("!", "'")):
            parts = line.split("|")
            out[parts[0].strip()] = float(parts[1].strip().replace("d", "e").replace("D", "e"))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("settings", help="a case's summa_inputs folder")
    p.add_argument("--upland", nargs=2, metavar=("CLASS", "SAND"), help="upland texture class and sand fraction")
    a = p.parse_args()
    default = defaults(os.path.join(a.settings, "localParamInfo.txt"))
    every = dict(ALL, frac_silt=1.0 - default["frac_sand"] - ALL["frac_clay"])
    with nc4.Dataset(os.path.join(a.settings, "coldState.nc")) as c:
        dom_type = np.asarray(c["domType"][:], int)  # (hru, dom)
    dom_type = dom_type[0] if dom_type.ndim == 3 else dom_type  # a coldState with a time dimension
    with nc4.Dataset(os.path.join(a.settings, "attributes.nc")) as d:
        n_hru = len(d.dimensions["hru"])
    if dom_type.shape[0] != n_hru:
        raise SystemExit(f"coldState.nc has {dom_type.shape[0]} HRUs, attributes.nc {n_hru}")
    with nc4.Dataset(os.path.join(a.settings, "trialParams.nc"), "a") as t:
        if "dom" not in t.dimensions:
            t.createDimension("dom", dom_type.shape[1])
        upland = dict(UPLAND_CLASS[a.upland[0]], frac_sand=float(a.upland[1])) if a.upland else {}
        if upland:
            upland["frac_silt"] = 1.0 - upland["frac_sand"] - ALL["frac_clay"]
        for name in dict.fromkeys(list(DEBRIS) + list(every) + list(upland)):
            value = np.full(dom_type.T.shape, every.get(name, default[name]))
            if name in DEBRIS:
                value[dom_type.T == GLAC_DBR] = DEBRIS[name]
            if name in upland:
                value[dom_type.T == UPLAND] = upland[name]
            var = t[name] if name in t.variables else t.createVariable(name, "f8", ("dom", "hru"))
            var[:] = value
    print(f"{a.settings}/trialParams.nc: {len(DEBRIS)} debris parameters, frac_clay {every['frac_clay']} and frac_silt "
          f"{every['frac_silt']:.2f} everywhere, "
          f"{int((dom_type == GLAC_DBR).sum())} debris domains" + (f", upland {a.upland[0]} sand {a.upland[1]}" if upland else ""))


if __name__ == "__main__":
    main()
