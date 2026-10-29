Per-step cost of IDA on the gulkana_wolverine case, summa solver slowdown plan, 29 Oct 2026.

- ensemble.py, profile.py   copies from ../ida_stiff; ensemble.py points the case at this folder, profile.py anchors its process match to the exe
- attribute.py   splits malloc/free, pow and memmove samples in `sample` call graphs by their nearest libsumma caller
- tolall.py      copy from ../../2026-10-28/ida_solver (bundled Wolverine calibration test, 8 trials)
- alloc_scope.py splits malloc/free samples by the innermost enclosing routine (computFlux, summaSolv4ida, opSplittin, ...)
- pow_check.py   old vs two-pow forms of the soil_utils van Genuchten functions over a grid of psi, T, alpha, n
- compare_obj.py objectives of tolall runs trial by trial against a reference
- *.out          results: prof3/prof4 profiles (head 67f0d897, then with c8b9be7c and 97f7a3af), cnt (Brent and IDA window counts),
                 h1/h05/hbase (warm initial step, rejected), fbase/flux, tol_* (bundled test CPU)
                 base2/base3 (head 97f7a3af), stk (-fstack-arrays, segfaults after 2 min, dropped), alloc (234d4ae5 + 10a0b5de: 3316 -> 3123 s, bit-identical)
                 base4 (97f7a3af) vs tab (7b627b83, soil lookup tables kept by parameters): 3508 -> 3012 s, bit-identical
                 tab2 (7b627b83) vs pow (5c93c446, two-pow soil functions): 3084 -> 2935 s, objectives within 3e-6
                 queue_total.sh: 67f0d897 vs 006eaf96 paired, see queue_total.out (Wolverine IDA 3901 -> 2893 s, BE 1191 -> 905 s; Bow IDA 121 -> 97 s, BE 66 -> 60 s)
