import re
f="glacAreaChange.f90"; s=open(f).read()
def rep(old,new,count=1):
    global s
    assert s.count(old)>=1, old
    s=s.replace(old,new,count)
rep("real(rkind),parameter :: maxDebrisTop=0.05_rkind     ! maximum thickness of the top debris layer (m)\n",
"real(rkind),parameter :: maxDebrisTop=0.05_rkind     ! maximum thickness of the top debris layer (m)\n"
"real(rkind),save :: dg_vEmerg=0._rkind, dg_vRock=0._rkind, dg_vClear=0._rkind ! DIAG debris budget (m3)\n"
"integer(i4b),save :: dg_nClear=0, dg_call=0 ! DIAG\n"
"character(len=512),save :: dg_dir='' ! DIAG\n")
# before run_flowModel call
rep("    ! run the flow model, which updates surface and debris\n",
"""    call get_environment_variable('SUMMA_DEBRIS_DIAG', dg_dir)
    dg_vEmerg=0._rkind; dg_vRock=0._rkind; dg_vClear=0._rkind; dg_nClear=0; dg_call=dg_call+1
    write(*,'(a,i0,1x,i0,3(1x,f12.1),2(1x,i0),3(1x,f9.1))') 'DBRDIAG pre glac,call,ELAcl,ELAdb,ELAuse,validCount,smin,smax= ', &
      glacInfo(iGlac)%glac_id, dg_call, ELA_elev(1), ELA_elev(2), ELA_use_glac, validCount, &
      minval(surface, mask=surface-bed>thick4area), maxval(surface, mask=surface-bed>thick4area)
    write(*,'(a,i0,1x,i0,1x,i0,1x,f12.1)') 'DBRDIAG preDebris glac,nGlacCells,nDebris>=2cm,vol(m3)= ', glacInfo(iGlac)%glac_id, &
      count(surface-bed>thick4area), count(surface-bed>thick4area .and. debris>=min_thickness), sum(debris)*dx*dy
    if(iGlac==1)then
      do dbr=1,2
        write(*,'(a,i1,50(1x,f9.1))') 'DBRDIAG mbpts dbr',dbr-1, (validElev(i,dbr),validMassChange(i,dbr), i=1,validCount(dbr))
      enddo
    endif
    ! run the flow model, which updates surface and debris
""")
rep("    totVolume = totVolume + volume ! includes debris, not currently used\n",
"""    totVolume = totVolume + volume ! includes debris, not currently used
    write(*,'(a,i0,1x,i0,1x,i0,4(1x,f12.1),1x,i0)') 'DBRDIAG post glac,nGlacCells,nDebris>=2cm,vol,vEmerg,vRock,vClear,nClear= ', &
      glacInfo(iGlac)%glac_id, count(surface-bed>thick4area), count(surface-bed>thick4area .and. debris>=min_thickness), &
      sum(debris)*dx*dy, dg_vEmerg, dg_vRock, dg_vClear, dg_nClear
    if(len_trim(dg_dir)>0 .and. nx*ny>1000)then
      block
        integer(i4b) :: u
        character(len=600) :: fn
        write(fn,'(a,"/grid_",i0,"_",i3.3,".txt")') trim(dg_dir), glacInfo(iGlac)%glac_id, dg_call
        open(newunit=u, file=trim(fn), status='replace')
        write(u,'(2i6,1x,f12.3)') nx, ny, ELA_use_glac
        do j=1,ny; do i=1,nx
          write(u,'(2f10.2,f10.4,i3)') surface(i,j), bed(i,j), debris(i,j), cell2hru(i,j)
        enddo; enddo
        close(u)
      end block
    endif
""")
# static: after emergence mask
rep("      emergenceMask = merge(1_i4b, 0_i4b, S<emergenceElev .and. S>B)\n",
"""      emergenceMask = merge(1_i4b, 0_i4b, S<emergenceElev .and. S>B)
      write(*,'(a,4(1x,f9.2),2(1x,i0))') 'DBRDIAG emerg ELA,top,meanSlope,emergElev,nEmerg,nGlac= ', ELA, topElev, mean_slope, &
        emergenceElev, count(emergenceMask==1_i4b), countGlac
""")
rep("""  else
    lat_rockfall = 0._rkind
  endif

end subroutine static_emergElev_latRockfall""",
"""    if(count(lat_rockfall>0._rkind)>0) write(*,'(a,i0,1x,f9.4,1x,f9.1)') 'DBRDIAG rock nCells,mean(m/yr),meanRockLen= ', count(lat_rockfall>0._rkind), &
      sum(lat_rockfall)/count(lat_rockfall>0._rkind)*secprday*365.25_rkind, sum(rockface_len_local,mask=lat_rockfall>0._rkind)/count(lat_rockfall>0._rkind)
  else
    lat_rockfall = 0._rkind
  endif

end subroutine static_emergElev_latRockfall""")
rep("""    debris = debris + (div_uD + influx)* deltat
""","""    debris = debris + (div_uD + influx)* deltat
    dg_vEmerg = dg_vEmerg + sum(englacial_emerg)/(iden_soil*(1._rkind - theta_sat))*dx*dy*deltat
    dg_vRock  = dg_vRock  + sum(lat_rockfall)*dx*dy*deltat
""")
rep("""      do j = 1, ny
        do i = 1, nx
          if(drivingStress(i,j) > debrisCritStress)then ! yield stress
""","""      dg_tmp = sum(debris)
      do j = 1, ny
        do i = 1, nx
          if(drivingStress(i,j) > debrisCritStress)then ! yield stress
            write(*,'(a,2(1x,i0),5(1x,es10.3),1x,i0)') 'DBRDIAG yield i,j,stress,debris,slope_k,slope_l,S,nDbr= ', i, j, drivingStress(i,j), &
              debris(i,j), slope_k(i,j), slope_l(i,j), S(i,j), count(debris>=min_thickness)
""")
rep("""            endif
          endif
        enddo
      enddo
    else
      debris = 0._rkind
    endif

    ! add debris back to surface""","""            endif
          endif
        enddo
      enddo
      if(sum(debris)<dg_tmp)then; dg_vClear = dg_vClear + (dg_tmp-sum(debris))*dx*dy; dg_nClear = dg_nClear + 1; endif
    else
      debris = 0._rkind
    endif

    ! add debris back to surface""")
rep("  real(rkind) :: drivingStress(nx,ny)\n","  real(rkind) :: drivingStress(nx,ny)\n  real(rkind) :: dg_tmp\n")
open(f,"w").write(s)
