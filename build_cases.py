#!/usr/bin/env python3
"""Build the SUMMA cases (tests and full runs) of cases.yaml from the glacier domains in data/.

Each case takes its domain's attributes_glac.nc and a cold state written for its own first forcing month
(glacier_cold_state.py --start), so the soil starts from the air temperature of the year the run spins up
over. Its text settings and trialParams.nc are the case's own, kept in <dest>/summa_inputs. Its forcing is
the domain's raw ERA5 (forcing/SUMMA_input) or the station correction (forcing/SUMMA_input/station_corrected)
over the case's months: copied into <dest>/forcing for a test, read in place for a run. The soil parameters
that differ between the upland soil and the debris are then written into its trialParams.nc (domain_soil_params.py).

  stream  the domain gets a stream HRU and a one-reach topology (add_stream_hru.py), whose forcing
          and topology are written into <dest>
  merge   two domains become one, one GRU each, with their HRUs, glacier grids and forcing side by side

    ./build_cases.py cases.yaml gulkana_test wolverine_test
"""

import argparse
import csv
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


def set_precip_grad(inputs, source):
    """precipElevGrad in the case's localParamInfo.txt, from the station correction's corrections.csv (0 without one)."""
    grad = 0.0
    path = os.path.join(source, "corrections.csv")
    if os.path.exists(path):
        for row in csv.reader(open(path)):
            if row and row[0] == "precipElevGrad_per_m":
                grad = float(row[1])
    params = os.path.join(inputs, "localParamInfo.txt")
    lines = [l for l in open(params) if l.split("|")[0].strip() != "precipElevGrad"]
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.append(f"{'precipElevGrad':<26}| {grad:12.5f} | {0.0:12.4f} | {0.005:12.4f}\n")
    open(params, "w").writelines(lines)


def merge_netcdf(paths, out, concat, shift, keep=None):
    """One file of several domains' files, concatenated along the dimensions in concat, the others padded to
    the largest, padding at each variable's fill value, compressed; shift(name, values, k) renumbers part k's
    ids. keep, if given, lists the variables written."""
    srcs = [nc4.Dataset(p) for p in paths]
    for s in srcs:
        s.set_auto_mask(False)
    with nc4.Dataset(out, "w", format="NETCDF4") as d:
        for name in srcs[0].dimensions:
            size = sum(len(s.dimensions[name]) for s in srcs) if name in concat else \
                max(len(s.dimensions[name]) for s in srcs if name in s.dimensions)
            d.createDimension(name, size)
        for name, v in srcs[0].variables.items():
            if keep is not None and name not in keep:
                continue
            fill = getattr(v, "_FillValue", None)
            var = d.createVariable(name, v.dtype, v.dimensions, fill_value=fill, zlib=v.dtype != str, complevel=4)
            var.setncatts({k: v.getncattr(k) for k in v.ncattrs() if k != "_FillValue"})
            shape = tuple(len(d.dimensions[x]) for x in v.dimensions)
            if not shape:
                var.assignValue(v.getValue())
                continue
            axes = [v.dimensions.index(c) for c in concat if c in v.dimensions]
            if not axes:
                var[:] = v[:]
                continue
            axis = axes[0]
            data = np.full(shape, fill if fill is not None else 0, dtype=v.dtype)
            start = 0
            for k, s in enumerate(srcs):
                part = shift(name, np.array(s[name][:]), k)
                idx = [slice(0, n) for n in part.shape]
                idx[axis] = slice(start, start + part.shape[axis])
                data[tuple(idx)] = part
                start += part.shape[axis]
            var[:] = data
    for s in srcs:
        s.close()


def summa_shift(hru_offsets):
    """Renumbering of a SUMMA file's ids when domains are merged: HRUs by hru_offsets, GRUs and reaches by part."""
    def shift(name, part, k):
        if name == "hruId":
            return part + hru_offsets[k]
        if name in ("gruId", "hru2gruId"):
            return part + k
        if name == "cell2hruId":
            return np.where(part > 0, part + hru_offsets[k], part)
        if name == "streamSegId":
            return np.where(part > 0, part + k, part)
        return part
    return shift


def topology_shift(name, part, k):
    """Renumbering of a one-reach topology when domains are merged: the GRU, its reach and the reach below."""
    if name in ("hruId", "hruToSegId", "segId"):
        return part + k
    if name == "downSegId":
        return np.where(part > 0, part + k, part)
    return part


def write_trial_params(trial, attributes):
    """trialParams.nc of a merged domain: its HRU and GRU ids, and the per-GRU values the case's own
    trialParams.nc already holds (by GRU), the rest at their defaults."""
    keep = {}
    if os.path.exists(trial):
        with nc4.Dataset(trial) as t:
            keep = {v: np.array(t[v][:]) for v in t.variables if t[v].dimensions == ("gru",) and v != "gruId"}
    with nc4.Dataset(attributes) as a:
        hru_ids, gru_ids = np.array(a["hruId"][:]), np.array(a["gruId"][:])
    with nc4.Dataset(trial, "w", format="NETCDF4") as d:
        d.createDimension("hru", len(hru_ids))
        d.createDimension("gru", len(gru_ids))
        d.createVariable("hruId", "i4", ("hru",))[:] = hru_ids
        d.createVariable("gruId", "i4", ("gru",))[:] = gru_ids
        for name, values in keep.items():
            if len(values) != len(gru_ids):
                raise SystemExit(f"{trial}: {name} has {len(values)} GRUs, the domain {len(gru_ids)}")
            d.createVariable(name, "f8", ("gru",))[:] = values


