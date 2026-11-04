#!/bin/bash
# compile engine files alone with -Warray-temporaries; args: files in dependency order
B=${B:-/Users/amedin/Research/SummaSundials/summa/build/cmake_build_mizu}
E=/Users/amedin/Research/SummaSundials/summa/build/source/engine
O=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/f319b5c1-d797-49e3-adf4-91c243ec2412/scratchpad/tmpchk
INC="-I$O -I$B -I$B/summa_comm_mod -I$B/summa_noahmp_mod -I$B/summa_nrtype_mod -I$B/summa_data_types_mod -I/Users/amedin/Research/SummaSundials/sundials/instdir/fortran -I/opt/local/include"
for f in "$@"; do
  /opt/local/bin/gfortran -c -O3 -ffree-line-length-none -fPIC -cpp -ffpe-summary=none -Warray-temporaries -J$O $INC $E/$f -o $O/${f%.f90}.o 2>&1 | grep -A1 "^$E" | grep -v "^--" | paste - - | sed "s|$E/||"
done
