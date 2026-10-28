#!/usr/bin/env python3
"""Run a glacier study end to end from a domain YAML: observations, domain, cases, calibration, evaluation, checks.

Steps, in order (--steps picks some; the default is all of them):

  observations  acquire_observations.py: the YAML's `observations:` block, over forcing_period
  domain        setup_glacier_domain.py: rasters extend hrus zonal era5 forcing coldstate (--domain-steps picks some)
  cases         build_cases.py: the cases.yaml full runs of this domain (--cases names others)
  calibrate     runs/calibrate.py calibrate, for each case; arguments after -- go to it
  evaluate      runs/calibrate.py evaluate, for each case
  checks        check_glacier_imagery.py for the YAML's `imagery:` years

The observation and domain steps need the by-hand downloads of README.md first.  Calibration is long and needs MPI SUMMA.

    ./run_study.py domains/gulkana.yaml --steps observations domain cases
    ./run_study.py domains/gulkana.yaml --steps calibrate -- --population 32 --generations 15 --ranks 9
"""

import argparse
import os
import subprocess
import sys

import yaml

from domain_config import load_config

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = ("observations", "domain", "cases", "calibrate", "evaluate", "checks")


def run(*args, cwd=None):
    print("\n$ " + " ".join(str(x) for x in args), flush=True)
    subprocess.run([str(x) for x in args], check=True, cwd=cwd)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--cases-file", default=os.path.join(HERE, "cases.yaml"))
    p.add_argument("--steps", nargs="+", choices=STEPS, default=list(STEPS))
    p.add_argument("--domain-steps", nargs="+", help="steps of setup_glacier_domain.py")
    p.add_argument("--cases", nargs="+", help="cases to build, calibrate and evaluate; default the full runs of this domain")
    a, extra = p.parse_known_args()
    extra = [x for x in extra if x != "--"]
    c = load_config(a.config)
    stem = os.path.splitext(os.path.basename(a.config))[0]
    py = sys.executable

    with open(a.cases_file) as f:
        every = yaml.safe_load(f)
    cases = a.cases or [k for k, v in every.items() if v.get("domain") == stem and "calibrate" in v]

    if "observations" in a.steps:
        run(py, os.path.join(HERE, "acquire_observations.py"), a.config)
    if "domain" in a.steps:
        run(py, os.path.join(HERE, "setup_glacier_domain.py"), a.config, *(["--steps", *a.domain_steps] if a.domain_steps else []))
    if "cases" in a.steps:
        run(py, os.path.join(HERE, "build_cases.py"), a.cases_file, *cases)
    for mode in ("calibrate", "evaluate"):
        if mode in a.steps:
            for case in cases:
                run(py, os.path.join(HERE, "runs", "calibrate.py"), mode, case, *extra, cwd=os.path.join(HERE, "runs"))
    if "checks" in a.steps and c.get("imagery"):
        im = c["imagery"]
        run(py, os.path.join(HERE, "check_glacier_imagery.py"), a.config, "--landsat", *im.get("landsat", []),
            "--sentinel", *im.get("sentinel", []))


if __name__ == "__main__":
    main()
