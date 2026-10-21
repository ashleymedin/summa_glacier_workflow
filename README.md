# summa_glacier_workflow

The glacier setup and runs of SUMMA on Gulkana and Wolverine glaciers, Alaska: from global glacier
products and on-site observations to the domains, the tests and the full 2008–2022 calibrations of the
glacier paper. It sits beside the `summa` checkout and uses its executables; set `SUMMA_DIR` if summa is
elsewhere.

## Layout

| Path | What |
| --- | --- |
| `data/domain_{Gulkana,Wolverine}/` | each domain: the SYMFLUENCE upland domain, raw ERA5 2008–2022, the USGS station records, stakes and observations, copied in; and everything the pipeline writes |
| `data/external/` | RGI 6.0, Herreid and Pellicciotti debris extent, Rounce debris thickness and Millan ice thickness (the domain YAMLs' `data:` paths); not in git |
| `domains/{gulkana,wolverine}.yaml` | each domain's bounding box, gauge, data paths and setup choices |
| `setup_glacier_domain.py` | runs the glacier pipeline on a domain, `--steps` to pick some |
| `cases.yaml`, `build_cases.py` | builds the tests and runs from the domains |
| `tests/` | short calibrations of each glacier (`test_calibration_{gulkana,wolverine}.sh`) |
| `runs/` | the four full runs and `calibrate.py`, which calibrates them and evaluates their fronts |
| `notebooks/glacier_setup.ipynb` | the pipeline step by step, with plots |
| `notebooks/glacier_plots.ipynb` | discharge, storage and glacier-surface plots of a glacier run |

The pipeline's scripts: `glacier_rasters.py`, `glacier_extend.py`, `glacier_zonal_stats.py`,
`correct_forcing_to_station.py`, `spechum_ratio_from_campaign.py` and `glacier_cold_state.py`; and
`acquire_glacier_mass_balance.py` for the mass-balance observations. `acquire_balance_profile.py` writes the USGS
yearly balance profiles as a `glacierMassBalFile`, which `runs/rerun_trials.py --massbal` gives the flow model in
place of the simulated balance (USGS heights are ellipsoidal, 16.1 m above the model's at Gulkana, 14.0 at Wolverine).

`check_glacier_imagery.py` checks a domain's starting glacier and debris extent against the late-summer
Landsat or Sentinel-2 scene with the least cloud and snow, writing areas, classes and a figure per date to
`observations/imagery`.

The observation scripts `acquire_streamflow.py`, `acquire_stream_temperature.py`, `acquire_grace_tws.py` and
`acquire_groundwater_level.py` fetch records from the web and write them with `observation_netcdf.py`, in the
form a SUMMA calibration target reads. `add_stream_hru.py` gives a one-GRU domain a stream HRU and a one-reach
mizuRoute topology; `add_stream_network.py` splits tributary GRUs off it, each with its own reach, from a JSON
spec such as `wolverine_network.json`, Wolverine Creek's tributary network. `add_wetland.py` gives an HRU a
wetland domain (a proglacial lake or wetted forefield) copied from the stream domain's column, and
`acquire_lake_area.py` measures open water in a box on every Sentinel-2 scene, beside the gauged flow, to size it.

## Building

```bash
./setup_glacier_domain.py domains/gulkana.yaml       # rasters extend hrus zonal forcing coldstate
./setup_glacier_domain.py domains/wolverine.yaml
./build_cases.py cases.yaml                          # every test and run, or name some
```

1. **rasters.** RGI 6.0 outlines, replaced by the Herreid and Pellicciotti (2020) outline where it has
   one, and the benchmark glacier's by its last USGS survey outline before 2008 (`usgs_outline`: Gulkana
   11 August 2007, Wolverine 8 August 2006). Their ablation zones (buffered 50 m) and debris cover give the
   domain type: 1 upland, 2 accumulation, 3 clean ablation, 4 debris ablation. Debris thickness is Rounce
   et al. (2021), raised to 4 cm where thinner. The bed is the glacier surface less the Millan et al. (2022)
   thickness, filled from the nearest Millan cell where an outline reaches past it. The glacier surface is the DEM, or that survey's own DEM on the
   glacier where `usgs_outline` names one (`dem`), levelled to the DEM on the ground around it. Where the survey
   covers less than half a cell, its change from the DEM is carried harmonically to zero at the ice-free ground.
2. **extend.** The basin is delineated on the bed above the gauge, and each glacier at least 80% inside
   it gets room to advance by dragging its terminus downstream.
3. **hrus.** Each HRU's area, centre, elevation, slope and contour length in `attributes.nc` and the HRU
   shapefile, from its polygon (in `utm_crs`) and the DEM.
4. **zonal.** Per-HRU debris thickness, domain-type cell counts, and elevation, slope and aspect of each
   domain type; and the HRU of every DEM cell.
5. **forcing.** The station correction:
   - air temperature by an offset per HRU, month and wet or dry hour;
   - humidity by a ratio on the same split;
   - shortwave and pressure by one ratio per HRU;
   - wind by the monthly station ratio;
   - snowfall in the stake intervals scaled to the stakes' winter balances;
   - on Gulkana (`gauge_rain`), the rest of the precipitation by the undercatch-corrected 1480 and 1725 m
     gauges' monthly ratio to the forcing, interpolated in elevation: about 1.15 in June and 1.5–3 in
     July–September, where ERA5 has half the gauged rain.

   Wolverine's HRUs without stakes take the SA-shielded gauge. Gulkana's April–August humidity comes from
   Wilson et al.'s 2024 Site B station. The output is `forcing/SUMMA_input/station_corrected`.
6. **coldstate.** `attributes_glac.nc` and `coldstate_glac.nc`:
   - **Ice:** five layers, 0.15 to 23 m, starting at −5 °C, with ice fraction 0.90 to 0.98 down the column.
   - **Debris:** 2 to 5 soil layers over the ice, enough for the thickest debris cell in the HRU. The top
     layer is at most 5 cm and each layer below is a fixed ratio times the one above, as SUMMA re-splits
     the debris at each glacier update.
   - **Soil and debris temperature:** 1.5 °C above the HRU's mean air temperature over its first 12
     forcing months.

`build_cases.py` gives each case the domain's attributes and a cold state started from the case's own
first month, the year the calibration spins up over:

| Case | Where | Forcing | Scored |
| --- | --- | --- | --- |
| `gulkana_test` | `tests/gulkana` | raw, 2008–2012 | 2009–2012, discharge + mass balance |
| `wolverine_test` | `tests/wolverine` | raw, 2016–2019, stream HRU | 2017–2019, discharge + temperature + mass balance |
| `gulkana_wolverine` | summa `utils/test/test_calibration/gulkana_wolverine` | raw, Oct 2008 – Dec 2011, 2 GRUs | Oct 2009 – Dec 2011, each glacier's mass balance |
| `{gulkana,wolverine}_{raw,corrected}` | `runs/` | raw or station-corrected, 2008–2022 | calibrated 2009–2015, evaluated 2016–2022 |

## The full runs

```bash
cd runs
./calibrate.py calibrate gulkana_raw --population 32 --generations 15 --ranks 9
./calibrate.py evaluate  gulkana_raw --ranks 2
```

The calibration scores discharge and the glacier-wide seasonal mass balance over 2009–2015, after a
spin-up over 2008. `--search paper1` (the default) searches the paper-1 calibrations' 29 parameters, one soil for
every domain and debrisConc pinned at 1 kg m-3. `--search domain` searches 32: the upland soil and the debris
apart (`name@upland`, `name@glacDbr`), their sand fractions setting the conductivity of the solids, and debrisConc;
it needs a SUMMA with `[calibration.parameter_bounds]` and the debris values that `domain_soil_params.py` writes
into trialParams.nc. Wall erosion is fixed at 1 mm yr-1. The evaluation reruns each front member
over 2009–2022 with its parameters pinned and scores 2016–2022, adding Wolverine's water temperature,
which the gauge records only from 2016. It writes `evaluation/evaluation.csv`. The observations for
2008–2022 are in each domain's `observations/calibration`.

## Data

Downloaded by hand to the paths in the domain YAMLs:

| Product | Source |
| --- | --- |
| RGI 6.0 outlines, region 01 | https://daacdata.apps.nsidc.org/pub/DATASETS/nsidc0770_rgi_v6/ |
| Debris cover, ablation zones and outlines (Herreid and Pellicciotti, 2020), S1 | https://zenodo.org/records/3866466/files/SupplementaryInformation.zip |
| Debris thickness (Rounce et al., 2021) | https://n5eil01u.ecs.nsidc.org/HMA/HMA_DTE.001/2000.01.01/ |
| USGS benchmark-glacier survey outlines (McNeil et al., 2019, ver. 3.0), to `GlacierDEM/` | https://doi.org/10.5066/P9R8BP3K |
| Glacier thickness (Millan et al., 2022) | https://www.sedoo.fr/theia-publication-products/?uuid=55acbdd5-3982-4eac-89b2-46703557938c |
| USGS benchmark-glacier stations, stakes and glacier-wide balances | https://www.sciencebase.gov/catalog/item/6441de03d34ee8d4ade7d2a5 |
| Gulkana 2024 Site B station (Wilson et al.) | `data/domain_Gulkana/Wilson_gulkana_2024_data` |

The forcing, station records and built forcing are git-ignored (about 1 GB). Discharge and water
temperature come from `acquire_streamflow.py` and `acquire_stream_temperature.py`.

## Environment

```bash
conda env create -f environment.yml    # the glacier environment: every script here, pysheds and the imagery tools
conda activate glacier
```

The pysheds fork still calls `np.in1d`, so numpy stays below 2.4. `spechum_ratio_from_campaign.py` pulls ERA5
with gcsfs and zarr, unless its cached pulls (`forcing/spechum_ratios_*_era5_*.npz`) are present.
