#!/bin/bash
# Reruns this failed calibration trial with the serial executable; trial.json says how it failed.
# Set SUMMA_EXE to use another build. Output goes to output/ and rerun.log beside this script.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
SUMMA_EXE="${SUMMA_EXE:-/Users/amedin/Research/SummaSundials/summa/bin/summa_sundials_mizuroute.exe}"
mkdir -p "${here}/output"
sed -e "s|^\([[:space:]]*state_path[[:space:]]*=\).*|\1 \"${here}/\"|" \
    -e "s|^\([[:space:]]*init_condition[[:space:]]*=\).*|\1 \"initial_state.nc\"|" \
    -e "s|^\([[:space:]]*output_path[[:space:]]*=\).*|\1 \"${here}/output/\"|" \
    -e "s|^\([[:space:]]*work_path[[:space:]]*=\).*|\1 \"${here}/output\"|" \
    "${here}/config.toml" > "${here}/rerun.toml"
# relative paths in the configuration resolve from where the calibration was launched
cd "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs"
"${SUMMA_EXE}" -c "${here}/rerun.toml" \
  --param aquiferBaseflowExp 5.4707784260400469E+00 \
  --param aquiferBaseflowRate 4.0748635837852031E-03 \
  --param qSurfScale 3.2026934750557984E+01 \
  --param Fcapil 4.4645534864961700E-02 \
  --param windReductionParam 9.5914362496778760E-01 \
  --param routingGammaScale 4.5050751958632944E+04 \
  --param routingGammaShape 2.2432638650992853E+00 \
  --param glacStor_kIce 8.4413017186699071E+04 \
  --param glacStor_kSnow 1.1884845593280271E+05 \
  --param glacStor_kFirn 5.6878059092899284E+05 \
  --param k_snow 4.2440626431306215E-02 \
  --param mw_exp 1.7692380481739787E+00 \
  --param albedoDecayRate 1.0198145201835280E+06 \
  --param albedoMax 8.1784548654697753E-01 \
  --param k_soil@upland 1.1873626520593486E-08 \
  --param k_macropore@upland 7.0841465455484766E-08 \
  --param theta_sat@upland 6.4743836777296215E-01 \
  --param vGn_n@upland 2.3911763948284626E+00 \
  --param frac_sand@upland 5.9807248450873507E-01 \
  --param theta_sat@glacDbr 3.3812242560115480E-01 \
  --param frac_sand@glacDbr 2.9623684572037012E-01 \
  --param debrisConc 7.1636341225218914E-01 \
  --param theta_res@upland 7.4804690687432548E-02 \
  --param critSoilWilting@upland 9.9465652566583948E-02 \
  --param critSoilTranspire@upland 3.2777192270004141E-01 \
  --param fieldCapacity@upland 5.8489231413153375E-01 \
  --param frac_silt@upland 0.30192751549126493 \
  2>&1 | tee "${here}/rerun.log"
