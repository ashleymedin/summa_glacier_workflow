import subprocess
from pick import pick
from rerun import EXE, S
jobs = []
for c in ('cor', 'raw'):
    s, o, par = pick(f'{S}/cal_{c}_1r/wolverine_calibration.nc')['bal']
    d = f'{S}/runs/{c}_1r_soil'
    args = [EXE, '-c', f'{d}/rerun.toml'] + sum([['--param', p, repr(float(v))] for p, v in par.items()], [])
    jobs.append((c, s, subprocess.Popen(args, cwd=d, stdout=open(f'{d}/rerun.log', 'w'), stderr=subprocess.STDOUT)))
for c, s, p in jobs: print(c, s, p.wait())
