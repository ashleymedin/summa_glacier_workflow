! Known-answer tests of glacAreaChange.f90's diffusion_MUSCL, stepped as run_flowModel steps it (no debris):
!  1 Halfar dome on a flat bed against the similarity solution, and its volume
!  2 a valley glacier over a bed step, 1D (ny=1) against 2D (walled valley), with a volume budget
program sia_test
  use sia_extract
  implicit none
  integer(i4b), parameter :: n = 3
  real(rkind), parameter :: A = 2.4e-24, cfl = 0.124, rhoi = 917._rkind, g = 9.80616_rkind, yr = 365.25_rkind*86400._rkind
  real(rkind) :: gamma
  gamma = 2._rkind * A * (rhoi*g)**n / (n + 2_i4b)
  call halfar()
  call valley()
  closeEdge = .true.; oneSided = .true.
  write(*,'(/a)') '=== mask edge closed + one-sided cross slopes ==='
  call halfar()
  call valley()
contains

  ! one run_flowModel-style integration over t_total (s); mb(z) in m s-1 added to the surface, budget terms in m3
  subroutine integrate(S, B, mask, dx, t_total, useMB, mbScale, vMB, vDiv, vClamp, vLeak)
    real(rkind), intent(inout) :: S(:,:)
    real(rkind), intent(in)    :: B(:,:), dx, t_total, mbScale
    integer(i4b), intent(in)   :: mask(:,:)
    logical, intent(in)        :: useMB
    real(rkind), intent(inout) :: vMB, vDiv, vClamp, vLeak
    integer(i4b) :: nx, ny, i
    integer(i4b), allocatable :: l(:), lp(:), lm(:), lpp(:), lmm(:), k(:), kp(:), km(:), kpp(:), kmm(:)
    real(rkind), allocatable :: div_q(:,:), m_dot(:,:), Sn(:,:)
    real(rkind) :: t, dt_cfl, deltat
    nx = size(S,1); ny = size(S,2)
    allocate(div_q(nx,ny), m_dot(nx,ny), Sn(nx,ny))
    l = [(i, i=1, ny)]; lp = [(i, i=2, ny), ny]; lpp = [(i, i=3, ny), ny, ny]; lm = [1, (i, i=1, ny-1)]; lmm = [1, 1, (i, i=1, ny-2)]
    if(ny == 1)then; lpp = [1]; lmm = [1]; lp = [1]; lm = [1]; endif
    k = [(i, i=1, nx)]; kp = [(i, i=2, nx), nx]; kpp = [(i, i=3, nx), nx, nx]; km = [1, (i, i=1, nx-1)]; kmm = [1, 1, (i, i=1, nx-2)]
    t = 0._rkind
    do while(t < t_total)
      m_dot = 0._rkind
      if(useMB) m_dot = merge(mbScale*min(0.007_rkind*(S - 2000._rkind), 2._rkind)/yr, 0._rkind, mask==1)
      call diffusion_MUSCL(S, B, mask, gamma, n, cfl, 31._rkind*86400._rkind, nx, ny, dx, dx, div_q, dt_cfl, &
                           l, lp, lm, lpp, lmm, k, kp, km, kpp, kmm)
      deltat = min(dt_cfl, t_total - t, 31._rkind*86400._rkind)
      if(dt_cfl >= 3600._rkind .and. deltat < 3600._rkind) deltat = 3600._rkind
      t = t + deltat
      vMB  = vMB  + sum(m_dot)*deltat*dx*dx
      vDiv = vDiv + sum(div_q)*deltat*dx*dx
      Sn = S + (m_dot + div_q)*deltat
      vClamp = vClamp + sum(max(B - Sn, 0._rkind))*dx*dx
      Sn = max(Sn, B)
      vLeak = vLeak + sum(merge(Sn - B, 0._rkind, mask==0))*dx*dx
      S = merge(B, Sn, mask==0)
    enddo
  end subroutine integrate

  ! Halfar (1983) dome, n=3, flat bed: H = H0 (t0/t)^(1/9) [1 - ((t0/t)^(1/18) r/R0)^(4/3)]^(3/7)
  subroutine halfar()
    integer(i4b), parameter :: nx = 121
    real(rkind), parameter :: dx = 250._rkind, R0 = 10000._rkind, H0 = 300._rkind
    real(rkind) :: S(nx,nx), B(nx,nx), Ha(nx,nx), r(nx,nx), t0, t, vMB, vDiv, vClamp, vLeak, v0
    integer(i4b) :: mask(nx,nx), i, j, iy
    t0 = (7._rkind/4._rkind)**3 * R0**4 / (18._rkind * gamma * H0**7)
    do j = 1, nx; do i = 1, nx; r(i,j) = dx*sqrt(real((i-61)**2 + (j-61)**2, rkind)); enddo; enddo
    B = 0._rkind; mask = 1
    S = dome(t0)
    v0 = sum(S)*dx*dx
    vMB = 0; vDiv = 0; vClamp = 0; vLeak = 0
    write(*,'(a,f8.1,a)') 'Halfar dome, R0 10 km, H0 300 m, 250 m cells; t0 = ', t0/yr, ' yr'
    write(*,'(a)') '   years   H(0) model  analytic   max|dH| (m)  rms dH   R(model)  R(analytic) (km)  dV/V0'
    t = t0
    do iy = 1, 5
      call integrate(S, B, mask, dx, 200._rkind*yr, .false., 0._rkind, vMB, vDiv, vClamp, vLeak)
      t = t + 200._rkind*yr
      Ha = dome(t)
      write(*,'(i8,2f11.2,2f11.2,2f10.2,es13.3)') iy*200, S(61,61), Ha(61,61), maxval(abs(S-Ha)), sqrt(sum((S-Ha)**2)/count(Ha>0 .or. S>0.1)), &
            dx*count(S(61:,61)>0.1_rkind)/1000._rkind, R0*(t/t0)**(1._rkind/18._rkind)/1000._rkind, (sum(S)*dx*dx - v0)/v0
    enddo
    write(*,'(a,4es11.3)') '   budget (m3): divergence, clamp, leak, volume change =', vDiv, vClamp, vLeak, sum(S)*dx*dx - v0
  end subroutine halfar

  function dome(t) result(H)
    real(rkind), intent(in) :: t
    real(rkind) :: H(121,121), t0, x
    real(rkind), parameter :: R0 = 10000._rkind, H0 = 300._rkind, dx = 250._rkind
    integer(i4b) :: i, j
    t0 = (7._rkind/4._rkind)**3 * R0**4 / (18._rkind * gamma * H0**7)
    do j = 1, 121; do i = 1, 121
      x = (t0/t)**(1._rkind/18._rkind) * dx*sqrt(real((i-61)**2 + (j-61)**2, rkind)) / R0
      H(i,j) = 0._rkind
      if(x < 1._rkind) H(i,j) = H0 * (t0/t)**(1._rkind/9._rkind) * (1._rkind - x**(4._rkind/3._rkind))**(3._rkind/7._rkind)
    enddo; enddo
  end function dome

  ! valley glacier on a 0.1 slope with a 100 m bed step down at 8 km, b = 0.007 (z - 2000) m w.e. yr-1, at most 2;
  !  1D, then 2D: the whole grid glacier (should equal 1D), and 7 cells wide between walls 0, 50 and 500 m high
  subroutine valley()
    integer(i4b), parameter :: nx = 200, ny = 11, w0 = 3, w1 = 9, nYr = 600
    real(rkind), parameter :: dx = 100._rkind
    real(rkind) :: S1(nx,1), B1(nx,1), S2(nx,ny), B2(nx,ny), x, wall(6) = [-1._rkind, 0._rkind, 50._rkind, 500._rkind, 50._rkind, 500._rkind]
    real(rkind) :: a(4), c(4)
    integer(i4b) :: m1(nx,1), m2(nx,ny), i, iw, width
    do i = 1, nx
      x = (i - 0.5_rkind)*dx
      B1(i,1) = 2500._rkind - 0.1_rkind*x
      if(x > 8000._rkind) B1(i,1) = B1(i,1) - 100._rkind
    enddo
    m1 = 1; S1 = B1; a = 0
    call integrate(S1, B1, m1, dx, nYr*yr, .true., 1._rkind, a(1), a(2), a(3), a(4))
    write(*,'(/a,i0,a)') 'Valley over a 100 m bed step at 8 km, 100 m cells, ', nYr, ' yr from no ice'
    write(*,'(a)') '   run              V/width (m2)  terminus (km)  centre S - 1D max (m)  budget: mb, divergence, clamp, leak (m3)'
    write(*,'(a,f14.0,f12.2,f20.2,4es11.3)') '   1D            ', sum(S1-B1)*dx, dx*count(S1(:,1)-B1(:,1)>0.1_rkind)/1000._rkind, 0._rkind, a
    do iw = 1, 6
      B2 = spread(B1(:,1), 2, ny); m2 = 1; width = ny
      if(wall(iw) >= 0._rkind)then
        m2 = 0; m2(:, w0:w1) = 1; width = w1-w0+1
        if(iw > 4) m2 = 1
        B2(:, :w0-1) = B2(:, :w0-1) + wall(iw); B2(:, w1+1:) = B2(:, w1+1:) + wall(iw)
      endif
      S2 = B2; c = 0
      call integrate(S2, B2, m2, dx, nYr*yr, .true., 1._rkind, c(1), c(2), c(3), c(4))
      if(wall(iw) < 0._rkind)then
        write(*,'(a)', advance='no') '   2D full width '
      else
        write(*,'(a,i4,a)', advance='no') '   2D walls', int(wall(iw)), merge(' m in   ', ' m      ', iw > 4)
      endif
      write(*,'(f8.0,f12.2,f20.2,4es11.3)') sum(S2(:,w0:w1)-B2(:,w0:w1))*dx/merge(width, w1-w0+1, wall(iw) >= 0._rkind), dx*count(S2(:,6)-B2(:,6)>0.1_rkind)/1000._rkind, &
            maxval(abs(S2(:,6)-S1(:,1))), c
      write(*,'(a,7f6.0,a,7f6.0)') '      thickness across at 4 km:', (S2(40,i)-B2(40,i), i=w0,w1), '   at 8.5 km:', (S2(85,i)-B2(85,i), i=w0,w1)
      flush(6)
    enddo
  end subroutine valley
end program sia_test
