#!/usr/bin/env python3
"""Build the SUMMA cases (tests and full runs) of cases.yaml from the glacier domains in data/.

Each case takes its domain's attributes_glac.nc and a cold state written for its own first forcing month
(glacier_cold_state.py --start), so the soil starts from the air temperature of the year the run spins up
over. Its text settings and trialParams.nc are the case's own, kept in <dest>/summa_inputs. Its forcing is
the domain's raw ERA5 (forcing/SUMMA_input) or the station correction (forcing/SUMMA_input/station_corrected)
over the case's months: copied into <dest>/forcing for a test, read in place for a run. The soil parameters
that differ between the upland soil and the debris are then written into its trialParams.nc (domain_soil_params.py).

  stream   the domain gets a stream HRU and a one-reach topology (add_stream_hru.py), whose forcing
           and topology are written into <dest>, with the mizuRoute parameters of `routing`
           (default tests/wolverine/mizuroute.param), their wscale set to the reach width
  wetland  a stream case gets a wetland domain (add_wetland.py) of the given area (m2) and elevation (m) in one
           land HRU, the lowest unless `hru` gives its hruId; `depth` (m) and `temp` (K) start its water.
           `outlet_depth` [value, lower, upper] is wetlandMinDepth, its mean depth filled to the outlet (m);
           `max_area` (m2) lets its area follow its volume up to that, and `mask` (an index of the domain's
           observations.lake_area boxes) writes the cells it fills once free of ice (wetland_mask.py)
  merge    two domains become one, one GRU each, with their HRUs, glacier grids and forcing side by side
  decisions  choices of modelDecisions.txt that differ from the template's

    ./build_cases.py cases.yaml gulkana_test wolverine_test
"""

import argparse
import csv
import glob
import os
import re
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
                    "--domain", c["domain"], "--utm-epsg", str(c["utm_epsg"]), "--start", start, "--soil-offset", str(c.get("soil_offset", 1.5)),
                    "--ice-temp", str(c.get("ice_temp", -5.0)), "--output-dir", out_dir], check=True)
    return c


def forcing_dir_of(c, forcing):
    base = os.path.join(c["project_dir"], "forcing", "SUMMA_input")
    return base if forcing == "raw" else os.path.join(base, "station_corrected")


def csv_row(path, key):
    """The values after key in the first column of a corrections.csv or remap.csv, or None."""
    if os.path.exists(path):
        for row in csv.reader(open(path)):
            if row and row[0] == key:
                return [float(x) for x in row[1:]]
    return None


def set_param_line(params, name, value, lower, upper):
    lines = [l for l in open(params) if l.split("|")[0].strip() != name]
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.append(f"{name:<26}| {value:12.6f} | {lower:12.4f} | {upper:12.4f}\n")
    open(params, "w").writelines(lines)


def set_precip_grad(inputs, source):
    """precipElevGrad and tempLapseRate in the case's localParamInfo.txt: the gradient from the station correction's
    corrections.csv (0 without one), the lapse rate the year's mean of the monthly ones the forcing was carried to the
    HRUs with (corrections.csv, else remap_forcing's remap.csv)."""
    path = os.path.join(source, "corrections.csv")
    params = os.path.join(inputs, "localParamInfo.txt")
    grad = csv_row(path, "precipElevGrad_per_m")
    set_param_line(params, "precipElevGrad", grad[0] if grad else 0.0, 0.0, 0.005)
    lapse = csv_row(path, "lapse_rate_K_per_km") or csv_row(os.path.join(source, "remap.csv"), "lapse_rate_K_per_km")
    if lapse is None:
        raise SystemExit(f"no lapse_rate_K_per_km in {source}/corrections.csv or remap.csv; rerun remap_forcing.py")
    set_param_line(params, "tempLapseRate", -np.mean(lapse[:12]) / 1000.0, 0.0, 0.0098)
    set_wind_factor(params, wind_exposure_station() if os.path.exists(path) else 1.0)
    set_param_line(params, "glacierTempReduction", air_cooling_station(), 0.5, 0.9)


