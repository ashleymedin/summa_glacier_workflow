f="glacAreaChange.f90"; s=open(f).read()
def rep(old,new):
    global s
    assert s.count(old)==1, old
    s=s.replace(old,new)
rep("        if(debris(k,j) > 0._rkind) dbr = 1\n","        if(debris(k,j) >= min_thickness) dbr = 1\n")
rep("        ind = validCount(dbr+1)+1 ! elevation above the valid elevation, extrapolate up\n","        ind = 1 ! segment 1 extrapolates above the highest point\n")
rep("          if(S(k,j) <= validElev(i,dbr+1)) ind = i\n","          if(S(k,j) <= validElev(i,dbr+1)) ind = i+1 ! segment i+1 joins points i and i+1\n")
rep("""  if(nPts == 1)then
    intercept(1) = massChange(1)""","""  if(nPts == 1)then
    intercept(1:2) = massChange(1)""")
rep("""    call static_emergElev_latRockfall(S, B, ELA, latMoraineWidth,""","""    call static_emergElev_latRockfall(S, B, debris, ELA, latMoraineWidth,""")
rep("""subroutine static_emergElev_latRockfall(S, B, ELA, latMoraineWidth,""","""subroutine static_emergElev_latRockfall(S, B, debris, ELA, latMoraineWidth,""")
rep("""  real(rkind), intent(in) :: S(nx,ny), B(nx,ny), ELA, latMoraineWidth""","""  real(rkind), intent(in) :: S(nx,ny), B(nx,ny), debris(nx,ny), ELA, latMoraineWidth""")
rep("""      emergenceMask = merge(1_i4b, 0_i4b, S<emergenceElev .and. S>B)\n""","""      emergenceMask = merge(1_i4b, 0_i4b, S<emergenceElev .and. S>B .and. debris>=min_thickness) ! debris septa crop out under existing debris\n""")
rep("""  englacial_emerg = -merge(m_dot, 0._rkind, emergenceMask==1_i4b) * debrisConc ! (kg m-2 s-1)""",
"""  englacial_emerg = merge(max(-m_dot, 0._rkind), 0._rkind, emergenceMask==1_i4b) * iden_water/iden_ice * debrisConc ! (kg m-2 s-1)""")
i0=s.index("      do j = 1, ny\n        do i = 1, nx\n          if(drivingStress(i,j) > debrisCritStress)then ! yield stress")
i1=s.index("    else\n      debris = 0._rkind\n    endif\n\n    ! add debris back to surface")
s=s[:i0]+"      where(drivingStress > debrisCritStress) debris = 0._rkind ! the debris layer that exceeds its yield stress slides off\n"+s[i1:]
open(f,"w").write(s)
