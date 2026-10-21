import os, shutil, subprocess
from pick import pick
S = os.path.dirname(os.path.abspath(__file__))
s, o, par = pick(f'{S}/cal_cor_1r/wolverine_calibration.nc')['bal']
src, d = f'{S}/runs/lat_base', f'{S}/runs/lat_parent'
shutil.rmtree(d, ignore_errors=True); os.makedirs(f'{d}/output')
shutil.copytree(f'{src}/settings', f'{d}/settings'); shutil.copy(f'{src}/initial_state.nc', d)
open(f'{d}/rerun.toml', 'w').write(open(f'{src}/rerun.toml').read().replace(src, d))
args = [f'{S}/wtp/bin/summa_sundials_mizuroute.exe', '-c', f'{d}/rerun.toml'] + sum([['--param', k, repr(float(v))] for k, v in par.items()], [])
print(subprocess.run(args, cwd=d, stdout=open(f'{d}/rerun.log', 'w'), stderr=subprocess.STDOUT).returncode)
