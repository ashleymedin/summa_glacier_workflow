Allocation counts for the summa solver slowdown plan, 4 Nov 2026. Counts are deterministic, so a busy machine does not bias them.

- mcount.c     interposed malloc/calloc/realloc counter, totals at exit: `clang -dynamiclib -O2 -w mcount.c -o libmcount.dylib`, then `DYLD_INSERT_LIBRARIES=libmcount.dylib summa_sundials.exe -m <fileManager> ...`
- mcaller.c    malloc count by calling function (single thread)
- mcaller2.c   malloc count by (caller, caller's caller); arm64 macOS keeps frame pointers, so no -g build is needed
- rcaller.c    realloc count by calling function
- bitcmp2.py   every variable of two summa_test_cases output tags compared exactly: `bitcmp2.py <output dir> <solver> <tagA> <tagB>`
- tmpchk.sh    recompiles single engine files against a build's modules with -Warray-temporaries

gulkana_wolverine (2 GRUs, 6 HRUs, homegrown, double) mallocs per run:
HEAD 70d21750 499M; hot temporaries (96f28b7c, 81df1918) 495M; computFlux argument objects reused 452M;
opSplittin and coupled_em single cached set 378M; opSplittin cache of 8 sets 274M; 32 sets 197M;
systemSolv/varSubstep/summaSolv4ida flux structures cached 156M; coupled_em cache of 32 sets 112M.
mcaller2_ws6.out is the top of the last of these.
