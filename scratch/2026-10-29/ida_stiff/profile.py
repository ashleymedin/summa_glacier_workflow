#!/usr/bin/env python3
"""Sample a running SUMMA single-process run and total inclusive samples per libsumma routine, with the simulated date at each sample.
usage: profile.py tag exe_substring [interval_s=60] [sample_s=8]   (run ensemble.py with ONLY=<set> NW=1 under the same tag first)"""
import sys, os, re, subprocess, time, json, collections
S = os.path.dirname(os.path.abspath(__file__))
tag, key = sys.argv[1], sys.argv[2]
gap = float(sys.argv[3]) if len(sys.argv) > 3 else 60; dur = int(sys.argv[4]) if len(sys.argv) > 4 else 8
def pid():
    out = subprocess.run(["pgrep", "-f", key], capture_output=True, text=True).stdout.split()
    return int(out[-1]) if out else None
def lastdate():
    f = [os.path.join(r, "run.log") for r, d, fs in os.walk(f"{S}/ens_{tag}") if "run.log" in fs]
    if not f: return ""
    d = re.findall(r"^\s*(20\d\d)\s+(\d+)\s+(\d+)\s", open(f[0]).read(), flags=re.M)
    return "-".join(d[-1]) if d else ""
res = []
while True:
    p = pid()
    if p is None: break
    fn = f"{S}/prof_{tag}_{len(res):03d}.txt"
    d0 = lastdate()
    subprocess.run(["sample", str(p), str(dur), "-file", fn], capture_output=True)
    if not os.path.exists(fn): break
    inc = collections.Counter(); top = collections.Counter()
    txt = open(fn).read()
    for m in re.finditer(r"^[ +!:|]*?(\d+) (\S+)  \(in libsumma\.dylib\)", txt.split("Total number in stack")[0], flags=re.M):
        inc[m.group(2)] += int(m.group(1))
    sec = txt.split("Sort by top of stack")[-1]
    for m in re.finditer(r"^\s+(\S+)  \(in (\S+)\)\s+(\d+)$", sec, flags=re.M):
        top[m.group(1) + " [" + m.group(2) + "]"] += int(m.group(3))
    res.append({"date": lastdate() or d0, "inc": dict(inc), "top": dict(top)})
    json.dump(res, open(f"{S}/prof_{tag}.json", "w"))
    time.sleep(gap)
print("samples", len(res))
