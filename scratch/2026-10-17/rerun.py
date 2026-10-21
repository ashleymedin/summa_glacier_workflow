"""Rerun chosen trials of a calibration from its spin-up state with hourly output.

    rerun.py <case>   (case = cor_1r | raw_1r | cor_net | raw_net)  [end time]
Writes runs/<case>_<pick>/output/.
"""
import os, re, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pick import pick

S = os.path.dirname(os.path.abspath(__file__))
EXE = os.environ.get('SUMMA_EXE', f'{S}/wt/bin/summa_sundials_mizuroute.exe')
TAG = os.environ.get('RUN_TAG', '')
OUTCTL = """basin__GlacierMassChange | 1
averageRoutedRunoff | 1
glacierRoutedRunoff | 1
averageRoutedRunoffTemp | 1
basin__AquiferBaseflow | 1
scalarSWE | 24
scalarAquiferBaseflow | 1
scalarSurfaceRunoff | 1
scalarSoilBaseflow | 1
scalarAquiferTemp | 24
"""

def rerun(case, end=None):
    cal = f'{S}/cal_{case}'
    cfg = open(f'{cal}/config.toml').read()
    data = re.search(r'settings_path\s*=\s*"(.*)summa_inputs/"', cfg).group(1)
    spin = [f for f in os.listdir(f'{cal}/state') if 'spinup' in f][0]
    jobs = []
    for k, (s, o, par) in pick(f'{cal}/wolverine_calibration.nc' if os.path.exists(f'{cal}/wolverine_calibration.nc') else f'{cal}/output/wolverine_calibration.nc').items():
        run = f'{S}/runs/{case}{TAG}_{k}'
        shutil.rmtree(run, ignore_errors=True); os.makedirs(f'{run}/output'); os.makedirs(f'{run}/settings')
        for f in os.listdir(f'{data}summa_inputs'):
            shutil.copy(f'{data}summa_inputs/{f}', f'{run}/settings/')
        open(f'{run}/settings/outputControl.txt', 'w').write(OUTCTL)
        shutil.copy(f'{cal}/state/{spin}', f'{run}/initial_state.nc')
        c = cfg
        for key, val in (('settings_path', f'{run}/settings/'), ('state_path', f'{run}/'), ('init_condition', 'initial_state.nc'),
                         ('output_path', f'{run}/output/'), ('work_path', f'{run}/output'), ('write_timeseries', 'true')):
            q = '' if val == 'true' else '"'
            c = re.sub(rf'^(\s*{key}\s*=).*$', rf'\1 {q}{val}{q}', c, flags=re.M)
        c = re.sub(r'^(\s*write_Qreach\s*=).*$', r'\1 true', c, flags=re.M)
        if end:
            c = re.sub(r'^(\s*end_time\s*=).*$', rf'\1 "{end}"', c, flags=re.M)
        open(f'{run}/rerun.toml', 'w').write(c)
        args = [EXE, '-c', f'{run}/rerun.toml'] + sum([['--param', p, repr(float(v))] for p, v in par.items()], [])
        open(f'{run}/trial.txt', 'w').write(f'sample {s} objectives {list(o)}\n')
        jobs.append((run, args))
    def go(j):
        run, args = j
        with open(f'{run}/rerun.log', 'w') as log:
            r = subprocess.run(args, cwd=run, stdout=log, stderr=subprocess.STDOUT)
        return run, r.returncode
    with ThreadPoolExecutor(int(os.environ.get('NPAR', 4))) as ex:
        for run, rc in ex.map(go, jobs):
            print(os.path.basename(run), 'exit', rc)

if __name__ == '__main__':
    rerun(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
