! smallest vGn_n at which the floored analytic dPsiLiq_dPsi0 is off by >1% at a given distance below psiSmooth
program fd_nscan
  use nr_type
  use soil_utils_module,only:liquidHead,dVolFracTot_dPsi,psiSmooth
  implicit none
  real(rkind),parameter :: alpha=-0.84_rkind, thr=0.03_rkind, ths0=0.5_rkind, ice=0.4_rkind
  real(rkind) :: ds(4)=[-1.e-3_rkind,-1.e-4_rkind,-5.e-5_rkind,-2.e-5_rkind]
  real(rkind) :: n,m,liq,p,h,pl,pp,pm,dA,dT; integer :: l,i,err; character(256) :: msg
  liq=ths0-ice
  do l=1,4
    do i=0,280
      n=1.2_rkind+0.01_rkind*i; m=1._rkind-1._rkind/n; p=psiSmooth+ds(l); h=1.e-3_rkind*abs(ds(l))
      call liquidHead(p,liq,ice,alpha,n,ths0,thr,m,dVolFracTot_dPsi(p,alpha,thr,ths0,n,m),-1._rkind,pl,dA,dT,err,msg)
      call liquidHead(p+h,liq,ice,alpha,n,ths0,thr,m,dVolFracTot_dPsi(p+h,alpha,thr,ths0,n,m),-1._rkind,pp,dT,dT,err,msg)
      call liquidHead(p-h,liq,ice,alpha,n,ths0,thr,m,dVolFracTot_dPsi(p-h,alpha,thr,ths0,n,m),-1._rkind,pm,dT,dT,err,msg)
      if(abs(dA/((pp-pm)/(2*h))-1._rkind) > 1.e-2_rkind)then
        write(*,'(a,es8.1,a,f5.2,a,es10.2,a,f6.3)') 'psi0-psiSmooth',ds(l),'  first bad n',n,'  analytic',dA,'  FD',(pp-pm)/(2*h); exit
      endif
    end do
  end do
end program
