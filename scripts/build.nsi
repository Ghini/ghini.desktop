;
; NSIS Install Script for Bauble
;
; TODO: should create two version of this installer, one that bundles GTK and
; one that doesn't
; could also create one that asks the use if they would like to download and
; install the GTK libs if they aren't available, ala slickrun

; include Modern UI
!include "MUI.nsh"

; general
Name "Bauble"
!define version "0.4.5"
!define src_dir "../dist"
Outfile "bauble-${version}-setup.exe"
 
!define prodname "Bauble"
!define exec "bauble.exe"
!define license_file "LICENSE"
!define readme "README"
 
; icons must be Microsoft .ICO files
; !define icon "icon.ico"
 
; file containing list of file-installation commands
; !define files "files.nsi"
 
; file containing list of file-uninstall commands
; !define unfiles "unfiles.nsi"
 
; registry stuff
!define regkey "Software\${prodname}"
!define uninstkey "Software\Microsoft\Windows\CurrentVersion\Uninstall\${prodname}"

!define startmenu "$SMPROGRAMS\${prodname}"
!define uninstaller "uninstall.exe"
  
SetDateSave on
SetDatablockOptimize on
CRCCheck on
SilentInstall normal
 
InstallDir "$PROGRAMFILES\${prodname}"
InstallDirRegKey HKLM "${regkey}" ""
  
;--------------------------------
;Interface Settings

!define MUI_ABORTWARNING

;--------------------------------
;Pages

!insertmacro MUI_PAGE_LICENSE "${src_dir}/${license_file}"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
;--------------------------------
;Languages
 
!insertmacro MUI_LANGUAGE "English"
;--------------------------------
;Installer Sections

Section "Dummy Section" SecDummy
    SetOutPath "$INSTDIR"
    ;ADD YOUR OWN FILES HERE...
    
    ;Store installation folder
    WriteRegStr HKCU "${regkey}" "" $INSTDIR
    ; Uninstall reg keys
    WriteRegStr HKLM "${uninstkey}" "DisplayName" "${prodname} (remove only)"
    WriteRegStr HKLM "${uninstkey}" "UninstallString" '"$INSTDIR\${uninstaller}"'
    ;Create uninstaller
    WriteUninstaller "$INSTDIR\${uninstaller}"

    ; package all files, recursively, preserving attributes
    ; assume files are in the correct places
    File /a /r "${src_dir}\*.*" 
  
SectionEnd
 
; create shortcuts
Section
    CreateDirectory "${startmenu}"
    SetOutPath $INSTDIR ; for working directory
    CreateShortCut "${startmenu}\${prodname}.lnk" "$INSTDIR\${exec}" 
SectionEnd
 
; Uninstaller
; All section names prefixed by "Un" will be in the uninstaller
 
UninstallText "This will uninstall ${prodname}."
  
Section "Uninstall"
    DeleteRegKey HKLM "${uninstkey}"
    DeleteRegKey HKLM "${regkey}"  
    Delete "${startmenu}\*.*"
    Delete "${startmenu}"
    SetOutPath $TEMP
    RMDir /r "$INSTDIR"
    RMDir /r ${startmenu}
SectionEnd

