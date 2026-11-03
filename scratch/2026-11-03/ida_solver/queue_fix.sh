#!/bin/bash
# dPsiLiq_dPsi0 ratio fix (psi-deriv b19bba51 + diag): sampled first generation at both tolerances, then default Wolverine paired with the old exe
T="$(dirname "$0")/../../2026-10-28/ida_solver"; cd "$T"
S=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/2a6f22b4-4aee-4d50-b41c-e8841a6ef481/scratchpad
X=$S/wpd/bin/summa_sundials_mizuroute_opt.exe; X0=$S/wdg/bin/summa_sundials_mizuroute_opt.exe
export IDA_DEADBAND=0
R="caffeinate -i python3 tolall.py"
P=k_soil,vGn_n,theta_sat,Fcapil
# 1. sampled first generation with the fix, water absTol 1e-4 vs default
PARAMS=$P TOLNAMES=absTolMatric,absTolAquifr,absTolWatVeg $R fx4_wol 1.0d-4 16 3 $X > fx4_wol.out 2>&1 &
PARAMS=$P $R fx5_wol dflt 16 3 $X > fx5_wol.out 2>&1 &
wait
# 2. default parameters, fixed vs old exe, concurrent
$R dfx_wol dflt 8 3 $X > dfx_wol.out 2>&1 &
$R dg6_wol dflt 8 3 $X0 > dg6_wol.out 2>&1 &
wait
