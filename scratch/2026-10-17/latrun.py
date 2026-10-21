"""Rerun the corrected balanced trial on the bucket-latflow build: base, latflow + constant, latflow + exp_prof."""
import os, re, shutil, subprocess, sys
from pick import pick
S = os.path.dirname(os.path.abspath(__file__))
EXE = f'{S}/wtl/bin/summa_sundials_mizuroute.exe'
OUT = """basin__GlacierMassChange | 1
averageRoutedRunoff | 1
glacierRoutedRunoff | 1
averageRoutedRunoffTemp | 1
mLayerTemp | 24
mLayerHeight | 24
mLayerVolFracLiq | 24
mLayerColumnOutflow | 24
scalarSoilBaseflow | 24
scalarSoilDrainage | 24
scalarSurfaceRunoff | 24
scalarAquiferBaseflow | 24
scalarSWE | 24
"""
CASES = {'base': {}, 'lat_const': {'soilLatflw': 'latflow'},
         'lat_exp': {'soilLatflw': 'latflow', 'hc_profile': 'exp_prof', 'infRateMax': 'topmodel_GA'}}
src = f'{S}/runs/cor_1r_bal'
s, o, par = pick(f'{S}/cal_cor_1r/wolverine_calibration.nc')['bal']
procs = []
for name, dec in CASES.items():
    d = f'{S}/runs/lat_{name}'
    shutil.rmtree(d, ignore_errors=True); os.makedirs(f'{d}/output')
    shutil.copytree(f'{src}/settings', f'{d}/settings'); shutil.copy(f'{src}/initial_state.nc', d)
    open(f'{d}/settings/outputControl.txt', 'w').write(OUT)
    md = open(f'{d}/settings/modelDecisions.txt').read()
    for k, v in dec.items():
        if re.search(rf'^{k}\s', md, re.M): md = re.sub(rf'^({k}\s+)\S+', rf'\g<1>{v}', md, flags=re.M)
        else: md += f'{k:<32}{v:<16}! added for the lateral-flow test\n'
    open(f'{d}/settings/modelDecisions.txt', 'w').write(md)
    open(f'{d}/rerun.toml', 'w').write(open(f'{src}/rerun.toml').read().replace(src, d))
    args = [EXE, '-c', f'{d}/rerun.toml'] + sum([['--param', p, repr(float(v))] for p, v in par.items()], [])
    procs.append((name, subprocess.Popen(args, cwd=d, stdout=open(f'{d}/rerun.log', 'w'), stderr=subprocess.STDOUT)))
for name, p in procs: print(name, p.wait(), flush=True)
