! analytic vs finite-difference dPsiLiq_dPsi0 of liquidHead across psiSmooth, at fixed liquid water and ice
program fd_nofloor2
  use nr_type
  use soil_utils_module,only:liquidHead,smoothHead,dSmoothHead_dPsi,psiSmooth
  implicit none
  real(rkind),parameter :: alpha=-0.84_rkind, thr=0.03_rkind
  real(rkind) :: ns(4)=[1.2_rkind,1.5_rkind,2._rkind,4._rkind], ths(2)=[0.45_rkind,0.6_rkind], fi(2)=[0.7_rkind,0.95_rkind]
  real(rkind) :: ds(9)=[-1.e-3_rkind,-1.e-4_rkind,-1.e-5_rkind,-1.e-6_rkind,-1.e-7_rkind,1.e-7_rkind,1.e-5_rkind,1.e-4_rkind,1.e-3_rkind]
  real(rkind) :: n,m,ths0,ice,liq,psi0,h,pl,pp,pm,dA,dFD,dL,dR
  integer :: i,j,k,l,err; character(256) :: msg
  write(*,'(a)') '    n  th_sat   ice  psi0-psiS     analytic          FD(c)   FD(left)  FD(right)'
  do i=1,4; do j=1,2; do k=1,2
    n=ns(i); m=1._rkind-1._rkind/n; ths0=ths(j)
    ice=fi(k)*(ths0-thr); liq=ths0-ice  ! saturated total water with fixed liquid and ice
    do l=1,9
      psi0=psiSmooth+ds(l); h=1.e-3_rkind*min(abs(ds(l)),1.e-4_rkind)
      call lh(psi0,pl,dA); call lh(psi0+h,pp,dL); call lh(psi0-h,pm,dL)
      dFD=(pp-pm)/(2*h); dL=(pl-pm)/h; dR=(pp-pl)/h
      write(*,'(f5.1,f7.2,f7.3,es11.1,4es15.6)') n,ths0,ice,ds(l),dA,dFD,dL,dR
    end do
  end do; end do; end do
contains
  subroutine lh(p,psiL,d)
    real(rkind),intent(in) :: p; real(rkind),intent(out) :: psiL,d
    real(rkind) :: dT
    call liquidHead(p,liq,ice,alpha,n,ths0,thr,m,dth(smoothHead(p))*dSmoothHead_dPsi(p),-1._rkind,psiL,d,dT,err,msg)
  end subroutine
  function dth(q); real(rkind),intent(in)::q; real(rkind)::dth,x1,s
    x1=(q*alpha)**(n-1._rkind); s=1._rkind+x1*q*alpha; dth=(ths0-thr)*(-m*s**(-m)/s)*n*x1*alpha
  end function
end program
