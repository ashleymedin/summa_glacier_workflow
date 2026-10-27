#!/usr/bin/env python3
"""Run perturbed copies of sampled parameter sets as single-process SUMMA runs and report wall and physics time.
usage: [ONLY=s2,s4] caffeinate -i ensemble.py tag absTol n_per_set cpu_timeout_s [exe]   (parameter sets are listed in SETS below)"""
import sys, os, shutil, subprocess, re, time, random
from concurrent.futures import ThreadPoolExecutor
S = os.path.dirname(os.path.abspath(__file__))
tag, tol, nper, tmax = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
exe = sys.argv[5] if len(sys.argv) > 5 else "/Users/amedin/Research/SummaSundials/summa/bin/summa_sundials_mizuroute.exe"
NAMES = "frozenPrecipMultip tempCritRain glacierWindFactor glacierTempReduction albedoMax aquiferBaseflowExp k_soil vGn_n theta_sat Fcapil".split()
SETS = {
 "s2":  "1.4753935848833497 272.64411833063042 2.9289012346653633 0.21585158280329225 0.75107389642769640 5.8420514920895146 1.0130227912114580E-006 3.4474058760376587 0.43592252161317796 0.17000414213732229",
 "s4":  "0.65039376800000748 273.91996220407560 2.0573335651990363 2.0644860955677218 0.86324250498725330 6.7941161584697944 4.2787498807860219E-006 1.4777223925145866 0.51512947980068846 8.4955987981928743E-002",
 "s12": "1.4753935848833497 272.64195768246725 2.9341782359363151 0.21585158280329225 0.70943539303354686 6.8016184703804727 1.0130227912114580E-006 3.4474058760376591 0.26143485752130385 0.17068438109326081",
}
ROOT = f"{S}/ens_{tag}"; shutil.rmtree(ROOT, ignore_errors=True); os.makedirs(ROOT)
inputs = f"{ROOT}/inputs"; shutil.copytree(f"{S}/tol_t4j/inputs", inputs, symlinks=False)
base = open(f"{S}/wolida4/config.toml").read(); base = base[:base.index("[calibration]")]
base = re.sub(r'start_time = .*', 'start_time = "2015-10-01 00:00"', base)
def cpu(pid):
    out = subprocess.run(["ps", "-o", "time=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    if not out: return 0.0
    t = 0.0
    for x in out.split(":"): t = t*60 + float(x)
    return t
def one(job):
    name, i, vals = job
    R = f"{ROOT}/{name}_{i:02d}"; os.makedirs(f"{R}/output"); os.makedirs(f"{R}/state")
    shutil.copy(f"{S}/wolida4/state/coldState.nc", f"{R}/state/")
    c = base.replace("/wolida4/summa_inputs/", "X").replace(f"{S}/wolida4/inputs/", f"{inputs}/").replace(f"{S}/wolida4/", f"{R}/")
    open(f"{R}/config.toml", "w").write(c)
    args = []
    for n, v in zip(NAMES, vals): args += ["--param", n, repr(v)]
    for n in ("absTolMatric", "absTolAquifr", "absTolWatVeg"): args += ["--param", n, tol]
    t0 = time.time()
    p = subprocess.Popen([exe, "-c", "config.toml"] + args, cwd=R, stdout=open(f"{R}/run.log", "w"), stderr=subprocess.STDOUT, start_new_session=True)
    while p.poll() is None and cpu(p.pid) < tmax: time.sleep(5)
    status = "done"
    if p.poll() is None:
        status = "TIMEOUT"
        try: os.killpg(p.pid, 15)
        except Exception: pass
    log = open(f"{R}/run.log").read()
    m = re.search(r"elapsed physics =\s*([0-9.]+)", log)
    dates = re.findall(r"^\s*(20\d\d)\s+(\d+)\s+(\d+)\s", log, flags=re.M)
    return name, i, status, time.time() - t0, float(m.group(1)) if m else float("nan"), "-".join(dates[-1]) if dates else ""
random.seed(1)
jobs = []
for name, s in SETS.items():
    if os.environ.get("ONLY") and name not in os.environ["ONLY"].split(","): continue
    v = [float(x) for x in s.split()]
    for i in range(nper):
        w = list(v); w[6] *= 1 + random.choice([-1, 1]) * random.uniform(1e-4, 2e-3); jobs.append((name, i, w))
res = []
with ThreadPoolExecutor(max_workers=5) as ex:
    for r in ex.map(one, jobs):
        res.append(r); print("%s %02d %-7s wall %6.0f s physics %6.0f s last %s" % r, flush=True)
for name in sorted({r[0] for r in res}):
    t = [r[3] for r in res if r[0] == name]; slow = sum(1 for r in res if r[0] == name and r[2] == "TIMEOUT")
    print(name, "runs", len(t), "timeouts", slow, "median wall %.0f max wall %.0f" % (sorted(t)[len(t)//2], max(t)))
