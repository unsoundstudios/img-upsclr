; NSIS installer script for IMG-UPSCLR

!ifndef APP_NAME
  !define APP_NAME "IMG-UPSCLR"
!endif

!ifndef APP_VERSION
  !define APP_VERSION "1.0.0"
!endif

!define APP_PUBLISHER "Unsound Studios"
!define APP_EXE "IMG-UPSCLR.exe"
!define APP_SOURCE_DIR "dist\IMG-UPSCLR"
!define APP_INSTALL_DIR "$PROGRAMFILES64\${APP_NAME}"
!define APP_OUTPUT_DIR "installers\windows\output"

Unicode True
SetCompressor /SOLID lzma
RequestExecutionLevel admin

Name "${APP_NAME}"
OutFile "${APP_OUTPUT_DIR}\${APP_NAME}-Setup-${APP_VERSION}.exe"
InstallDir "${APP_INSTALL_DIR}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "Install_Dir"

ShowInstDetails show
ShowUnInstDetails show

Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

Section "Install"
  SetShellVarContext all
  SetOutPath "$INSTDIR"

  File /r "${APP_SOURCE_DIR}\*"

  WriteRegStr HKLM "Software\${APP_NAME}" "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
SectionEnd

Section "Uninstall"
  SetShellVarContext all

  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"

  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey HKLM "Software\${APP_NAME}"
SectionEnd
