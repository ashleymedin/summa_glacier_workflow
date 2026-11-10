#!/bin/bash
# Reruns failed trial nsga2_g4_s000125 (wolverine_added) serially to just past its failure.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
SUMMA_EXE="${SUMMA_EXE:-/Users/amedin/Research/SummaSundials/summa/bin/summa_sundials_mizuroute.exe}"
"$SUMMA_EXE" -c "$here/rerun.toml" \
  --param aquiferBaseflowExp 4.851574615551906 \
  --param aquiferBaseflowRate 2.396979705182851e-05 \
  --param qSurfScale 3.484098152663178 \
  --param Fcapil 0.1784603541622165 \
  --param windReductionParam 0.7480384763698138 \
  --param routingGammaScale 9796.065786316636 \
  --param routingGammaShape 2.2639987835032542 \
  --param glacStor_kIce 45016.11637844165 \
  --param glacStor_kSnow 457187.04886229424 \
  --param glacStor_kFirn 3244092.901354385 \
  --param k_snow 0.02786372362297313 \
  --param mw_exp 1.1138370901098824 \
  --param albedoDecayRate 4173244.6860632054 \
  --param albedoMax 0.8874074903153821 \
  --param newSnowDenMin 67.53596126903375 \
  --param k_soil@upland 5.129058188505923e-07 \
  --param k_macropore@upland 7.893426029709833e-07 \
  --param theta_sat@upland 0.6440803582584179 \
  --param vGn_n@upland 2.9138828131873282 \
  --param frac_sand@upland 0.8936677029548559 \
  --param theta_sat@glacDbr 0.30862529247532294 \
  --param frac_sand@glacDbr 0.08643026618774995 \
  --param debrisConc 1.1203992037168162 \
  --param theta_res@upland 0.029404893138644878 \
  --param critSoilWilting@upland 0.09488264705353013 \
  --param critSoilTranspire@upland 0.17054119390773526 \
  --param fieldCapacity@upland 0.4164877540078174 \
  2>&1 | tee "$here/rerun.log"
