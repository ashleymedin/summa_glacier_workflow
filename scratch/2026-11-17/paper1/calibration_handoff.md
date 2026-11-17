# Paper 1 calibrations, round 2 (18 Nov 2026)

Run the four paper-1 calibrations on the inputs committed in e4c7df2, then their post-processing. Report the
front, the balanced trial's scores and any parameter at a search limit for each case.

## What changed since the 17 Nov calibrations (all four cases are rebuilt and respun)

- SUMMA multi-calib (1d6519a3 and before): Mahrt (1987) stability and a 2 m measurement height over glacier ice and
  snow (the summer melt deficit, `../melt_deficit/README.md`). Built in `summa/build/cmake_build_mizu`; the
  calibration test passes.
- General cases: glacier snowfall on the stakes' gradient, 0.0017 m-1, as a shape in `trialParams.nc`;
  `frozenPrecipMultip@glacier` is searched as a spatial multiplier of it (`build_cases.glacier_snow_shape`,
  `calibrate.RAW_MULTIPLIERS`). Its value is the glacier snowfall over ERA5's at the glacier's mean elevation.
- Glacier wind and cooling stay fixed (twin, `../twin2/`), now from Site B against each case's own forcing:
  added 0.595 and 0.790, general 0.605 and 0.818.
- Search bound: albedoDecayRate 0.2e6-5e6 s.

The 17 Nov results are not comparable with these.

## How

`run.sh` and `post_cal.py` in this folder run the chain. Before starting:

1. **Move the old results aside.** `calibrate.py calibrate` deletes `<case>/<name>` first. Rename
   `gulkana_added/calibration*`, `wolverine_general/calibration*` and `gulkana_general/calibration*` to
   `calibration*_1117`. The `wolverine_added` ones already carry `_oldforcing`. `post_cal.py` waits for
   `<case>/calibration`, so keep that name for the new runs.
2. **Use a new log folder.** Use `runs/logs/2026-11-18` and pass it as `post_cal.py`'s second argument (in `run.sh`).
3. **Before a long unattended run,** start `caffeinate -ims` and export `OMPI_MCA_mpi_yield_when_idle=1`.
   The laptop has 10 cores, so run two cases at 4 ranks each, as `run.sh` does.
4. **Never rebuild `summa/build/cmake_build_mizu` or relink `summa/bin` while a run uses them.** macOS kills
   running jobs (signal 9), which is how the 17 Nov gulkana_general calibration stopped at 392 trials.

## Stream cases

The stream cases (`*_stream*`, paper 2) are rebuilt with the added-data factors (0.595, 0.790) and respun too.
