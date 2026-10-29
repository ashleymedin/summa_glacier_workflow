#!/usr/bin/env python3
"""Attribute leaf samples (malloc/free, pow, memmove) in `sample` call graphs to their nearest libsumma caller.
usage: attribute.py prof_<tag>_*.txt"""
import sys, re, collections
LEAF = {"alloc": re.compile(r"malloc|_free$|^free$|xzm_|deduplicated|calloc|realloc"),
        "pow": re.compile(r"^pow$|DYLD-STUB\$\$pow"), "copy": re.compile(r"memmove|memset|memcpy")}
pat = re.compile(r"^([ +!:|]*)(\d+) (.+?)  \(in (\S+)\)")
res = {k: collections.Counter() for k in LEAF}; tot = collections.Counter(); main = 0
for fn in sys.argv[1:]:
    txt = open(fn).read().split("Total number in stack")[0]
    stack = []
    for line in txt.splitlines():
        m = pat.match(line)
        if not m: continue
        depth, n, name, lib = len(m.group(1)), int(m.group(2)), m.group(3).split(" ")[0], m.group(4)
        while stack and stack[-1][0] >= depth: stack.pop()
        stack.append((depth, name, lib, n))
        if name == "__summa_simulation_MOD_evaluate_objectives": main += n
        for k, rx in LEAF.items():
            if rx.search(name) and lib != "libsumma.dylib":
                parent = stack[-2] if len(stack) > 1 else None
                if parent and rx.search(parent[1]): continue  # count the outermost leaf frame only
                caller = next((s[1] for s in reversed(stack[:-1]) if s[2] == "libsumma.dylib"), "?")
                res[k][caller] += n; tot[k] += n
for k in LEAF:
    print(f"== {k}: {100*tot[k]/main:.1f}% of main-thread samples")
    for c, n in res[k].most_common(15): print(f"  {100*n/main:5.1f}%  {c}")
