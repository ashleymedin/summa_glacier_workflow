import sys
v=sys.argv[1]
def row(n): return n.ljust(25)+" | "+v.rjust(12)+" | "+"0.0".rjust(12)+" | "+"0.1".rjust(12)
rows="\\n".join(row(n) for n in ("absTolMatric","absTolAquifr","absTolWatVeg"))
print("localParamInfo.txt:^(lowerBoundHead [^\\n]*)(?=\\n)=>\\g<1>\\n"+rows)
