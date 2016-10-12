;
; NSIS Install Script for Ghini
;

; Installer CLI options: /AllUsers or /CurrentUser
;                      : /S             #Silent install
;                      : /D=C:/...      #Set $INSTDIR
;                      : /C=gFC         #Install Components, where:
;                                               g = Unselect Ghini (normally always installed, used for component only installs)
;                                               F = select Apache FOP
;                                               C = select MS Visual C runtime
;
; A silent, system wide install, in the default location, with all components would look like this: 
; >ghini.desktop-1.0.60-setup.exe /S /AllUsers /C=FC




;---
; Plugins, required to compile:
; -
; nsExec (included in NSIS v3.0) for executing commands
; WordFunc.nsh (included in NSIS v3.0) for comparing versions
; FileFunc.nsh (included in NSIS v3.0) for command line options
; MUI2 (included in NSIS v3.0)
; UAC (included in NsisMultiUser)
; NsisMultiUser (https://github.com/Drizin/NsisMultiUser)
; nsisunz (http://nsis.sourceforge.net/Nsisunz_plug-in)
; Inetc (http://nsis.sourceforge.net/Inetc_plug-in)
; MD5 (http://nsis.sourceforge.net/MD5_plugin)
;---



;----------------------------------------------------------------
;  GENERAL
;----------------------------------------------------------------

;--------------------------------
; Global
Name "Ghini"

!define VERSION "1.0.60" ; :bump
!define src_dir "..\dist"
!define PRODUCT_NAME "ghini.desktop"
Outfile "${PRODUCT_NAME}-${VERSION}-setup.exe"
!define PROGEXE "ghini.exe"
!define COMPANY_NAME ""
!define license_file "LICENSE"
!define readme "README.rst"

!define startmenu "$SMPROGRAMS\${PRODUCT_NAME}"
!define UNINSTALL_FILENAME "uninstall.exe"

;--------------------------------
; FOP - full path http://www.apache.org/dyn/closer.cgi?filename=xmlgraphics/fop/binaries/fop-2.1-bin.zip&action=download
!define FOP_MIRROR "http://www.apache.org/dyn/closer.cgi?filename=xmlgraphics/fop/binaries"
!define FOP_VERSION "2.1"
!define FOP_BINZIP "fop-${FOP_VERSION}-bin.zip"
; http://www-eu.apache.org/dist/xmlgraphics/fop/binaries/fop-2.1-bin.zip.md5
!define FOP_MD5 "http://www-eu.apache.org/dist/xmlgraphics/fop/binaries/${FOP_BINZIP}.md5"
!define FOP_JRE "1.6"
!define JRE_WEB "https://java.com/download"
Var JREFwd

;--------------------------------
; Microsoft Visual C++ 2008 Redistributable - x86 9.0.21022(.8)
!define MSVC_GUID "{FF66E9F6-83E7-3A3E-AF14-8DE9A809A6A4}"
!define MSVC_DISP_NAME "Microsoft Visual C++ 2008 Redistributable - x86 9.0.21022"
!define MSVC_FILE "vcredist_x86.exe"
!define MSVC_URL "https://download.microsoft.com/download/1/1/1/1116b75a-9ec3-481a-a3c8-1777b5381140/"




;----------------------------------------------------------------
;  COMPRESSION SETTINGS
;----------------------------------------------------------------

;--------------------------------
; Compression
SetCompressor /FINAL /SOLID lzma
; default is 8mb, setting to 64mb reduced installer size by 1+mb
SetCompressorDictSize 64

;--------------------------------
; Other
SetDateSave on
SetDatablockOptimize on
CRCCheck on




;----------------------------------------------------------------
;  SETTINGS
;----------------------------------------------------------------

;--------------------------------
; Multi User Settings (must come before the NsisMultiUser script)
!define MULTIUSER_INSTALLMODE_INSTDIR "${PRODUCT_NAME}"
!define MULTIUSER_INSTALLMODE_INSTALL_REGISTRY_KEY "${PRODUCT_NAME}"
!define MULTIUSER_INSTALLMODE_UNINSTALL_REGISTRY_KEY "${PRODUCT_NAME}"
!define MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_VALUENAME "UninstallString"
!define MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_VALUENAME "InstallLocation"
!define MULTIUSER_INSTALLMODE_ALLOW_ELEVATION   ; allow requesting for elevation... 
!define MULTIUSER_INSTALLMODE_DEFAULT_ALLUSERS

;--------------------------------
; Modern User Interface v2 Settings
!define MUI_ABORTWARNING
!define MUI_UNABORTWARNING
!define MUI_ICON "${src_dir}\bauble\images\icon.ico"
!define MUI_UNICON "${src_dir}\bauble\images\icon.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "${src_dir}\bauble\images\ghini_logo.bmp"
!define MUI_HEADERIMAGE_UNBITMAP "${src_dir}\bauble\images\ghini_logo.bmp"
!define MUI_HEADERIMAGE_RIGHT
!define MUI_COMPONENTSPAGE_SMALLDESC
!define MUI_COMPONENTSPAGE_TEXT_COMPLIST "Or, select the optional components you wish to install: \
    $\r$\n$\r$\n* Extra Components marked (Download) will require an internet connection."
;!define MUI_FINISHPAGE_NOAUTOCLOSE  ;allows users to check install log before continuing
!define MUI_FINISHPAGE_TEXT_REBOOT "Rebooting is recommended but not required to start using ${PRODUCT_NAME} immediately"
!define MUI_FINISHPAGE_TEXT_REBOOTNOW "Reboot now (required before using Apache FOP option)"
!define MUI_FINISHPAGE_REBOOTLATER_DEFAULT
!define MUI_FINISHPAGE_RUN_TEXT "Start Ghini"
!define MUI_FINISHPAGE_RUN $INSTDIR\${PROGEXE}
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!define MUI_FINISHPAGE_LINK "Visit the Ghini home page"
!define MUI_FINISHPAGE_LINK_LOCATION http://ghini.github.io/




;----------------------------------------------------------------
;  SCRIPTS
;----------------------------------------------------------------

;--------------------------------
; include NsisMultiUser - all settings need to be set before including the NsisMultiUser.nsh header file.
; thanks to Richard Drizin for https://github.com/Drizin/NsisMultiUser
!include "NsisMultiUser.nsh" 
!include "MUI2.nsh"
!include "UAC.nsh"
!include "WordFunc.nsh"
!include "FileFunc.nsh"






;----------------------------------------------------------------
;  PAGES
;----------------------------------------------------------------

;--------------------------------
; Installer
!insertmacro MUI_PAGE_LICENSE "${src_dir}\${license_file}"
!insertmacro MULTIUSER_PAGE_INSTALLMODE
; this will show the 2 install options, unless it's an elevated inner process 
; (in that case we know we should install for all users)
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

;--------------------------------
; Uninstaller
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES




;----------------------------------------------------------------
;  LANGUAGES
;----------------------------------------------------------------

;--------------------------------
; MUIv2 macros (must be after scripts and pages)
; TODO add more languages?
!insertmacro MUI_LANGUAGE English




;----------------------------------------------------------------
;  INSTALLER SECTIONS
;----------------------------------------------------------------

;--------------------------------
; Install Types
InstType "Base"
InstType "Full"
InstType "Components Only"
; Custom is also be included by default

;--------------------------------
; Main Section
;--------------------------------

Section "!Ghini.desktop" SecMain

    SectionIN 1 2
    
    ; Install Files
    SetOutPath "$INSTDIR"
    SetOverwrite on
    ; package all files, recursively, preserving attributes
    ; assume files are in the correct places
    File /a /r "${src_dir}\*.*"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\${UNINSTALL_FILENAME}"

    ; add registry keys
	!insertmacro MULTIUSER_RegistryAddInstallInfo 
    ; create shortcuts 
    CreateDirectory "${startmenu}"
    CreateShortcut "${startmenu}\${PRODUCT_NAME}.lnk" "$INSTDIR\${PROGEXE}" \
        "" "$INSTDIR\${PROGEXE}" "" SW_SHOWNORMAL \
        "" "Ghini biodiversity collection manager"
    ; desktop shortcut
    CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\${PROGEXE}" \
        "" "$INSTDIR\${PROGEXE}" "" SW_SHOWNORMAL \
        "" "Ghini biodiversity collection manager"

    ; Register pixbufs, immodules, pango
    ReadEnvStr $0 COMSPEC
    nsExec::ExecToLog '$0 /C gtk\bin\pango-querymodules.exe > gtk\etc\pango\pango.modules'
    nsExec::ExecToLog '$0 /C gtk\bin\gtk-query-immodules-2.0.exe > gtk\etc\gtk-2.0\gtk.immodules'
    nsExec::ExecToLog '$0 /C gtk\bin\gdk-pixbuf-query-loaders.exe > gtk\etc\gtk-2.0\gdk-pixbuf.loaders'
    nsExec::ExecToLog '$0 /C gtk\bin\gdk-pixbuf-query-loaders.exe > gtk\lib\gdk-pixbuf-2.0\2.10.0\loaders.cache'

SectionEnd



;------------------------------------------------
; +Components Group
;------------------------------------------------

SectionGroup /e "Extra Components" SecOPs

;--------------------------------
; --Apache FOP
;--------------------------------

Section /o "Apache FOP v${FOP_VERSION} (24MB Download)" SecFOP

    SectionIN 2 3
    ClearErrors
    ; as its a download we need to inform of section size.
    AddSize 103424
    
    ; Check for FOP
    nsExec::ExecToStack /TIMEOUT=9000 '"where" fop.bat'
        Pop $0  ; error level
        Pop $1  ; output
        DetailPrint "FOP check - error level: $0"
        DetailPrint "FOP check - output: $1"
        StrCmp $0 0 0 DownloadFOP
    MessageBox MB_ICONINFORMATION "A working version of Apache FOP was found on your system.$\r$\n$\r$\nThere is  \
            no need to install it now and it could cause conflict to do so.$\r$\n$\r$\nShould you wish to upgrade to \
            version ${FOP_VERSION} or to install for all users (administrator only) you should remove your current \
            version (including the PATH entry) first, then re-run this installer.$\r$\n$\r$\nYour current version of \
            Apache FOP was found here:$\r$\n$1" /SD IDOK
        Goto DoneFOP
    
    ; Download FOP
    DownloadFOP:
        InitPluginsDir
        ClearErrors
        inetc::get /caption "Downloading Apache FOP version ${FOP_VERSION}" /canceltext "Cancel FOP Download" \
            "${FOP_MIRROR}/${FOP_BINZIP}&action=download" "$PLUGINSDIR\${FOP_BINZIP}" /END
            Pop $0
            DetailPrint "Apache FOP Download Status: $0"
            StrCmp $0 "OK" MD5checkFOP FOPFail

    
    ; MD5 hash check
    MD5checkFOP:
        ClearErrors
        inetc::get /silent "${FOP_MD5}" "$PLUGINSDIR\fop.md5" /END
            Pop $0
            DetailPrint "Apache FOP MD5 Download Status: $0"
            StrCmp $0 "OK" 0 FOPFail
        md5dll::GetMD5File "$PLUGINSDIR\${FOP_BINZIP}"
            Pop $1
            ClearErrors
            FileOpen $0 "$PLUGINSDIR\fop.md5" r
            IfErrors FOPFail
            FileRead $0 $2 32
            StrCmp $2 $1 InstalFOP 
            DetailPrint "Apache FOP MD5 check failed"
            Goto FOPFail


    ; Unpack and install FOP
    InstalFOP:
        DetailPrint "Please wait... prepairing to extract and install Apache FOP"
        ClearErrors
        ; determine SHELL_CONTEXT
        StrCmp "$MultiUser.InstallMode" "AllUsers" AdminFOP
        
            ; Current User install
            StrCpy $R0 "$LOCALAPPDATA"  ; Dont use $INSTDIR or FOP will install under Ghini.
            StrCpy $R1 "USER"
            Goto UnpackFOP
            
        AdminFOP:
            ; Local Machine install
            StrCpy $R0 "$PROGRAMFILES"  ; Dont use $INSTDIR or FOP will install under Ghini.
            StrCpy $R1 "SYSTEM"
            
    UnpackFOP:
    ; Unzip FOP
        nsisunz::UnzipToStack "$PLUGINSDIR\${FOP_BINZIP}" "$R0\"
            Pop $0
            StrCmp $0 "success" ZipFOP_OK
                DetailPrint "Unzip Error: $0"
                Goto FOPFail
            ZipFOP_OK:
            ; if no errors unzipping then print a list of the files to the log.
            ZipFOP_next:
                Pop $0
                DetailPrint "Extracting  $0"
            StrCmp $0 "" 0 ZipFOP_next
    
    Call AddFOPtoPATH
    
    Call CheckForJRE

    ; $R1 = 0 if java versions are equal, 1 if newer than required, 2 if older than required, 3 if none found
    IntCmp $R1 "2" +1 DoneFOP +3
    MessageBox MB_YESNO|MB_ICONQUESTION  "The version of Java Runtime Environment found on your system is an \
            earlier version than is required by Apache FOP.  To be able to use FOP you will need to upgrade \
            Java. $\r$\n$\r$\nJava Runtime Environment is only available directly from the Java web site. \ 
            $\r$\n$\r$\nClick YES to be directed to the Java web site after this installer is finished." \
                    /SD IDNO IDYES FWard2JRE
                    Goto DoneFOP 
    MessageBox MB_YESNO|MB_ICONQUESTION "No version of Java Runtime Environment, required by Apache FOP, was found \
            on your system.  To be able to use FOP you will need to install Java. $\r$\n$\r$\nJava Runtime \
            Environment is only available directly from the Java web site. $\r$\n$\r$\n$\r$\nClick YES to be \
            directed to the Java web site after this installer is finished." \
                    /SD IDNO IDYES FWard2JRE
                    Goto DoneFOP 
    
    FWard2JRE:
        DetailPrint "forward to Java download site = true"
        StrCpy $JREFwd "true"
        SetRebootFlag False
        DetailPrint "Reboot flag = False"
        Goto DoneFOP

    ; Error with FOP install
    FOPFail:
        MessageBox MB_OK|MB_ICONEXCLAMATION "An ERROR occured while installing Apache FOP, installation aborted \
                $\r$\n$\r$\n to try again re-run this installer at a later date" /SD IDOK

    DoneFOP:

SectionEnd

;--------------------------------
; --MS Visual C runtime Section
;--------------------------------

Section /o "MS Visual C runtime DLL (1.73MB Download)" SecMSC

    SectionIN 2 3
    ClearErrors
    ; as its a download we need to inform of section size (Approximate only).
    AddSize 12186
    
    ; Check if the correct version of the MS Visual C runtime, needed by Python programs, is already installed
    Call CheckForMSVC
        StrCmp $R1 "Success" GotMSVC

    ; Download MS Visual C runtime
    InitPluginsDir
    ClearErrors
    inetc::get /caption "Downloading ${MSVC_DISP_NAME}" /canceltext "Cancel runtime Download" \
        "${MSVC_URL}${MSVC_FILE}" "$PLUGINSDIR\${MSVC_FILE}" /END
        Pop $0
        DetailPrint "${MSVC_FILE} Download Status: $0"
        StrCmp $0 "OK" InstalMSVC
        MessageBox MB_OK|MB_ICONEXCLAMATION "Download Error, $0 aborting MS Visual C runtime installation.$\r$\n to \
            try again re-run this installer at a later date" /SD IDOK 
    Goto DoneMSVC

    ; Install MS Visual C Runtime
    ; TODO there seems to be a bug in the installer that leaves junk files in the root directory of the largest drive
    InstalMSVC:
        ; run installer silently (no user input, no cancel button)
        ExecWait '"$PLUGINSDIR\${MSVC_FILE}" /qb!'
        ; Check for successful install 
        Call CheckForMSVC
            StrCmp $R1 "Success" DoneMSVC
        DetailPrint "error installing ${MSVC_DISP_NAME}"
        MessageBox MB_OK|MB_ICONEXCLAMATION "Installer Error, aborting MS Visual C runtime installation.$\r$\n to try \
            again re-run this installer at a later date" /SD IDOK 
        Goto DoneMSVC
    
    GotMSVC:
        DetailPrint "${MSVC_DISP_NAME} found, install cancelled"
        MessageBox MB_ICONINFORMATION "It appears you already have ${MSVC_DISP_NAME} on your system and \
                    there is no need to install it" /SD IDOK

    DoneMSVC:

SectionEnd

SectionGroupEnd




;----------------------------------------------------------------
;  UNINSTALLER SECTIONS
;----------------------------------------------------------------
; All section names prefixed by "Un" will be in the uninstaller
; TODO include a FOP uninstaller

;--------------------------------
; Settings
UninstallText "This will uninstall ${PRODUCT_NAME}."

;--------------------------------
; Main Uninstall Section
;--------------------------------

Section "Uninstall" SecUnMain
    ; Remove registry keys
    !insertmacro MULTIUSER_RegistryRemoveInstallInfo
    Delete "${startmenu}\*.*"
    Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
    SetOutPath $TEMP
    RMDir /r "$INSTDIR"
    RMDir /r "${startmenu}"
SectionEnd
    



;----------------------------------------------------------------
;  SECTION DESCRIPTIONS
;----------------------------------------------------------------

;--------------------------------
; Language Strings
LangString DESC_SecMain ${LANG_ENGLISH} "Ghini.desktop - biodiversity collection manager - this is the main component \
                                        (required)"
LangString DESC_SecOPs ${LANG_ENGLISH} "Optional extras that you may be needed to either run Ghini.desktop or to get \
                                        the most from it."
LangString DESC_SecFOP ${LANG_ENGLISH} "Apache FOP is required for XSL report templates. No uninstaller provided. \
                                        (Java RE required)"
LangString DESC_SecMSC ${LANG_ENGLISH} "Microsoft Visual C++ 2008 Redistributable Package is required by Ghini.desktop."

; uninstaller
LangString DESC_SecUnMain ${LANG_ENGLISH} "Removes the main component - Ghini.desktop."

;--------------------------------
; Initialise Language Strings (must come after the sections)
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_SecMain)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecOPs} $(DESC_SecOPs)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecFOP} $(DESC_SecFOP)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMSC} $(DESC_SecMSC)
  
  ; uninstaller
  !insertmacro MUI_DESCRIPTION_TEXT ${SecUnMain} $(DESC_SecUnMain)
