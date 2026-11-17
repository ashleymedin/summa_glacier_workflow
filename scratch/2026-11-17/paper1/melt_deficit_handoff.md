# Handoff: the glaciers melt too little in summer (paper-1 added-data cases, 17 Nov 2026)

## The task

Find out why the added-data setups (`wolverine_added`, `gulkana_added`) melt too little glacier ice in summer, and fix
the cause in the physics, the forcing or the fixed parameter values. **Do not fix it by searching
`glacierWindFactor`, `glacierTempReduction`, the rain-snow threshold or `precipElevGrad` again.** We stopped searching
them after the twin tests of 16 Nov. In those tests the wind factor, the cooling factor and the snowfall multipliers
traded off against each other, so the search could not identify them (`scratch/2026-11-16/twin*.py`,
`twin_all.log`, and the 17 Nov `twin_*`, `oat_*`, `split_*`, `upland_*` reports in `scratch/2026-11-17/`). Searching
them again would hide the deficit, not explain it.

## What the 17 Nov calibrations show

Each case was calibrated with `./calibrate.py calibrate <case> --search domain --population 32 --generations 15`
(NSGA-II on discharge KGE and seasonal mass-balance RMSE, WY2006–2015, held-out years WY2016–2026). The balanced trial
is the front member nearest the ideal point, with each objective scaled by its range on the front.

| case | balanced trial | KGE cal / held out | MB RMSE cal / held out (mm w.e.) | 10 Nov, before the search change |
|---|---|---|---|---|
| wolverine_added | 391 | 0.77 / 0.80 | 423 / 387 | 0.94 / 0.89, 428 / 406 |
| gulkana_added | 450 | 0.66 / 0.70 | 446 / 451 | 0.71 / 0.75, 375 / 409 |

The KGE is lost to volume, not timing (`kge_parts.py` in this folder, over the calibration years):

| case | r | α (sim/obs σ) | β (sim/obs mean) | annual mass change, sim − obs |
|---|---|---|---|---|
| wolverine_added 391 | 0.91 | 0.82 | 0.88 | −92 mm/yr |
| gulkana_added 450 | 0.90 | 0.76 | 0.78 | +509 mm/yr |

- **Gulkana:** most of the missing runoff is glacier water. A +509 mm/yr glacier over the glacierized fraction is
  about 290 of the 510 mm/yr basin deficit.
- **Signs the search was short of melt:** in gulkana_added, every member of the front has `albedoMax` at its 0.80
  floor. The balanced trial's `debrisConc` is at its floor and `albedoDecayRate` is near its low end. The front has
  only 5 members.
- **The deficit is there before any calibration.** The stake comparison at the default parameters on 16 Nov
  (`runs/logs/2026-11-16/stake_seasons_*_added.txt`, from `scratch/2026-11-16/stake_seasons.py`) gives these mean
  summer balances, sim against obs (m w.e.):

| HRU | Wolverine | Gulkana |
|---|---|---|
| 1 (lowest) | −4.13 vs −6.06 | −1.92 vs −4.17 |
| 2 | −2.53 vs −3.29 | −0.57 vs −1.43 |
| 3 | −0.99 vs −1.83 | +0.31 vs −0.58 |

  Winter balances are close at Gulkana. At Wolverine they are 0.2–0.8 m low, but Wolverine's glacier snowfall
  multipliers came from the gauge correction that has since been redone. **The summer shortfall is the robust signal:
  every HRU at both basins, worst in the ablation zone.**

## What has probably been ruled out

**The forcing at the weather stations.** `scratch/2026-11-16/levels_vs_station_all.txt` has the station-corrected
pressure-level temperature within about ±0.5 K of the stations in summer. `lw_vs_station.txt` has the basin-mean
longwave within about +3 W m-2 in JJA at Gulkana. Check summer shortwave and humidity the same way before ruling the
forcing out altogether.

## Where to look

1. **Glacier surface energy balance in summer at a stake site** (Gulkana Site B or AB, Wolverine's lowest stakes).
   The wind factor (0.59) and the multiplicative cooling (0.73 of the air temperature above freezing) are both Site B
   fits and both cut the sensible heat flux. Check:
   - what they were fitted against, and whether the model applies them as the fit assumed;
   - whether both now apply at once where the fit only had one;
   - whether they act at every HRU, including the lowest, which sits below Site B.
2. **Ice and firn albedo and exposure.** `albedoMax` wants to go below 0.80 at Gulkana. Check whether bare ice is
   exposed in July–August in the lowest HRU, and the ice albedo the model uses there. The firn-to-ice change
   (summa 3e377319, close-off 830 kg m-3) can keep firn or snow on the surface longer.
3. **Changes since 10 Nov that touched melt:**
   - WorldCover vegetation (13 Nov): the lowest HRU is now mixed tundra, mHeight 3.5 m;
   - pressure-level forcing (17c6131) and basin-mean longwave (a9c3605);
   - firn to ice;
   - wind and cooling fixed rather than searched (9c82584).

   A rerun of trial 450 with one change reverted at a time, scored with `rerun_trials.py --aligned
   --calibration-years`, would apportion the deficit.

The test of a fix is the summer stake balances at the default parameters (rerun `stake_seasons.py`), not a
calibration score.

## Running jobs and state (shared working tree; check before touching)

- `scratch/2026-11-17/paper1/run.sh` is calibrating `wolverine_general` and `gulkana_general` (8 MPI ranks, ends
  about 21:00 JST 17 Nov), then runs `post_cal.py`.
- `redo_wolverine_added.sh` is spinning `wolverine_added` up on its rebuilt forcing. It recalibrates that case once
  run.sh ends. Don't rebuild or re-spin the four paper cases while these run.
- `gulkana_added/calibration*` holds the 17 Nov results. `wolverine_added/calibration*_oldforcing` holds trial 391,
  run on the forcing before today's re-correction.
- The user's rebuild left uncommitted changes in `README.md`, `correct_forcing_to_station.py`,
  `plot_basin_setup.py`, `plot_glacier_end.py` and the case inputs. Leave them.
- Environment: `~/miniconda3/envs/glacier/bin/python`; `export OMPI_MCA_mpi_yield_when_idle=1`; run long jobs under
  `caffeinate -ims`. The SUMMA build is `~/Research/SummaSundials/summa` (branch multi-calib). Commit locally, never
  push, no Co-Authored-By line.
