# Paper 2 handoffs, 26 Nov 2026

Three agents, one per basin. All share this machine (10 cores) and the workflow checkout `summa_glacier_workflow` (main).

**Shared rules for all three**
- Read the plan doc first, then `glacier_forcing_runs.tex` (`~/Research/USask/Writeups/summa_sundials_svn/coldstream/streamtemp/`): your basin's section.
- SUMMA code: multi-calib. It has the advective-heat fix (fd892832), white ice and cold-air pooling. Frozen build for runs: `SUMMA_DIR=~/Research/SummaSundials/summa_r10` (9f34c049, same physics). Don't touch `summa_next` (old code, bf5ddb11) or `summa_r10`.
- Before launching anything: check `ps`. Round 10b (`scratch/2026-11-26/r10b/run.sh`, 2 × 4 ranks) and Lemon's paired test (`scratch/2026-11-25/lemon_pair_adv.sh`, 2 × 4 ranks) run until about tonight. Keep to 4 ranks or fewer, use `caffeinate -ims nice -n 10`, and export `OMPI_MCA_mpi_yield_when_idle=1`.
- `cases.yaml` is shared. Edit only your basin's keys, and commit them straight away. `search_of` in calibrate.py reads `cases.yaml` while a run is live.
- Scripts go in `scratch/<date>/` and get committed. Never push, and no Co-Authored-By.
- Wolverine before Gulkana in every table and sentence.

---

## 1. Wolverine stream (wolverine_stream_delta)

**State.**
- Round 9's balanced added-data trial 465 was rerun on the stream cases, on old code: Figs 2, 3 and 7 (`lake_heat.pdf`), `scratch/2026-11-25/stream_r9`.
- The cheap stream search `runs/wolverine_stream_delta/stream_cheap_r9` (12 × 8, WY2006–22, pinned at 465, old code) has a one-trial front, trial 79.
  - Water-temperature RMSE 0.69 K at discharge KGE 0.87.
  - wetlandPoolCooling 3.1 K, wind factor 0.99, air cooling 0.52, wetlandStorageK at its 10-minute bound.
  - Pooling is the only parameter that matters: under 2 K or over 6 K gives 0.76–0.91 K.
- The tex has a "The pooling calibrated" paragraph in sec:lakeice.
- Its held-out evaluation was launched 26 Nov ~11:00 (`scratch/2026-11-26/stream_cheap_r9/evaluate.sh`, output in `stream_cheap_r9_evaluation`).

**Why it is provisional.**
- The search used old code and a round 9 trial.
- The paper's trial will come from round 10b (`wolverine_added_10b`: no rain rise and no upland snow rise above the gauge; see `scratch/2026-11-26/DECISIONS_precip_rise.md`).
- The user judges stream_cheap_r9 close enough to move forward with now.

**Tasks.**
1. When the evaluation lands, add trial 79's held-out RMSE, its peak lake ice and its opening dates (`scratch/2026-11-23/white_ice.py`, `scratch/2026-11-20/stage0_months.py`) to the paragraph, as a row of tab:lakeice.
2. When round 10b's Wolverine merged front is done (post_merge picks the balanced trial):
   - Point the stream case at 10b. Do this with a calibration_r10b link, as calibration_r9 was done, or by changing the case's parent; drop `upland_snow_grad`.
   - Rebuild and spin up `wolverine_stream_delta` on summa_r10.
   - Rerun the balanced trial (delta, plus the nolake/infill/fetch variants of stream_r9/run.sh).
   - Run the stream search pinned at it. Use the same search as stream_cheap_r9; if time allows, 32 × 15 rather than 12 × 8.
3. Refresh tab:wetland, which is still trial 405 / round 3, and tab:lakeice, which is still round 5b, from the 10b runs. Redraw Figs 2, 3 and 7 with `scratch/2026-11-25/stream_r9/figs.sh`, pointed at 10b.
4. Open items in the tex: May still runs warm; June–September is cold by 0.2–0.4 K (the remaining heat is the reach that lengthens as the glacier retreats, sec:streamsetup).

**Gulkana stream.** Gulkana is test-only and not in paper 2. After 10b, rebuild `gulkana_stream` too, since it inherits the key. Only rerun its balanced trial (nowet/fan/scale) for Fig 3.

---

## 2. Lemon Creek

**State.**
- Cases:
  - `lemon_added` (wind_station 1280 forcing).
  - `lemon_general`.
  - `lemon_grus`, and `lemon_grus_snow` (the upland snow rise), both on 3 GRUs.
- Forcing is NCAR ERA5 to 2026-07. The CDS download (`raw_data`) is still running, and the switch to it comes when it completes.
- The rain rise above the gauge is kept for Lemon, because the gauge is the sea-level airport.
- The upland snow rise is undecided. The deciding test is running now: `scratch/2026-11-25/lemon_pair_adv.sh`, `cheap_adv` searches of lemon_grus and lemon_grus_snow on the new code, seed 42, then evaluated. Results are in `runs/lemon_grus*/cheap_adv*`.
- On the old code, lemon_grus took an upland multiplier of 4.8–5.0 (limit 5) without the rise and 1.67–1.92 (limit 2) with it. Balanced held-out KGE was 0.79 flat against 0.71–0.72, which is not like for like.
- Lake chain of three, no delta. Tex section sec:newbasins.

**Tasks.**
1. When the paired test finishes, compare like for like: KGE, mass balance, Hugonnet, and the upland multiplier against its bound. Write up the snow-rise decision for the user in DECISIONS_precip_rise.md. Don't put an upland snow note in the tex until the user decides.
2. Then calibrate Lemon properly (32 × 15, seeds 42 and 43, as round 10 did) on the chosen case.
3. Check the CDS `raw_data` progress. When it is complete, remap and correct from it in place of NCAR, and add 2026-08/09.
4. Lemon's stream and lake stage: the lake chain as wetlands, then stream temperature (15-minute record from Nov 2017). Copy Wolverine's pooling result if it holds up.

---

## 3. Slate Creek (no ice)

**State.**
- Built 23–24 Nov: 3 GRUs, 9 HRUs, and the stream network (`add_stream_grus.py`, `build_cases stream: grus`).
- Case `slate_stream` (loam upland, sand 0.44) runs through the driver with mizuRoute on test months, to Dec 2007 (`scratch/2026-11-25/slate_creek_2007.yaml`, slate_run.log).
- ERA5 comes from NCAR. The single-level and pressure-level downloads are still running under retry.sh (`data/domain_SlateCreek/forcing/logs`).
- Lakes are natural flow-through, about 4% of the drainage, with no wetland domain.
- General-setup forcing: CHELSA precipitation and wind climatology.

**Tasks.**
1. Check the downloads. When they are complete, remap the full record from raw_data_ncar, run the coldstate, extend slate_stream's months and periods, and spin up. The last month or two of 2026 may need `--source cds` for the levels.
2. Default-parameter run: discharge KGE, water temperature, permafrost or active layer. This basin is where `deepTherml`/`bedrockLyrs` gets tested (on/off moved Wolverine by only 0.01 K).
3. Calibrate discharge plus stream temperature (no glacier targets), cheap first.
4. Fill in Slate Creek's part of sec:newbasins.
