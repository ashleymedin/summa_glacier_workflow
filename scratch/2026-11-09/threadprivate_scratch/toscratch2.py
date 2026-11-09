import re, sys
# convert the automatic arrays declared in lines l0..l1 of one procedure to allocatable, save, threadprivate scratch
# usage: toscratch2.py file l0 l1 [skipname,...]
p, l0, l1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); skip = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else set()
L = open(p).read().splitlines(True)
T = r"(real\((?:rkind|qp)\)|integer\(i4b\)|logical\(lgt\))"
pa = re.compile(r"^(\s*)" + T + r"(\s*)::(\s*)(\w+)\(([^()]*[A-Za-z][^()]*)\)(\s*)(!.*)?$", re.S)
pb = re.compile(r"^(\s*)" + T + r",dimension\(([^()]*[A-Za-z][^()]*)\)(\s*)::(\s*)(\w+)(\s*)(!.*)?$", re.S)
def newhead(typ, oldlen):
    h = typ + ",allocatable,save"; return h.ljust(oldlen) if len(h) < oldlen else h + " "
groups = {}; names = []; last = None
for i in range(l0 - 1, l1):
    m = pa.match(L[i])
    if m:
        ind, typ, sp1, sp2, name, dims, sp3, com = m.groups(); oldtail = len(name) + len(dims) + 2 + len(sp3); head = len(typ + sp1)
    else:
        m = pb.match(L[i])
        if not m: continue
        ind, typ, dims, sp1, sp2, name, sp3, com = m.groups(); oldtail = len(name) + len(sp3); head = len(typ + ",dimension(" + dims + ")" + sp1)
    if name in skip: continue
    d = [x.strip().replace(" ", "") for x in dims.split(",")]
    shape = "(:)" if len(d) == 1 else "(:,:)"
    tail = (name + shape).ljust(oldtail - 1) + " "
    L[i] = ind + newhead(typ, head) + "::" + sp2 + tail + (com if com else "\n")
    if len(d) == 1:
        lb, ub = d[0].split(":") if ":" in d[0] else ("1", d[0]); key = (typ.startswith("real"), "2" if False else typ, lb + "," + ub)
        key = ("r" if typ.startswith("real") else typ, lb + "," + ub)
    else:
        key = ("r2", ",".join(d))
    groups.setdefault(key, []).append(name); names.append(name); last = i
assert names, "no arrays"
def wrap(prefix, items, cont, close):
    lines = []; line = prefix
    for k, x in enumerate(items):
        tok = x + (", " if k < len(items) - 1 else close)
        if len(line) + len(tok) > 118: lines.append(line.rstrip() + " &"); line = cont
        line += tok
    lines.append(line); return "\n".join(lines) + "\n"
ind = re.match(r"^(\s*)", L[last]).group(1)
tp = ind + "! one copy of the scratch arrays per thread\n" + wrap(ind + "!$omp threadprivate(", names, ind + "!$omp& ", ")")
calls = ""
for (kind, b), v in groups.items():
    n = 20 if kind == "r" else 4 if kind == "r2" else 2
    for k in range(0, len(v), n): calls += wrap(ind + "call sizeScratch(" + b + ",", v[k:k + n], ind + "                &", ")")
j = l1
while j < len(L) and (L[j].strip() == "" or L[j].lstrip().startswith("!")): j += 1
L.insert(j, calls + "\n"); L.insert(last + 1, tp)
s = "".join(L)
if "scratch_module" not in s: s = re.sub(r"(?m)^(USE nr_type.*\n)", r"\1USE scratch_module,only:sizeScratch  ! size the per-thread scratch arrays\n", s, count=1)
open(p, "w").write(s); print(p, {f"{k[0]}({k[1]})": len(v) for k, v in groups.items()})
