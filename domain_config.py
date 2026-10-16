"""Read a domain YAML of domains/ and fill in the paths it leaves out."""

import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))


def load_config(path):
    """The domain settings, with project_dir and the data directories resolved; relative paths are
    relative to this folder (summa_glacier)."""
    with open(path) as f:
        c = yaml.safe_load(f)
    resolve = lambda p: os.path.abspath(os.path.join(HERE, os.path.expanduser(p)))
    c["project_dir"] = resolve(c["project_dir"])
    c.setdefault("domain", os.path.basename(c["project_dir"].rstrip("/")).replace("domain_", "", 1))
    c["data"] = {k: resolve(v) for k, v in c.get("data", {}).items()}
    return c
