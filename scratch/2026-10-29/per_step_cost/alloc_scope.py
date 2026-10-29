#!/usr/bin/env python3
"""Split malloc/free samples by the outermost enclosing routine of interest (per residual, per Jacobian, per window).
usage: alloc_scope.py prof_<tag>_*.txt"""
import sys, re, collections
LEAF = re.compile(r"malloc|_free$|^free$|xzm_|deduplicated|calloc|realloc")
SCOPES = ["eval8summa4ida", "computjacob4ida", "computflux", "eval8summawithprime", "summasolv4ida", "opsplittin", "coupled_em"]
pat = re.compile(r"^([ +!:|]*)(\d+) (.+?)  \(in (\S+)\)")
res = collections.Counter(); main = 0; tot = 0
for fn in sys.argv[1:]:
    txt = open(fn).read().split("Total number in stack")[0]
    stack = []
    for line in txt.splitlines():
        m = pat.match(line)
        if not m: continue
        depth, n, name, lib = len(m.group(1)), int(m.group(2)), m.group(3).split(" ")[0], m.group(4)
        while stack and stack[-1][0] >= depth: stack.pop()
        stack.append((depth, name.lower(), lib, n))
        if name == "__summa_simulation_MOD_evaluate_objectives": main += n
        if LEAF.search(name) and lib != "libsumma.dylib":
            if len(stack) > 1 and LEAF.search(stack[-2][1]): continue
            names = [s[1] for s in stack[:-1]]
            inner = next((sc for sc in reversed(SCOPES) for nm in [names] if any(sc in x for x in nm)), "other")
            # innermost scope: search from the deepest frame up
            inner = "other"
            for x in reversed(names):
                hit = next((sc for sc in SCOPES if sc in x), None)
                if hit: inner = hit; break
            res[inner] += n; tot += n
print(f"alloc {100*tot/main:.1f}% of main thread, by innermost enclosing routine:")
for k, n in res.most_common(): print(f"  {100*n/main:5.1f}%  {k}")
