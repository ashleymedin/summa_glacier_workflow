#!/bin/bash
# Remaining 29 Oct handoff items on merged multi-calib (53f28374 + diag4.patch): slow windows left, energy relTol 0, sampled first generation at absTol 1e-4
T="$(dirname "$0")/../../2026-10-28/ida_solver"; cd "$T"
X=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/2a6f22b4-4aee-4d50-b41c-e8841a6ef481/scratchpad/wdg/bin/summa_sundials_mizuroute_opt.exe
export IDA_DEADBAND=0
R="caffeinate -i python3 tolall.py"
# 1. default tolerances, with and without energy relTol 0 (Wolverine pair concurrent, Bow pair in sequence alongside)
$R dg5_wol dflt 8 3 $X > dg5_wol.out 2>&1 &
SCALED=1 RELTOL_ENERGY=0.0d0 $R rq0_wol 1.0d-5 8 3 $X > rq0_wol.out 2>&1 &
(CASE=bow $R dg5_bow dflt 48 3 $X > dg5_bow.out 2>&1
 CASE=bow SCALED=1 RELTOL_ENERGY=0.0d0 $R rq0_bow 1.0d-5 48 3 $X > rq0_bow.out 2>&1) &
wait
# 2. Wolverine at scaled 1e-3, with and without energy relTol 0
SCALED=1 $R sc3_wol 1.0d-3 8 3 $X > sc3_wol.out 2>&1 &
SCALED=1 RELTOL_ENERGY=0.0d0 $R rq0sc3_wol 1.0d-3 8 3 $X > rq0sc3_wol.out 2>&1 &
wait
# 3. Wolverine first generation with sampled soil parameters, water absTol 1e-4 vs default
P=k_soil,vGn_n,theta_sat,Fcapil
PARAMS=$P TOLNAMES=absTolMatric,absTolAquifr,absTolWatVeg $R fg4_wol 1.0d-4 16 3 $X > fg4_wol.out 2>&1 &
PARAMS=$P $R fg5_wol dflt 16 3 $X > fg5_wol.out 2>&1 &
wait
