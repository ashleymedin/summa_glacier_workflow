#!/usr/bin/env python3
"""Calibrate a full glacier run, then score its Pareto front on the held-out years.

  calibrate  NSGA-II over the case's calibrate years of cases.yaml after a spin-up over the year before, on
             discharge and the glacier-wide seasonal mass balance, in <case>/<name> (default calibration);
             --search stream adds the water temperature where the case has it
  evaluate   each front member rerun from the calibration start to the end of its evaluate years with its
             parameters pinned (both bounds set to its value) and scored over the evaluate years, in
             <case>/<name>_evaluation/sample_<n>; a routed Wolverine run adds its water temperature, which is only
             recorded from 2016; writes <case>/<name>_evaluation/evaluation.csv

A run is routed through mizuRoute, and scored at its reach, when its folder holds a topology.nc (a stream case
of cases.yaml); otherwise discharge is the GRU's own.

The spin-up runs at the default parameters for every trial, in calibration and evaluation alike, as the
calibration driver does. Needs summa's MPI calibration executable (bin/summa_sundials_mizuroute_opt.exe).

    ./calibrate.py calibrate gulkana_added --search domain --population 32 --generations 15 --ranks 4
    ./calibrate.py evaluate gulkana_added --ranks 2 --jobs 4
    ./calibrate.py calibrate gulkana_general --population 20 --generations 10 --ranks 5 --name pilot
"""

import argparse
import csv
import datetime
import glob
import os
import shutil
import subprocess
import tomllib
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import netCDF4 as nc4
import numpy as np
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
GLACIER = os.path.dirname(HERE)
SUMMA_DIR = os.path.abspath(os.environ.get("SUMMA_DIR", os.path.join(GLACIER, "..", "summa")))

# paper1: one value of each soil parameter for every domain; the glacier wind and cooling stay at Site B's against the case's
# forcing (build_cases.set_glacier_factors), which trade off with the snow albedo (scratch/2026-11-17/twin2), and the rain--snow
# split at SUMMA's default (273.16 K, 2 K), which trades off with the snowfall multipliers (scratch/2026-11-16/twin.py); the upland canopy is fixed at Noah-MP's mixed tundra
# (2.0 and 0.2 m, LAI 1.8)
PAPER1 = ["k_soil", "theta_sat", "aquiferBaseflowExp", "aquiferBaseflowRate", "qSurfScale", "frozenPrecipMultip",
          "Fcapil", "windReductionParam", "vGn_n", "routingGammaScale", "routingGammaShape",
          "glacStor_kIce", "glacStor_kSnow", "glacStor_kFirn", "k_snow",
          "mw_exp", "albedoDecayRate", "albedoMax", "k_macropore", "thCond_soil"]
PAPER1_CHAIN = ["theta_res", "critSoilWilting", "critSoilTranspire", "fieldCapacity", "theta_sat"]

# domain: the upland soil and the debris searched apart, the debris's other soil values fixed in trialParams.nc and its englacial
# concentration in basinParamInfo.txt (0.44 kg m-3, Anderson et al. (2021) at Kennicott), which the glacier-wide balances cannot constrain;
# the snowfall multiplier apart on the upland and the glaciers, where it takes in blown and avalanched snow;
# frac_sand (with frac_clay fixed) sets the conductivity of the solids, which thCondSoil = funcSoilWet uses; frac_silt is their remainder.
# Fixed in localParamInfo.txt, as the calibrations cannot identify them (scratch/2026-11-23/fix3): the snow's capillary retention at
# 0.07 of pore volume (Colbeck 1974; Coleou and Lesaffre 1998), the canopy wind reduction at SUMMA's 0.28 (little canopy) and the
# debris porosity at 0.3 (Fontrodona-Bach et al. 2025)
DOMAIN = [p for p in PAPER1 if p not in ("k_soil", "theta_sat", "vGn_n", "k_macropore", "thCond_soil", "frozenPrecipMultip",
                                         "Fcapil", "windReductionParam")] + \
         ["k_soil@upland", "k_macropore@upland", "theta_sat@upland", "vGn_n@upland", "frac_sand@upland",
          "frac_sand@glacDbr", "frozenPrecipMultip@upland", "frozenPrecipMultip@glacier"]
