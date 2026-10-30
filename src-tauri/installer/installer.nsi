; Medicsoft installer artwork, consistent DPI layout and Windows app-theme support.
; Based on the official Tauri CLI v2.12.0 NSIS template.
; Upstream: https://github.com/tauri-apps/tauri/tree/tauri-cli-v2.12.0
Unicode true
ManifestDPIAware true
; Add in `dpiAwareness` `PerMonitorV2` to manifest for Windows 10 1607+ (note this should not affect lower versions since they should be able to ignore this and pick up `dpiAware` `true` set by `ManifestDPIAware true`)
; Currently undocumented on NSIS's website but is in the Docs folder of source tree, see
; https://github.com/kichik/nsis/blob/5fc0b87b819a9eec006df4967d08e522ddd651c9/Docs/src/attributes.but#L286-L300
; https://github.com/tauri-apps/tauri/pull/10106
ManifestDPIAwareness PerMonitorV2

!if "{{compression}}" == "none"
  SetCompress off
!else
  ; Compress files independently so the first dialog does not seek/decompress
  ; through the bundled application and offline WebView2 runtime.
  SetCompressor "{{compression}}"
!endif

; Keep above !include to stay ahead of any plugin command
; see https://github.com/tauri-apps/tauri/pull/15422#discussion_r3289239624
{{#if signed_plugins_path}}
!addplugindir "{{signed_plugins_path}}"
{{/if}}

!include MUI2.nsh
!include FileFunc.nsh
!include x64.nsh
!include WordFunc.nsh
!include "utils.nsh"
!include "FileAssociation.nsh"
!include "Win\COM.nsh"
!include "Win\Propkey.nsh"
!include "Win\RestartManager.nsh"
!include "StrFunc.nsh"
${StrCase}
${StrLoc}

{{#if installer_hooks}}
!include "{{installer_hooks}}"
{{/if}}

!define WEBVIEW2APPGUID "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"

!define MANUFACTURER "{{manufacturer}}"
!define PRODUCTNAME "{{product_name}}"
!define VERSION "{{version}}"
!define VERSIONWITHBUILD "{{version_with_build}}"
!define HOMEPAGE "{{homepage}}"
!define INSTALLMODE "{{install_mode}}"
!define LICENSE "{{license}}"
!define INSTALLERICON "{{installer_icon}}"
!define SIDEBARIMAGE "{{sidebar_image}}"
!define HEADERIMAGE "{{header_image}}"
!define UNINSTALLERICON "{{uninstaller_icon}}"
!define UNINSTALLERHEADERIMAGE "{{uninstaller_header_image}}"
!define MAINBINARYNAME "{{main_binary_name}}"
!define MAINBINARYSRCPATH "{{main_binary_path}}"
!define BUNDLEID "{{bundle_id}}"
!define COPYRIGHT "{{copyright}}"
!define OUTFILE "{{out_file}}"
!define ARCH "{{arch}}"
!define ADDITIONALPLUGINSPATH "{{additional_plugins_path}}"
!define ALLOWDOWNGRADES "{{allow_downgrades}}"
!define DISPLAYLANGUAGESELECTOR "{{display_language_selector}}"
!define INSTALLWEBVIEW2MODE "{{install_webview2_mode}}"
!define WEBVIEW2INSTALLERARGS "{{webview2_installer_args}}"
!define WEBVIEW2BOOTSTRAPPERPATH "{{webview2_bootstrapper_path}}"
!define WEBVIEW2INSTALLERPATH "{{webview2_installer_path}}"
!define MINIMUMWEBVIEW2VERSION "{{minimum_webview2_version}}"
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCTNAME}"
!define MANUKEY "Software\${MANUFACTURER}"
!define MANUPRODUCTKEY "${MANUKEY}\${PRODUCTNAME}"
!define UNINSTALLERSIGNCOMMAND "{{uninstaller_sign_cmd}}"
!define ESTIMATEDSIZE "{{estimated_size}}"
!define STARTMENUFOLDER "{{start_menu_folder}}"
!define PLMS_SHORTCUT_ICON "$INSTDIR\Resources\Branding\medicsoft-plms-184a3b174087.ico"

Var PassiveMode
Var UpdateMode
Var NoShortcutMode
Var WixMode
Var PLMSDesignState
Var PLMSThemeModule
Var DeleteAppDataCheckbox
Var DeleteAppDataCheckboxState
Var PLMSRepairMode
Var PLMSRefreshOnly
Var OldMainBinaryName

Name "${PRODUCTNAME}"
SetFont "Segoe UI" 9
BrandingText "Medicsoft Corporation"
OutFile "${OUTFILE}"

; We don't actually use this value as default install path,
; it's just for nsis to append the product name folder in the directory selector
; https://nsis.sourceforge.io/Reference/InstallDir
!define PLACEHOLDER_INSTALL_DIR "placeholder\${PRODUCTNAME}"
InstallDir "${PLACEHOLDER_INSTALL_DIR}"

VIProductVersion "${VERSIONWITHBUILD}"
VIAddVersionKey "CompanyName" "${MANUFACTURER}"
VIAddVersionKey "ProductName" "${PRODUCTNAME}"
VIAddVersionKey "FileDescription" "${PRODUCTNAME}"
VIAddVersionKey "LegalCopyright" "${COPYRIGHT}"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"

# additional plugins
!addplugindir "${ADDITIONALPLUGINSPATH}"

; Uninstaller signing command
!if "${UNINSTALLERSIGNCOMMAND}" != ""
  !uninstfinalize '${UNINSTALLERSIGNCOMMAND}'
!endif

; Handle install mode, `perUser`, `perMachine` or `both`
!if "${INSTALLMODE}" == "perMachine"
  RequestExecutionLevel admin
!endif

!if "${INSTALLMODE}" == "currentUser"
  RequestExecutionLevel user
!endif

!if "${INSTALLMODE}" == "both"
  !define MULTIUSER_MUI
  !define MULTIUSER_INSTALLMODE_INSTDIR "${PRODUCTNAME}"
  !define MULTIUSER_INSTALLMODE_COMMANDLINE
  !if "${ARCH}" == "x64"
    !define MULTIUSER_USE_PROGRAMFILES64
  !else if "${ARCH}" == "arm64"
    !define MULTIUSER_USE_PROGRAMFILES64
  !endif
  !define MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_KEY "${UNINSTKEY}"
  !define MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_VALUENAME "CurrentUser"
  !define MULTIUSER_INSTALLMODEPAGE_SHOWUSERNAME
  !define MULTIUSER_INSTALLMODE_FUNCTION RestorePreviousInstallLocation
  !define MULTIUSER_EXECUTIONLEVEL Highest
  !include MultiUser.nsh
!endif

; Medicsoft visual theme. Keep the native wizard, upgrade and data handling intact.
!define MUI_FONT "Segoe UI"
!define MUI_CUSTOMFUNCTION_GUIINIT PLMSGuiInit
!define MUI_CUSTOMFUNCTION_UNGUIINIT un.PLMSGuiInit
!define MUI_TEXTCOLOR "234534"
!define MUI_BGCOLOR "FFFFFF"
!define MUI_HEADERIMAGE_RIGHT
!define MUI_WELCOMEFINISHPAGE_BITMAP_STRETCH "FitControl"
!define MUI_WELCOMEPAGE_TITLE "Welcome to Medicsoft PLMS"
!define MUI_WELCOMEPAGE_TEXT "Pathology Lab Management System$\r$\n$\r$\nInstall PLMS for local database storage and laboratory workflows.$\r$\n$\r$\nWork online or offline after installation.$\r$\n$\r$\nSelect Next to continue."
!define MUI_FINISHPAGE_TITLE "Medicsoft PLMS is ready"
!define MUI_FINISHPAGE_TEXT "PLMS has been installed on this computer.$\r$\n$\r$\nDefault sign-in: U001 / 123.$\r$\nYour records are kept when upgrading.$\r$\n$\r$\nSelect Finish to close Setup."
!define MUI_FINISHPAGE_RUN_TEXT "Open PLMS"

; Installer icon
!if "${INSTALLERICON}" != ""
  !define MUI_ICON "${INSTALLERICON}"
!endif

; Installer sidebar image
!if "${SIDEBARIMAGE}" != ""
  !define MUI_WELCOMEFINISHPAGE_BITMAP "${SIDEBARIMAGE}"
!endif

; Enable header images for installer and uninstaller pages when either image is configured.
!if "${HEADERIMAGE}" != ""
  !define MUI_HEADERIMAGE
!else if "${UNINSTALLERHEADERIMAGE}" != ""
  !define MUI_HEADERIMAGE
!endif

; Installer header image
!if "${HEADERIMAGE}" != ""
  !define MUI_HEADERIMAGE_BITMAP "${HEADERIMAGE}"
!endif

; Uninstaller header image
!if "${UNINSTALLERHEADERIMAGE}" != ""
  !define MUI_HEADERIMAGE_UNBITMAP "${UNINSTALLERHEADERIMAGE}"
!endif

; Uninstaller icon
!if "${UNINSTALLERICON}" != ""
  !define MUI_UNICON "${UNINSTALLERICON}"
!endif

; Define registry key to store installer language
!define MUI_LANGDLL_REGISTRY_ROOT "HKCU"
!define MUI_LANGDLL_REGISTRY_KEY "${MANUPRODUCTKEY}"
!define MUI_LANGDLL_REGISTRY_VALUENAME "Installer Language"

!searchreplace PLMS_PAGES_PATH "${SIDEBARIMAGE}" "sidebar.bmp" "PLMSPages.nsh"
!include "${PLMS_PAGES_PATH}"

; Installer pages, must be ordered as they appear
; 2. License Page (if defined)
!if "${LICENSE}" != ""
  !define MUI_PAGE_CUSTOMFUNCTION_PRE SkipIfPassive
  !define MUI_PAGE_CUSTOMFUNCTION_SHOW PLMSPageShow
!insertmacro MUI_PAGE_LICENSE "${LICENSE}"
!endif

; 3. Install mode (if it is set to `both`)
!if "${INSTALLMODE}" == "both"
  !define MUI_PAGE_CUSTOMFUNCTION_PRE SkipIfPassive
  !define MUI_PAGE_CUSTOMFUNCTION_SHOW PLMSPageShow
!insertmacro MULTIUSER_PAGE_INSTALLMODE
!endif

; 4. Custom page to ask user if he wants to reinstall/uninstall
;    only if a previous installation was detected
Var ReinstallPageCheck
Page custom PageReinstall PageLeaveReinstall
Function PageReinstall
  ; Uninstall previous WiX installation if exists.
  ;
  ; A WiX installer stores the installation info in registry
  ; using a UUID and so we have to loop through all keys under
  ; `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`
  ; and check if `DisplayName` and `Publisher` keys match ${PRODUCTNAME} and ${MANUFACTURER}
  ;
  ; This has a potential issue that there maybe another installation that matches
  ; our ${PRODUCTNAME} and ${MANUFACTURER} but wasn't installed by our WiX installer,
  ; however, this should be fine since the user will have to confirm the uninstallation
  ; and they can chose to abort it if doesn't make sense.
  StrCpy $0 0
  wix_loop:
    EnumRegKey $1 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" $0
    StrCmp $1 "" wix_loop_done ; Exit loop if there is no more keys to loop on
    IntOp $0 $0 + 1
    ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$1" "DisplayName"
    ReadRegStr $R1 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$1" "Publisher"
    StrCmp "$R0$R1" "${PRODUCTNAME}${MANUFACTURER}" 0 wix_loop
    ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$1" "UninstallString"
    ${StrCase} $R1 $R0 "L"
    ${StrLoc} $R0 $R1 "msiexec" ">"
    StrCmp $R0 0 0 wix_loop_done
    StrCpy $WixMode 1
    StrCpy $R6 "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$1"
    Goto compare_version
  wix_loop_done:

  ; Check if there is an existing installation, if not, abort the reinstall page
  ReadRegStr $R0 SHCTX "${UNINSTKEY}" ""
  ReadRegStr $R1 SHCTX "${UNINSTKEY}" "UninstallString"
  ${IfThen} "$R0$R1" == "" ${|} Abort ${|}

  ; Compare this installar version with the existing installation
  ; and modify the messages presented to the user accordingly
  compare_version:
  StrCpy $R4 "$(older)"
  ${If} $WixMode = 1
    ReadRegStr $R0 HKLM "$R6" "DisplayVersion"
  ${Else}
    ReadRegStr $R0 SHCTX "${UNINSTKEY}" "DisplayVersion"
  ${EndIf}
  ${IfThen} $R0 == "" ${|} StrCpy $R4 "$(unknown)" ${|}

  nsis_tauri_utils::SemverCompare "${VERSION}" $R0
  Pop $R0
  ; Reinstalling the same version
  ${If} $R0 = 0
    StrCpy $R1 "$(alreadyInstalledLong)"
    StrCpy $R2 "$(addOrReinstall)"
    StrCpy $R3 "$(uninstallApp)"
    !insertmacro MUI_HEADER_TEXT "$(alreadyInstalled)" "$(chooseMaintenanceOption)"
  ; Upgrading
  ${ElseIf} $R0 = 1
    StrCpy $R1 "$(olderOrUnknownVersionInstalled)"
    StrCpy $R2 "$(uninstallBeforeInstalling)"
    StrCpy $R3 "$(dontUninstall)"
    !insertmacro MUI_HEADER_TEXT "$(alreadyInstalled)" "$(choowHowToInstall)"
  ; Downgrading
  ${ElseIf} $R0 = -1
    StrCpy $R1 "$(newerVersionInstalled)"
    StrCpy $R2 "$(uninstallBeforeInstalling)"
    !if "${ALLOWDOWNGRADES}" == "true"
      StrCpy $R3 "$(dontUninstall)"
    !else
      StrCpy $R3 "$(dontUninstallDowngrade)"
    !endif
    !insertmacro MUI_HEADER_TEXT "$(alreadyInstalled)" "$(choowHowToInstall)"
  ${Else}
    Abort
  ${EndIf}

  ; Skip showing the page if passive
  ;
  ; Note that we don't call this earlier at the beginning
  ; of this function because we need to populate some variables
  ; related to current installed version if detected and whether
  ; we are downgrading or not.
  ${If} $PassiveMode = 1
    Call PageLeaveReinstall
  ${Else}
    nsDialogs::Create 1018
    Pop $R4
    System::Call '"$PLUGINSDIR\plms-theme.dll"::BindPage(p $HWNDPARENT,p $R4)'
    ${IfThen} $(^RTL) = 1 ${|} nsDialogs::SetRTL $(^RTL) ${|}

    ${NSD_CreateRadioButton} 0 0 870 42 "Repair Installation"
    Pop $R2
    System::Call '"$PLUGINSDIR\plms-theme.dll"::BindOption(p $HWNDPARENT,i 4,p $R2)'
    ${NSD_OnClick} $R2 PageReinstallUpdateSelection
    ${NSD_CreateLabel} 40 42 825 34 "Reinstall application files and keep existing data."
    Pop $0
    ${NSD_CreateRadioButton} 0 92 870 42 "Uninstall PLMS"
    Pop $R3
    System::Call '"$PLUGINSDIR\plms-theme.dll"::BindOption(p $HWNDPARENT,i 5,p $R3)'
    ${NSD_OnClick} $R3 PageReinstallUpdateSelection
    ${NSD_CreateLabel} 40 134 825 34 "Remove the application from this computer."
    Pop $0
    ${NSD_CreateRadioButton} 0 184 870 42 "Exit Setup"
    Pop $PLMSExitChoice
    System::Call '"$PLUGINSDIR\plms-theme.dll"::BindOption(p $HWNDPARENT,i 6,p $PLMSExitChoice)'
    ${NSD_CreateLabel} 40 226 825 34 "Keep the current installation."
    Pop $0
    ${NSD_CreateLabel} 0 290 870 56 "Your patient records and settings are retained by default."
    Pop $0
    ${NSD_Check} $R2
    ; Do not allow a lower version to overwrite a newer installation.
    !if "${ALLOWDOWNGRADES}" == "false"
      ${If} $R0 = -1
        EnableWindow $R2 0
        ${NSD_Check} $R3
      ${EndIf}
    !endif
    ${NSD_SetFocus} $R2
    Push 3
    Call PLMSDesign
    nsDialogs::Show
  ${EndIf}
FunctionEnd
Function PageReinstallUpdateSelection
  ${NSD_GetState} $R2 $R1
  ${If} $R1 == ${BST_CHECKED}
    StrCpy $ReinstallPageCheck 1
  ${Else}
    StrCpy $ReinstallPageCheck 2
  ${EndIf}
FunctionEnd
Function PageLeaveReinstall
  ${If} $PassiveMode <> 1
    ${NSD_GetState} $PLMSExitChoice $0
    ${If} $0 = ${BST_CHECKED}
      Quit
    ${EndIf}
    ${NSD_GetState} $R3 $0
    ${If} $0 = ${BST_CHECKED}
      ReadRegStr $1 SHCTX "${UNINSTKEY}" "UninstallString"
      HideWindow
      ExecWait '$1' $0
      ${If} $0 = 0
        Quit
      ${EndIf}
      BringToFront
      System::Call '"$PLUGINSDIR\plms-theme.dll"::Unlock(p $HWNDPARENT)'
      Abort
    ${EndIf}
  ${EndIf}
  ; Repair follows the approved direct-to-install flow using the stored folder.
  StrCpy $PLMSRepairMode 1
  ; Repair/upgrade retains the existing database and replaces program files.
  ${If} $WixMode <> 1
    ${If} $PassiveMode <> 1
      Return
    ${EndIf}
  ${EndIf}
  ${NSD_GetState} $R2 $R1

  ; If migrating from Wix, always uninstall
  ${If} $WixMode = 1
    Goto reinst_uninstall
  ${EndIf}

  ; In update mode, always proceeds without uninstalling
  ${If} $UpdateMode = 1
    Goto reinst_done
  ${EndIf}

  ; $R0 holds whether same(0)/upgrading(1)/downgrading(-1) version
  ; $R1 holds the radio buttons state:
  ;   1 => first choice was selected
  ;   0 => second choice was selected
  ${If} $R0 = 0 ; Same version, proceed
    ${If} $R1 = 1              ; User chose to add/reinstall
      Goto reinst_done
    ${Else}                    ; User chose to uninstall
      Goto reinst_uninstall
    ${EndIf}
  ${ElseIf} $R0 = 1 ; Upgrading
    ${If} $R1 = 1              ; User chose to uninstall
      Goto reinst_uninstall
    ${Else}
      Goto reinst_done         ; User chose NOT to uninstall
    ${EndIf}
  ${ElseIf} $R0 = -1 ; Downgrading
    ${If} $R1 = 1              ; User chose to uninstall
      Goto reinst_uninstall
    ${Else}
      Goto reinst_done         ; User chose NOT to uninstall
    ${EndIf}
  ${EndIf}

  reinst_uninstall:
    HideWindow
    ClearErrors

    ${If} $WixMode = 1
      ReadRegStr $R1 HKLM "$R6" "UninstallString"
      ExecWait '$R1' $0
    ${Else}
      ReadRegStr $4 SHCTX "${MANUPRODUCTKEY}" ""
      ReadRegStr $R1 SHCTX "${UNINSTKEY}" "UninstallString"
      ${IfThen} $UpdateMode = 1 ${|} StrCpy $R1 "$R1 /UPDATE" ${|} ; append /UPDATE
      ${IfThen} $PassiveMode = 1 ${|} StrCpy $R1 "$R1 /P" ${|} ; append /P
      StrCpy $R1 "$R1 _?=$4" ; append uninstall directory
      ExecWait '$R1' $0
    ${EndIf}

    BringToFront

    ${IfThen} ${Errors} ${|} StrCpy $0 2 ${|} ; ExecWait failed, set fake exit code

    ${If} $0 <> 0
    ${OrIf} ${FileExists} "$INSTDIR\${MAINBINARYNAME}.exe"
      ; User cancelled wix uninstaller? return to select un/reinstall page
      ${If} $WixMode = 1
      ${AndIf} $0 = 1602
        Abort
      ${EndIf}

      ; User cancelled NSIS uninstaller? return to select un/reinstall page
      ${If} $0 = 1
        Abort
      ${EndIf}

      ; Other errors? show generic error message and return to select un/reinstall page
      MessageBox MB_ICONEXCLAMATION "$(unableToUninstall)"
      Abort
    ${EndIf}
  reinst_done:
FunctionEnd

Page custom PLMSOptions PLMSOptionsLeave
Var AppStartMenuFolder
; Keep Tauri's start-menu bookkeeping without an extra visible wizard page.
!define MUI_PAGE_CUSTOMFUNCTION_PRE Skip
!define MUI_STARTMENUPAGE_DEFAULTFOLDER "${STARTMENUFOLDER}"
!insertmacro MUI_PAGE_STARTMENU Application $AppStartMenuFolder
!define MUI_PAGE_CUSTOMFUNCTION_SHOW PLMSInstalling
!insertmacro MUI_PAGE_INSTFILES
Page custom PLMSComplete PLMSCompleteLeave

; Shared installer / uninstaller HTML host. Native NSIS content stays hidden.

!searchreplace PLMS_UI_PATH "${SIDEBARIMAGE}" "sidebar.bmp" "ui\dialog.html"
!searchreplace PLMS_LOADER_PATH "${SIDEBARIMAGE}" "sidebar.bmp" "theme\build\WebView2Loader.dll"
!searchreplace PLMS_THEME_DLL "${SIDEBARIMAGE}" "sidebar.bmp" "theme\build\plms-theme.dll"

!macro PLMS_WIZARD_FUNCTIONS PREFIX
Function ${PREFIX}PLMSGuiInit
  Push $0
  StrCpy $0 $OUTDIR
  InitPluginsDir
  !if "${PREFIX}" == ""
    StrCpy $PLMSDesktopState 1
    StrCpy $PLMSLaunchState 1
  !endif
  SetOutPath $PLUGINSDIR
  File /oname=plms-theme.dll "${PLMS_THEME_DLL}"
  File /oname=WebView2Loader.dll "${PLMS_LOADER_PATH}"
  File /oname=plms-dialog.html "${PLMS_UI_PATH}"
  System::Call 'kernel32::LoadLibraryW(w "$PLUGINSDIR\plms-theme.dll")p.s'
  Pop $PLMSThemeModule
  ; The approved HTML UI needs the same WebView2 Runtime as PLMS itself.
  System::Call '"$PLUGINSDIR\plms-theme.dll"::RuntimeAvailable(w "$PLUGINSDIR")i.r1'
  ${If} $1 = 0
    !if "${PREFIX}" == ""
      !if "${INSTALLWEBVIEW2MODE}" == "offlineInstaller"
        File /oname=plms-WebView2Runtime.exe "${WEBVIEW2INSTALLERPATH}"
        ExecWait '$\"$PLUGINSDIR\plms-WebView2Runtime.exe$\" ${WEBVIEW2INSTALLERARGS} /install' $1
        System::Call '"$PLUGINSDIR\plms-theme.dll"::RuntimeAvailable(w "$PLUGINSDIR")i.r1'
      !endif
      ${If} $1 = 0
        MessageBox MB_ICONSTOP "The Microsoft WebView2 Runtime could not be prepared. Setup cannot display its interface."
        SetErrorLevel 1
        Quit
      ${EndIf}
    !else
      MessageBox MB_ICONSTOP "The Microsoft WebView2 Runtime is missing. Restore it to use this interface, or run uninstall.exe /S for unattended removal."
      SetErrorLevel 1
      Quit
    !endif
  ${EndIf}
  SetOutPath $0
  System::Call '"$PLUGINSDIR\plms-theme.dll"::Configure(p $HWNDPARENT,w "$PLUGINSDIR\plms-dialog.html")'
  Pop $0
FunctionEnd

Function ${PREFIX}PLMSPageShow
  ; HTML owns all visible controls, fonts, artwork and window chrome.
FunctionEnd

Function ${PREFIX}PLMSFreeArtwork
  System::Call '"$PLUGINSDIR\plms-theme.dll"::Detach(p $HWNDPARENT)'
  ${If} $PLMSThemeModule != 0
    System::Call 'kernel32::FreeLibrary(p $PLMSThemeModule)'
    StrCpy $PLMSThemeModule 0
  ${EndIf}
FunctionEnd
!macroend

!insertmacro PLMS_WIZARD_FUNCTIONS ""
!insertmacro PLMS_WIZARD_FUNCTIONS "un."

Function .onGUIEnd
  Call PLMSFreeArtwork
FunctionEnd
Function un.onGUIEnd
  Call un.PLMSFreeArtwork
FunctionEnd


Function RunMainBinary
  nsis_tauri_utils::RunAsUser "$INSTDIR\${MAINBINARYNAME}.exe" ""
FunctionEnd

; Uninstaller Pages
; 1. Confirm uninstall page
UninstPage custom un.PLMSOptions un.PLMSOptionsLeave
!define MUI_PAGE_CUSTOMFUNCTION_SHOW un.PLMSInstalling
!insertmacro MUI_UNPAGE_INSTFILES
UninstPage custom un.PLMSComplete

;Languages
{{#each languages}}
!insertmacro MUI_LANGUAGE "{{this}}"
{{/each}}
!insertmacro MUI_RESERVEFILE_LANGDLL
{{#each language_files}}
  !include "{{this}}"
{{/each}}

Function .onInit
  ${GetOptions} $CMDLINE "/P" $PassiveMode
  ${IfNot} ${Errors}
    StrCpy $PassiveMode 1
  ${EndIf}

  ${GetOptions} $CMDLINE "/NS" $NoShortcutMode
  ${IfNot} ${Errors}
    StrCpy $NoShortcutMode 1
  ${EndIf}

  ${GetOptions} $CMDLINE "/UPDATE" $UpdateMode
  ${IfNot} ${Errors}
    StrCpy $UpdateMode 1
  ${EndIf}

  !if "${DISPLAYLANGUAGESELECTOR}" == "true"
    !insertmacro MUI_LANGDLL_DISPLAY
  !endif

  !insertmacro SetContext

  ${If} $INSTDIR == "${PLACEHOLDER_INSTALL_DIR}"
    ; Set default install location
    !if "${INSTALLMODE}" == "perMachine"
      ${If} ${RunningX64}
        !if "${ARCH}" == "x64"
          StrCpy $INSTDIR "$PROGRAMFILES64\Medicsoft\PLMS"
        !else if "${ARCH}" == "arm64"
          StrCpy $INSTDIR "$PROGRAMFILES64\Medicsoft\PLMS"
        !else
          StrCpy $INSTDIR "$PROGRAMFILES\Medicsoft\PLMS"
        !endif
      ${Else}
        StrCpy $INSTDIR "$PROGRAMFILES\Medicsoft\PLMS"
      ${EndIf}
    !else if "${INSTALLMODE}" == "currentUser"
      StrCpy $INSTDIR "$LOCALAPPDATA\Medicsoft\PLMS"
    !endif

    Call RestorePreviousInstallLocation
    ; Upgrade the old default into the shared parent; retain custom choices.
    ${If} $INSTDIR == "$PROGRAMFILES64\${PRODUCTNAME}"
    ${OrIf} $INSTDIR == "$PROGRAMFILES\${PRODUCTNAME}"
      ${If} ${RunningX64}
        StrCpy $INSTDIR "$PROGRAMFILES64\Medicsoft\PLMS"
      ${Else}
        StrCpy $INSTDIR "$PROGRAMFILES\Medicsoft\PLMS"
      ${EndIf}
    ${EndIf}
  ${EndIf}


  !if "${INSTALLMODE}" == "both"
    !insertmacro MULTIUSER_INIT
  !endif
FunctionEnd


Section EarlyChecks
  ; Abort silent installer if downgrades is disabled
  !if "${ALLOWDOWNGRADES}" == "false"
  ${If} ${Silent}
    ; If downgrading
    ${If} $R0 = -1
      System::Call 'kernel32::AttachConsole(i -1)i.r0'
      ${If} $0 <> 0
        System::Call 'kernel32::GetStdHandle(i -11)i.r0'
        System::call 'kernel32::SetConsoleTextAttribute(i r0, i 0x0004)' ; set red color
        FileWrite $0 "$(silentDowngrades)"
      ${EndIf}
      Abort
    ${EndIf}
  ${EndIf}
  !endif

SectionEnd

Section WebView2
  ; Check if Webview2 is already installed and skip this section
  ${If} ${RunningX64}
    ReadRegStr $4 HKLM "SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\${WEBVIEW2APPGUID}" "pv"
  ${Else}
    ReadRegStr $4 HKLM "SOFTWARE\Microsoft\EdgeUpdate\Clients\${WEBVIEW2APPGUID}" "pv"
  ${EndIf}
  ${If} $4 == ""
    ReadRegStr $4 HKCU "SOFTWARE\Microsoft\EdgeUpdate\Clients\${WEBVIEW2APPGUID}" "pv"
  ${EndIf}

  ${If} $4 == ""
    ; Webview2 installation
    ;
    ; Skip if updating
    ${If} $UpdateMode <> 1
      !if "${INSTALLWEBVIEW2MODE}" == "downloadBootstrapper"
        Delete "$TEMP\MicrosoftEdgeWebview2Setup.exe"
        DetailPrint "$(webview2Downloading)"
        NSISdl::download "https://go.microsoft.com/fwlink/p/?LinkId=2124703" "$TEMP\MicrosoftEdgeWebview2Setup.exe"
        Pop $0
        ${If} $0 == "success"
          DetailPrint "$(webview2DownloadSuccess)"
        ${Else}
          DetailPrint "$(webview2DownloadError)"
          Abort "$(webview2AbortError)"
        ${EndIf}
        StrCpy $6 "$TEMP\MicrosoftEdgeWebview2Setup.exe"
        Goto install_webview2
      !endif

      !if "${INSTALLWEBVIEW2MODE}" == "embedBootstrapper"
        Delete "$TEMP\MicrosoftEdgeWebview2Setup.exe"
        File "/oname=$TEMP\MicrosoftEdgeWebview2Setup.exe" "${WEBVIEW2BOOTSTRAPPERPATH}"
        DetailPrint "$(installingWebview2)"
        StrCpy $6 "$TEMP\MicrosoftEdgeWebview2Setup.exe"
        Goto install_webview2
      !endif

      !if "${INSTALLWEBVIEW2MODE}" == "offlineInstaller"
        Delete "$TEMP\MicrosoftEdgeWebView2RuntimeInstaller.exe"
        File "/oname=$TEMP\MicrosoftEdgeWebView2RuntimeInstaller.exe" "${WEBVIEW2INSTALLERPATH}"
        DetailPrint "$(installingWebview2)"
        StrCpy $6 "$TEMP\MicrosoftEdgeWebView2RuntimeInstaller.exe"
        Goto install_webview2
      !endif

      Goto webview2_done

      install_webview2:
        DetailPrint "$(installingWebview2)"
        ; $6 holds the path to the webview2 installer
        ExecWait "$6 ${WEBVIEW2INSTALLERARGS} /install" $1
        ${If} $1 = 0
          DetailPrint "$(webview2InstallSuccess)"
        ${Else}
          DetailPrint "$(webview2InstallError)"
          Abort "$(webview2AbortError)"
        ${EndIf}
      webview2_done:
    ${EndIf}
  ${Else}
    !if "${MINIMUMWEBVIEW2VERSION}" != ""
      ${VersionCompare} "${MINIMUMWEBVIEW2VERSION}" "$4" $R0
      ${If} $R0 = 1
        update_webview:
          DetailPrint "$(installingWebview2)"
          ${If} ${RunningX64}
            ReadRegStr $R1 HKLM "SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate" "path"
          ${Else}
            ReadRegStr $R1 HKLM "SOFTWARE\Microsoft\EdgeUpdate" "path"
          ${EndIf}
          ${If} $R1 == ""
            ReadRegStr $R1 HKCU "SOFTWARE\Microsoft\EdgeUpdate" "path"
          ${EndIf}
          ${If} $R1 != ""
            ; Chromium updater docs: https://source.chromium.org/chromium/chromium/src/+/main:docs/updater/user_manual.md
            ; Modified from "HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Microsoft EdgeWebView\ModifyPath"
            ExecWait `"$R1" /install appguid=${WEBVIEW2APPGUID}&needsadmin=true` $1
            ${If} $1 = 0
              DetailPrint "$(webview2InstallSuccess)"
            ${Else}
              MessageBox MB_ICONEXCLAMATION|MB_ABORTRETRYIGNORE "$(webview2InstallError)" IDIGNORE ignore IDRETRY update_webview
              Quit
              ignore:
            ${EndIf}
          ${EndIf}
      ${EndIf}
    !endif
  ${EndIf}
SectionEnd

Section Install
  ; Keep writable data outside Program Files and retain it during upgrades.
  SetShellVarContext all
  CreateDirectory "$APPDATA\Medicsoft\PLMS"
  nsExec::ExecToStack '"$SYSDIR\icacls.exe" "$APPDATA\Medicsoft\PLMS" /grant *S-1-5-32-545:(OI)(CI)M /T /C'
  Pop $0
  Pop $1
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Could not prepare the Medicsoft PLMS data folder. Setup cannot continue."
    Abort
  ${EndIf}
  SetOutPath $INSTDIR

  !ifmacrodef NSIS_HOOK_PREINSTALL
    !insertmacro NSIS_HOOK_PREINSTALL
  !endif

  ; A renamed executable may still be running during an in-place repair.
  ReadRegStr $OldMainBinaryName SHCTX "${UNINSTKEY}" "MainBinaryName"
  ${If} $OldMainBinaryName != ""
  ${AndIf} $OldMainBinaryName != "${MAINBINARYNAME}.exe"
    !insertmacro CheckIfAppIsRunning "$INSTDIR\$OldMainBinaryName" "${PRODUCTNAME}"
  ${EndIf}
  !insertmacro CheckIfAppIsRunning "$INSTDIR\${MAINBINARYNAME}.exe" "${PRODUCTNAME}"

  ; Copy main executable
  File "${MAINBINARYSRCPATH}"

  ; Remove the retired adapter when upgrading an existing installation.
  Delete "$INSTDIR\System\native-office.js"

  ; Copy resources
  {{#each resources_dirs}}
    CreateDirectory "$INSTDIR\\{{this}}"
  {{/each}}
  {{#each resources}}
    File /a "/oname={{this.[1]}}" "{{no-escape @key}}"
  {{/each}}

  ; Copy external binaries
  {{#each binaries}}
    File /a "/oname={{this}}" "{{no-escape @key}}"
  {{/each}}

  ; Create file associations
  {{#each file_associations as |association| ~}}
    {{#each association.ext as |ext| ~}}
       !insertmacro APP_ASSOCIATE "{{ext}}" "{{or association.name ext}}" "{{association-description association.description ext}}" "$INSTDIR\${MAINBINARYNAME}.exe,0" "Open with ${PRODUCTNAME}" "$INSTDIR\${MAINBINARYNAME}.exe $\"%1$\""
    {{/each}}
  {{/each}}

  ; Register deep links
  {{#each deep_link_protocols as |protocol| ~}}
    WriteRegStr SHCTX "Software\Classes\\{{protocol}}" "URL Protocol" ""
    WriteRegStr SHCTX "Software\Classes\\{{protocol}}" "" "URL:${BUNDLEID} protocol"
    WriteRegStr SHCTX "Software\Classes\\{{protocol}}\DefaultIcon" "" "$\"$INSTDIR\${MAINBINARYNAME}.exe$\",0"
    WriteRegStr SHCTX "Software\Classes\\{{protocol}}\shell\open\command" "" "$\"$INSTDIR\${MAINBINARYNAME}.exe$\" $\"%1$\""
  {{/each}}

  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"

  ; Save $INSTDIR in registry for future installations
  WriteRegStr SHCTX "${MANUPRODUCTKEY}" "" $INSTDIR

  !if "${INSTALLMODE}" == "both"
    ; Save install mode to be selected by default for the next installation such as updating
    ; or when uninstalling
    WriteRegStr SHCTX "${UNINSTKEY}" $MultiUser.InstallMode 1
  !endif

  ; Remove old main binary if it doesn't match new main binary name
  ReadRegStr $OldMainBinaryName SHCTX "${UNINSTKEY}" "MainBinaryName"
  ${If} $OldMainBinaryName != ""
  ${AndIf} $OldMainBinaryName != "${MAINBINARYNAME}.exe"
    Delete "$INSTDIR\$OldMainBinaryName"
  ${EndIf}

  ; Save current MAINBINARYNAME for future updates
  WriteRegStr SHCTX "${UNINSTKEY}" "MainBinaryName" "${MAINBINARYNAME}.exe"

  ; Registry information for add/remove programs
  WriteRegStr SHCTX "${UNINSTKEY}" "DisplayName" "${PRODUCTNAME}"
  WriteRegStr SHCTX "${UNINSTKEY}" "DisplayIcon" "$\"${PLMS_SHORTCUT_ICON}$\",0"
  WriteRegStr SHCTX "${UNINSTKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr SHCTX "${UNINSTKEY}" "Publisher" "${MANUFACTURER}"
  WriteRegStr SHCTX "${UNINSTKEY}" "InstallLocation" "$\"$INSTDIR$\""
  WriteRegStr SHCTX "${UNINSTKEY}" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
  WriteRegDWORD SHCTX "${UNINSTKEY}" "NoModify" "1"
  WriteRegDWORD SHCTX "${UNINSTKEY}" "NoRepair" "1"

  ${GetSize} "$INSTDIR" "/M=uninstall.exe /S=0K /G=0" $0 $1 $2
  IntOp $0 $0 + ${ESTIMATEDSIZE}
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD SHCTX "${UNINSTKEY}" "EstimatedSize" "$0"

  !if "${HOMEPAGE}" != ""
    WriteRegStr SHCTX "${UNINSTKEY}" "URLInfoAbout" "${HOMEPAGE}"
    WriteRegStr SHCTX "${UNINSTKEY}" "URLUpdateInfo" "${HOMEPAGE}"
    WriteRegStr SHCTX "${UNINSTKEY}" "HelpLink" "${HOMEPAGE}"
  !endif

  ; Repair existing shortcuts on every install/update, even when creation is off.
  SetOutPath "$INSTDIR"
  StrCpy $PLMSRefreshOnly 0
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    Call CreateOrUpdateStartMenuShortcut
  !insertmacro MUI_STARTMENU_WRITE_END
  Call CreateOrUpdateDesktopShortcut
  !if "${INSTALLMODE}" == "perMachine"
    ; Older per-user shortcuts may coexist with the new all-users installation.
    SetShellVarContext current
    StrCpy $PLMSRefreshOnly 1
    Call CreateOrUpdateStartMenuShortcut
    Call CreateOrUpdateDesktopShortcut
    StrCpy $PLMSRefreshOnly 0
    SetShellVarContext all
  !endif

  ; Retire the removed account setup helper when upgrading older packages.
  Delete /REBOOTOK "$INSTDIR\backend\plms-account-setup.exe"
  ClearErrors

  !ifmacrodef NSIS_HOOK_POSTINSTALL
    !insertmacro NSIS_HOOK_POSTINSTALL
  !endif

  ; Auto-advance successful GUI installs to the approved completion page.
  SetAutoClose true
  ${If} $PassiveMode = 1
    SetAutoClose true
  ${EndIf}
SectionEnd

Function .onInstSuccess
  ; Check for `/R` flag only in silent and passive installers because
  ; GUI installer has a toggle for the user to (re)start the app
  ${If} $PassiveMode = 1
  ${OrIf} ${Silent}
    ${GetOptions} $CMDLINE "/R" $R0
    ${IfNot} ${Errors}
      ${GetOptions} $CMDLINE "/ARGS" $R0
      nsis_tauri_utils::RunAsUser "$INSTDIR\${MAINBINARYNAME}.exe" "$R0"
    ${EndIf}
  ${EndIf}
FunctionEnd

Function un.onInit
  !insertmacro SetContext

  !if "${INSTALLMODE}" == "both"
    !insertmacro MULTIUSER_UNINIT
  !endif

  !insertmacro MUI_UNGETLANGUAGE

  ${GetOptions} $CMDLINE "/P" $PassiveMode
  ${IfNot} ${Errors}
    StrCpy $PassiveMode 1
  ${EndIf}

  ${GetOptions} $CMDLINE "/UPDATE" $UpdateMode
  ${IfNot} ${Errors}
    StrCpy $UpdateMode 1
  ${EndIf}
FunctionEnd

Section Uninstall

  !ifmacrodef NSIS_HOOK_PREUNINSTALL
    !insertmacro NSIS_HOOK_PREUNINSTALL
  !endif

  !insertmacro CheckIfAppIsRunning "$INSTDIR\${MAINBINARYNAME}.exe" "${PRODUCTNAME}"

  ; Explicit data deletion runs before removing the worker. It accepts no path.
  ; Upgrades and normal uninstall retain both current and legacy PLMS data.
  ${If} $DeleteAppDataCheckboxState = 1
  ${AndIf} $UpdateMode <> 1
    InitPluginsDir
    ClearErrors
    CopyFiles /SILENT "$INSTDIR\Root\plms-backend.exe" "$PLUGINSDIR\plms-data-cleanup.exe"
    IfErrors plms_data_cleanup_failed
    ; The backend is a console executable for its stdin/stdout API. nsExec
    ; runs cleanup without allocating a visible console and preserves its exit code.
    nsExec::ExecToStack '"$PLUGINSDIR\plms-data-cleanup.exe" --delete-app-data'
    Pop $0
    Pop $1
    ${If} $0 == "error"
      Goto plms_data_cleanup_failed
    ${EndIf}
    ${If} $0 == "timeout"
      Goto plms_data_cleanup_failed
    ${EndIf}
    ${If} $0 != 0
      Goto plms_data_cleanup_failed
    ${EndIf}
    Goto plms_data_cleanup_done
    plms_data_cleanup_failed:
      StrCpy $DeleteAppDataCheckboxState 0
      MessageBox MB_ICONEXCLAMATION "PLMS app data could not be fully deleted. Retained data remains available for recovery. LIS and the shared Medicsoft folder are not deletion targets."
    plms_data_cleanup_done:
  ${EndIf}

  ; Delete the app directory and its content from disk
  ; Copy main executable
  Delete "$INSTDIR\${MAINBINARYNAME}.exe"

  ; Delete resources
  {{#each resources}}
    Delete "$INSTDIR\\{{this.[1]}}"
  {{/each}}

  ; Delete external binaries
  {{#each binaries}}
    Delete "$INSTDIR\\{{this}}"
  {{/each}}

  ; Delete app associations
  {{#each file_associations as |association| ~}}
    {{#each association.ext as |ext| ~}}
      !insertmacro APP_UNASSOCIATE "{{ext}}" "{{or association.name ext}}"
    {{/each}}
  {{/each}}

  ; Delete deep links
  {{#each deep_link_protocols as |protocol| ~}}
    ReadRegStr $R7 SHCTX "Software\Classes\\{{protocol}}\shell\open\command" ""
    ${If} $R7 == "$\"$INSTDIR\${MAINBINARYNAME}.exe$\" $\"%1$\""
      DeleteRegKey SHCTX "Software\Classes\\{{protocol}}"
    ${EndIf}
  {{/each}}


  ; Delete uninstaller
  Delete "$INSTDIR\uninstall.exe"

  {{#each resources_ancestors}}
  RMDir /REBOOTOK "$INSTDIR\\{{this}}"
  {{/each}}
  RMDir "$INSTDIR"

  ; Remove shortcuts if not updating
  ${If} $UpdateMode <> 1
    !insertmacro DeleteAppUserModelId

    ; Remove start menu shortcut
    !insertmacro MUI_STARTMENU_GETFOLDER Application $AppStartMenuFolder
    !insertmacro IsShortcutTarget "$SMPROGRAMS\$AppStartMenuFolder\${PRODUCTNAME}.lnk" "$INSTDIR\${MAINBINARYNAME}.exe"
    Pop $0
    ${If} $0 = 1
      !insertmacro UnpinShortcut "$SMPROGRAMS\$AppStartMenuFolder\${PRODUCTNAME}.lnk"
      Delete "$SMPROGRAMS\$AppStartMenuFolder\${PRODUCTNAME}.lnk"
      RMDir "$SMPROGRAMS\$AppStartMenuFolder"
    ${EndIf}
    !insertmacro IsShortcutTarget "$SMPROGRAMS\${PRODUCTNAME}.lnk" "$INSTDIR\${MAINBINARYNAME}.exe"
    Pop $0
    ${If} $0 = 1
      !insertmacro UnpinShortcut "$SMPROGRAMS\${PRODUCTNAME}.lnk"
      Delete "$SMPROGRAMS\${PRODUCTNAME}.lnk"
    ${EndIf}

    ; Remove desktop shortcuts
    !insertmacro IsShortcutTarget "$DESKTOP\${PRODUCTNAME}.lnk" "$INSTDIR\${MAINBINARYNAME}.exe"
    Pop $0
    ${If} $0 = 1
      !insertmacro UnpinShortcut "$DESKTOP\${PRODUCTNAME}.lnk"
      Delete "$DESKTOP\${PRODUCTNAME}.lnk"
    ${EndIf}
  ${EndIf}

  ${If} $UpdateMode <> 1
    !insertmacro IsShortcutTarget "$DESKTOP\PLMS.lnk" "$INSTDIR\${MAINBINARYNAME}.exe"
    Pop $0
    ${If} $0 = 1
      Delete "$DESKTOP\PLMS.lnk"
    ${EndIf}
    !insertmacro IsShortcutTarget "$SMPROGRAMS\PLMS.lnk" "$INSTDIR\${MAINBINARYNAME}.exe"
    Pop $0
    ${If} $0 = 1
      Delete "$SMPROGRAMS\PLMS.lnk"
    ${EndIf}
  ${EndIf}

  ; Remove registry information for add/remove programs
  !if "${INSTALLMODE}" == "both"
    DeleteRegKey SHCTX "${UNINSTKEY}"
  !else if "${INSTALLMODE}" == "perMachine"
    DeleteRegKey HKLM "${UNINSTKEY}"
  !else
    DeleteRegKey HKCU "${UNINSTKEY}"
  !endif

  ; Removes the Autostart entry for ${PRODUCTNAME} from the HKCU Run key if it exists.
  ; This ensures the program does not launch automatically after uninstallation if it exists.
  ; If it doesn't exist, it does nothing.
  ; We do this when not updating (to preserve the registry value on updates)
  ${If} $UpdateMode <> 1
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${PRODUCTNAME}"
  ${EndIf}

  ; Delete app data if the checkbox is selected
  ; and if not updating
  ${If} $DeleteAppDataCheckboxState = 1
  ${AndIf} $UpdateMode <> 1
    ; Clear the install location $INSTDIR from registry
    DeleteRegKey SHCTX "${MANUPRODUCTKEY}"
    DeleteRegKey /ifempty SHCTX "${MANUKEY}"

    ; Clear the install language from registry
    DeleteRegValue HKCU "${MANUPRODUCTKEY}" "Installer Language"
    DeleteRegKey /ifempty HKCU "${MANUPRODUCTKEY}"
    DeleteRegKey /ifempty HKCU "${MANUKEY}"

    ; PLMS-only app data cleanup was handled by the worker above.
    ; Never remove the shared Medicsoft parent or a LIS sibling.
  ${EndIf}

  !ifmacrodef NSIS_HOOK_POSTUNINSTALL
    !insertmacro NSIS_HOOK_POSTUNINSTALL
  !endif

  ; Advance successful removal to the approved completion page.
  SetAutoClose true
SectionEnd

Function RestorePreviousInstallLocation
  ReadRegStr $4 SHCTX "${MANUPRODUCTKEY}" ""
  ${If} $4 == ""
    ReadRegStr $4 SHCTX "${UNINSTKEY}" "InstallLocation"
    ${If} $4 != ""
      ; Tauri writes InstallLocation with enclosing quotes; strip them before reuse.
      StrCpy $5 $4 1
      ${If} $5 == '$\"'
        StrCpy $4 $4 -1 1
      ${EndIf}
      StrCpy $INSTDIR $4
      Return
    ${EndIf}
    ReadRegStr $4 SHCTX "Software\org\${PRODUCTNAME}" ""
  ${EndIf}
  StrCmp $4 "" +2 0
    StrCpy $INSTDIR $4
FunctionEnd

Function Skip
  Abort
FunctionEnd

Function SkipIfPassive
  ${IfThen} $PassiveMode = 1  ${|} Abort ${|}
FunctionEnd
Function un.SkipIfPassive
  ${IfThen} $PassiveMode = 1  ${|} Abort ${|}
FunctionEnd

!macro PLMS_WRITE_SHORTCUT LINK
  ; An explicit, content-versioned icon avoids reusing an old executable icon cache.
  ClearErrors
  CreateShortcut "${LINK}" "$INSTDIR\${MAINBINARYNAME}.exe" "" "${PLMS_SHORTCUT_ICON}" 0 SW_SHOWNORMAL "" "Medicsoft PLMS"
  ${IfNot} ${Errors}
    !insertmacro SetLnkAppUserModelId "${LINK}"
    ; SHCNE_UPDATEITEM | SHCNF_PATHW | SHCNF_FLUSHNOWAIT: refresh this link only.
    System::Call 'shell32::SHChangeNotify(i 0x00002000,i 0x00002005,w "${LINK}",p 0)'
  ${EndIf}
!macroend

!macro PLMS_REFRESH_OWNED_SHORTCUT LINK
  !insertmacro IsShortcutTarget "${LINK}" "$INSTDIR\${MAINBINARYNAME}.exe"
  Pop $0
  ${If} $0 != 1
  ${AndIf} $OldMainBinaryName != ""
    !insertmacro IsShortcutTarget "${LINK}" "$INSTDIR\$OldMainBinaryName"
    Pop $0
  ${EndIf}
  ${If} $0 = 1
    !insertmacro PLMS_WRITE_SHORTCUT "${LINK}"
    StrCpy $R0 1
  ${EndIf}
!macroend

Function CreateOrUpdateStartMenuShortcut
  StrCpy $R0 0
  !insertmacro PLMS_REFRESH_OWNED_SHORTCUT "$SMPROGRAMS\$AppStartMenuFolder\${PRODUCTNAME}.lnk"
  !insertmacro PLMS_REFRESH_OWNED_SHORTCUT "$SMPROGRAMS\${PRODUCTNAME}.lnk"
  !insertmacro PLMS_REFRESH_OWNED_SHORTCUT "$SMPROGRAMS\PLMS.lnk"
  ${If} $R0 = 1
    Return
  ${EndIf}
  ${If} $PLMSRefreshOnly = 1
    Return
  ${EndIf}
  ${If} $WixMode = 0
    ${If} $UpdateMode = 1
    ${OrIf} $NoShortcutMode = 1
      Return
    ${EndIf}
  ${EndIf}
  !if "${STARTMENUFOLDER}" != ""
    ; Do not replace a same-named shortcut belonging to a different application.
    ${If} ${FileExists} "$SMPROGRAMS\$AppStartMenuFolder\${PRODUCTNAME}.lnk"
      Return
    ${EndIf}
    CreateDirectory "$SMPROGRAMS\$AppStartMenuFolder"
    !insertmacro PLMS_WRITE_SHORTCUT "$SMPROGRAMS\$AppStartMenuFolder\${PRODUCTNAME}.lnk"
  !else
    ${If} ${FileExists} "$SMPROGRAMS\${PRODUCTNAME}.lnk"
      Return
    ${EndIf}
    !insertmacro PLMS_WRITE_SHORTCUT "$SMPROGRAMS\${PRODUCTNAME}.lnk"
  !endif
FunctionEnd

Function CreateOrUpdateDesktopShortcut
  StrCpy $R0 0
  !insertmacro PLMS_REFRESH_OWNED_SHORTCUT "$DESKTOP\${PRODUCTNAME}.lnk"
  !insertmacro PLMS_REFRESH_OWNED_SHORTCUT "$DESKTOP\PLMS.lnk"
  ${If} $R0 = 1
    Return
  ${EndIf}
  ${If} $PLMSRefreshOnly = 1
    Return
  ${EndIf}
  ${If} $WixMode = 0
    ${If} $UpdateMode = 1
    ${OrIf} $NoShortcutMode = 1
      Return
    ${EndIf}
  ${EndIf}
  ${If} $PLMSDesktopState != 1
  ${AndIf} $PassiveMode != 1
  ${AndIfNot} ${Silent}
    Return
  ${EndIf}
  ${If} ${FileExists} "$DESKTOP\${PRODUCTNAME}.lnk"
    Return
  ${EndIf}
  !insertmacro PLMS_WRITE_SHORTCUT "$DESKTOP\${PRODUCTNAME}.lnk"
FunctionEnd
