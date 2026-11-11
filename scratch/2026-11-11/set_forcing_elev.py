#!/usr/bin/env python3
"""Add forcingElev to the built general cases' attributes.nc, as build_cases.py now writes it for raw-forcing cases.

    python scratch/2026-11-11/set_forcing_elev.py wolverine_general gulkana_general
"""
import os
import sys

import netCDF4 as nc4

WF = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, WF)
from build_cases import set_forcing_elev  # noqa: E402
from domain_config import load_config  # noqa: E402

for case in sys.argv[1:]:
    attributes = os.path.join(WF, "runs", case, "summa_inputs", "attributes.nc")
    set_forcing_elev(attributes, load_config(os.path.join(WF, "domains", f"{case}.yaml")))
    with nc4.Dataset(attributes) as a:
        print(case, "elevation", a["elevation"][:].round(0), "forcingElev", a["forcingElev"][:].round(0))
