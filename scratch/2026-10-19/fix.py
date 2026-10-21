f="glacAreaChange.f90"; s=open(f).read()
def rep(old,new):
    global s
    assert s.count(old)==1, old
    s=s.replace(old,new)
# 1 debris mass-balance curve only for cells that are debris domains
rep("        if(debris(k,j) > 0._rkind) dbr = 1\n","        if(debris(k,j) >= min_thickness) dbr = 1\n")
# 2 emergence only within the existing debris footprint
rep("""    call static_emergElev_latRockfall(S, B, ELA, latMoraineWidth, debrisConc, wallErosionRate, nx, ny, dx, dy, &""",
"""    call static_emergElev_latRockfall(S, B, debris, ELA, latMoraineWidth, debrisConc, wallErosionRate, nx, ny, dx, dy, &""")
rep("""subroutine static_emergElev_latRockfall(S, B, ELA, latMoraineWidth,""","""subroutine static_emergElev_latRockfall(S, B, debris, ELA, latMoraineWidth,""")
rep("""  real(rkind), intent(in) :: S(nx,ny), B(nx,ny), ELA, latMoraineWidth""","""  real(rkind), intent(in) :: S(nx,ny), B(nx,ny), debris(nx,ny), ELA, latMoraineWidth""")
rep("""      emergenceMask = merge(1_i4b, 0_i4b, S<emergenceElev .and. S>B)\n""","""      emergenceMask = merge(1_i4b, 0_i4b, S<emergenceElev .and. S>B .and. debris>=min_thickness) ! debris septa crop out under existing debris\n""")
# 3 emergence from ice melt only, in m ice
rep("""  englacial_emerg = -merge(m_dot, 0._rkind, emergenceMask==1_i4b) * debrisConc ! (kg m-2 s-1)""",
"""  englacial_emerg = merge(max(-m_dot, 0._rkind), 0._rkind, emergenceMask==1_i4b) * iden_water/iden_ice * debrisConc ! (kg m-2 s-1)""")
# 4 yield: remove only the failing cells
i0=s.index("      dg_tmp = sum(debris)\n")
i1=s.index("      if(sum(debris)<dg_tmp)then")
s=s[:i0]+"""      dg_tmp = sum(debris)
      where(drivingStress > debrisCritStress) debris = 0._rkind ! the debris layer that exceeds its yield stress slides off
"""+s[i1:]
open(f,"w").write(s)