# glacier wind and air temperature above freezing over the forcing station's, from Gulkana Site B (Wilson et al. 2026),
# wind_exposure_from_campaign.py and air_cooling_from_campaign.py
WIND_EXPOSURE_CSV = os.path.join(HERE, "data", "domain_Gulkana", "forcing", "wind_exposure_wilson2024.csv")
AIR_COOLING_CSV = os.path.join(HERE, "data", "domain_Gulkana", "forcing", "air_cooling_wilson2024.csv")


def wind_exposure_station():
    """The campaign's heat-weighted ratio of glacier-surface wind to the reference station's."""
    for row in csv.DictReader(open(WIND_EXPOSURE_CSV)):
        if row["month"] == "all":
            return float(row["heat_weighted_ratio"])
    raise SystemExit(f"no campaign ratio in {WIND_EXPOSURE_CSV}")


def air_cooling_station():
    """The campaign's glacier-surface air temperature above freezing as a fraction of the station's (searched on ERA5)."""
    for row in csv.DictReader(open(AIR_COOLING_CSV)):
        if row["month"] == "all":
            return float(row["factor"])
    raise SystemExit(f"no campaign factor in {AIR_COOLING_CSV}")


def set_wind_factor(params, value):
    """glacierWindFactor in localParamInfo.txt, the glacier surface wind over the forcing's: the campaign's
    on station-corrected wind, 1 on ERA5's (where it is searched); windExposure, which it replaces, is dropped."""
    lines = [l for l in open(params) if l.split("|")[0].strip() != "windExposure"]
    open(params, "w").writelines(lines)
    set_param_line(params, "glacierWindFactor", value, 0.3, 1.5)


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


def set_reach_width(routing, topology, width):
    """wscale in a one-reach case's mizuRoute parameters, so the reach is as wide as its stream HRU: mizuRoute's width
    is wscale x the square root of the area above the reach."""
    with nc4.Dataset(topology) as t:
        area = float(np.sum(t["area"][:]))
    text, n = re.subn(r"(?m)^(\s*wscale\s*=\s*)\S+", lambda m: f"{m.group(1)}{width / np.sqrt(area):.6g}", open(routing).read())
    if n != 1:
        raise SystemExit(f"{routing} has no wscale")
    open(routing, "w").write(text)


def wetland_domain(inputs, wetland, domain):
    """A wetland domain in one land HRU of the cold state in inputs (add_wetland.py); returns that HRU's id."""
    with nc4.Dataset(os.path.join(inputs, "attributes.nc")) as a:
        ids, elev = np.array(a["hruId"][:]), np.array(a["elevation"][:], float)
        land = np.array(a["streamSegId"][:]) <= 0
    if "hru" in wetland:
        found = np.where((ids == wetland["hru"]) & land)[0]
        if len(found) != 1:
            raise SystemExit(f"wetland: no land HRU {wetland['hru']} in {inputs}/attributes.nc")
        ix = int(found[0])
    else:
        ix = int(np.where(land, elev, np.inf).argmin())
    cold = os.path.join(inputs, "coldState.nc")
    args = [f"--{k}={wetland[k]}" for k in ("depth", "temp") if k in wetland]
    max_area = float(wetland.get("max_area", 0))
    if max_area > 0:
        args.append(f"--contour={np.sqrt(max(max_area, wetland['area']))}")
    subprocess.run([sys.executable, os.path.join(HERE, "add_wetland.py"), cold, cold + ".wet", "--hru", str(ix),
                    "--area", str(wetland["area"]), "--elev", str(wetland["elevation"]), *args], check=True)
    os.replace(cold + ".wet", cold)
    params = os.path.join(inputs, "localParamInfo.txt")
    if "outlet_depth" in wetland:
        set_param_line(params, "wetlandMinDepth", *wetland["outlet_depth"])
    if max_area > 0:
        set_param_line(params, "wetlandMaxArea", max_area, 0.0, 1e9)
    if "mask" in wetland:
        if max_area <= 0:
            raise SystemExit("wetland: a mask needs max_area")
        subprocess.run([sys.executable, os.path.join(HERE, "wetland_mask.py"), os.path.join(inputs, "attributes.nc"),
                        os.path.join(HERE, "domains", f"{domain}.yaml"), str(max_area), str(int(ids[ix])),
                        "--box", str(wetland["mask"])], check=True)
    return int(ids[ix])


