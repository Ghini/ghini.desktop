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
Name "Ghini"

!define version "1.0.60" ; :bump
!define src_dir "../dist"
Outfile "ghini.desktop-${version}-setup.exe"

!define prodname "Ghini.desktop"
!define exec "ghini.exe"
!define license_file "LICENSE"
!define readme "README.rst"

; icons must be Microsoft .ICO files
; !define icon "${src_dir}/bauble/images/icon.ico"

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
InstallDirRegKey HKCU "${regkey}" ""

;--------------------------------
;Interface Settings
; MUI Settings

!define MUI_ABORTWARNING
!define MUI_UNABORTWARNING
!define MUI_ICON "${src_dir}/bauble/images/icon.ico"
!define MUI_UNICON "${src_dir}/bauble/images/icon.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "${src_dir}\bauble\images\ghini_logo.bmp"
!define MUI_HEADERIMAGE_UNBITMAP "${src_dir}\bauble\images\ghini_logo.bmp"
!define MUI_HEADERIMAGE_RIGHT
; allow users to check install log before continuing
!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_FINISHPAGE_NOREBOOTSUPPORT
!define MUI_FINISHPAGE_RUN_TEXT "Start Ghini"
!define MUI_FINISHPAGE_RUN $INSTDIR\${exec}
!define MUI_FINISHPAGE_LINK "Visit the Ghini home page"
!define MUI_FINISHPAGE_LINK_LOCATION http://ghini.github.io/

;--------------------------------
;Pages

!insertmacro MUI_PAGE_LICENSE "${src_dir}/${license_file}"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

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
    ; run gdk-pixbuf-query-loaders, gtk-query-immodules & pango-querymodules
    ReadEnvStr $0 COMSPEC
    nsExec::ExecToLog '$0 /C gtk\bin\pango-querymodules.exe > gtk\etc\pango\pango.modules'
    nsExec::ExecToLog '$0 /C gtk\bin\gtk-query-immodules-2.0.exe > gtk\etc\gtk-2.0\gtk.immodules'
    nsExec::ExecToLog '$0 /C gtk\bin\gdk-pixbuf-query-loaders.exe > gtk\etc\gtk-2.0\gdk-pixbuf.loaders'
    nsExec::ExecToLog '$0 /C gtk\bin\gdk-pixbuf-query-loaders.exe > gtk\lib\gdk-pixbuf-2.0\2.10.0\loaders.cache'
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