def stream_domain(c, spec, stream, first, last, tmp, files, source):
    """The domain with a stream HRU and a one-reach topology, built by add_stream_hru.py in tmp/built."""
    settings = os.path.join(tmp, "settings")
    shutil.copytree(os.path.join(c["project_dir"], "settings", "SUMMA"), settings)
    shutil.copy(os.path.join(tmp, "attributes_glac.nc"), os.path.join(settings, "attributes_glac.nc"))
    shutil.copy(os.path.join(tmp, "coldstate_glac.nc"), os.path.join(settings, "coldstate_glac.nc"))
    write_file_list(os.path.join(settings, "forcingFileList.txt"), [os.path.basename(f) for f in files])
    built = os.path.join(tmp, "built")
    subprocess.run([sys.executable, os.path.join(HERE, "add_stream_hru.py"),
                    settings, source, built, "--attributes", "attributes_glac.nc", "--cold-state", "coldstate_glac.nc",
                    "--first-month", first, "--last-month", last,
                    "--length", str(stream["length"]), "--slope", str(stream["slope"]), "--width", str(stream["width"]),
                    "--elevation", str(stream["elevation"]), "--latitude", str(stream["latitude"]),
                    "--longitude", str(stream["longitude"])], check=True)
    return built


def build(name, spec, cases_dir):
    """A case's inputs, then the soil parameters that differ by domain type (domain_soil_params.py)."""
    build_inputs(name, spec, cases_dir)
    inputs = os.path.join(os.path.abspath(os.path.join(cases_dir, spec["dest"])), "summa_inputs")
    subprocess.run([sys.executable, os.path.join(HERE, "domain_soil_params.py"), inputs], check=True)


def build_inputs(name, spec, cases_dir):
    dest = os.path.abspath(os.path.join(cases_dir, spec["dest"]))
    inputs = os.path.join(dest, "summa_inputs")
    if not os.path.isdir(inputs):
        template = os.path.abspath(os.path.join(cases_dir, spec["template"]))
        shutil.copytree(template, inputs, ignore=shutil.ignore_patterns("attributes.nc", "coldState.nc", "forcingFileList.txt"))
    months = months_between(spec["first_month"], spec["last_month"])
    copy_forcing = spec.get("copy_forcing", True)
    with tempfile.TemporaryDirectory() as tmp:
        if "merge" in spec:
            parts = []  # (config, folder with attributes.nc, coldState.nc, trialParams.nc and forcing/, topology or None)
            for k, part in enumerate(spec["merge"]):
                out = os.path.join(tmp, part["domain"])
                c = domain_cold_state(part["domain"], spec["first_month"], out)
                files = forcing_files(forcing_dir_of(c, spec["forcing"]), months)
                if "stream" in part:
                    built = stream_domain(c, spec, part["stream"], spec["first_month"], spec["last_month"], out, files,
                                          forcing_dir_of(c, spec["forcing"]))
                    parts.append((c, os.path.join(built, "summa_inputs"), sorted(glob.glob(os.path.join(built, "forcing", "*.nc"))),
                                  os.path.join(built, "topology.nc")))
                else:
                    shutil.copy(os.path.join(out, "attributes_glac.nc"), os.path.join(out, "attributes.nc"))
                    shutil.copy(os.path.join(out, "coldstate_glac.nc"), os.path.join(out, "coldState.nc"))
                    shutil.copy(os.path.join(c["project_dir"], "settings", "SUMMA", "trialParams.nc"), os.path.join(out, "trialParams.nc"))
                    parts.append((c, out, files, None))
            offsets, n = [], 0
            for _, folder, _, _ in parts:
                offsets.append(n)
                with nc4.Dataset(os.path.join(folder, "attributes.nc")) as a:
                    n += len(a.dimensions["hru"])
            shift = summa_shift(offsets)
            for f in ("attributes.nc", "coldState.nc"):
                merge_netcdf([os.path.join(folder, f) for _, folder, _, _ in parts], os.path.join(inputs, f), ("hru", "gru"), shift)
            write_trial_params(os.path.join(inputs, "trialParams.nc"), os.path.join(inputs, "attributes.nc"))
            if all(top for _, _, _, top in parts):
                merge_netcdf([top for _, _, _, top in parts], os.path.join(dest, "topology.nc"), ("hru", "seg"), topology_shift)
            forcing = os.path.join(dest, "forcing")
            if os.path.isdir(forcing):
                shutil.rmtree(forcing)
            os.makedirs(forcing)
            names = []
            for m, month_files in zip(months, zip(*[files for _, _, files, _ in parts])):
                fname = spec["forcing_name"].format(Y=m[:4], M=m[4:])
                merge_netcdf(month_files, os.path.join(forcing, fname), ("hru",), shift)
                names.append(fname)
            write_file_list(os.path.join(inputs, "forcingFileList.txt"), names)
            print(f"{name}: {len(parts)} domains merged, {len(names)} forcing files in {forcing}")
            return

        c = domain_cold_state(spec["domain"], spec["first_month"], tmp)
        source = forcing_dir_of(c, spec["forcing"])
        files = forcing_files(source, months)
        if "stream" in spec:
            built = stream_domain(c, spec, spec["stream"], spec["first_month"], spec["last_month"], tmp, files, source)
            for f in ("attributes.nc", "coldState.nc", "forcingFileList.txt"):
                shutil.copy(os.path.join(built, "summa_inputs", f), os.path.join(inputs, f))
            shutil.copy(os.path.join(built, "topology.nc"), os.path.join(dest, "topology.nc"))
            if os.path.isdir(os.path.join(dest, "forcing")):
                shutil.rmtree(os.path.join(dest, "forcing"))
            shutil.copytree(os.path.join(built, "forcing"), os.path.join(dest, "forcing"))
            print(f"{name}: stream HRU added, {len(files)} forcing files in {dest}/forcing")
            return

        set_precip_grad(inputs, source)
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
