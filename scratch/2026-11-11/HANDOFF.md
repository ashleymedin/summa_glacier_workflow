# Handoff, 11 Nov 2026 evening: forcing rework for the glacier paper (general vs added-data setups)

## Goal
Make the general setup (raw ERA5 + global data only) correct its forcing the same way the added-data setup
corrects to stations and stakes, variable by variable, then recalibrate all four cases
(wolverine_added, gulkana_added, wolverine_general, gulkana_general) and redo the paper's tables and figures.
Paper: ~/Research/USask/Writeups/summa_sundials_svn/glacier/glacier.tex (Table 2 = tab:calibrationParameters,
Table 4 = tab:forcing). Figures 2-6: ../streamtemp/figs/plot_forcing_runs.py etc. (glacier_forcing_runs.tex).
Wolverine always before Gulkana in tables, figures and sentences.

## Running now (leave alone)
CHELSA-precipitation general calibrations, started 16:05 under caffeinate
(scratch/2026-11-11/overnight/calibrate_chelsa.sh): NSGA-II 32 x 15, generation ~11 of 15 at 18:50, then
post_cal.py (picks, evaluate, aligned reruns, glacier change). Logs: runs/logs/2026-11-11/chelsa/.
Outputs: runs/<case>/calibration, calibration_rerun, calibration_evaluation. Expect done ~21:00-22:00.
These use raw ERA5 x CHELSA precipitation ratio only (precipElevGrad 0, old wind, old SUMMA binary).
They are a precipitation-only diagnostic; everything below supersedes them.
Earlier general runs kept for comparison: calibration*_nov11 (10 Nov, flat ERA5) and calibration*_grad
(calibrated precipElevGrad from the ERA5 cell height: overfit, Gulkana collapsed to 9.3 km2 in held-out years).

