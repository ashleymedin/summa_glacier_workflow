"""Refit correct_forcing_to_station.py for Wolverine and Gulkana into forcing/station_corrected_v3, with the setup step's arguments."""
import os, sys, subprocess
sys.path.insert(0, os.getcwd())  # run from the workflow root
from domain_config import load_config
for name in ("wolverine", "gulkana"):
    c = load_config(f"domains/{name}.yaml"); project = c["project_dir"]
    forcing = os.path.join(project, "forcing", "SUMMA_input")
    out = os.path.join(project, "forcing", "station_corrected_v3")
    args = [sys.executable, "correct_forcing_to_station.py", forcing, os.path.join(project, c["stations"]),
            os.path.join(project, "settings", "SUMMA", "attributes.nc"), out]
    if c.get("stakes"): args += ["--stakes", os.path.join(project, c["stakes"])]
    if c.get("gauge_shield"): args += ["--gauge-shield", c["gauge_shield"]]
    if c.get("gauge_rain"): args += ["--gauge-rain"]
    if c.get("fit_years"): args += ["--fit-years", *c["fit_years"]]
    if c.get("correct"): args += ["--correct", *c["correct"]]
    if c.get("wind_10m"): args += ["--wind-10m", *c["wind_10m"]]
    if c.get("precip_grad"):
        args += ["--precip-grad"]
        st = os.path.join(project, "settings", "SUMMA", "coldstate_glac.nc")
        if os.path.exists(st): args += ["--glacier-state", st]
    camp = c.get("spechum_campaign")
    if camp: args += ["--spechum-ratios", os.path.join(project, camp["ratios"])]
    print(" ".join(args), flush=True)
    with open(os.path.join(project, "forcing", "refit_v3.log"), "w") as log:
        subprocess.run(args, check=True, stdout=log, stderr=subprocess.STDOUT)
    print(name, "done", flush=True)
