import re
def move(fn, pat_hdr_before, items, after_key, drop_hdrs):
    L=open(fn).read().split('\n')
    # pull item lines
    pulled={}
    out=[]
    for l in L:
        m=[k for k in items if re.search(r"[%\s]"+k+r"\b\s*(\)|=|;)?",l) and (('::' in l) or ('mpar_meta' in l) or ('case(' in l)) and re.search(r"(::\s*|%|case\(')"+k+r"\b",l)]
        if m: pulled[m[0]]=l
        else: out.append(l)
    return out,pulled
