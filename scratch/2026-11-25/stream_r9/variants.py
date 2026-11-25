#!/usr/bin/env python3
"""The stream cases' figure variants, built in runs/ as folders of their own and spun up: wolverine_stream_lake (the lake without its
delta), gulkana_stream_fan and gulkana_stream_nowet. Their summa_inputs go to rerun_trials.py --inputs; cases.yaml is left alone."""
import os, subprocess, sys
import yaml
WF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
sys.path.insert(0, os.path.join(WF, "runs"))
import calibrate
import spinup

with open(os.path.join(WF, "cases.yaml")) as f:
    cases = yaml.safe_load(f)
V = {}
for name, base, drop in [("wolverine_stream_lake", "wolverine_stream_delta", "delta"), ("gulkana_stream_fan", "gulkana_stream", None),
                         ("gulkana_stream_nowet", "gulkana_stream", "wetland")]:
    V[name] = {k: v for k, v in cases[base].items() if k != drop}
    V[name]["dest"] = f"runs/{name}"
    cases[name] = V[name]
if sys.argv[1] == "build":
    path = os.path.join(WF, "cases_r9_variants_tmp.yaml")  # beside cases.yaml, whose folder the dest and template paths are from
    with open(path, "w") as f:
        yaml.safe_dump({**{p: cases[p] for p in ("wolverine_added", "gulkana_added")}, **V}, f)
    try:
        subprocess.run([sys.executable, "build_cases.py", path, *V], cwd=WF, check=True)
    finally:
        os.remove(path)
else:
    class _Yaml:  # calibrate.case_spec reads cases.yaml; the variants are added to it
        safe_load = staticmethod(lambda f: cases)
    calibrate.yaml = _Yaml
    sys.argv = ["spinup.py", sys.argv[2]]
    spinup.main()
