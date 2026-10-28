"""Short SUMMA experiments from trial 451's pinned settings (old attributes, 26.62 km2), 2009-2014."""
import os, shutil, re, glob, sys
import numpy as np, netCDF4 as nc
HERE = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs/gulkana_timing_diagnosis/exp"
SRC = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs/gulkana_corrected/calibration_rerun/sample_451"
FORC = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/data/domain_Gulkana/forcing/SUMMA_input/station_corrected/"

def setparam(path, name, val):
    out = []
    for line in open(path):
        if "|" in line and not line.lstrip().startswith("!") and line.split("|")[0].strip() == name:
            line = f"{name:<26}| {val:>12.4f} | {val:>12.4f} | {val:>12.4f}\n"
        out.append(line)
    open(path, "w").writelines(out)

def make(name, params={}, forcing=None):
    work = f"{HERE}/{name}"; st = work + "_settings"
    for d in (work, st):
        if os.path.isdir(d): shutil.rmtree(d)
    shutil.copytree(SRC + "_settings", st)
    for k, v in params.items():
        for f in ("localParamInfo.txt", "basinParamInfo.txt"): setparam(f"{st}/{f}", k, v)
    os.makedirs(work + "/output"); os.makedirs(work + "/state")
    shutil.copy(f"{st}/coldState.nc", work + "/state")
    c = open(SRC + "/config.toml").read()
    c = c.replace(SRC + "_settings", st).replace(SRC, work)
    c = c.replace('end_time   = "2022-12-31 23:00"', 'end_time   = "2014-12-31 23:00"')
    c = c.replace('start_date = "2016-01-01"', 'start_date = "2010-01-01"').replace('end_date   = "2022-12-31"', 'end_date   = "2014-12-31"')
    if forcing: c = c.replace(FORC, forcing)
    open(work + "/config.toml", "w").write(c)

def scaled_forcing(name, months, factor):
    out = f"{HERE}/{name}"; os.makedirs(out, exist_ok=True)
    for f in sorted(glob.glob(FORC + "*.nc")):
        yyyymm = re.search(r"(\d{6})\.nc$", f).group(1)
        if int(yyyymm[:4]) > 2014: continue
        dst = f"{out}/{os.path.basename(f)}"; shutil.copy(f, dst)
        if int(yyyymm[4:]) in months:
            with nc.Dataset(dst, "a") as d: d["pptrate"][:] = d["pptrate"][:] * factor
    return out + "/"

if __name__ == "__main__":
    make("E0_base")
    make("E1_nodebris", {"debrisConc": 0.0, "wallErosionRate": 0.0})
    make("E2_icealb", {"albedoFrznWatVisible": 0.45, "albedoFrznWatNearIR": 0.25})
    make("E3_rainx1.9", forcing=scaled_forcing("forcing_JJAS_x1.9", [6, 7, 8, 9], 1.9))

def more():
    alb = {"albedoFrznWatVisible": 0.45, "albedoFrznWatNearIR": 0.25, "albedoDecayRate": 1.0e6, "albedoMax": 0.84}
    make("E4_icealb_snowalb", alb)
    make("E5_all", {**alb, "debrisConc": 0.0, "wallErosionRate": 0.0}, forcing=f"{HERE}/forcing_JJAS_x1.9/")
    shutil.copy(f"{HERE}/E3_rainx1.9_settings/forcingFileList.txt", f"{HERE}/E5_all_settings/forcingFileList.txt")