DOMAIN_CHAIN = ["theta_res@upland", "critSoilWilting@upland", "critSoilTranspire@upland", "fieldCapacity@upland",
                "theta_sat@upland"]

# stream: the domain search with the wetland's outflow time constant held, its mean depth filled to the outlet and its cold-air
# pooling; its wind and air are the HRU's, its area is the imagery's, its snowfall and lapse the HRU's, the reach width mizuRoute's. --pin-trial holds the
# rest at a glacier calibration's trial
STREAM_ONLY = ["wetlandStorageK", "wetlandMinDepth", "wetlandPoolCooling",
               "albedoFrznWatVisible@wetland", "albedoFrznWatNearIR@wetland"]
STREAM = DOMAIN + STREAM_ONLY

SEARCHES = {
    "paper1": {"params": PAPER1, "logs": ["k_soil", "aquiferBaseflowRate", "k_macropore"],
               "chains": [(PAPER1_CHAIN, 0.025)], "bounds": {}},
    "domain": {"params": DOMAIN, "logs": ["k_soil@upland", "aquiferBaseflowRate", "k_macropore@upland"],
               "chains": [(DOMAIN_CHAIN, 0.025)],
               "bounds": {"theta_sat@upland": (0.35, 0.65),     # mineral soil
                          "frac_sand@upland": (0.0, 0.9),       # up to what the fixed clay (0.1) leaves
                          "frac_sand@glacDbr": (0.0, 0.9),
                          "albedoDecayRate": (0.2e6, 5.0e6),    # s; summer snow at Gulkana Site B decays in 2-6 days (Wilson et al. 2026)
                          "frozenPrecipMultip": (0.2, 5.0),
                          "frozenPrecipMultip@upland": (0.2, 5.0),       # ERA5 with CHELSA is 0.6 of the gauges at Gulkana, up to twice them at Wolverine
                          "frozenPrecipMultip@glacier": (0.2, 5.0)}},  # with blown and avalanched snow, Kneib et al. (2025)
}
SEARCHES["domain_soil"] = dict(SEARCHES["domain"], soil=True)  # the upland soil searched even on a case with a SoilGrids class
SEARCHES["domain_gru"] = dict(SEARCHES["domain"])  # with the glacier albedo by GRU (cases.yaml albedo_gru)
SEARCHES["stream"] = dict(SEARCHES["domain"], params=STREAM,
                          bounds=dict(SEARCHES["domain"]["bounds"],
                                      wetlandStorageK=(600.0, 600.0),    # s; held at SUMMA's floor, the fit flat below about 1000 s (stream_cheap_r9)
                                      wetlandPoolCooling=(0.0, 8.0),     # K of cold-air pooling while the upland holds snow
                                      **{"albedoFrznWatVisible@wetland": (0.7, 0.7),   # lake ice in spring, held (Sentinel-2 openings, 23 Nov)
                                         "albedoFrznWatNearIR@wetland": (0.5, 0.5)}))

# fixed on the station-corrected cases, where the stakes set the glacier domains' snowfall through frozenPrecipMultip in
# trialParams.nc (build_cases.set_glacier_snowfall); raw ERA5 searches it. The upland snowfall is searched on both, as the
# gauges miss the snow the wind takes off their orifice and drifts onto the upland
STATION_FIXED = ["frozenPrecipMultip", "frozenPrecipMultip@glacier"]

# fixed on a case with upland_soil in cases.yaml, its SoilGrids class (domain_soil_params.py); the macropores stay searched
UPLAND_SOIL = ["k_soil@upland", "theta_sat@upland", "vGn_n@upland", "frac_sand@upland"] + DOMAIN_CHAIN

