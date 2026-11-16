# Too much snow on the added cases: firn that never becomes ice, and the new longwave

16 Nov 2026. All four calibrations on the pressure-level forcing are stopped. The two general ones were started
at 09:45 and killed. The two added ones never started, because the gulkana_added spin-up failed. Nothing is
running.

## What failed

`deploy_levels.sh` (`scratch/2026-11-11/overnight/`) finished the levels download (264 months), the remap, the
station correction, `build_cases.py` and three spin-ups on 15 Nov. **gulkana_added failed at spin-up cycle 18 of
30** (`runs/gulkana_added/spinup/run.log`):

```
check_icond/cannot initialize the model with volumetric fraction of ice > 0.70: layer = 9
```

The layer is snow on the **upland** domain of HRU 3, the top band (2,043 m). That domain has 9 snow layers about
20 m deep, holding 13.4 m w.e. Its bottom layer has ice fraction 0.81. Non-glacier snow may start at most
`maxVolIceContent` (0.70) + 0.1 (`check_icond.f90:476-498`). The spin-up repeats WY2005 (2004-10-01 to
2005-09-30), and in that year the HRU 3 upland keeps about **0.78 m w.e.** (12,596 → 13,373 kg m⁻² from one cycle
to the next). The HRU 3 glacier domain keeps about **1.75 m w.e.** (28,419 → 30,167).

The other cases at the end of their spin-ups, top band, from `runs/<case>/summa_inputs/coldState.nc`:

| Case | Upland SWE | Glacier SWE | Densest glacier snow layer |
|---|---|---|---|
| wolverine_added | 0.1 m w.e. | 40.6 m w.e. | 0.89 |
| gulkana_added (cycle 17) | 13.4 m w.e. | 30.2 m w.e. | 0.86 |
| wolverine_general | 0.2 m w.e. | 0.2 m w.e. | 0.42 |
| gulkana_general | 0.2 m w.e. | 0.3 m w.e. | 0.32 |

