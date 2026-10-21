! One year of glacAreaChange's flow on a real start grid with no mass balance: volume budget, and where ice moves
program real_grid
  use sia_extract
  implicit none
  integer(i4b), parameter :: n = 3
  real(rkind), parameter :: A = 2.4e-24, cfl = 0.124, yr = 365.25_rkind*86400._rkind
  real(rkind), allocatable :: S(:,:), B(:,:), Mr(:,:), S0(:,:), div_q(:,:), Sn(:,:)
  integer(i4b), allocatable :: mask(:,:), l(:), lp(:), lm(:), lpp(:), lmm(:), k(:), kp(:), km(:), kpp(:), kmm(:)
  integer(i4b) :: nx, ny, i, u, iv, nsteps
  real(rkind) :: dx, t, dt_cfl, deltat, vDiv, vClamp, vLeak, gamma, fac
  character(len=64) :: case
  call get_command_argument(1, case)
  open(newunit=u, file=trim(case)//'.txt'); read(u,*) nx, ny, dx; close(u)
  allocate(S(nx,ny), B(nx,ny), Mr(nx,ny), mask(nx,ny), div_q(nx,ny), Sn(nx,ny), S0(nx,ny))
  open(newunit=u, file=trim(case)//'.bin', access='stream', form='unformatted'); read(u) S, B, Mr; close(u)
  mask = nint(Mr)
  l = [(i, i=1, ny)]; lp = [(i, i=2, ny), ny]; lpp = [(i, i=3, ny), ny, ny]; lm = [1, (i, i=1, ny-1)]; lmm = [1, 1, (i, i=1, ny-2)]
  k = [(i, i=1, nx)]; kp = [(i, i=2, nx), nx]; kpp = [(i, i=3, nx), nx, nx]; km = [1, (i, i=1, nx-1)]; kmm = [1, 1, (i, i=1, nx-2)]
  S = merge(S, B, mask==1); S0 = S
  do iv = 1, 2
    oneSided = iv == 2
    fac = 1._rkind
    gamma = 2._rkind * fac * A * (917._rkind*9.80616_rkind)**n / (n + 2_i4b)
    S = S0; t = 0; vDiv = 0; vClamp = 0; vLeak = 0; nsteps = 0
    do while(t < yr)
      call diffusion_MUSCL(S, B, mask, gamma, n, cfl, 31._rkind*86400._rkind, nx, ny, dx, dx, div_q, dt_cfl, l, lp, lm, lpp, lmm, k, kp, km, kpp, kmm)
      deltat = min(dt_cfl, yr - t, 31._rkind*86400._rkind)
      if(dt_cfl >= 3600._rkind .and. deltat < 3600._rkind) deltat = 3600._rkind
      t = t + deltat; nsteps = nsteps + 1
      vDiv = vDiv + sum(div_q)*deltat*dx*dx
      Sn = S + div_q*deltat
      vClamp = vClamp + sum(max(B - Sn, 0._rkind))*dx*dx
      Sn = max(Sn, B)
      vLeak = vLeak + sum(merge(Sn - B, 0._rkind, mask==0))*dx*dx
      S = merge(B, Sn, mask==0)
    enddo
    write(*,'(a,a,l2,a,i7,a)') trim(case), '  one-sided', oneSided, ', ', nsteps, ' steps in a year'
    write(*,'(a,4es11.3,a,f7.3,a)') '   divergence, clamp, leak, volume change (m3):', vDiv, vClamp, vLeak, sum(S-S0)*dx*dx, &
          '  = ', sum(S-S0)/count(S0-B>0.1_rkind), ' m over the ice'
    write(*,'(a,f8.2,a,f8.2)') '   thickening on the lowest 10% of the ice (m/yr):', sum(S-S0, mask=S0-B>0.1_rkind .and. S0<lowq(S0,B)) / &
          count(S0-B>0.1_rkind .and. S0<lowq(S0,B)), '   max |dS|', maxval(abs(S-S0))
    flush(6)
    if(iv == 1)then; open(newunit=u, file=trim(case)//'_1yr.bin', access='stream', form='unformatted', status='replace'); write(u) S; close(u); endif
    exit
  enddo
contains
  real(rkind) function lowq(S0, B)
    real(rkind), intent(in) :: S0(:,:), B(:,:)
    real(rkind), allocatable :: z(:)
    integer :: m
    z = pack(S0, S0-B>0.1_rkind); m = size(z)
    call sort(z); lowq = z(max(1, m/10))
  end function lowq
  subroutine sort(z)
    real(rkind), intent(inout) :: z(:)
    integer :: i, j; real(rkind) :: v
    do i = 2, size(z); v = z(i); j = i - 1
      do while(j >= 1); if(z(j) <= v) exit; z(j+1) = z(j); j = j - 1; enddo
      z(j+1) = v
    enddo
  end subroutine sort
end program real_grid
