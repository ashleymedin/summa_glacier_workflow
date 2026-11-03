#!/bin/bash
# psiSmooth 1e-12 m (kink back, ratio-of-slopes derivative kept) vs 1e-2 m: sampled first generation, default Wolverine, Bow
T="$(dirname "$0")/../../2026-10-28/ida_solver"; cd "$T"
S=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/2a6f22b4-4aee-4d50-b41c-e8841a6ef481/scratchpad
X=$S/wpd/bin/summa_sundials_mizuroute_opt.exe; XN=$S/wpd/nosm/summa_sundials_mizuroute_opt.exe
export IDA_DEADBAND=0
R="caffeinate -i gtimeout -k 60 9000 python3 tolall.py"
P=k_soil,vGn_n,theta_sat,Fcapil
# 1. sampled first generation without smoothing, water absTol 1e-4 vs default (compare fx4_wol, fx5_wol)
PARAMS=$P TOLNAMES=absTolMatric,absTolAquifr,absTolWatVeg $R ns4_wol 1.0d-4 16 3 $XN > ns4_wol.out 2>&1 &
PARAMS=$P $R ns5_wol dflt 16 3 $XN > ns5_wol.out 2>&1 &
wait
# 2. default parameters without vs with smoothing, concurrent; Bow pair in sequence alongside
$R dns_wol dflt 8 3 $XN > dns_wol.out 2>&1 &
$R dsm_wol dflt 8 3 $X > dsm_wol.out 2>&1 &
(CASE=bow $R dns_bow dflt 48 3 $XN > dns_bow.out 2>&1
 CASE=bow $R dsm_bow dflt 48 3 $X > dsm_bow.out 2>&1) &
wait
