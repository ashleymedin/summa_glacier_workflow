#!/bin/sh
# run gulkana_wolverine with build $1 (base|new), solver $2, malloc counting on; output in run2/$1_$2
S=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/3d62acff-ed72-4c63-89f4-7bfe47923f58/scratchpad; B=/Users/amedin/Research/SummaSundials/summa_test_cases/test_cases; F=/Users/amedin/Research/SummaSundials/summa_test_cases/test_cases/settings/multiGruTestCases/gulkana_wolverine/fileManagers/fileManager_gulkana-wolverine.txt
mkdir -p $S/run2/$1_$2; sed -e "s#<BASEDIR>#$B#g" -e "s#<SOLVER>#$2#" -e "s#<PRECISION>#double_precision.txt#" -e "s#^outputPath .*#outputPath '$S/run2/$1_$2/' !#" $F > $S/run2/fm_$1_$2.txt
DYLD_INSERT_LIBRARIES=$S/tools/libmcount.dylib $S/$1/bin/summa_sundials.exe -m $S/run2/fm_$1_$2.txt > $S/run2/log_$1_$2.txt 2>&1
echo "$1 $2 exit $? $(tail -1 $S/run2/log_$1_$2.txt)"