!insertmacro MUI_FUNCTION_DESCRIPTION_END





;----------------------------------------------------------------
;  USER FUNCTIONS
;----------------------------------------------------------------

;--------------------------------
; Add FOP to PATH
;--------------------------------
Function AddFOPtoPATH
    
    ; Checking before adding FOP to PATH, this may be a reinstall?
    StrCpy $0 "$R0\fop-${FOP_VERSION}"
    StrLen $1 $0
    ReadEnvStr $2 PATH
    DetailPrint "Checking it FOP is already in the PATH"
    StrLen $3 $2
    StrCpy $4 "0"
    PathFOP_Loop:
        StrCpy $5 $2 $1 $4
        StrCmp $5 $0 PathFOP_Same
        IntOp $4 $4 + 1
        IntCmp $4 $3 PathFOP_Not PathFOP_Loop PathFOP_Not
    
    ; Dont add FOP to PATH
    PathFOP_Same:
        DetailPrint "fop is already in the path, not adding it again"
        Return

    ; Adding FOP to PATH
    PathFOP_Not:
        ; copy the script to a temp dir
        SetOutPath "$PLUGINSDIR\"
        SetOverwrite on
        File /a "Add_to_PATH.vbs"
        ExecWait '"$SYSDIR\wscript.exe" //E:vbscript "$PLUGINSDIR\Add_to_PATH.vbs" /path:"$R0\fop-${FOP_VERSION}\" /env:"$R1"'
        DetailPrint "Apache FOP added to $R1 PATH as: $R0\fop-${FOP_VERSION}\"
        SetRebootFlag True
        DetailPrint "Reboot flag = True"
        Return

