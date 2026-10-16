#!/usr/bin/env python3
"""Build the SUMMA cases (tests and full runs) of cases.yaml from the glacier domains in data/.

Each case takes its domain's attributes_glac.nc and a cold state written for its own first forcing month
(glacier_cold_state.py --start), so the soil starts from the air temperature of the year the run spins up
over. Its text settings and trialParams.nc are the case's own, kept in <dest>/summa_inputs. Its forcing is
the domain's raw ERA5 (forcing/SUMMA_input) or the station correction (forcing/SUMMA_input/station_corrected)
over the case's months: copied into <dest>/forcing for a test, read in place for a run.

  stream  the domain gets a stream HRU and a one-reach topology (summa's add_stream_hru.py), whose forcing
          and topology are written into <dest>
  merge   two domains become one, one GRU each, with their HRUs, glacier grids and forcing side by side

    ./build_cases.py cases.yaml gulkana_test wolverine_test
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile

import netCDF4 as nc4
import numpy as np
import yaml

from domain_config import load_config

HERE = os.path.dirname(os.path.abspath(__file__))
SUMMA_DIR = os.path.abspath(os.environ.get("SUMMA_DIR", os.path.join(HERE, "..", "summa")))


def months_between(first, last):
    y0, m0 = map(int, first.split("-"))
    y1, m1 = map(int, last.split("-"))
    return [f"{y:04d}{m:02d}" for y in range(y0, y1 + 1) for m in range(1, 13) if (y0, m0) <= (y, m) <= (y1, m1)]


def forcing_files(forcing_dir, months):
    """The domain's monthly forcing files for the months, in order."""
    files = []
    for m in months:
        found = glob.glob(os.path.join(forcing_dir, f"*{m}.nc"))
        if len(found) != 1:
            raise SystemExit(f"expected one forcing file for {m} in {forcing_dir}, found {len(found)}")
        files.append(found[0])
    return files


def write_file_list(path, names):
    with open(path, "w") as f:
        f.writelines(f"{n}\n" for n in names)


def domain_cold_state(config, start, out_dir):
    """attributes_glac.nc and coldstate_glac.nc of a domain, the cold state started at start, in out_dir."""
    c = load_config(os.path.join(HERE, "domains", f"{config}.yaml"))
    subprocess.run([sys.executable, os.path.join(HERE, "glacier_cold_state.py"), c["project_dir"],
                    "--utm-epsg", str(c["utm_epsg"]), "--start", start, "--soil-offset", str(c.get("soil_offset", 1.5)),
                    "--ice-temp", str(c.get("ice_temp", -5.0)), "--output-dir", out_dir], check=True)
    return c


def forcing_dir_of(c, forcing):
    base = os.path.join(c["project_dir"], "forcing", "SUMMA_input")
    return base if forcing == "raw" else os.path.join(base, "station_corrected")


def merge_netcdf(paths, out, hru_offsets):
    """One file of several domains' files, concatenated along hru and gru, other dimensions padded to the
    largest, padding at each variable's fill value; hruId and hru2gruId renumbered by hru_offsets."""
    srcs = [nc4.Dataset(p) for p in paths]
    for s in srcs:
        s.set_auto_mask(False)
    with nc4.Dataset(out, "w", format="NETCDF4") as d:
        for name in srcs[0].dimensions:
            size = sum(len(s.dimensions[name]) for s in srcs) if name in ("hru", "gru") else \
                max(len(s.dimensions[name]) for s in srcs if name in s.dimensions)
            d.createDimension(name, size)
        for name, v in srcs[0].variables.items():
            fill = getattr(v, "_FillValue", None)
            var = d.createVariable(name, v.dtype, v.dimensions, fill_value=fill)
            var.setncatts({k: v.getncattr(k) for k in v.ncattrs() if k != "_FillValue"})
            shape = tuple(len(d.dimensions[x]) for x in v.dimensions)
            if not shape:
                var.assignValue(v.getValue())
                continue
            if "hru" not in v.dimensions and "gru" not in v.dimensions:
                var[:] = v[:]
                continue
            axis = v.dimensions.index("hru" if "hru" in v.dimensions else "gru")
            data = np.full(shape, fill if fill is not None else 0, dtype=v.dtype)
            start = 0
            for k, s in enumerate(srcs):
                part = np.array(s[name][:])
                if name in ("hruId", "gruId"):
                    part = part + (hru_offsets[k] if name == "hruId" else k)
                if name == "hru2gruId":
                    part = part + k
                if name == "cell2hruId":
                    part = np.where(part > 0, part + hru_offsets[k], part)
                idx = [slice(0, n) for n in part.shape]
                idx[axis] = slice(start, start + part.shape[axis])
                data[tuple(idx)] = part
                start += part.shape[axis]
            var[:] = data
    for s in srcs:
        s.close()


