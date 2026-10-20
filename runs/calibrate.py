#!/usr/bin/env python3
"""Calibrate a full glacier run, then score its Pareto front on the held-out years.

  calibrate  NSGA-II over 2009-2015 after a spin-up over 2008, on discharge and the glacier-wide seasonal
             mass balance, in <case>/<name> (default calibration)
  evaluate   each front member rerun over 2009-2022 with its parameters pinned (both bounds set to its
             value) and scored over 2016-2022, in <case>/<name>_evaluation/sample_<n>; a routed Wolverine run
             adds its water temperature, which is only recorded from 2016; writes <case>/<name>_evaluation/evaluation.csv

A run is routed through mizuRoute, and scored at its reach, when its folder holds a topology.nc (a stream case
of cases.yaml); otherwise discharge is the GRU's own.

The spin-up runs at the default parameters for every trial, in calibration and evaluation alike, as the
calibration driver does. Needs summa's MPI calibration executable (bin/summa_sundials_mizuroute_opt.exe).

    ./calibrate.py calibrate gulkana_raw --population 32 --generations 15 --ranks 9
    ./calibrate.py evaluate gulkana_raw --ranks 2 --jobs 4
    ./calibrate.py calibrate gulkana_raw --population 20 --generations 10 --ranks 5 --name pilot
"""

import argparse
import csv
import os
import shutil
import subprocess
import tomllib
from concurrent.futures import ThreadPoolExecutor

import netCDF4 as nc4
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GLACIER = os.path.dirname(HERE)
SUMMA_DIR = os.path.abspath(os.environ.get("SUMMA_DIR", os.path.join(GLACIER, "..", "summa")))

# paper1: one value of each soil parameter for every domain; windExposure is fixed per case, 0.77 on station wind, 1 on ERA5
PAPER1 = ["k_soil", "theta_sat", "aquiferBaseflowExp", "aquiferBaseflowRate", "qSurfScale", "summerLAI",
          "frozenPrecipMultip", "Fcapil", "tempCritRain", "heightCanopyTop", "heightCanopyBottom",
          "windReductionParam", "vGn_n", "routingGammaScale", "routingGammaShape", "glacierWindFactor",
          "glacierTempReduction", "glacStor_kIce", "glacStor_kSnow", "glacStor_kFirn", "k_snow",
          "mw_exp", "albedoDecayRate", "albedoMax", "k_macropore", "tempRangeTimestep", "thCond_soil",
          "newSnowDenMin"]
PAPER1_CHAIN = ["theta_res", "critSoilWilting", "critSoilTranspire", "fieldCapacity", "theta_sat"]
CANOPY_CHAIN = (["heightCanopyBottom", "heightCanopyTop"], 0.25, False)

# domain: the upland soil and the debris searched apart, and the englacial debris concentration, the debris's other soil values fixed in trialParams.nc;
# frac_sand (with frac_clay fixed) sets the conductivity of the solids, which thCondSoil = funcSoilWet uses
DOMAIN = [p for p in PAPER1 if p not in ("k_soil", "theta_sat", "vGn_n", "k_macropore", "thCond_soil")] + \
         ["k_soil@upland", "k_macropore@upland", "theta_sat@upland", "vGn_n@upland", "frac_sand@upland",
          "theta_sat@glacDbr", "frac_sand@glacDbr", "debrisConc"]
DOMAIN_CHAIN = ["theta_res@upland", "critSoilWilting@upland", "critSoilTranspire@upland", "fieldCapacity@upland",
                "theta_sat@upland"]

SEARCHES = {
    "paper1": {"params": PAPER1, "logs": ["k_soil", "aquiferBaseflowRate", "k_macropore"],
               "chains": [CANOPY_CHAIN, (PAPER1_CHAIN, 0.025, True)], "bounds": {}},
    "domain": {"params": DOMAIN, "logs": ["k_soil@upland", "aquiferBaseflowRate", "k_macropore@upland"],
               "chains": [CANOPY_CHAIN, (DOMAIN_CHAIN, 0.025, True)],
               "bounds": {"theta_sat@upland": (0.35, 0.65),     # mineral soil
                          "theta_sat@glacDbr": (0.2, 0.45),     # supraglacial debris, Fontrodona-Bach et al. (2025)
                          "debrisConc": (0.1, 6.4)}},           # kg m-3, Anderson and Anderson (2018)
}

CASES = {  # domain, observation files and gauge of each run
    "gulkana": {"obs": "data/domain_Gulkana/observations/calibration", "flow": "USGS_15478040_daily_flow.nc",
                "mb": "gulkana_mass_balance_seasonal.nc"},
    "wolverine": {"obs": "data/domain_Wolverine/observations/calibration", "flow": "USGS_15236900_daily_flow.nc",
                  "mb": "wolverine_mass_balance_seasonal.nc", "temp": "USGS_15236900_daily_temperature.nc"},
}


def search_of(calibration):
    """The search a calibration ran (parameters, log transforms, ordered chains, bounds), from its config.toml."""
    with open(os.path.join(calibration, "config.toml"), "rb") as f:
        t = tomllib.load(f)
    cal = t["calibration"]
    chains = [(o["parameters"], o["gap_fraction"], o.get("sample_gaps", False))
              for o in t.get("parameter_dependencies", {}).get("ordered", [])]
    return {"params": cal["param_list"], "logs": list(cal.get("parameter_transformations", {})), "chains": chains,
            "bounds": {k: tuple(v) for k, v in cal.get("parameter_bounds", {}).items()}}