# searched on raw ERA5 as multipliers of trialParams.nc's values, the glacier snowfall's elevation shape
# (build_cases.glacier_snow_shape), so one number scales the snowfall of every glacier domain
RAW_MULTIPLIERS = ["frozenPrecipMultip@glacier"]


NETCDF = Lock()  # netCDF/HDF5 is not thread-safe; threads that run models in parallel take turns at the files

def case_spec(case):
    """A run's entry in cases.yaml, with the keys a stream case inherits from its parent (build_cases.INHERITED)."""
    with open(os.path.join(GLACIER, "cases.yaml")) as f:
        cases = yaml.safe_load(f)
    spec = cases[case]
    for key in ("upland_soil", "air_cooling", "firn_viscosity", "cal_obs", "eval_obs", "upland_snow_grad"):
        if "parent" in spec and key in cases[spec["parent"]]:
            spec.setdefault(key, cases[spec["parent"]][key])
    return spec


def periods(case):
    """(calibration start, calibration end, evaluation start, evaluation end) of a run in cases.yaml, YYYY-MM-DD."""
    c = case_spec(case)
    return tuple(str(d) for d in c["calibrate"] + c["evaluate"])


def no_ice_temp(case):
    """A case with the water temperature and no glacier target: every search scores the temperature on it."""
    targets = case_spec(case).get("targets", [])
    return "stream_temperature" in targets and not {"mass_balance", "wgms_amce", "grace"} & set(targets)


def search_for(case, name):
    """The named search, without the STATION_FIXED parameters on a station-corrected case, and without the debris
    ones on a case with no debris-covered domain (domType 4), the glacier ones on a case with no glacier, where they select nothing,
    or the wetland ones on a case with no wetland domain (domType 5)."""
    search = dict(SEARCHES[name])
    if case_spec(case).get("forcing") == "station_corrected":
        search["params"] = [q for q in search["params"] if q not in STATION_FIXED]
    else:
        search["multipliers"] = [q for q in RAW_MULTIPLIERS if q in search["params"]]
    if case_spec(case).get("upland_soil") and not search.get("soil"):
        search["params"] = [q for q in search["params"] if q not in UPLAND_SOIL]
        search["logs"] = [q for q in search["logs"] if q not in UPLAND_SOIL]
        search["chains"] = [(c, g) for c, g in search["chains"] if not set(c) & set(UPLAND_SOIL)]
    if case_spec(case).get("glacier_k"):  # trialParams.nc's k of each GRU, by glacier length, under one multiplier of each
        ks = ["glacStor_kIce", "glacStor_kSnow", "glacStor_kFirn"]
        search["multipliers"] = search.get("multipliers", []) + ks
        search["bounds"] = dict(search["bounds"], **{k: (0.334, 2.0) for k in ks[:1]}, glacStor_kSnow=(0.334, 1.66), glacStor_kFirn=(0.334, 1.73))
    if case_spec(case).get("upland_snow_grad"):  # trialParams.nc's upland snowfall rise with elevation, under one multiplier
        search["multipliers"] = search.get("multipliers", []) + ["frozenPrecipMultip@upland"]
        search["bounds"] = dict(search["bounds"], **{"frozenPrecipMultip@upland": tuple(case_spec(case)["upland_snow_grad"])})
    snow = [f"frozenPrecipMultip@glacier_gru{g}" for g in case_spec(case).get("gru_snow", [])]  # a multiplier of the glacier snowfall of these GRUs
    if snow:  # (the SUMMA of branch gru-select)
        search["multipliers"] = search.get("multipliers", []) + snow
        search["params"] = search["params"] + snow
        search["bounds"] = dict(search["bounds"], **{q: (0.4, 1.5) for q in snow})
    if name == "domain_gru":  # the snow albedo of each GRU's glaciers apart, and of the upland
        for q in ("albedoDecayRate", "albedoMax"):
            apart = [f"{q}@upland"] + [f"{q}@glacier_gru{g}" for g in case_spec(case)["albedo_gru"]]
            search["params"] = [n for n in search["params"] if n != q] + apart
            if q in search["bounds"]:
                search["bounds"] = dict(search["bounds"], **{n: search["bounds"][q] for n in apart})
    with nc4.Dataset(os.path.join(HERE, case, "summa_inputs", "coldState.nc")) as d:
        types = np.asarray(d["domType"][:])
    if not np.any(types == 4):
        search["params"] = [q for q in search["params"] if not q.endswith("@glacDbr")]
    if not np.any(np.isin(types, (2, 3, 4))):  # a basin without glaciers
        search["params"] = [q for q in search["params"] if not q.endswith("@glacier") and not q.startswith("glacStor_")]
        search["multipliers"] = [q for q in search.get("multipliers", []) if not q.endswith("@glacier")]
    if not np.any(types == 5):
        search["params"] = [q for q in search["params"] if not q.startswith("wetland")]
        search["logs"] = [q for q in search["logs"] if not q.startswith("wetland")]
    elif not isinstance(case_spec(case).get("wetland", {}).get("outlet_depth", []), list):
        search["params"] = [q for q in search["params"] if q != "wetlandMinDepth"]  # fixed from the bed
    return search


