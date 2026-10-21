module sia_extract
  implicit none
  integer, parameter :: rkind = selected_real_kind(15), i4b = selected_int_kind(9)
  logical :: oneSided = .false.  ! cross slopes one-sided where a neighbour has no ice
contains
subroutine diffusion_MUSCL(S, B, mask, gamma, n, cfl, max_dt, nx, ny, dx, dy, div_q, dt_cfl, &
                          l, lp, lm, lpp, lmm, k, kp, km, kpp, kmm)
  implicit none
  ! Arguments
  real(rkind), intent(in) :: S(nx,ny), B(nx,ny), dx, dy, gamma, cfl, max_dt
  integer(i4b), intent(in) :: mask(nx,ny), nx, ny, n
  integer(i4b), intent(in) :: l(ny), lp(ny), lm(ny), lpp(ny), lmm(ny)
  integer(i4b), intent(in) :: k(nx), kp(nx), km(nx), kpp(nx), kmm(nx)
  real(rkind), intent(out) :: div_q(nx,ny), dt_cfl
  ! Local variables
  real(rkind) :: H(nx,ny)
  real(rkind) :: Sklp(nx,ny), Sklm(nx,ny), Skplp(nx,ny), Skplm(nx,ny), Skpl(nx,ny), Skl(nx,ny)
  real(rkind) :: Skmlp(nx,ny), Skmlm(nx,ny), Skml(nx,ny)
  real(rkind) :: Hkpl(nx,ny), Hkppl(nx,ny), Hkml(nx,ny), Hkmml(nx,ny), Hkl(nx,ny), Hklp(nx,ny)
  real(rkind) :: Hklpp(nx,ny), Hklm(nx,ny), Hklmm(nx,ny)
  real(rkind) :: H_l_up_m(nx,ny), H_l_up_p(nx,ny)
  real(rkind) :: H_l_dn_m(nx,ny), H_l_dn_p(nx,ny)
  real(rkind) :: f_l_p(nx,ny), f_l_m(nx,ny)
  real(rkind) :: D_l_up_m(nx,ny), D_l_up_p(nx,ny), D_l_up_min(nx,ny), D_l_up_max(nx,ny)
  real(rkind) :: D_l_dn_m(nx,ny), D_l_dn_p(nx,ny), D_l_dn_min(nx,ny), D_l_dn_max(nx,ny)
  real(rkind) :: D_l_up(nx,ny), D_l_dn(nx,ny)
  real(rkind) :: H_k_up_m(nx,ny), H_k_up_p(nx,ny), H_k_dn_m(nx,ny), H_k_dn_p(nx,ny)
  real(rkind) :: f_k_p(nx,ny), f_k_m(nx,ny)
  real(rkind) :: D_k_up_m(nx,ny), D_k_up_p(nx,ny), D_k_up_min(nx,ny), D_k_up_max(nx,ny)
  real(rkind) :: D_k_dn_m(nx,ny), D_k_dn_p(nx,ny), D_k_dn_min(nx,ny), D_k_dn_max(nx,ny)
  real(rkind) :: D_k_up(nx,ny), D_k_dn(nx,ny)
  real(rkind) :: divisor, div_k(nx,ny), div_l(nx,ny)
  integer(i4b) :: i, j
  real(rkind), dimension(nx,ny) :: Xkpl, Xkml, Xkplp, Xkmlp, Xkplm, Xkmlm, Xklp, Xklm, Yplp, Yplm, Ymlp, Ymlm

  ! Keep diffusion thickness nonnegative and zero outside glacier mask.
  H = merge(max(S - B, 0._rkind), 0._rkind, mask==1_i4b) ! H = ice thickness, S = surface height, B = bed topography

  ! indices
  Sklp  = S(k  ,lp )
  Sklm  = S(k  ,lm )
  Skplp = S(kp ,lp )
  Skplm = S(kp ,lm )
  Skpl  = S(kp ,l  )
  Skl   = S(k  ,l  )
  Skmlp = S(km ,lp )
  Skmlm = S(km ,lm )
  Skml  = S(km ,l  )
  !
  Hkpl  = H(kp ,l  )
  Hkppl = H(kpp,l  )
  Hkml  = H(km ,l  )
  Hkmml = H(kmm,l  )
  Hkl   = H(k  ,l  )
  Hklp  = H(k  ,lp )
  Hklpp = H(k  ,lpp)
  Hklm  = H(k  ,lm )
  Hklmm = H(k  ,lmm)

  ! cross-slope neighbours: an ice-free neighbour is replaced by the reflection of the other side
  Xkpl = Skpl; Xkml = Skml; Xkplp = Skplp; Xkmlp = Skmlp; Xkplm = Skplm; Xkmlm = Skmlm
  Xklp = Sklp; Xklm = Sklm
  if(oneSided)then
    call refl(S(kp,l ), S(k,l ), S(km,l ), H(kp,l )>0, H(km,l )>0, Xkpl , Xkml )
    call refl(S(kp,lp), S(k,lp), S(km,lp), H(kp,lp)>0, H(km,lp)>0, Xkplp, Xkmlp)
    call refl(S(kp,lm), S(k,lm), S(km,lm), H(kp,lm)>0, H(km,lm)>0, Xkplm, Xkmlm)
    call refl(S(k ,lp), S(k,l ), S(k ,lm), H(k,lp )>0, H(k,lm )>0, Xklp , Xklm )
    call refl(S(kp,lp), S(kp,l), S(kp,lm), H(kp,lp)>0, H(kp,lm)>0, Yplp, Yplm)
    call refl(S(km,lp), S(km,l), S(km,lm), H(km,lp)>0, H(km,lm)>0, Ymlp, Ymlm)
  else
    Yplp = Skplp; Yplm = Skplm; Ymlp = Skmlp; Ymlm = Skmlm
  endif

  ! calculate l+1/2 index
  H_l_up_m = minus(Hklm, Hkl, Hklp)
  H_l_up_p = pluss(Hkl, Hklp, Hklpp)
  H_l_up_m = max(H_l_up_m, 0._rkind)
  H_l_up_p = max(H_l_up_p, 0._rkind)

  ! calculate l-1/2 index
  H_l_dn_m = minus(Hklmm, Hklm, Hkl)
  H_l_dn_p = pluss(Hklm, Hkl, Hklp)
  H_l_dn_m = max(H_l_dn_m, 0._rkind)
  H_l_dn_p = max(H_l_dn_p, 0._rkind)

  ! calculate l flux
  f_l_p = flux(Xkpl, Xkml, Xkplp, Xkmlp, Sklp, Skl, dy, dx, n)
  f_l_m  = flux(Xkpl, Xkml, Xkplm, Xkmlm, Skl, Sklm, dy, dx, n)

  ! calculate l Diffusivity
  D_l_up_m = gamma * H_l_up_m**(n+2_i4b) * f_l_p  ! equation 30 Jarosh 2013
  D_l_up_p = gamma * H_l_up_p**(n+2_i4b) * f_l_p  ! equation 30 Jarosh 2013
  D_l_up_min = min(D_l_up_m, D_l_up_p)            ! equation 31 Jarosh 2013
  D_l_up_max = max(D_l_up_m, D_l_up_p)            ! equation 32 Jarosh 2013
  !
  D_l_dn_m = gamma * H_l_dn_m**(n+2_i4b) * f_l_m  ! equation 30 Jarosh 2013
  D_l_dn_p = gamma * H_l_dn_p**(n+2_i4b) * f_l_m  ! equation 30 Jarosh 2013
  D_l_dn_min = min(D_l_dn_m, D_l_dn_p)            ! equation 31 Jarosh 2013
  D_l_dn_max = max(D_l_dn_m, D_l_dn_p)            ! equation 32 Jarosh 2013

  ! equation 33 Jarosh 2013
  D_l_up = 0._rkind
  do j = 1, nx
    do i = 1, ny
      if(Sklp(j,i) <= Skl(j,i) .and. H_l_up_m(j,i) <= H_l_up_p(j,i))then
        D_l_up(j,i) = D_l_up_min(j,i)
      else if(Sklp(j,i) <= Skl(j,i) .and. H_l_up_m(j,i) > H_l_up_p(j,i))then
        D_l_up(j,i) = D_l_up_max(j,i)
      else if(Sklp(j,i) > Skl(j,i) .and. H_l_up_m(j,i) <= H_l_up_p(j,i))then
        D_l_up(j,i) = D_l_up_max(j,i)
      else if(Sklp(j,i) > Skl(j,i) .and. H_l_up_m(j,i) > H_l_up_p(j,i))then
        D_l_up(j,i) = D_l_up_min(j,i)
      endif
    enddo
  enddo
  D_l_dn = 0._rkind
  do j = 1, nx
    do i = 1, ny
      if(Skl(j,i) <= Sklm(j,i) .and. H_l_dn_m(j,i) <= H_l_dn_p(j,i))then
        D_l_dn(j,i) = D_l_dn_min(j,i)
      else if(Skl(j,i) <= Sklm(j,i) .and. H_l_dn_m(j,i) > H_l_dn_p(j,i))then
        D_l_dn(j,i) = D_l_dn_max(j,i)
      else if(Skl(j,i) > Sklm(j,i) .and. H_l_dn_m(j,i) <= H_l_dn_p(j,i))then
        D_l_dn(j,i) = D_l_dn_max(j,i)
      else if(Skl(j,i) > Sklm(j,i) .and. H_l_dn_m(j,i) > H_l_dn_p(j,i))then
        D_l_dn(j,i) = D_l_dn_min(j,i)
      endif
    enddo
  enddo
  ! enforce zero diffusion outside the mask
  D_l_up = merge(0._rkind, D_l_up, mask==0)
  D_l_dn = merge(0._rkind, D_l_dn, mask==0)

  ! calculate k+1/2 index
  H_k_up_m = minus(Hkml, Hkl, Hkpl)
  H_k_up_p = pluss(Hkl, Hkpl, Hkppl)
  H_k_up_m = max(H_k_up_m, 0._rkind)
  H_k_up_p = max(H_k_up_p, 0._rkind)

  ! calculate k-1/2 index
  H_k_dn_m = minus(Hkmml, Hkml, Hkl)
  H_k_dn_p = pluss(Hkml, Hkl, Hkpl)
  H_k_dn_m = max(H_k_dn_m, 0._rkind)
  H_k_dn_p = max(H_k_dn_p, 0._rkind)

  ! calculate k flux
  f_k_p = flux(Xklp, Xklm, Yplp, Yplm, Skpl, Skl, dx, dy, n)
  f_k_m = flux(Xklp, Xklm, Ymlp, Ymlm, Skl, Skml, dx, dy, n)

  ! calculate k Diffusivity
  D_k_up_m = gamma * H_k_up_m**(n+2_i4b) * f_k_p  ! equation 30 Jarosh 2013
  D_k_up_p = gamma * H_k_up_p**(n+2_i4b) * f_k_p  ! equation 30 Jarosh 2013
  D_k_up_min = min(D_k_up_m, D_k_up_p)            ! equation 31 Jarosh 2013
  D_k_up_max = max(D_k_up_m, D_k_up_p)            ! equation 32 Jarosh 2013
  !
  D_k_dn_m = gamma * H_k_dn_m**(n+2_i4b) * f_k_m  ! equation 30 Jarosh 2013
  D_k_dn_p = gamma * H_k_dn_p**(n+2_i4b) * f_k_m  ! equation 30 Jarosh 2013
  D_k_dn_min = min(D_k_dn_m, D_k_dn_p)            ! equation 31 Jarosh 2013
  D_k_dn_max = max(D_k_dn_m, D_k_dn_p)            ! equation 32 Jarosh 2013

  ! equation 33 Jarosh 2013
  D_k_up = 0._rkind
  do j = 1, nx
    do i = 1, ny
      if(Skpl(j,i) <= Skl(j,i) .and. H_k_up_m(j,i) <= H_k_up_p(j,i))then
        D_k_up(j,i) = D_k_up_min(j,i)
      else if(Skpl(j,i) <= Skl(j,i) .and. H_k_up_m(j,i) > H_k_up_p(j,i))then
        D_k_up(j,i) = D_k_up_max(j,i)
      else if(Skpl(j,i) > Skl(j,i) .and. H_k_up_m(j,i) <= H_k_up_p(j,i))then
        D_k_up(j,i) = D_k_up_max(j,i)
      else if(Skpl(j,i) > Skl(j,i) .and. H_k_up_m(j,i) > H_k_up_p(j,i))then
        D_k_up(j,i) = D_k_up_min(j,i)
      endif
    enddo
  enddo
  D_k_dn = 0._rkind
  do j = 1, nx
    do i = 1, ny
      if(Skl(j,i) <= Skml(j,i) .and. H_k_dn_m(j,i) <= H_k_dn_p(j,i))then
        D_k_dn(j,i) = D_k_dn_min(j,i)
      else if(Skl(j,i) <= Skml(j,i) .and. H_k_dn_m(j,i) > H_k_dn_p(j,i))then
        D_k_dn(j,i) = D_k_dn_max(j,i)
      else if(Skl(j,i) > Skml(j,i) .and. H_k_dn_m(j,i) <= H_k_dn_p(j,i))then
        D_k_dn(j,i) = D_k_dn_max(j,i)
      else if(Skl(j,i) > Skml(j,i) .and. H_k_dn_m(j,i) > H_k_dn_p(j,i))then
        D_k_dn(j,i) = D_k_dn_min(j,i)
      endif
    enddo
  enddo
  ! enforce zero diffusion outside the mask
  D_k_up = merge(0._rkind, D_k_up, mask==0)
  D_k_dn = merge(0._rkind, D_k_dn, mask==0)

  ! calculate delta t and t
  divisor = max(maxval(abs(D_k_up)), maxval(abs(D_k_dn)), maxval(abs(D_l_up)), maxval(abs(D_l_dn)))
  if(divisor == 0._rkind)then
    dt_cfl = max_dt
  else
    dt_cfl = cfl * min(dy**2, dx**2) / divisor
  endif

  ! Calculate the time step values
  div_l = SIA(D_l_up, Sklp, Skl, D_l_dn, Sklm, dy) ! equation 36 Jarosh 2013
  div_k = SIA(D_k_up, Skpl, Skl, D_k_dn, Skml, dx) ! equation 36 Jarosh 2013
  div_q = div_k + div_l