FunctionEnd




;--------------------------------
; Check for MS Visual C Runtime
;--------------------------------

Function CheckForMSVC  
    
    ClearErrors
    StrCpy $2 "0"
    SetRegView 32
    Goto MSVCMainCheck

    MSVC64Check:
        SetRegView 64

    MSVCMainCheck:
        Push "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${MSVC_GUID}"
        Push "SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\${MSVC_GUID}"
        
    MSVCCheckNext:
        IntOp $2 $2 + 1
        IntCmp $2 "3" MSVC64Check 0 0
        IntCmp $2 "6" NoMSVC 0 NoMSVC
        Pop $0
        ReadRegStr $1 HKLM $0 "DisplayName"
        IfErrors MSVCCheckNext
        DetailPrint "MSVC RegStr: $1"
        StrCmp $1 "${MSVC_DISP_NAME}" FoundMSVC MSVCCheckNext
        
    NoMSVC:
        StrCpy $R1 "Fail"
        return
    
    FoundMSVC:
        StrCpy $R1 "Success"
        
FunctionEnd




;--------------------------------
; Check for Java RE
;--------------------------------

Function CheckForJRE    
    
    ClearErrors
    StrCpy $2 "0"
    SetRegView 32
    Goto JREMainCheck

    JRE64Check:
        SetRegView 64

    JREMainCheck:
        Push "SOFTWARE\Wow6432Node\JavaSoft\Java Runtime Environment"
        Push "SOFTWARE\JavaSoft\Java Runtime Environment"
        
    JRECheckNext:
        IntOp $2 $2 + 1
        IntCmp $2 "3" JRE64Check 0 0
        IntCmp $2 "6" NoJRE 0 NoJRE
        Pop $0
        ReadRegStr $1 HKLM $0 "CurrentVersion"
        IfErrors JRECheckNext
        ${VersionCompare} $1 ${FOP_JRE} $R1
        DetailPrint "Java RE version $1 found"
        return
        
    NoJRE:
        DetailPrint "No Java RE found"
        StrCpy $R1 "3"
    ; $R1 = 0 if java versions are equal, 1 if newer than required, 2 if older than required, 3 if none found
