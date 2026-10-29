#!/usr/bin/env python3
"""Old vs two-pow forms of the soil_utils van Genuchten functions, max relative difference over a grid of psi, T, alpha, n."""
import numpy as np
kB=1e-4; Tf=273.16; kap=333700/(9.80616*Tf); ts,tr,ks=0.4,0.05,1e-5
def blend_d(psi,od,ov):
    t=np.clip((psi+kB)/kB,0,1); s=3*t*t-2*t**3; return np.where(psi<-kB,od,od*(1-s)+(ks-ov)*6*t*(1-t)/kB)
def old(psi,T,a,n):
    m=1-1/n; x=psi*a; r={}
    o=ks*(((1-x**(n-1)*(1+x**n)**(-m))**2)/((1+x**n)**(m/2))); r["hydCond"]=o
    r["dTheta_dPsi"]=(ts-tr)*(-m*(1+x**n)**(-m-1))*n*x**(n-1)*a
    fx1=x**(n-1); fx2=(1+x**n)**(-m); dx1=a*(n-1)*x**(n-2); dx2=a*n*x**(n-1)*(-m)*(1+x**n)**(-m-1)
    fnm=(1-fx1*fx2)**2; dnm=(-dx1*fx2-fx1*dx2)*2*(1-fx1*fx2); fdm=(1+x**n)**(m/2); ddm=a*n*x**(n-1)*(m/2)*(1+x**n)**(m/2-1)
    r["dHydCond"]=blend_d(psi,ks*(dnm*fdm-ddm*fnm)/fdm**2,ks*fnm/fdm)
    mf=(-m*n*a*x**(n-1))*(1+x**n)**-1.; mfp=-m*n*a*(n-1)*a*x**(n-2)*(1+x**n)**-1.-(n*a*x**(n-1)*(1+x**n)**-2.)*(-m*n*a*x**(n-1))
    vfl=tr+(ts-tr)*(1+x**n)**(-m); r["d2Theta_dPsi2"]=mf*r["dTheta_dPsi"]+mfp*(vfl-tr)
    xt=a*kap*(T-Tf); r["dTheta_dTk"]=(a*kap)*n*xt**(n-1)*(-m)*(1+xt**n)**(-m-1)*(ts-tr)
    r["d2Theta_dTk2"]=(-a*kap*m*n*a*kap)*(ts-tr)*((n-1)*xt**(n-2)*(1+xt**n)**(-m-1)+n*(-m-1)*xt**(2*n-2)*(1+xt**n)**(-m-2))
    te=np.clip((vfl-tr)/(ts-tr),1e-3,None); y1=te**(-1/m)-1; d1=(-1/m)*te**(-1/m-1)/(ts-tr); d2=(1/n)*np.maximum(1e-15,y1)**(1/n-1); r["dPsi_dTheta"]=d1*d2/a
    return r
def new(psi,T,a,n):
    m=1-1/n; x=psi*a; r={}
    xn1=x**(n-1); sm=(1+xn1*x)**(-m); r["hydCond"]=ks*(1-xn1*sm)**2*np.sqrt(sm)
    s=1+xn1*x; r["dTheta_dPsi"]=(ts-tr)*(-m*s**(-m)/s)*n*xn1*a
    fx1=xn1; xs=1+fx1*x; fx2=xs**(-m); dx1=a*(n-1)*fx1/x; dx2=a*n*fx1*(-m)*fx2/xs
    fnm=(1-fx1*fx2)**2; dnm=(-dx1*fx2-fx1*dx2)*2*(1-fx1*fx2); fdm=1/np.sqrt(fx2); ddm=a*n*fx1*(m/2)*fdm/xs
    r["dHydCond"]=blend_d(psi,ks*(dnm*fdm-ddm*fnm)/fdm**2,ks*fnm/fdm)
    mf=(-m*n*a*xn1)/s; mfp=-m*n*a*(n-1)*a*(xn1/x)/s-(n*a*xn1/(s*s))*(-m*n*a*xn1)
    dth=(ts-tr)*(-m*sm/s)*n*xn1*a; r["d2Theta_dPsi2"]=mf*dth+mfp*(ts-tr)*sm
    xt=a*kap*(T-Tf); x1=xt**(n-1); r["dTheta_dTk"]=(a*kap)*n*x1*(-m)*(1+x1*xt)**(-m-1)*(ts-tr)
    s2=1+x1*xt; sm1=s2**(-m-1); r["d2Theta_dTk2"]=(-a*kap*m*n*a*kap)*(ts-tr)*((n-1)*(x1/xt)*sm1+n*(-m-1)*x1*x1*sm1/s2)
    vfl=tr+(ts-tr)*(1+x**n)**(-m); te=np.clip((vfl-tr)/(ts-tr),1e-3,None); y1=te**(-1/m); d1=(-1/m)*(y1/te)/(ts-tr); y1=np.maximum(1e-15,y1-1); y2=y1**(1/n); d2=(1/n)*(y2/y1); r["dPsi_dTheta"]=d1*d2/a
    return r
psi=-np.logspace(-9,3,400); T=Tf-np.logspace(-6,1.5,400)
for a in (-0.84,-14.5,-0.01): 
  for n in (1.2,1.5,2.68,4.0):
    o,w=old(psi,T,a,n),new(psi,T,a,n)
    print(f"alpha {a:6} n {n}: "+" ".join(f"{k} {np.nanmax(np.abs(w[k]-o[k])/np.maximum(np.abs(o[k]),1e-300)):.1e}" for k in o))