contains
  ! neighbours p and m of centre c for a centred difference; one without ice is the reflection of the other, both: c
  subroutine refl(p, c, m, hasP, hasM, xp, xm)
    real(rkind), intent(in) :: p(:,:), c(:,:), m(:,:)
    logical, intent(in) :: hasP(:,:), hasM(:,:)
    real(rkind), intent(out) :: xp(:,:), xm(:,:)
    xp = merge(p, merge(2._rkind*c - m, c, hasM), hasP)
    xm = merge(m, merge(2._rkind*c - p, c, hasP), hasM)
  end subroutine refl
end subroutine diffusion_MUSCL
function superbee(r)
  implicit none
  real(rkind), intent(in) :: r(:,:)
  real(rkind), allocatable :: superbee(:,:)

  allocate(superbee(size(r,1), size(r,2)))
  superbee = max(0._rkind, min(2._rkind * r, 1._rkind), min(r, 2._rkind))
end function superbee

function flux(Skpl, Skml, Skplp, Skmlp, Sklp, Skl, dx, dy, n)
  implicit none
  real(rkind), intent(in) :: Skpl(:,:), Skml(:,:), Skplp(:,:), Skmlp(:,:), Sklp(:,:), Skl(:,:), dx, dy
  integer(i4b), intent(in) :: n
  real(rkind), allocatable :: flux(:,:)

  allocate(flux(size(Skpl,1), size(Skpl,2)))
  flux = ( (Skpl - Skml + Skplp - Skmlp)**2_i4b / (4._rkind * dx)**2_i4b & 
                 + (Sklp - Skl)**2_i4b / dy**2_i4b )**((n - 1.0) / 2._rkind)