FunctionEnd




;----------------------------------------------------------------
;  CALLBACK FUNCTIONS
;----------------------------------------------------------------

;-----------------------------------------
; On Initializing
Function .onInit
	; Initialize the NsisMultiUser plugin
	!insertmacro MULTIUSER_INIT
	; Check the command line option for components
	${GetOptions} $CMDLINE "/C=" $2
    CLLoop:
        StrCpy $1 $2 1 -1
        StrCpy $2 $2 -1
        StrCmp $1 "" CLDone
            StrCmp $1 "g" 0 +2
                SectionSetFlags ${SecMain} 16
            StrCmp $1 "F" 0 +2
                SectionSetFlags ${SecFOP} 1
            StrCmp $1 "C" 0 +2
                SectionSetFlags ${SecMSC} 1
        Goto CLLoop
    CLDone:
FunctionEnd

Function un.onInit
	; Initialize the NsisMultiUser plugin
	!insertmacro MULTIUSER_UNINIT
FunctionEnd

Function .onGUIEnd
    ; Open the Java download page on exit if user selected to do so.
    StrCmp $JREFwd "true" 0 +2
    ExecShell "open" "${JRE_WEB}"
FunctionEnd

;-----------------------------------------
; On verifying install dir
Function .onVerifyInstDir
        ; MS Visual C runtime Section is only avaiable if administrator
    	StrCmp "$MultiUser.InstallMode" "AllUsers" AllUser
	    SectionSetFlags ${SecMSC} 16
	Alluser:
FunctionEnd

;-----------------------------------------
; On selection change
Function .onSelChange
        ; prevent unavailable section selection due via instType change
    	StrCmp "$MultiUser.InstallMode" "AllUsers" AllUser
	    SectionSetFlags ${SecMSC} 16
	Alluser:
FunctionEnd

