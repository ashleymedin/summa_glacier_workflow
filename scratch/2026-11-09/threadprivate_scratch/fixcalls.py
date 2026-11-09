import re, sys
# move each block of sizeScratch calls below any declarations that follow it
decl = re.compile(r"^\s*(real\s*\(|integer\s*\(|logical\s*\(|character\s*[(*]|complex\s*\(|type\s*\(|class\s*\(|!\$omp\s+threadprivate|!\$omp&|save\b|use\b|implicit\b|&)", re.I)
for p in sys.argv[1:]:
    L = open(p).read().splitlines(True); i = 0; moved = 0
    while i < len(L):
        if re.match(r"^\s*call sizeScratch\(", L[i]) and not re.match(r"^\s*call sizeScratch\(", L[i-1]) and not L[i-1].lstrip().startswith("&"):
            j = i
            while j < len(L) and (re.match(r"^\s*call sizeScratch\(", L[j]) or L[j].lstrip().startswith("&")): j += 1
            blk = L[i:j]; k = j
            if k < len(L) and L[k].strip() == "": blk.append(L[k]); k += 1
            m = k
            while m < len(L) and (L[m].strip() == "" or L[m].lstrip().startswith("!") and not L[m].lstrip().lower().startswith("!$omp") or decl.match(L[m])): m += 1
            if any(decl.match(x) for x in L[k:m]):
                # insert just before the first executable, after its leading comment lines are kept above
                n = m
                while n > k and (L[n-1].lstrip().startswith("!") and not L[n-1].lstrip().lower().startswith("!$omp") or L[n-1].strip() == ""): n -= 1
                L = L[:i] + L[k:n] + blk + L[n:]; moved += 1
                i = n
            else: i = j
        i += 1
    open(p, "w").write("".join(L)); print(p, "moved", moved)
