import re, sys
# per converted procedure: threadprivate block directly after the last declaration, sizing calls directly before the first executable
iscall = lambda l: re.match(r"^\s*call sizeScratch\(", l) is not None
iscomment = lambda l: l.lstrip().startswith("!") and not l.lstrip().lower().startswith("!$omp")
for p in sys.argv[1:]:
    L = open(p).read().splitlines(True); out = []; i = 0; n = 0
    while i < len(L):
        if iscall(L[i]) and not iscall(L[i-1]) and not L[i-1].lstrip().startswith("&"):
            j = i
            while j < len(L) and (iscall(L[j]) or L[j].lstrip().startswith("&")): j += 1
            calls = L[i:j]
            # pull the threadprivate block for this procedure out of what is already emitted
            t = max(k for k in range(len(out)) if out[k].strip() == "! one copy of the scratch arrays per thread")
            e = t + 1
            while e < len(out) and (out[e].lstrip().lower().startswith("!$omp")): e += 1
            tp = out[t:e]; del out[t:e]
            # last declaration line among what is emitted: drop trailing blanks/comments to find it
            d = len(out)
            while d > 0 and (out[d-1].strip() == "" or iscomment(out[d-1])): d -= 1
            out[d:d] = tp
            # skip blank after calls; emit the separator comments then the calls
            k = j
            while k < len(L) and L[k].strip() == "": k += 1
            m = k
            while m < len(L) and (L[m].strip() == "" or iscomment(L[m])): m += 1
            sep = L[k:m]
            # keep comments that describe the executable code below (after the last separator line) below the calls
            s = max([q for q in range(len(sep)) if re.match(r"^\s*! -{10,}", sep[q])] + [-1]) + 1
            out += sep[:s]; out += calls; out += ["\n"]; out += sep[s:]
            i = m; n += 1; continue
        out.append(L[i]); i += 1
    open(p, "w").write("".join(out)); print(p, n)