CASES = {  # domain, observation files and gauge of each run
    "wolverine": {"obs": "data/domain_Wolverine/observations/calibration", "flow": "USGS_15236900_daily_flow.nc",
                  "mb": "wolverine_mass_balance_seasonal.nc", "temp": "USGS_15236900_daily_temperature.nc",
                  "grace": "wolverine_grace_tws.nc", "wgms_amce": "wolverine_wgms_amce.nc"},
    "gulkana": {"obs": "data/domain_Gulkana/observations/calibration", "flow": "USGS_15478040_daily_flow.nc",
                "mb": "gulkana_mass_balance_seasonal.nc", "temp": "USGS_15478040_daily_temperature.nc", "grace": "gulkana_grace_tws.nc", "wgms_amce": "gulkana_wgms_amce.nc"},
    "lemon": {"obs": "data/domain_LemonCreek/observations/calibration", "flow": "USGS_15052000_daily_flow.nc",
              "mb": "lemoncreek_mass_balance_seasonal.nc", "temp": "USGS_15052000_daily_temperature.nc",
              "grace": "lemoncreek_grace_tws.nc", "wgms_amce": "lemoncreek_wgms_amce.nc"},
    "slate": {"obs": "data/domain_SlateCreek/observations/calibration", "flow": "USGS_15564879_daily_flow.nc",
              "temp": "USGS_15564879_daily_temperature.nc", "grace": "slatecreek_grace_tws.nc"},
}


def search_of(calibration):
    """The search a calibration ran (parameters, log transforms, ordered chains, bounds), from its config.toml."""
    with open(os.path.join(calibration, "config.toml"), "rb") as f:
        t = tomllib.load(f)
    cal = t["calibration"]
    chains = [(o["parameters"], o["gap_fraction"]) for o in t.get("parameter_dependencies", {}).get("ordered", [])]
    if "param_list" in cal:  # a calibration run before the [calibration.parameters] format
        return {"params": cal["param_list"], "logs": list(cal.get("parameter_transformations", {})), "chains": chains,
                "bounds": {k: tuple(v) for k, v in cal.get("parameter_bounds", {}).items()}}
    multipliers = cal.get("spatial_multipliers", {})
    entries = dict(cal["parameters"], **multipliers)
    return {"params": list(entries), "logs": [k for k, v in entries.items() if v.get("transformation") == "log"],
            "chains": chains, "bounds": {k: (v["lower"], v["upper"]) for k, v in entries.items() if "lower" in v},
            "multipliers": list(multipliers)}


def has_obs(path, var, start, end):
    """Whether an observation file holds any value from start to end (YYYY-MM-DD)."""
    with nc4.Dataset(path) as d:
        t = nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False, only_use_python_datetimes=True)
        v = np.ma.filled(d[var][:].astype(float), np.nan).squeeze()
    day = np.array([x.strftime("%Y-%m-%d") for x in t])
    return bool(np.any((day >= start) & (day <= end) & np.isfinite(v)))