Until they finish: do NOT regenerate data/domain_*_general/forcing/SUMMA_input, edit runs/*_general/summa_inputs,
or rebuild into summa/build/cmake_build_mizu (bin/summa_sundials_mizuroute_opt.exe is in use).

## Committed, not yet deployed
summa (branch multi-calib; another agent/the user also drives this checkout, check `git status`/branch first,
commit by pathspec, never push, no Co-Authored-By, changelog entry per code change, code commit first):
- derivforce: tempLapseRate parameter (default 6.871 K/km); a domain off its HRU's elevation keeps the HRU's
  relative humidity (specific humidity at the domain's T and p) and sky emissivity (LW x (T_dom/T_HRU)^4).
  forcingElev attribute removed (precipElevGrad grades from the HRU elevation again).
- windExposure parameter removed; glacierWindFactor is the one glacier wind factor (applied on glacier domains
  only when air > 0 C; lower limit now 0.3). Changelog entries 93-94 (user reworded them).
- Also on develop: 06e59ad2 + 7ceb2360 (tempLapseRate/RH/LW only, not the wind change).
summa_glacier_workflow (master, commits 6e91793 .. 776271e):
- remap_forcing.py: ERA5 cells -> HRU: temperature lapse by month (currently constant 6.5 K/km, array `lapse`,
  see open item 1), hypsometric pressure, specific humidity at the cells' RH, LW at the cells' emissivity;
  with precip_climatology: precip x CHELSA bio12 ratio (HRU / cells); with wind_climatology: wind x CHELSA
  monthly sfcWind ratio (HRU / run-mean ERA5 wind that month). Writes forcing/SUMMA_input/remap.csv.
  Ratios: precip W 1.06-1.20, G 1.08-1.26; wind W ~5 (bottom) to 8-9 (top), G 1.9-4.8.
- acquire_climatology.py clips CHELSA (data/external/CHELSA/*_<Domain>.tif); general YAMLs carry
  precip_climatology and wind_climatology.
- correct_forcing_to_station.py: station humidity carried to each HRU at the station's RH (Gulkana has no
  hygrometer: keeps Wilson campaign ratios).
- build_cases.py: tempLapseRate = -mean(monthly lapse)/1000 from corrections.csv (added) or remap.csv (general);
  precipElevGrad from stakes (added) / 0 start (general); glacierWindFactor = Site B 0.594 (added) / 1 (general).
- runs/calibrate.py domain search on general: frozenPrecipMultip 0.3-2, precipElevGrad 0-0.0025 (from HRU
  elevation), glacierWindFactor 0.3-1.5. STATION_FIXED (fixed on added): frozenPrecipMultip, tempCritRain,
  tempRangeTimestep, glacierWindFactor, glacierTempReduction, precipElevGrad.
- scratch/2026-11-11/migrate_inputs.py: drops forcingElev from attributes.nc and turns windExposure lines into
  glacierWindFactor in every runs/*/summa_inputs and tests/*/summa_inputs. The new binary rejects both old names
  (unknown attribute/parameter is fatal), so run it together with installing the binary.

## Open decisions (ask the user)
1. Global lapse-rate source for remap (general) and its tempLapseRate. Tested against the stations' monthly lapse
   (W -5.5..-7.8, G -2.6 winter..-7.9 summer K/km): CHELSA tas lapse is flat (-4..-5); ERA5 2 m T regressed on cell
   elevation depends on window (coastal cells give W -11..-13 in winter; G overshoots inversions, +1..+3).
   Untested: ERA5 free-air lapse (scratch/2026-11-11/lapse/fetch.py + freeair_lapse.py; the pressure-level CDS
   request may never have completed: check for era5_pl_monthly.nc, re-run fetch.py if not).
2. glacierWindFactor only above freezing (current code) or on glacier ice at all times. Recommended to the user:
   always (it is an exposure factor; Site B 0.59 is melt-hour weighted; the 0 C switch is a jump in wind), keep the
   1.3 K cooling above freezing only. Awaiting answer; if yes, change derivforce + descriptions in var_lookup,
   get_ixname, popMetadat, derivforce comment, and Table 2/Table 4 "above 0 C" wording.
3. (Done by user's call) no calibration to Hugonnet thinning by band; the flow model's piecewise-linear mass
   balance is not the cause of Gulkana's top melting out (slope above top domain similar in both setups; level is
   1000-2000 mm lower on general = precipitation).

## Then, in order
1. When the CHELSA calibrations end: record their results (plan doc "Glacier Module Plan", list
   m9rqwn9hw2k.252738; compare with _nov11 and _grad).
2. git -C summa checkout multi-calib (if not), build: env FC=/opt/local/bin/gfortran LIBRARY_LINKS='-llapack'
   SUNDIALS_DIR=/Users/amedin/Research/SummaSundials/sundials/instdir/ cmake --build build/cmake_build_mizu --target all -j 8
3. python scratch/2026-11-11/migrate_inputs.py
4. remap_forcing.py on all four domains (domains/{wolverine,gulkana}{,_general}.yaml), then the station
   correction for the two added domains (same arguments as before; see README step 6 / corrections.csv), then
   rebuild the four cases (build_cases.py) so tempLapseRate etc. land in localParamInfo.txt.
5. Quick check: rerun one trial per case (runs/rerun_trials.py) to see the new binary and forcing run.
6. Recalibrate all four (calibrate.py calibrate <case> --search domain --population 32 --generations 15 --ranks 4
   --name calibration, plus post_cal.py; see scratch/2026-11-11/overnight/*.sh). Run under caffeinate -ims
   (the laptop sleeps). ~5 h for two cases in parallel.
7. Paper: refill Table 2 (fill_param_table), Table 4 \tbd (lapse source and values), f_A check, figures 2-6
   (plot_forcing_runs.py, panel (b) uses means), and rewrite the Forcing paragraph prose (its first sentence wrongly
   says "The general setup's hourly ERA5 ... is corrected toward the stations"). The fig:wolverine_best caption
   has a \citeA that breaks compilation (8 errors): needs \protect or a short caption.

## House rules
Analysis scripts go in summa_glacier_workflow/scratch/<date>/ and are committed. One-line code comments saying
what the code does, never history. Commit locally only.
