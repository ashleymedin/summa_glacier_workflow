#!/usr/bin/env python3
"""Write the soil parameters that differ by domain type into a case's trialParams.nc.

Each parameter below becomes a (dom, hru) variable of trialParams.nc, by the domain types of the case's
coldState.nc: debris-covered ice (glacDbr) takes the debris value, every other domain the value of
localParamInfo.txt, unless the parameter holds one value for all. The calibration's name@domainType
parameters then override these per domain type.

  debris   rock density of Conway and Rasmussen (2000); water retention and conductivity of the sand class
           of Carsel and Parrish (1988), since supraglacial debris has no measured hydraulic properties;
           wilting and transpiration points only kept in order below field capacity, as no plants grow
  all      frac_clay 0.1 in every domain, so frac_sand alone sets the conductivity of the solids under
           thCondSoil = funcSoilWet, 2.92 W m-1 K-1 at frac_sand 0 to 8.27 at 1

    ./domain_soil_params.py runs/gulkana_corrected/summa_inputs
"""

import argparse
import os

import netCDF4 as nc4
import numpy as np

GLAC_DBR = 4  # domain type of debris-covered ice in coldState.nc

DEBRIS = {"soil_dens_intr": 2700.,     # kg m-3
          "theta_res": 0.045,          # -
          "critSoilWilting": 0.05,     # -
          "critSoilTranspire": 0.08,   # -
          "fieldCapacity": 0.10,       # -
          "vGn_alpha": -14.5,          # m-1
          "vGn_n": 2.68,               # -
          "k_soil": 8.25e-5,           # m s-1
          "k_macropore": 8.25e-5,      # m s-1, no macropores
          "theta_mp": 0.15}            # -
ALL = {"frac_clay": 0.1}


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
    a = p.parse_args()
    default = defaults(os.path.join(a.settings, "localParamInfo.txt"))
    with nc4.Dataset(os.path.join(a.settings, "coldState.nc")) as c:
        dom_type = np.asarray(c["domType"][0], int)  # (hru, dom)
    with nc4.Dataset(os.path.join(a.settings, "attributes.nc")) as d:
        n_hru = len(d.dimensions["hru"])
    if dom_type.shape[0] != n_hru:
        raise SystemExit(f"coldState.nc has {dom_type.shape[0]} HRUs, attributes.nc {n_hru}")
    with nc4.Dataset(os.path.join(a.settings, "trialParams.nc"), "a") as t:
        if "dom" not in t.dimensions:
            t.createDimension("dom", dom_type.shape[1])
        for name in list(DEBRIS) + list(ALL):
            value = np.full(dom_type.T.shape, ALL.get(name, default[name]))
            if name in DEBRIS:
                value[dom_type.T == GLAC_DBR] = DEBRIS[name]
            var = t[name] if name in t.variables else t.createVariable(name, "f8", ("dom", "hru"))
            var[:] = value
    print(f"{a.settings}/trialParams.nc: {len(DEBRIS)} debris parameters, frac_clay {ALL['frac_clay']} everywhere, "
          f"{int((dom_type == GLAC_DBR).sum())} debris domains")


if __name__ == "__main__":
    main()
