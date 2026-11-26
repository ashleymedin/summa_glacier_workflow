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

## Next
- Cheap search: `cheap.sh` (12 × 8, 4 ranks, discharge + water temperature, `--search domain`; calibrate.py ebdcfd4 scores the temperature on a no-ice case and drops the glacier storage constants).
- Then rerun its balanced trial with none and airTempGW for the on/off test.
- Then the full record once the levels finish.
