# summa_glacier_workflow

The glacier setup and runs of SUMMA on Gulkana and Wolverine glaciers, Alaska: from global glacier
products and on-site observations to the domains, the tests and the full 2008–2022 calibrations of the
glacier paper. It sits beside the `summa` checkout, uses its executables and two of its scripts
(`utils/pre-processing/observation_netcdf.py` and `add_stream_hru.py`); set `SUMMA_DIR` if summa is
elsewhere.

## Layout

| Path | What |
| --- | --- |
| `data/domain_{Gulkana,Wolverine}/` | each domain: the SYMFLUENCE upland domain, raw ERA5 2008–2022, the USGS station records, stakes and observations, copied in; and everything the pipeline writes |
| `domains/{gulkana,wolverine}.yaml` | each domain's bounding box, gauge, data paths and setup choices |
| `setup_glacier_domain.py` | runs the glacier pipeline on a domain, `--steps` to pick some |
| `cases.yaml`, `build_cases.py` | builds the tests and runs from the domains |
| `tests/` | short calibrations of each glacier (`test_calibration_{gulkana,wolverine}.sh`) |
| `runs/` | the four full runs and `calibrate.py`, which calibrates them and evaluates their fronts |
| `notebooks/glacier_setup.ipynb` | the pipeline step by step, with plots |
| `notebooks/glacier_plots.ipynb` | discharge, storage and glacier-surface plots of a glacier run |

The pipeline's scripts: `glacier_rasters.py`, `glacier_extend.py`, `glacier_zonal_stats.py`,
`correct_forcing_to_station.py`, `spechum_ratio_from_campaign.py` and `glacier_cold_state.py`; and
`acquire_glacier_mass_balance.py` for the mass-balance observations. `wolverine_network.json` is
Wolverine Creek's tributary network for summa's `add_stream_network.py`.

## Building

```bash
./setup_glacier_domain.py domains/gulkana.yaml       # rasters extend zonal forcing coldstate
./setup_glacier_domain.py domains/wolverine.yaml
./build_cases.py cases.yaml                          # every test and run, or name some
```

1. **rasters.** RGI 6.0 outlines, replaced by the Herreid and Pellicciotti (2020) outline where it has
   one. Their ablation zones (buffered 50 m) and debris cover give the domain type: 1 upland,
   2 accumulation, 3 clean ablation, 4 debris ablation. Debris thickness is Rounce et al. (2021), raised
   to 4 cm where thinner. The bed is the surface less the Millan et al. (2022) thickness.
2. **extend.** The basin is delineated on the bed above the gauge, and each glacier at least 80% inside
   it gets room to advance by dragging its terminus downstream.
3. **zonal.** Per-HRU debris thickness, domain-type cell counts, and elevation, slope and aspect of each
   domain type; and the HRU of every DEM cell.
4. **forcing.** The station correction:
   - air temperature by an offset per HRU, month and wet or dry hour;
   - humidity by a ratio on the same split;
   - shortwave and pressure by one ratio per HRU;
   - wind by the monthly station ratio;
   - snowfall in the stake intervals scaled to the stakes' winter balances.

   Wolverine's HRUs without stakes take the SA-shielded gauge. Gulkana's April–August humidity comes from
   Wilson et al.'s 2024 Site B station. The output, `forcing/SUMMA_input/station_corrected`, reproduces
   the forcing of the 15–16 Oct calibrations exactly.
5. **coldstate.** `attributes_glac.nc` and `coldstate_glac.nc`:
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
spin-up over 2008, on the 30 parameters of the 16 Oct calibrations. The evaluation reruns each front member
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
| Glacier thickness (Millan et al., 2022) | https://www.sedoo.fr/theia-publication-products/?uuid=55acbdd5-3982-4eac-89b2-46703557938c |
| USGS benchmark-glacier stations, stakes and glacier-wide balances | https://www.sciencebase.gov/catalog/item/6441de03d34ee8d4ade7d2a5 |
| Gulkana 2024 Site B station (Wilson et al.) | `data/domain_Gulkana/Wilson_gulkana_2024_data` |

The forcing, station records and built forcing are git-ignored (about 1 GB). Discharge and water
temperature come from summa's `acquire_streamflow.py` and `acquire_stream_temperature.py`.

## Environment

numpy, netCDF4, xarray, rasterio, geopandas, rasterstats, scipy, pandas, shapely, pyproj and pyyaml; the
`modflow6` conda environment has them all. `glacier_extend.py` also needs pysheds: with numpy 2, the fork
`pip install git+https://github.com/ashleymedin/pysheds.git`, which still calls `np.in1d` (removed in numpy
2.4; replace it with `np.isin`). `spechum_ratio_from_campaign.py` pulls ERA5 with gcsfs and zarr, unless its
cached pulls (`forcing/spechum_ratios_*_era5_*.npz`) are present.
