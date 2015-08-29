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

!define version "1.0.50" ; :bump
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

SetCompressor /SOLID lzma
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
    ;Store installation folder
    WriteRegStr HKCU "${regkey}" "" $INSTDIR
    ; Uninstall reg keys
    WriteRegStr HKLM "${uninstkey}" "DisplayName" "${prodname} ${version} (remove only)"
    WriteRegStr HKLM "${uninstkey}" "UninstallString" '"$INSTDIR\${uninstaller}"'
    ;Create uninstaller
    WriteUninstaller "$INSTDIR\${uninstaller}"

    ; package all files, recursively, preserving attributes
    ; assume files are in the correct places
    File /a /r "${src_dir}\*.*"

SectionEnd

; create shortcuts
Section
    SetOutPath $INSTDIR ; for working directory
    CreateDirectory "${startmenu}"
    CreateShortCut "${startmenu}\${prodname}.lnk" "$INSTDIR\${exec}"
    ; have to use COMSPEC because of the redirection
    #Exec "$INSTDIR\loadpixbufs.bat"
    ExpandEnvStrings $0 %COMSPEC%

    ; create a .bat file to run gdk-pixbuf-query-loaders.exe
    Var /GLOBAL QUERY_PIXBUF_CMD
    StrCpy $QUERY_PIXBUF_CMD '"$INSTDIR\gtk\bin\gdk-pixbuf-query-loaders.exe" > "$INSTDIR\gtk\etc\gtk-2.0\gdk-pixbuf.loaders"' 
    FileOpen $0 $INSTDIR\query_pixbufs.bat w
    IfErrors done
    FileWrite $0 $QUERY_PIXBUF_CMD
    FileClose $0
;    MessageBox MB_OK|MB_ICONSTOP $INSTDIR
;    MessageBox MB_OK|MB_ICONSTOP $QUERY_PIXBUF_CMD   
    nsExec::Exec '"$INSTDIR\query_pixbufs.bat"'
    done:
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