def config_text(case, run_dir, settings, work, start, end, score_start, score_end, algorithm, n_samples,
                population, temperature, search=SEARCHES["paper1"], pinned=None):
    """The calibration driver's TOML for one search or one pinned trial; pinned name@domainType values are
    held by their bounds, the parameter files holding the rest (pin_settings)."""
    bounds = dict(search["bounds"])
    bounds.update({k: (v, v) for k, v in (pinned or {}).items() if "@" in k})
    c = CASES[case.split("_")[0]]
    routed = os.path.exists(os.path.join(run_dir, "topology.nc"))
    forcing_file = os.path.join(run_dir, "forcing_path.txt")
    forcing = open(forcing_file).read().strip() if os.path.exists(forcing_file) else os.path.join(run_dir, "forcing") + "/"
    obs = os.path.join(GLACIER, c["obs"]) + "/"
    gauge = "reach     = 1" if routed else "gru       = 1"
    lines = [f'''# generated by calibrate.py

[simulation]

case_name = "{case}"

# the driver spins up over the year before start_time, from the cold state, at the default parameters
start_time = "{start} 00:00"
end_time   = "{end} 23:00"
time_zone  = "utcTime"

use_mizuroute    = {"true" if routed else "false"}
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
    params = ",\n".join(f'    "{p}"' for p in search["params"])
    logs = "\n".join(f'"{p}" = "log"' for p in search["logs"])
    lines.append(f'''
[calibration]

algorithm = "{algorithm}"

start_date = "{score_start}"
end_date   = "{score_end}"

n_samples = {n_samples}

param_list = [
{params}
]

write_aligned = false


[calibration.parameter_transformations]

{logs}
''')
    if bounds:
        rows = "\n".join(f'"{k}" = [{float(lo)!r}, {float(hi)!r}]' for k, (lo, hi) in bounds.items())
        lines.append(f"\n\n[calibration.parameter_bounds]\n\n{rows}\n")
    for members, gap, sample in search["chains"]:
        names = ", ".join(f'"{m}"' for m in members)
        lines.append(f"\n\n[[parameter_dependencies.ordered]]\n\nparameters   = [{names}]\ngap_fraction = {gap}\n"
                     + ("sample_gaps  = true\n" if sample else ""))
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
    if temperature and routed and "temp" in c:
        lines.append(f'''

[[calibration.target]]

name      = "stream_temperature"
variable  = "T_reach"
reach     = 1
obs_path  = "{obs}"
obs_file  = "{c["temp"]}"
vname_obs = "t_obs"
metric    = "rmse"
''')
    lines.append(f'''

[[calibration.target]]

name       = "mass_balance"
variable   = "basin__GlacierMassChange"
gru        = 1
obs_path   = "{obs}"
obs_file   = "{c["mb"]}"
vname_obs  = "mb_obs"
accumulate = true
balance    = "seasonal"
metric     = "rmse"
''')
    return "".join(lines)


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
    names += [m for members, _, _ in search["chains"] for m in members if m not in names]
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
    p.add_argument("case", help="run folder, e.g. gulkana_raw")
    p.add_argument("--population", type=int, default=32)
    p.add_argument("--generations", type=int, default=15)
    p.add_argument("--ranks", type=int, default=9, help="MPI ranks: one dispatcher and the workers")
    p.add_argument("--jobs", type=int, default=1, help="evaluate: front members rerun at once, each on --ranks ranks")
    p.add_argument("--search", choices=sorted(SEARCHES), default="paper1",
                   help="calibrate: paper1 (one soil for every domain) or domain (upland soil and debris apart)")
    p.add_argument("--name", default="calibration",
                   help="folder of the calibration in <case>; its evaluation is <name>_evaluation")
    a = p.parse_args()
    run_dir = os.path.join(HERE, a.case)
    settings = os.path.join(run_dir, "summa_inputs")

    if a.mode == "calibrate":
        work = os.path.join(run_dir, a.name)
        config = config_text(a.case, run_dir, settings, work, "2009-01-01", "2015-12-31", "2009-01-01", "2015-12-31",
                             "nsga2", a.population * a.generations, a.population, temperature=False,
                             search=SEARCHES[a.search])
        run_driver(work, config, settings, a.ranks)
        print(f"calibration written to {work}/output/{a.case}_calibration.nc")
        return

    evaluation = os.path.join(run_dir, f"{a.name}_evaluation")
    search = search_of(os.path.join(run_dir, a.name))
    with nc4.Dataset(os.path.join(run_dir, a.name, "output", f"{a.case}_calibration.nc")) as d:
        front = np.flatnonzero(np.asarray(d["pareto_front"][:]) == 1)
        names = [n for n in searched_names(search) if n in d.variables]
        values = {i: {n: float(d[n][i]) for n in names} for i in front}
        cal = np.asarray(d["objective"][:])
        cal_names = [t.strip() for t in d["objective"].target.split(",")]

    def rerun(i):
        work = os.path.join(evaluation, f"sample_{i + 1}")
        pinned = os.path.join(work + "_settings")
        pin_settings(settings, pinned, values[i])
        config = config_text(a.case, run_dir, pinned, work, "2009-01-01", "2022-12-31", "2016-01-01", "2022-12-31",
                             "dds", 1, 1, temperature=True, search=search, pinned=values[i])
        run_driver(work, config, pinned, a.ranks)
        with nc4.Dataset(os.path.join(work, "output", f"{a.case}_calibration.nc")) as d:
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