def fit_trial_params(inputs):
    """trialParams.nc rewritten when it was made for another number of HRUs or domains than the case has."""
    trial, attributes = os.path.join(inputs, "trialParams.nc"), os.path.join(inputs, "attributes.nc")
    with nc4.Dataset(trial) as t, nc4.Dataset(attributes) as a, nc4.Dataset(os.path.join(inputs, "coldState.nc")) as s:
        stale = len(t.dimensions["hru"]) != len(a.dimensions["hru"]) or \
            ("dom" in t.dimensions and len(t.dimensions["dom"]) != len(s.dimensions["dom"]))
    if stale:
        write_trial_params(trial, attributes)


def set_decisions(inputs, decisions):
    """The case's own choices in modelDecisions.txt, each replacing the template's line of that name."""
    path = os.path.join(inputs, "modelDecisions.txt")
    lines, left = [], dict(decisions)
    for line in open(path):
        key = line.split()[0] if line.split() else ""
        if key in left:
            line = f"{key:<32}{left.pop(key):<16}!" + line.split("!", 1)[1]
        lines.append(line)
    if left:
        raise SystemExit(f"{path} has no decision {', '.join(left)}")
    open(path, "w").writelines(lines)


def build(name, spec, cases_dir):
    """A case's inputs, then the soil parameters that differ by domain type (domain_soil_params.py)."""
    build_inputs(name, spec, cases_dir)
    inputs = os.path.join(os.path.abspath(os.path.join(cases_dir, spec["dest"])), "summa_inputs")
    if "decisions" in spec:
        set_decisions(inputs, spec["decisions"])
    subprocess.run([sys.executable, os.path.join(HERE, "domain_soil_params.py"), inputs], check=True)


def build_inputs(name, spec, cases_dir):
    dest = os.path.abspath(os.path.join(cases_dir, spec["dest"]))
    inputs = os.path.join(dest, "summa_inputs")
    if not os.path.isdir(inputs):
        template = os.path.abspath(os.path.join(cases_dir, spec["template"]))
        shutil.copytree(template, inputs, ignore=shutil.ignore_patterns("attributes.nc", "coldState.nc", "forcingFileList.txt"))
    if os.path.exists(os.path.join(inputs, "coldState_cold.nc")):  # spinup.py would start from the old domain's state
        os.remove(os.path.join(inputs, "coldState_cold.nc"))
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
                    if "wetland" in part:
                        wetland_domain(os.path.join(built, "summa_inputs"), part["wetland"], part["domain"])
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
            set_precip_grad(inputs, source)
            built = stream_domain(c, spec, spec["stream"], spec["first_month"], spec["last_month"], tmp, files, source)
            for f in ("attributes.nc", "coldState.nc", "forcingFileList.txt"):
                shutil.copy(os.path.join(built, "summa_inputs", f), os.path.join(inputs, f))
            shutil.copy(os.path.join(built, "topology.nc"), os.path.join(dest, "topology.nc"))
            routing = os.path.join(dest, "mizuroute.param")
            if not os.path.exists(routing):
                shutil.copy(os.path.join(cases_dir, spec.get("routing", "tests/wolverine/mizuroute.param")), routing)
            set_reach_width(routing, os.path.join(dest, "topology.nc"), spec["stream"]["width"])
            if os.path.isdir(os.path.join(dest, "forcing")):
                shutil.rmtree(os.path.join(dest, "forcing"))
            shutil.copytree(os.path.join(built, "forcing"), os.path.join(dest, "forcing"))
            wet = f", wetland in HRU {wetland_domain(inputs, spec['wetland'], spec['domain'])}" if "wetland" in spec else ""
            fit_trial_params(inputs)
            print(f"{name}: stream HRU added{wet}, {len(files)} forcing files in {dest}/forcing")
            return
        if "wetland" in spec:
            raise SystemExit(f"{name}: a wetland needs a stream, whose water column it copies")

        set_precip_grad(inputs, source)
        shutil.copy(os.path.join(tmp, "attributes_glac.nc"), os.path.join(inputs, "attributes.nc"))
        shutil.copy(os.path.join(tmp, "coldstate_glac.nc"), os.path.join(inputs, "coldState.nc"))
        fit_trial_params(inputs)  # the template may be a case with another number of HRUs, as with a stream HRU
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