def config_text(case, run_dir, settings, work, start, end, score_start, score_end, algorithm, n_samples,
                population, temperature, search=SEARCHES["paper1"], pinned=None, targets=None, seed=42, geodetic_base=None):
    """The calibration driver's TOML for one search or one pinned trial; every pinned value is held by equal
    bounds, which override the search's own (pin_settings also pins the plain names in the parameter files).
    Every member of an ordered chain is searched."""
    bounds = dict(search["bounds"])
    bounds.update({k: (v, v) for k, v in (pinned or {}).items()})
    c = CASES[case.split("_")[0]]
    c = {**c, **(case_spec(case).get("eval_obs" if algorithm == "dds" else "cal_obs") or {})}  # observation files masked to the years each is scored on
    targets = targets or case_spec(case).get("targets", ["discharge", "mass_balance", "stream_temperature"])
    reach, balance_gru = case_spec(case).get("gauge_reach", 1), case_spec(case).get("balance_gru", 1)
    routed = os.path.exists(os.path.join(run_dir, "topology.nc"))
    forcing_file = os.path.join(run_dir, "forcing_path.txt")
    forcing = open(forcing_file).read().strip() if os.path.exists(forcing_file) else os.path.join(run_dir, "forcing") + "/"
    obs = os.path.join(GLACIER, c["obs"]) + "/"
    n_gru = 1
    with nc4.Dataset(os.path.join(settings, "attributes.nc")) as d:
        n_gru = len(d.dimensions["gru"])
    gauge = f'spatial_unit = "reach"\nspatial_id   = {reach}' if routed else 'spatial_unit = "gru"\nspatial_id   = 1' if n_gru == 1 else 'spatial_unit = "domain"'  # every GRU's runoff
    lines = [f'''# generated by calibrate.py

[simulation]

case_name = "{case}"

# the driver spins up over the year before start_time, from the cold state, at the default parameters
start_time = "{start} 00:00"
end_time   = "{end} 23:00"
time_zone  = "utcTime"

use_mizuroute    = {"true" if routed else "false"}
stream_temp      = {"true" if temperature and routed and "temp" in c and "stream_temperature" in targets else "false"}
write_timeseries = false

work_path = "{work}/output"


[summa_files]

settings_path = "{settings}/"
forcing_path  = "{forcing}"
state_path    = "{work}/state/"
output_path   = "{work}/output/"

init_condition = "coldState.nc"
attributes     = "attributes.nc"
forcing_list   = "forcingFileList.txt"

decisions        = "modelDecisions.txt"
output_control   = "outputControl.txt"
trial_params     = "trialParams.nc"
local_parameters = "localParamInfo.txt"
basin_parameters = "basinParamInfo.txt"

vegetation_table = "TBL_VEGPARM.TBL"
soil_table       = "TBL_SOILPARM.TBL"
general_table    = "TBL_GENPARM.TBL"
noahmp_table     = "TBL_MPTABLE.TBL"
''']
    if routed:
        lines.append(f'''
[mizuRoute]

namelist_path = "{run_dir}/"
namelist_file = "mizuroute.param"

methods = "3"
dt      = 3600

write_qbasin = false
write_Qreach = false


[hydrofabric]

hfabric_path = "{run_dir}/"
hfabric_file = "topology.nc"

dname_seg = "seg"
dname_hru = "hru"

varname_HRUid     = "hruId"
varname_segId     = "segId"
varname_hruSegId  = "hruToSegId"
varname_downSegId = "downSegId"

varname_area   = "area"
varname_slope  = "slope"
varname_length = "length"
''')
    def entry(p):
        e = [f"lower = {float(bounds[p][0])!r}", f"upper = {float(bounds[p][1])!r}"] if p in bounds else []
        e += ['transformation = "log"'] if p in search["logs"] else []
        return f'"{p}" = {{ {", ".join(e)} }}' if e else f'"{p}" = {{}}'
    multipliers = search.get("multipliers", [])
    names = searched_names(search)
    names += [p for p in (pinned or {}) if p not in names]  # a pinned name@domain the search lacks
    params = "\n".join(entry(p) for p in names if p not in multipliers)
    scaled = "\n\n[calibration.spatial_multipliers]\n\n" + "\n".join(entry(p) for p in multipliers) + "\n" if multipliers else ""
    lines.append(f'''
[calibration]

algorithm = "{algorithm}"

start_date = "{score_start}"
end_date   = "{score_end}"

n_samples = {n_samples}
seed      = {seed}

write_aligned = false


[calibration.parameters]

{params}
{scaled}''')
    for members, gap in search["chains"]:
        names = ", ".join(f'"{m}"' for m in members)
        lines.append(f"\n\n[[parameter_dependencies.ordered]]\n\nparameters   = [{names}]\ngap_fraction = {gap}\n")
    for p in searched_names(search):
        if p.split("@")[0] == "frac_sand":  # silt takes what sand and clay leave, so the three add to one
            at = p[len("frac_sand"):]
            lines.append(f'\n\n[[parameter_dependencies.remainder]]\n\nparameter = "frac_silt{at}"\n'
                         f'of        = ["frac_sand{at}", "frac_clay{at}"]\n')
    if algorithm == "nsga2":
        lines.append(f"\n[calibration.nsga2]\n\npopulation_size = {population}\n")
    lines.append(f'''

[[calibration.target]]

name      = "discharge"
variable  = "streamflow"
{gauge}
obs_path  = "{obs}"
obs_file  = "{c["flow"]}"
vname_obs = "q_obs"
metric    = "kge"
''')
    if (temperature and routed and "temp" in c and "stream_temperature" in targets
            and has_obs(os.path.join(obs, c["temp"]), "t_obs", score_start, score_end)):  # a window with no record cannot be scored
        lines.append(f'''

[[calibration.target]]

name      = "stream_temperature"
variable  = "T_reach"
spatial_unit = "reach"
spatial_id   = {reach}
obs_path  = "{obs}"
obs_file  = "{c["temp"]}"
vname_obs = "t_obs"
metric    = "rmse"
''')
    if "grace" in targets:
        base = datetime.date.fromisoformat(start)  # both series are departures from their mean over the first year
        lines.append(f'''

[[calibration.target]]

name           = "grace_tws"
variable       = "basin__StorageChange"
spatial_unit   = "gru"
spatial_id     = 1
obs_path       = "{obs}"
obs_file       = "{c["grace"]}"
vname_obs      = "tws_obs"
accumulate     = true
baseline_start = "{base}"
baseline_end   = "{base + datetime.timedelta(days=364)}"
metric         = "rmse"
''')
    if "wgms_amce" in targets:
        lines.append(f'''

[[calibration.target]]

name       = "wgms_amce"
variable   = "basin__GlacierMassChange"
spatial_unit = "gru"
spatial_id   = {balance_gru}
obs_path   = "{obs}"
obs_file   = "{c["wgms_amce"]}"
vname_obs  = "mb_obs"
accumulate = true
balance    = "annual"
metric     = "rmse"
''')
    if "mass_balance" in targets:
        lines.append(f'''

[[calibration.target]]

name       = "mass_balance"
variable   = "basin__GlacierMassChange"
spatial_unit = "gru"
spatial_id   = {balance_gru}
obs_path   = "{obs}"
obs_file   = "{(case_spec(case).get("eval_obs") or {}).get("mb") if algorithm == "dds" and "mb" in (case_spec(case).get("eval_obs") or {}) else case_spec(case).get("mb_file", c["mb"])}"
vname_obs  = "mb_obs"
accumulate = true
balance    = "seasonal"
metric     = "rmse"
''')
    for g, (gru, weight) in (case_spec(case).get("geodetic") or {}).items():  # cumulative mass change of another GRU's glacier; weight 0 reports it only
        if algorithm == "dds" and case_spec(case).get("eval_obs"):  # Hugonnet's years are all calibrated on
            continue
        if weight == 0 and algorithm == "nsga2":  # NSGA-II takes no diagnostic target; an evaluation's rerun scores it
            continue
        base = datetime.date.fromisoformat(score_start)
        if base.year >= 2019 or not has_obs(os.path.join(obs, f"lemoncreek_hugonnet_{g}.nc"), "mb_obs", str(base), score_end):
            continue
        base = datetime.date.fromisoformat(geodetic_base or score_start)  # the change since then, scored in the scoring years only
        lines.append(f'''

[[calibration.target]]

name           = "hugonnet_{g}"
variable       = "basin__GlacierMassChange"
spatial_unit   = "gru"
spatial_id     = {gru}
obs_path       = "{obs}"
obs_file       = "lemoncreek_hugonnet_{g}.nc"
vname_obs      = "mb_obs"
accumulate     = true
baseline_start = "{base}"
baseline_end   = "{base + datetime.timedelta(days=366)}"
metric         = "rmse"
weight         = {float(weight)}
''')
    return "".join(lines)