def build(name, spec, cases_dir):
    dest = os.path.abspath(os.path.join(cases_dir, spec["dest"]))
    inputs = os.path.join(dest, "summa_inputs")
    if not os.path.isdir(inputs):
        template = os.path.abspath(os.path.join(cases_dir, spec["template"]))
        shutil.copytree(template, inputs, ignore=shutil.ignore_patterns("attributes.nc", "coldState.nc", "forcingFileList.txt"))
    months = months_between(spec["first_month"], spec["last_month"])
    copy_forcing = spec.get("copy_forcing", True)
    with tempfile.TemporaryDirectory() as tmp:
        if "merge" in spec:
            parts = []
            for k, dom in enumerate(spec["merge"]):
                out = os.path.join(tmp, dom)
                c = domain_cold_state(dom, spec["first_month"], out)
                parts.append((c, out))
            offsets, n = [], 0
            for c, out in parts:
                offsets.append(n)
                with nc4.Dataset(os.path.join(out, "attributes_glac.nc")) as a:
                    n += len(a.dimensions["hru"])
            merge_netcdf([os.path.join(o, "attributes_glac.nc") for _, o in parts], os.path.join(inputs, "attributes.nc"), offsets)
            merge_netcdf([os.path.join(o, "coldstate_glac.nc") for _, o in parts], os.path.join(inputs, "coldState.nc"), offsets)
            forcing = os.path.join(dest, "forcing")
            os.makedirs(forcing, exist_ok=True)
            names = []
            per_domain = [forcing_files(forcing_dir_of(c, spec["forcing"]), months) for c, _ in parts]
            for m, files in zip(months, zip(*per_domain)):
                fname = spec["forcing_name"].format(Y=m[:4], M=m[4:])
                merge_netcdf(files, os.path.join(forcing, fname), offsets)
                names.append(fname)
            write_file_list(os.path.join(inputs, "forcingFileList.txt"), names)
            print(f"{name}: {len(parts)} domains merged, {len(names)} forcing files in {forcing}")
            return

        c = domain_cold_state(spec["domain"], spec["first_month"], tmp)
        source = forcing_dir_of(c, spec["forcing"])
        files = forcing_files(source, months)
        if "stream" in spec:
            settings = os.path.join(tmp, "settings")
            shutil.copytree(os.path.join(c["project_dir"], "settings", "SUMMA"), settings)
            shutil.copy(os.path.join(tmp, "attributes_glac.nc"), os.path.join(settings, "attributes_glac.nc"))
            shutil.copy(os.path.join(tmp, "coldstate_glac.nc"), os.path.join(settings, "coldstate_glac.nc"))
            write_file_list(os.path.join(settings, "forcingFileList.txt"), [os.path.basename(f) for f in files])
            built = os.path.join(tmp, "built")
            s = spec["stream"]
            subprocess.run([sys.executable, os.path.join(SUMMA_DIR, "utils", "pre-processing", "add_stream_hru.py"),
                            settings, source, built, "--attributes", "attributes_glac.nc", "--cold-state", "coldstate_glac.nc",
                            "--first-month", spec["first_month"], "--last-month", spec["last_month"],
                            "--length", str(s["length"]), "--slope", str(s["slope"]), "--width", str(s["width"]),
                            "--elevation", str(s["elevation"]), "--latitude", str(s["latitude"]),
                            "--longitude", str(s["longitude"])], check=True)
            for f in ("attributes.nc", "coldState.nc", "forcingFileList.txt"):
                shutil.copy(os.path.join(built, "summa_inputs", f), os.path.join(inputs, f))
            shutil.copy(os.path.join(built, "topology.nc"), os.path.join(dest, "topology.nc"))
            if os.path.isdir(os.path.join(dest, "forcing")):
                shutil.rmtree(os.path.join(dest, "forcing"))
            shutil.copytree(os.path.join(built, "forcing"), os.path.join(dest, "forcing"))
            print(f"{name}: stream HRU added, {len(files)} forcing files in {dest}/forcing")
            return

        shutil.copy(os.path.join(tmp, "attributes_glac.nc"), os.path.join(inputs, "attributes.nc"))
        shutil.copy(os.path.join(tmp, "coldstate_glac.nc"), os.path.join(inputs, "coldState.nc"))
        write_file_list(os.path.join(inputs, "forcingFileList.txt"), [os.path.basename(f) for f in files])
        if copy_forcing:
            forcing = os.path.join(dest, "forcing")
            if os.path.isdir(forcing):
                shutil.rmtree(forcing)
            os.makedirs(forcing)
            for f in files:
                shutil.copy(f, forcing)
            print(f"{name}: {len(files)} forcing files copied to {forcing}")
        else:
            with open(os.path.join(dest, "forcing_path.txt"), "w") as f:
                f.write(source + "/\n")
            print(f"{name}: forcing read in place from {source}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("cases", help="cases.yaml")
    p.add_argument("names", nargs="*", help="cases to build, default all")
    a = p.parse_args()
    with open(a.cases) as f:
        cases = yaml.safe_load(f)
    cases_dir = os.path.dirname(os.path.abspath(a.cases))
    for name in a.names or cases:
        build(name, cases[name], cases_dir)


if __name__ == "__main__":
    main()
