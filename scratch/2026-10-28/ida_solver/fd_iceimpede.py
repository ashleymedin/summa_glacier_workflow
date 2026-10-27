from decimal import Decimal as D, getcontext
getcontext().prec=60
th_sat, th_res = D('0.3'), D('0.03')
def run(n, alpha, psi, xnum):
    n=D(n); alpha=D(alpha); m=1-1/n
    def eff(p):               # effective saturation from liquid head (exact)
        return (1+(-p*alpha)**n)**(-m)
    def deff(p):
        x=(-p*alpha)
        return (-m)*(1+x**n)**(-m-1)*n*x**(n-1)*(-alpha)   # d eff / d psi
    xnum=D(xnum)
    e=eff(psi); avail=xnum/e                 # theta_sat - ice - theta_res (exact)
    ice_exact=th_sat-th_res-avail
    # what the code sees: double-rounded ice, liq, then availPore from subtraction
    ice_d=float(ice_exact); liq_d=float(xnum+th_res)
    avail_d=D(0.3)*0+ (D(float(th_sat)) - D(ice_d) - D(float(th_res)))   # computed in exact arithmetic from the doubles' values
    # in double arithmetic:
    avail_dbl=0.3-ice_d-0.03
    liq_res=liq_d-0.03
    # analytic (code): availPore^2/(liq-theta_res) * deff
    ana=D(avail_dbl)**2/D(liq_res)*deff(psi)
    # exact derivative of ice w.r.t. psi at fixed liquid: (liq-res)/eff^2 * deff
    ex=xnum/e**2*deff(psi)
    # central difference of ice_exact(psi) = th_sat-th_res - xnum/eff(psi)
    h=abs(psi)*D('1e-6')
    fd=((th_sat-th_res-xnum/eff(psi+h))-(th_sat-th_res-xnum/eff(psi-h)))/(2*h)
    print(f"n={n} psi={psi} 1-eff={float(1-e):.2e} availPore={float(avail):.3e} | exact={float(ex):.4e} FD={float(fd):.4e} code={float(ana):.4e} | rel err code vs exact={float(abs(ana-ex)/abs(ex)):.2e}")
for n in ('1.5','2.0','3.0'):
    for psi in ('-2e-4','-1e-6','-1e-2'):
        run(n,'0.84',D(psi),'1.4e-8')
