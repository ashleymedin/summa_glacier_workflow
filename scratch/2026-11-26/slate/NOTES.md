# Slate Creek, 26 Nov: default runs and the deep thermal options

## Forcing
- NCAR single levels are complete to 2026-07 (2026-08/09 need `--source cds`).
- Pressure levels: 87 of 264 months (Oct 2004–Dec 2011) at 12:54, about 20 min a month, so about 2–3 days to go (retry.sh, `forcing/logs/levels_ncar.log`).
- Until then, `raw_data_test` links those 87 months and `slate_creek_2011.yaml` remaps them. The cold state is rebuilt from them too (`forcing_coldstate.log`).
- `slate_stream`: spin-up WY2005, calibrate WY2006–09, evaluate WY2010–Dec 2011.

## Fix
- Every Slate case scored reach 1 (Myrtle Creek), because `gauge_reach` defaulted to 1. It is now 3, the reach at the gauge (88c7131).
- The 25 Nov test numbers were Myrtle Creek's.

## Default parameters, at the gauge (`slate_default.py`, `default_scores.log`)
Each case was spun up with 30 cycles of WY2005 (`spinup.sh`), on summa_r10.

| deepTherml | KGE WY06–09 | KGE WY10–11 | T RMSE WY06–09 (K) | T RMSE WY10–11 (K) | T bias (K) |
|---|---|---|---|---|---|
| bedrockLyrs (slate_stream) | 0.44 | 0.29 | 3.39 | 3.13 | +1.7 / +1.4 |
| none | 0.45 | 0.31 | 3.22 | 3.14 | +1.6 / +1.5 |
| airTempGW | 0.45 | 0.31 | 3.22 | 3.14 | +1.6 / +1.5 |

Mean discharge is 0.4–0.55 of the gauge's (beta).

| month | May | Jun | Jul | Aug | Sep |
|---|---|---|---|---|---|
| Q sim / obs (m³/s) | 4.2 / 6.3 | 3.1 / 4.0 | 0.9 / 2.9 | 0.4 / 2.7 | 0.25 / 2.0 |
| T sim / obs (°C) | 0.8 / 1.2 | 9.3 / 6.5 | 13.8 / 9.4 | 10.6 / 8.1 | 5.1 / 4.6 |

- Precipitation is 390–530 mm a year (ERA5 × CHELSA).
- The model's runoff is 0.19–0.36 of it; the gauge's runoff is 0.30–0.71 of it (124–377 mm, WY2006–11).
- The aquifer is empty (2 mm) and baseflow is under 25 mm a year.
- So the summer flow is snowmelt and surface runoff only, and it runs dry and 3–4 K too warm in July–August.
- Water held above the frozen ground at 2–3 m evaporates instead of draining.

## Frozen ground (the 9 land HRUs, WY2006–11)
- Maximum thaw reaches the 1.25 m layer on the upper HRUs and the 2.0 m layer elsewhere.
  - The layers are coarse (1.0–1.5 m and 1.5–2.5 m).
  - It is too deep: published active layers near Coldfoot are 0.5–1 m (unburned Dall Creek 0.9–1 m, Rey et al. 2020 GRL; Dalton Highway MP 8–12, 0.5–1 m, AKDOT FHWA-AK-RD-10-06; from a web search, papers not yet read).
  - Coldfoot is a CALM site (southern Brooks Range foothills); its own record is still to fetch.
- Frozen all year below 2.0–3.25 m: permafrost in every HRU and every option.
- Under bedrockLyrs, the base at 25 m holds −0.7 to −2.7 °C.
  - It cools by 0.4–0.8 K over six years: WY2005, the spin-up year, is the warmest (−4.1 °C mean air, against −3.9 to −6.0 °C for WY2006–11).
- Under none, the soil base at 3.25 m swings from −2 to −6 °C year to year.
- The three options change the gauge's water temperature by at most 0.17 K.
  - airTempGW equals none, because the aquifer it warms is empty.
  - So the on/off test has to wait for a calibration that fills the aquifer.

## Cheap search (`cheap.sh`, `runs/slate_stream/cheap`, `cheap_evaluation`)
- 12 × 8, 4 ranks, discharge + water temperature, `--search domain` (calibrate.py ebdcfd4).
- Front of 17: KGE 0.52–0.58 and T RMSE 2.76–2.89 K on WY2006–09; held out, KGE 0.28–0.35 and 2.72–2.81 K.
- The members are nearly one parameter set:
  - upland snow multiplier 1.45–1.48 (limit 5);
  - aquiferBaseflowRate 0.0004–0.009 (default 0.1);
  - k_macropore 1e-4 (default 1e-3).
- Balanced trial 87: KGE 0.56 / 0.33, T RMSE 2.84 / 2.81 K, beta 0.78 / 0.58.
  - June now runs high (6.5 against 4.0 m³/s).
  - July–October is still a third or less of the gauge's (Aug 0.44 / 2.65, Sep 0.22 / 1.99, Oct 0.08 / 1.16 m³/s).
  - July is still 4 K warm (13.4 / 9.4 °C).

## Deep thermal on/off, trial 87 (`onoff.sh`, `onoff_score.py`, `onoff_scores.log`)
Each option runs on its own spun-up inputs.

| deepTherml | KGE WY06–09 | KGE WY10–11 | T RMSE WY06–09 (K) | T RMSE WY10–11 (K) |
|---|---|---|---|---|
| bedrockLyrs | 0.555 | 0.324 | 2.84 | 2.81 |
| none | 0.550 | 0.332 | 2.82 | 2.77 |
| airTempGW | 0.550 | 0.332 | 2.83 | 2.77 |

- The options still differ by under 0.04 K.
- The aquifer now holds 15–23 mm, against 2 mm at the defaults. Baseflow is still only 2–15 mm a year, so the groundwater's temperature barely reaches the stream.
  - airTempGW sets the temperature of the groundwater reaching the channel, so it can't matter at 2–15 mm a year.
  - scalarAquiferTemp stays at 0.01 °C here; it only evolves under aquiferTemp.
- Yearly ET is 250–320 mm of 450–650 mm precipitation, surface runoff is 110–275 mm, and baseflow is 2–15 mm.
- So the test can't decide anything on this basin until the model has a real groundwater flow in late summer.
  - The gauge's August–October flow (1–2.7 m³/s) has to come from groundwater draining through or under the frozen ground.
  - The model blocks that drainage at 2–3 m.

## Active layer
- At Coldfoot, a late-winter core gives an active layer of 63 cm, under 30–35 cm of organic soil (ERL 2018, doi 10.1088/1748-9326/aac4ad). Interior sites are 55–63 cm.
- The model thaws to the 1.25–2 m layer, about 2–3 times too deep.
- The model has no organic layer, and its 1.0–2.5 m layers are too coarse to resolve a 0.6 m active layer.

## Next
- Fixing the drainage is a structural change, not one the search can make:
  - finer, organic upper layers;
  - or a deeper or unfrozen pathway (a sub-permafrost or talik aquifer).
  - The user should decide between them.
- Then the full record once the levels finish.