end function flux

function SIA(Dup, Sup, S, Ddn, Sdn, d)
  implicit none
  real(rkind), intent(in) :: Dup(:,:), Sup(:,:), S(:,:), Ddn(:,:), Sdn(:,:), d
  real(rkind), allocatable :: SIA(:,:)

  allocate(SIA(size(Dup,1), size(Dup,2)))
  SIA = (Dup * (Sup - S) / d - Ddn * (S - Sdn) / d) / d
end function SIA

function midpt(h1, h2)
  implicit none
  real(rkind), intent(in) :: h1(:,:), h2(:,:)
  real(rkind), allocatable :: midpt(:,:)

  allocate(midpt(size(h1,1), size(h1,2)))
  midpt = 0.5_rkind * (h1 + h2)
end function midpt

function pluss(Hm, H, Hp)
  implicit none
  real(rkind), intent(in) :: Hm(:,:), H(:,:), Hp(:,:)
  real(rkind), allocatable :: pluss(:,:)
  logical, allocatable :: mask(:,:)
  real(rkind), allocatable :: divisor(:,:), ones(:,:)

  allocate(pluss(size(Hm,1), size(Hm,2)))
  allocate(mask(size(Hm,1), size(Hm,2)),divisor(size(Hm,1), size(Hm,2)),ones(size(Hm,1), size(Hm,2)))
  ones = 1.0_rkind
  mask = (Hp /= H) .and. (Hp /= Hm) .and. (H /= Hm)
  divisor = merge(Hp - H, ones, mask)
  pluss = merge(H - 0.5_rkind * superbee(abs((H - Hm) / divisor)) * (Hp - H), H, mask)
  deallocate(mask,divisor,ones)
end function pluss

function minus(Hm, H, Hp)
  implicit none
  real(rkind), intent(in) :: Hm(:,:), H(:,:), Hp(:,:)
  real(rkind), allocatable :: minus(:,:)
  logical, allocatable :: mask(:,:)
  real(rkind), allocatable :: divisor(:,:), ones(:,:)

  allocate(minus(size(Hm,1), size(Hm,2)))
  allocate(mask(size(Hm,1), size(Hm,2)),divisor(size(Hm,1), size(Hm,2)),ones(size(Hm,1), size(Hm,2)))
  ones = 1.0_rkind
  mask = (Hp /= H) .and. (Hp /= Hm) .and. (H /= Hm)
  divisor = merge(H - Hm, ones, mask)
  minus = merge(H + 0.5_rkind * superbee(abs((Hp - H) / divisor)) * (H - Hm), H, mask)
  deallocate(mask,divisor,ones)
end function minus
end module sia_extract