def calibration_file(work):
    """The trials file a calibration driver run wrote in <work>/output (<case>_run0001_calibration.nc, or the older
    <case>_calibration.nc)."""
    found = sorted(glob.glob(os.path.join(work, "output", "*_calibration.nc")))
    if not found:
        raise SystemExit(f"no *_calibration.nc in {work}/output")
    return found[0]


def run_driver(work, config, settings, ranks):
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(os.path.join(work, "output"))
    os.makedirs(os.path.join(work, "state"))
    shutil.copy(os.path.join(settings, "coldState.nc"), os.path.join(work, "state"))
    with open(os.path.join(work, "config.toml"), "w") as f:
        f.write(config)
    exe = os.path.join(SUMMA_DIR, "bin", "summa_sundials_mizuroute_opt.exe")
    with open(os.path.join(work, "run.log"), "w") as log:
        status = subprocess.run(["mpirun", "-np", str(ranks), exe, "-c", os.path.join(work, "config.toml")],
                                stdout=log, stderr=subprocess.STDOUT).returncode
    if status != 0:
        raise SystemExit(f"calibration driver exited {status}; see {work}/run.log")


def fit12(value):
    """The value at the most significant digits that fit SUMMA's f12.4 parameter columns."""
    for digits in range(10, 0, -1):
        text = f"{value:.{digits}g}"
        if "." not in text:  # f12.4 reads a number without a decimal point as ten-thousandths
            mant, _, exp = text.partition("e")
            text = mant + "." + ("e" + exp if exp else "")
        if len(text) <= 12:
            return f"{text:>12}"
    raise ValueError(f"{value} does not fit in 12 characters")


