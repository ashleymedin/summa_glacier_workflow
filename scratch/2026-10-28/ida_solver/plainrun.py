import sys, os, shutil, subprocess, re
tag=sys.argv[1]; vals=sys.argv[2].split(); extra=sys.argv[3:]
S=os.path.dirname(os.path.abspath(__file__)); R=f"{S}/p_{tag}"
shutil.rmtree(R, ignore_errors=True); os.makedirs(f"{R}/output"); os.makedirs(f"{R}/state")
shutil.copytree(f"{S}/tol_t4j/inputs", f"{R}/inputs", symlinks=False)
shutil.copy(f"{S}/wolida4/state/coldState.nc", f"{R}/state/")
c=open(f"{S}/wolida4/config.toml").read(); c=c[:c.index('[calibration]')].replace('/wolida4/',f'/p_{tag}/')
c=re.sub(r'start_time = .*','start_time = "2015-10-01 00:00"',c); open(f"{R}/config.toml","w").write(c)
names="frozenPrecipMultip tempCritRain glacierWindFactor glacierTempReduction albedoMax aquiferBaseflowExp k_soil vGn_n theta_sat Fcapil".split()
args=[]
for n,v in zip(names,vals): args+=["--param",n,v]
for e in extra:
    if "=>" in e:
        f,rx=e.split(":",1); a,b=rx.split("=>"); p=f"{R}/inputs/{f}"; t=open(p).read(); t2=re.sub(a,b,t,flags=re.M); assert t!=t2,e; open(p,"w").write(t2)
    else:
        k,v=e.split("="); args+=["--param",k,v]
subprocess.run(["caffeinate","-i","/Users/amedin/Research/SummaSundials/summa/bin/summa_sundials_mizuroute.exe","-c","config.toml"]+args,cwd=R,stdout=open(f"{R}/run.log","w"),stderr=subprocess.STDOUT)
