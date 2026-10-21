set -e
B="env FC=/opt/local/bin/gfortran LIBRARY_LINKS=-llapack SUNDIALS_DIR=/Users/amedin/Research/SummaSundials/sundials/instdir/ cmake --build /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/0145f8cb-2306-44c4-a47c-a55707ead47a/scratchpad/wtice/build/cmake_build -j 8"
$B > /dev/null
cd /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/0145f8cb-2306-44c4-a47c-a55707ead47a/scratchpad/run_new && /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/0145f8cb-2306-44c4-a47c-a55707ead47a/scratchpad/wtice/bin/summa_sundials.exe -m fm.txt > log.txt 2>&1
# baseline: undo the unit change only
sed -i '' -e 's#massBalance = massBalance / iden_ice#massBalance = massBalance / iden_water#' -e 's#emergenceMask==1_i4b) \* debrisConc#emergenceMask==1_i4b) * iden_water/iden_ice * debrisConc#' /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/0145f8cb-2306-44c4-a47c-a55707ead47a/scratchpad/wtice/build/source/engine/glacAreaChange.f90
$B > /dev/null
cd /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/0145f8cb-2306-44c4-a47c-a55707ead47a/scratchpad/run_old && /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/0145f8cb-2306-44c4-a47c-a55707ead47a/scratchpad/wtice/bin/summa_sundials.exe -m fm.txt > log.txt 2>&1
