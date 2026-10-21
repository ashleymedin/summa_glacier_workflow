"""rerun_trials.py with searched parameters replaced: OVERRIDE=name=value,name=value rerun_override.py <rerun_trials args>"""
import os, sys
sys.path.insert(0, '/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs')
os.chdir('/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs')
import rerun_trials
over = {k: float(v) for k, v in (kv.split('=') for kv in os.environ['OVERRIDE'].split(','))}
pin = rerun_trials.pin_settings
rerun_trials.pin_settings = lambda src, dst, values: pin(src, dst, {**values, **over})
rerun_trials.main()
