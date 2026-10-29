#!/bin/zsh
# Total speedup 67f0d897 (old) -> 006eaf96 (new), paired runs side by side: Wolverine and Bow, IDA and BE.
S=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/f4321113-5b43-47d1-97a1-96bbe81421b8/scratchpad
OLD=$S/wprof/bin/summa_sundials_mizuroute_opt.exe; NEW=$S/wpow/bin/summa_sundials_mizuroute_opt.exe
P=/Users/amedin/miniconda3/envs/glacier/bin/python
for c in wolverine bow; do for m in dflt be; do
  t=${c[1,3]}_${m}
  CASE=$c $P tolall.py ${t}_old $m 8 3 $OLD > tol_${t}_old.out 2>&1 &
  CASE=$c $P tolall.py ${t}_new $m 8 3 $NEW > tol_${t}_new.out 2>&1 &
  wait
  echo "== $t"; grep -h "exit\|^user" tol_${t}_old.out tol_${t}_new.out
  $P compare_obj.py ${t}_old ${t}_new 2>&1 | tail -1
done; done
