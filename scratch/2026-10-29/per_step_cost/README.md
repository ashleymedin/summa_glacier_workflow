Per-step cost of IDA on the gulkana_wolverine case, summa solver slowdown plan, 29 Oct 2026.

- ensemble.py, profile.py   copies from ../ida_stiff; ensemble.py points the case at this folder, profile.py anchors its process match to the exe
- attribute.py   splits malloc/free, pow and memmove samples in `sample` call graphs by their nearest libsumma caller
- tolall.py      copy from ../../2026-10-28/ida_solver (bundled Wolverine calibration test, 8 trials)
- compare_obj.py objectives of tolall runs trial by trial against a reference
- *.out          results: prof3/prof4 profiles (head 67f0d897, then with c8b9be7c and 97f7a3af), cnt (Brent and IDA window counts),
                 h1/h05/hbase (warm initial step, rejected), fbase/flux, tol_* (bundled test CPU)
