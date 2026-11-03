! closed-form dPsiLiq_dPsi0 of liquidHead vs finite differences at unsaturated total heads, at fixed liquid water and ice
program fd_fixed_dry
  use nr_type
  use soil_utils_module,only:liquidHead,volFracTot
  implicit none
  real(rkind),parameter :: alpha=-0.84_rkind, thr=0.03_rkind, ths0=0.5_rkind
  real(rkind) :: ns(3)=[1.2_rkind,1.5_rkind,3._rkind], ps(5)=[-5._rkind,-0.5_rkind,-0.02_rkind,-5.e-3_rkind,5.e-3_rkind]
  real(rkind) :: n,m,p,h,ice,liq,pl,pp,pm,dA,dT,mx; integer :: i,l,err; character(256) :: msg
  mx=0._rkind
  do i=1,3; do l=1,5
    n=ns(i); m=1._rkind-1._rkind/n; p=ps(l); h=1.e-6_rkind*max(abs(p),1.e-2_rkind)
    liq=0.4_rkind*(volFracTot(p,alpha,thr,ths0,n,m)-thr)+thr; ice=volFracTot(p,alpha,thr,ths0,n,m)-liq
    call liquidHead(p,liq,ice,alpha,n,ths0,thr,m,-1._rkind,pl,dA,dT,err,msg)
    call liquidHead(p+h,liq,ice,alpha,n,ths0,thr,m,-1._rkind,pp,dT,dT,err,msg)
    call liquidHead(p-h,liq,ice,alpha,n,ths0,thr,m,-1._rkind,pm,dT,dT,err,msg)
    write(*,'(f5.1,es11.2,2es15.6)') n,p,dA,(pp-pm)/(2*h); mx=max(mx,abs(dA*2*h/(pp-pm)-1._rkind))
  end do; end do
  write(*,'(a,es9.1)') 'max rel err',mx
end program
