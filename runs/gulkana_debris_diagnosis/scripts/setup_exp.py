"""Short debris experiments from trial 451's pinned settings. D*: polygon HRU areas, 2009-2013; G*: timing-diagnosis E6
(polygon areas + gauge summer rain), 2009-2014."""
import os, shutil, sys
HERE = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs/gulkana_debris_diagnosis/exp"
SRC = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs/gulkana_corrected/calibration_rerun/sample_451"
END = "2013"
E6 = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs/gulkana_timing_diagnosis/exp/E6_area_gaugerain"

def setparam(path, name, val):
    out, hit = [], False
    for line in open(path):
        if "|" in line and not line.lstrip().startswith("!") and line.split("|")[0].strip() == name:
            line = f"{name:<26}| {val:>12.4f} | {val:>12.4f} | {val:>12.4f}\n"; hit = True
        out.append(line)
    open(path, "w").writelines(out)
    return hit

def make(name, params={}, end=END, src=SRC):
    work = f"{HERE}/{name}"; st = work + "_settings"
    for d in (work, st):
        if os.path.isdir(d): shutil.rmtree(d)
    shutil.copytree(src + "_settings", st)
    for k, v in params.items():
        hits = [setparam(f"{st}/{f}", k, v) for f in ("localParamInfo.txt", "basinParamInfo.txt")]
        assert any(hits), k
    for d in ("output", "state", "grids"): os.makedirs(f"{work}/{d}")
    shutil.copy(f"{st}/coldState.nc", work + "/state")
    c = open(src + "/config.toml").read().replace(src + "_settings", st).replace(src, work)
    c = c.replace('end_time   = "2022-12-31 23:00"', f'end_time   = "{end}-12-31 23:00"').replace('end_time   = "2014-12-31 23:00"', f'end_time   = "{end}-12-31 23:00"')
    c = c.replace('end_date   = "2014-12-31"', f'end_date   = "{end}-12-31"')
    c = c.replace('start_date = "2016-01-01"', 'start_date = "2010-01-01"').replace('end_date   = "2022-12-31"', f'end_date   = "{end}-12-31"')
    open(work + "/config.toml", "w").write(c)

if __name__ == "__main__":
    exps = {"D0_base": {}, "D1_noRockfall": {"wallErosionRate": 0.0}, "D2_noEmergence": {"debrisConc": 0.0},
            "D3_conc1": {"debrisConc": 1.0}}
    e6 = {"G0_old": {}, "G1_fix1": {}, "G2_fix2": {}, "G3_old_conc1_noRock": {"debrisConc": 1.0, "wallErosionRate": 0.0},
          "G4_fix2_conc1": {"debrisConc": 1.0}, "G5_fix2_noRock": {"wallErosionRate": 0.0}}
    for n in sys.argv[1:]:
        if n in exps: make(n, exps[n])
        elif n.endswith("_full"): make(n, e6[n[:-5]], end="2022", src=E6)
        else: make(n, e6[n], end="2014", src=E6)
