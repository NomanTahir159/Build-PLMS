; Approved seven-state Medicsoft PLMS layout. Coordinates are logical pixels;
; the native Layout export scales them to the wizard's actual DPI/work area.
Var PLMSDialog
Var PLMSFolder
Var PLMSDesktop
Var PLMSLaunch
Var PLMSDesktopState
Var PLMSLaunchState
Var PLMSExitChoice

!macro PLMS_DESIGN_FUNCTION PREFIX
Function ${PREFIX}PLMSDesign
  Pop $PLMSDesignState
  Call ${PREFIX}PLMSPageShow
  System::Call '"$PLUGINSDIR\plms-theme.dll"::Layout(p $HWNDPARENT,i $PLMSDesignState)'
FunctionEnd
!macroend
!insertmacro PLMS_DESIGN_FUNCTION ""
!insertmacro PLMS_DESIGN_FUNCTION "un."

Function PLMSOptions
  Call SkipIfPassive
  ${If} $PLMSRepairMode = 1
    Abort
  ${EndIf}
  nsDialogs::Create 1018
  Pop $PLMSDialog
  System::Call '"$PLUGINSDIR\plms-theme.dll"::BindPage(p $HWNDPARENT,p $PLMSDialog)'
  ${If} $PLMSDialog == error
    Abort
  ${EndIf}
  ${NSD_CreateLabel} 0 0 870 34 "Installation Folder"
  Pop $0
  ${NSD_CreateText} 0 42 676 56 "$INSTDIR"
  Pop $PLMSFolder
  System::Call '"$PLUGINSDIR\plms-theme.dll"::BindOption(p $HWNDPARENT,i 1,p $PLMSFolder)'
  ${NSD_CreateBrowseButton} 694 42 176 56 "Browse..."
  Pop $0
  ${NSD_OnClick} $0 PLMSBrowse
  ${NSD_CreateCheckbox} 0 124 870 42 "Create a desktop shortcut"
  Pop $PLMSDesktop
  System::Call '"$PLUGINSDIR\plms-theme.dll"::BindOption(p $HWNDPARENT,i 2,p $PLMSDesktop)'
  ${NSD_CreateCheckbox} 0 182 870 42 "Launch PLMS after installation"
  Pop $PLMSLaunch
  System::Call '"$PLUGINSDIR\plms-theme.dll"::BindOption(p $HWNDPARENT,i 3,p $PLMSLaunch)'
  ${NSD_SetState} $PLMSDesktop $PLMSDesktopState
  ${NSD_SetState} $PLMSLaunch $PLMSLaunchState
  Push 0
  Call PLMSDesign
  nsDialogs::Show
FunctionEnd
Function PLMSBrowse
  Pop $0
  ${NSD_GetText} $PLMSFolder $1
  nsDialogs::SelectFolderDialog "Choose Installation Folder" "$1"
  Pop $1
  ${If} $1 != error
    ${NSD_SetText} $PLMSFolder $1
  ${EndIf}
FunctionEnd
Function PLMSOptionsLeave
  ${NSD_GetText} $PLMSFolder $INSTDIR
  ${If} $INSTDIR == ""
    MessageBox MB_ICONEXCLAMATION "Choose an installation folder."
    System::Call '"$PLUGINSDIR\plms-theme.dll"::Unlock(p $HWNDPARENT)'
    Abort
  ${EndIf}
  ; Require an absolute path; never allow a drive root or the shared Medicsoft parent.
  ${GetRoot} "$INSTDIR" $0
  ${If} $0 == ""
  ${OrIf} $INSTDIR == "$0"
  ${OrIf} $INSTDIR == "$0\"
  ${OrIf} $INSTDIR == "$PROGRAMFILES64\Medicsoft"
  ${OrIf} $INSTDIR == "$PROGRAMFILES\Medicsoft"
    MessageBox MB_ICONEXCLAMATION "Choose a dedicated PLMS application folder."
    System::Call '"$PLUGINSDIR\plms-theme.dll"::Unlock(p $HWNDPARENT)'
    Abort
  ${EndIf}
  ${NSD_GetState} $PLMSDesktop $PLMSDesktopState
  ${NSD_GetState} $PLMSLaunch $PLMSLaunchState
FunctionEnd
Function PLMSInstalling
  GetDlgItem $0 $HWNDPARENT 2
  EnableWindow $0 1
  Push 1
  Call PLMSDesign
FunctionEnd
Function PLMSComplete
  Call SkipIfPassive
  nsDialogs::Create 1018
  Pop $PLMSDialog
  System::Call '"$PLUGINSDIR\plms-theme.dll"::BindPage(p $HWNDPARENT,p $PLMSDialog)'
  ${NSD_CreateLabel} 90 40 780 80 "Installation completed successfully."
  Pop $0
  Push 2
  Call PLMSDesign
  nsDialogs::Show
FunctionEnd
Function PLMSCompleteLeave
  ${If} $PLMSLaunchState = 1
    Call RunMainBinary
  ${EndIf}
FunctionEnd
Function un.PLMSOptions
  Call un.SkipIfPassive
  ${If} $UpdateMode = 1
    Abort
  ${EndIf}
  nsDialogs::Create 1018
  Pop $PLMSDialog
  System::Call '"$PLUGINSDIR\plms-theme.dll"::BindPage(p $HWNDPARENT,p $PLMSDialog)'
  ${NSD_CreateLabel} 0 0 870 60 "Remove Medicsoft PLMS from this computer?"
  Pop $0
  ${NSD_CreateCheckbox} 0 88 870 64 "Delete patient records, catalog, settings and backups"
  Pop $DeleteAppDataCheckbox
  System::Call '"$PLUGINSDIR\plms-theme.dll"::BindOption(p $HWNDPARENT,i 7,p $DeleteAppDataCheckbox)'
  ${NSD_SetState} $DeleteAppDataCheckbox $DeleteAppDataCheckboxState
  ${NSD_CreateLabel} 40 160 830 66 "Leave unchecked to keep your data for reinstallation."
  Pop $0
  Push 4
  Call un.PLMSDesign
  nsDialogs::Show
FunctionEnd
Function un.PLMSOptionsLeave
  ${NSD_GetState} $DeleteAppDataCheckbox $DeleteAppDataCheckboxState
FunctionEnd
Function un.PLMSInstalling
  Push 5
  Call un.PLMSDesign
FunctionEnd
Function un.PLMSComplete
  Call un.SkipIfPassive
  ${If} $UpdateMode = 1
    Abort
  ${EndIf}
  System::Call '"$PLUGINSDIR\plms-theme.dll"::SetDataChoice(p $HWNDPARENT,i $DeleteAppDataCheckboxState)'
  nsDialogs::Create 1018
  Pop $PLMSDialog
  System::Call '"$PLUGINSDIR\plms-theme.dll"::BindPage(p $HWNDPARENT,p $PLMSDialog)'
  ${NSD_CreateLabel} 90 40 780 80 "Uninstallation completed successfully."
  Pop $0
  ${If} $DeleteAppDataCheckboxState = 1
    ${NSD_CreateLabel} 0 130 870 80 "Your selected PLMS data has been removed."
  ${Else}
    ${NSD_CreateLabel} 0 130 870 80 "Your patient records and backups have been retained."
  ${EndIf}
  Pop $0
  Push 6
  Call un.PLMSDesign
  nsDialogs::Show
FunctionEnd