Under the previous forcing (git HEAD's `runs/gulkana_added/summa_inputs/coldState.nc`), gulkana_added had only
0.59 m w.e. of upland snow on HRU 3 after the full spin-up.

## Problem 1: glacier firn never becomes ice

In SUMMA, snow on a glacier domain stays snow. `layerMerge.f90` (around line 472) labels a merged layer
`iname_glce` only when `nSnow == 0`. Nothing turns old firn into glacier ice. In an accumulation zone the snow
therefore piles up every year (30–40 m w.e. after 30 spin-up years) and keeps compacting.

- On a glacier domain the snow limit is the firn value, `min(maxVolIceContent+0.15, 0.85)`. It is set in the
  same way in `check_icond.f90`, `computJacob.f90`, `computJacobWithPrime.f90` and `snowLakeGlceLiqFlux.f90`.
- The restart check allows +0.1 over that, so 0.95.
- wolverine_added already has 0.89 after a spin-up that passed. A later restart (rerun, evaluation) or a longer
  spin-up will hit the limit.
- Above the limit, `snowLakeGlceLiqFlux.f90:207` treats the layer as unable to hold water.
- Compaction is in `snowLakeGlceDepth.f90`.

Proposed fix: on a glacier domain, when the bottom snow layer (the one on the glacier ice) reaches the firn limit
or pore close-off, relabel it `iname_glce`. Mass, depth and enthalpy stay as they are. Things to check:

- `nSnow` and `nGlce` are recounted.
- The layer-merge and layer-divide rules still hold for snow above ice.
- `glacMass4AreaChange` and the glacier mass balance count the mass once, not twice.
- The enthalpy routines (`*_snLaGl`) already treat snow and glacier ice alike.

This is post-V3 glacier code, so it gets no changelog entry.

## Problem 2: the new longwave adds snow at the top bands

`remap_forcing.py` (commit 17c6131, pressure levels) scales the ERA5 cell longwave by
(T_free-air at the HRU / T_free-air at the ERA5 cell's surface)⁴. It scaled before too, but from the shapefile
`elev_m`, a DEM mean (Gulkana cells 1,651 and 1,850 m). Now it scales from ERA5's real orography (Gulkana cells
1,345/1,372 m). So the top band is now about 670 m above the cell instead of about 250 m.

- Gulkana HRU 3, WY2005 JJA mean longwave: **282 W m⁻²**, against 303 at HRU 1 (1,337 m). That is about 21 W m⁻²
  lower, roughly 0.45 m w.e. less melt per summer.
- `correct_forcing_to_station.py` corrects temperature and humidity to the stations but **copies longwave
  unchanged** (its docstring, line 6). Its HRU 3 offsets in summer are now about 0 K, so temperature and longwave
  agree with each other. The longwave is simply lower than before.
- The general cases get the same longwave but no stake multiplier, so it does not build snow there. They have the
  opposite problem: in WY2005 almost no snow survives anywhere on the glacier (0.2–0.3 m w.e. on the top band).

Open questions:

- Is constant-emissivity T⁴ scaling over 670 m right, or should emissivity follow the humidity (Konzelmann et al.
  1994, as TopoSCALE does)?
- Does any station in the domains measure incoming longwave to test it against?
- Should the station correction adjust longwave when it shifts temperature?

## Problem 3 (on top of 2): the stake precipitation multiplier falls on upland as well

For the added cases, `correct_forcing_to_station.py` multiplies each HRU's precipitation by a ratio fitted to
glacier stakes. In `runs/logs/2026-11-12/levels/forcing_gulkana.log`, HRU 3 gets **×3.207** from 14 stake-years
at 1,944–2,078 m, and `precipElevGrad` is 0.0019 m⁻¹. Forcing is per HRU, so the upland domains get the stake
precipitation too. Stake winter balance includes snow blown and avalanched onto the ice, so the multiplier
probably overstates snowfall on the rock and tundra around it.

One option: a per-domain precipitation factor in SUMMA, so the upland keeps gauge-based precipitation. The other
options considered and set aside:

- Clearing upland snow between spin-up cycles fixes the spin-up only. A 22-year run still piles about 0.8 m/yr onto
  the upland, and that water never reaches the stream.
- Raising the upland limit to the firn value only delays the failure.

## State of things

- Forcing: `data/domain_<Dom>[_general]/forcing/SUMMA_input/` (264 months). Added cases read
  `.../SUMMA_input/station_corrected/`. `remap.csv` holds the free-air lapse rates.
- Cases are rebuilt for the new forcing. `runs/<case>/summa_inputs/` is uncommitted in the workflow checkout; it
  sits beside other agents' uncommitted work, so commit by pathspec.
- Three spin-ups finished (`coldState_cold.nc` kept in each case). gulkana_added's `coldState.nc` is the unspun
  cold state.
- Old calibrations:
  - General cases: renamed `calibration*_chelsa`. The new `runs/*_general/calibration/` folders are partial from
    this morning's 09:45 start and can be deleted.
  - Added cases: still `calibration*` (not yet renamed `_nov11`).
- Rerunning: `scratch/2026-11-16/calibrate_general.sh` runs the general pair. For the added pair, use the tail of
  `deploy_levels.sh`, which runs `spinup.py`, then `calibrate.py calibrate <case> --search domain --population 32
  --generations 15 --ranks 4`, then `post_cal.py`.
- Station comparison of the new forcing: `runs/logs/2026-11-12/levels/levels_vs_station.log`.
- glacier.tex still waits for these runs (its `\tbd` cells, the forcing numbers, Table 2, figures 2–6).
- Fetch-cooling A/B retest is to follow the new forcing (see `glacier_forcing_runs.tex`, `sec:fetch`).

## Rules

- Commit locally; never push. No `Co-Authored-By` line.
- Use a worktree for SUMMA branches; the `summa` checkout is shared.
- Comments are one line and say what the code does.
- Analysis scripts go in `summa_glacier_workflow/scratch/<date>/` and are committed.
- Run unattended jobs under `caffeinate -ims`.
- Wolverine comes before Gulkana everywhere.
- Build: `env FC=/opt/local/bin/gfortran LIBRARY_LINKS='-llapack'
  SUNDIALS_DIR=/Users/amedin/Research/SummaSundials/sundials/instdir/ cmake --build build/cmake_build_mizu
  --target all -j 8`
