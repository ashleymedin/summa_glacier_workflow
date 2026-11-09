import re, sys
# convert automatic real(rkind) arrays of one procedure to allocatable, save, threadprivate scratch sized by sizeScratch
# usage: toscratch.py file first_line last_line anchor_line_text dim1[,dim2...]
p, l0, l1, anchor, dims = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5].split(',')
L = open(p).read().splitlines(True); groups = {d: [] for d in dims}
pat = re.compile(r"^(\s*)real\(rkind\),dimension\((" + "|".join(map(re.escape, dims)) + r")\)(\s*)::(\s*)(\w+)(\s*)(!.*)?$", re.S)
for i in range(l0 - 1, l1):
    m = pat.match(L[i])
    if not m: continue
    ind, d, sp1, sp2, name, sp3, com = m.groups()
    head = "real(rkind),dimension(" + d + ")" + sp1
    newhead = "real(rkind),allocatable,save".ljust(len(head)) if len(head) > 28 else "real(rkind),allocatable,save "
    tail = name + "(:)" + " " * max(1, len(sp3) - 3)
    L[i] = ind + newhead + "::" + sp2 + tail + (com if com else "\n"); groups[d].append(name)
allnames = [n for d in dims for n in groups[d]]
def wrap(prefix, items, cont, close):
    lines = []; line = prefix
    for k, x in enumerate(items):
        tok = x + (", " if k < len(items) - 1 else close)
        if len(line) + len(tok) > 118: lines.append(line.rstrip() + " &"); line = cont
        line += tok
    lines.append(line); return "\n".join(lines) + "\n"
ins = "  ! one copy of the scratch arrays per thread\n" + wrap("  !$omp threadprivate(", allnames, "  !$omp& ", ")") + "\n"
for d in dims:
    for k in range(0, len(groups[d]), 20):
        ins += wrap("  call sizeScratch(1," + d + ",", groups[d][k:k + 20], "                  &", ")")
idx = [i for i in range(l0 - 1, len(L)) if L[i].rstrip("\n") == anchor]
assert idx, "anchor not found"
j = idx[0] - 1 if L[idx[0] - 1].strip() == "" else idx[0]
L.insert(j, ins)
s = "".join(L)
if "scratch_module" not in s: s = s.replace("USE nr_type\n", "USE nr_type\nUSE scratch_module,only:sizeScratch  ! size the per-thread scratch arrays\n", 1)
open(p, "w").write(s); print(p, {d: len(v) for d, v in groups.items()})