def searched_names(search):
    """Every parameter a search sets: its list and the members of its ordered chains."""
    names = list(search["params"])
    names += [m for members, _ in search["chains"] for m in members if m not in names]
    return names


def pin_settings(src, dst, values):
    """A copy of the settings with every searched parameter's bounds set to its value."""
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    for name in ("localParamInfo.txt", "basinParamInfo.txt"):
        path = os.path.join(dst, name)
        out = []
        for line in open(path):
            key = line.split("|")[0].strip() if "|" in line and not line.lstrip().startswith("!") else ""
            if key in values:
                default = line.split("|")[1].strip()
                line = f"{key:<26}| {default:>12} | {fit12(values[key])} | {fit12(values[key])}\n"
            out.append(line)
        open(path, "w").writelines(out)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("mode", choices=("calibrate", "evaluate"))
    p.add_argument("case", help="run folder, e.g. gulkana_added")
    p.add_argument("--population", type=int, default=32)
    p.add_argument("--seed", type=int, default=42, help="calibrate: the search's random-number seed")
    p.add_argument("--generations", type=int, default=15)
    p.add_argument("--ranks", type=int, default=9, help="MPI ranks: one dispatcher and the workers")
    p.add_argument("--jobs", type=int, default=1, help="evaluate: front members rerun at once, each on --ranks ranks")
    p.add_argument("--search", choices=sorted(SEARCHES), default="paper1",
                   help="calibrate: paper1 (one soil for every domain), domain (upland soil and debris apart) or stream "
                        "(domain with the wetland's two parameters, scored on the water temperature too)")
    p.add_argument("--name", default="calibration",
                   help="folder of the calibration in <case>; its evaluation is <name>_evaluation")
    p.add_argument("--cal-end", help="calibrate: end the calibration years here (YYYY-MM-DD) instead of at the case's, for a cheap test")
    p.add_argument("--score-start", help="calibrate: score from here (YYYY-MM-DD); the run still starts at the case's, so the glacier has its history")
    p.add_argument("--pin-trial", metavar="NAME:SAMPLE",
                   help="calibrate: hold every searched parameter but the stream ones (STREAM_ONLY) at that trial of "
                        "<case>/<NAME>, e.g. calibration_5b:412")
    a = p.parse_args()
    run_dir = os.path.join(HERE, a.case)
    settings = os.path.join(run_dir, "summa_inputs")
    cal0, cal1, ev0, ev1 = periods(a.case)

    if a.cal_end:
        cal1 = a.cal_end
    if a.mode == "calibrate":
        work = os.path.join(run_dir, a.name)
        search = search_for(a.case, a.search)
        pinned = None
        if a.pin_trial:
            name, sample = a.pin_trial.rsplit(":", 1)
            with nc4.Dataset(calibration_file(os.path.join(run_dir, name))) as d:
                pinned = {n: float(d[n][int(sample) - 1]) for n in searched_names(search)
                          if n in d.variables and n not in STREAM_ONLY}
            free = [n for n in searched_names(search) if n not in pinned]
            if not set(free) <= set(STREAM_ONLY):
                raise SystemExit(f"not in {name}, so not pinned: {', '.join(sorted(set(free) - set(STREAM_ONLY)))}")
            print(f"pinned {len(pinned)} parameters at {a.pin_trial}; searching {', '.join(free)}", flush=True)
        config = config_text(a.case, run_dir, settings, work, cal0, cal1, a.score_start or cal0, cal1,
                             "nsga2", a.population * a.generations, a.population, temperature=a.search == "stream" or no_ice_temp(a.case),
                             search=search, pinned=pinned, seed=a.seed, geodetic_base=cal0)
        run_driver(work, config, settings, a.ranks)
        print(f"calibration written to {calibration_file(work)}")
        return

    evaluation = os.path.join(run_dir, f"{a.name}_evaluation")
    search = search_of(os.path.join(run_dir, a.name))
    with nc4.Dataset(calibration_file(os.path.join(run_dir, a.name))) as d:
        front = np.flatnonzero(np.asarray(d["pareto_front"][:]) == 1)
        names = [n for n in searched_names(search) if n in d.variables]
        values = {i: {n: float(d[n][i]) for n in names} for i in front}
        cal = np.asarray(d["objective"][:])
        cal_names = [t.strip() for t in d["objective"].target.split(",")]

    def rerun(i):
        work = os.path.join(evaluation, f"sample_{i + 1}")
        pinned = os.path.join(work + "_settings")
        with NETCDF:
            pin_settings(settings, pinned, values[i])
            config = config_text(a.case, run_dir, pinned, work, cal0, ev1, ev0, ev1,
                                 "dds", 1, 1, temperature=True, search=search, pinned=values[i])
        run_driver(work, config, pinned, a.ranks)
        with NETCDF, nc4.Dataset(calibration_file(work)) as d:
            ev = np.ma.filled(d["objective"][0].astype(float), np.nan)
            ev_names = [t.strip() for t in d["objective"].target.split(",")]
        row = {"sample": int(i) + 1}
        row.update({f"cal_{n}": float(cal[i, k]) for k, n in enumerate(cal_names)})
        row.update({f"eval_{n}": float(ev[k]) for k, n in enumerate(ev_names)})
        print(row, flush=True)
        return row

    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        rows = list(pool.map(rerun, front))
    out = os.path.join(evaluation, "evaluation.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
