from pathlib import Path
import hashlib
import json
import re
import struct
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'src-tauri/installer'
UI=ART/'ui'
SOURCE=(ART/'installer.nsi').read_text(encoding='utf-8')
NATIVE=(ART/'theme/plms-theme.cpp').read_text(encoding='utf-8')
PAGES=(ART/'PLMSPages.nsh').read_text(encoding='utf-8')

class InstallerTests(unittest.TestCase):
    def test_approved_styles_are_copied_without_redrawing(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/build_installer_ui.py')],check=True,stdout=subprocess.DEVNULL)
        approved=(UI/'approved-preview.html').read_text(encoding='utf-8')
        actual=(UI/'dialog.html').read_text(encoding='utf-8')
        css=re.search(r'<style>([\s\S]*?)</style>',approved).group(1)
        self.assertIn('<style>'+css,actual)
        self.assertNotIn('void canvas(',NATIVE)
        self.assertIn('NavigateToString',NATIVE)
        self.assertNotIn('GradientFill(',NATIVE)

    def test_markup_contains_one_complete_brand_and_decoration(self):
        actual=(UI/'dialog.html').read_text(encoding='utf-8')
        for marker in ['class="product-logo"','class="product-name"','class="product-subtitle"','class="lab-microscope"','class="lab-tubes"']:
            self.assertEqual(actual.count(marker),1,marker)
        self.assertEqual(actual.count('data:image/svg+xml;base64,'),2)
        self.assertNotIn('data-lucide=',actual)
        self.assertNotIn('preview-controls',actual.split('</style>',1)[1])

    def test_runtime_has_no_external_web_dependencies(self):
        actual=(UI/'dialog.html').read_text(encoding='utf-8')
        self.assertNotRegex(actual,r'<(?:script|link)[^>]+(?:src|href)="https?://')
        self.assertIn("default-src 'none'",actual)
        self.assertIn('lstrcmpW(source,L"about:blank")==0',NATIVE)
        self.assertIn('event->put_Cancel(TRUE)',NATIVE)
        self.assertIn('event->put_Handled(TRUE)',NATIVE)

    def test_seven_real_states_and_no_simulated_progress(self):
        js=(UI/'host.js').read_text()
        for name in ['install','installing','installed','maintenance','uninstall','uninstalling','uninstalled']:
            self.assertIn("'"+name+"'",js)
        self.assertNotIn('setInterval',js)
        self.assertIn('PBM_GETPOS',NATIVE)
        self.assertIn('PBM_GETRANGE',NATIVE)
        self.assertIn('kind\\\":\\\"progress',NATIVE)
        self.assertIn('MoveFocus',NATIVE)

    def test_bound_controls_are_the_actual_nsis_controls(self):
        for value,role in [('PLMSFolder',1),('PLMSDesktop',2),('PLMSLaunch',3),('DeleteAppDataCheckbox',7)]:
            self.assertIn('::BindOption(p $HWNDPARENT,i '+str(role)+',p $'+value+')',PAGES)
        for role in [4,5,6]:self.assertIn('::BindOption(p $HWNDPARENT,i '+str(role),SOURCE)
        self.assertIn('::BindPage(',PAGES)
        self.assertIn('NSD_GetText} $PLMSFolder $INSTDIR',PAGES)
        self.assertIn('NSD_GetState} $DeleteAppDataCheckbox $DeleteAppDataCheckboxState',PAGES)
        self.assertIn('::Unlock(',PAGES)
        self.assertIn('::SetDataChoice(',PAGES)

    def test_native_pages_cannot_cover_html_or_cut_logo(self):
        self.assertIn('child!=c->host)hideChild(child)',NATIVE)
        self.assertIn('position->flags|=SWP_HIDEWINDOW',NATIVE)
        self.assertIn('GetDlgCtrlID(child)==HtmlHostId',NATIVE)
        self.assertIn('SetWindowPos(c->host,HWND_TOP',NATIVE)
        self.assertIn('PostMessageW(window,SyncMessage',NATIVE)
        self.assertIn('!c->rendered',NATIVE)
        self.assertIn('action==L"painted"',NATIVE)
        self.assertNotIn('FindWindowExW(',NATIVE)
        self.assertNotIn('WM_PAINT',NATIVE)
        self.assertNotIn('RDW_ERASE',NATIVE)

    def test_exact_design_geometry_and_custom_window_chrome(self):
        actual=(UI/'dialog.html').read_text()
        for marker in ['width:952px;height:998px','height:50px','height:126px','width:144px;height:144px']:
            self.assertIn(marker,actual)
        self.assertIn('WS_CAPTION|WS_THICKFRAME|WS_BORDER|WS_DLGFRAME',NATIVE)
        self.assertIn('WS_EX_WINDOWEDGE|WS_EX_CLIENTEDGE',NATIVE)
        self.assertIn('952*factor',NATIVE)
        self.assertIn('998*factor',NATIVE)
        self.assertIn('info.rcWork',NATIVE)

    def test_loader_is_pinned_and_offline_runtime_precedes_gui(self):
        self.assertIn('GET_MODULE_HANDLE_EX_FLAG_PIN',NATIVE)
        self.assertIn('::Detach(',SOURCE)
        self.assertLess(SOURCE.index('RuntimeAvailable('),SOURCE.index('::Configure('))
        self.assertIn('File /oname=WebView2Loader.dll',SOURCE)
        self.assertIn('File /oname=plms-dialog.html',SOURCE)
        self.assertIn('${WEBVIEW2INSTALLERPATH}',SOURCE)
        self.assertIn('uninstall.exe /S',SOURCE)

    def test_sdk_is_official_and_checksum_pinned(self):
        text=(ROOT/'scripts/webview2_sdk.py').read_text()
        self.assertIn('https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/',text)
        self.assertRegex(text,r"SHA256='[a-f0-9]{64}'")
        self.assertIn("hashlib.sha256(payload).hexdigest()!=SHA256",text)
        build=(ROOT/'scripts/build_installer_theme.py').read_text()
        self.assertIn('/W4 /WX',build)
        self.assertIn('str(smoke)',build)
        smoke=(ART/'theme/smoke.cpp').read_text()
        self.assertIn('native page cannot cover HTML',smoke)
        self.assertIn('CapturePreview',smoke)
        self.assertIn('for(int state=0;state<7',smoke)

    def test_official_logo_is_preserved(self):
        svg=ET.parse(ART/'medicsoft-logo.svg').getroot()
        self.assertEqual(svg.attrib['viewBox'],'0 0 69.24 69.24')
        self.assertTrue(list(svg.iter('{http://www.w3.org/2000/svg}path')))
        text=(ART/'medicsoft-logo.svg').read_text()
        for color in ['#fff','#22cf8b','#29b473']:self.assertIn(color,text)

    def test_all_icons_use_same_official_artwork(self):
        icon=(ROOT/'src-tauri/icons/icon.ico').read_bytes()
        self.assertEqual(icon,(ART/'medicsoft-installer.ico').read_bytes())
        self.assertEqual(icon,(ROOT/'src/Resources/app.ico').read_bytes())
        part=re.search(r'!define PLMS_SHORTCUT_ICON "\$INSTDIR(.*?)"',SOURCE).group(1)
        resource=ROOT/'src'/part.strip(chr(92)).replace(chr(92),'/')
        self.assertEqual(resource.read_bytes(),icon)
        self.assertIn(hashlib.sha256(icon).hexdigest()[:12],resource.name)
        for name in ['32x32.png','128x128.png','128x128@2x.png','icon.png']:
            self.assertEqual((ROOT/'src-tauri/icons'/name).read_bytes()[25],6,name)

    def test_bitmap_assets_for_upstream_template(self):
        for name,size in [('sidebar.bmp',(328,628)),('header-light.bmp',(300,114))]:
            raw=(ART/name).read_bytes()
            self.assertEqual(raw[:2],b'BM')
            self.assertEqual(struct.unpack_from('<ii',raw,18),size)

    def test_shortcut_repair_precedes_no_new_shortcut_guard(self):
        for name in ['CreateOrUpdateDesktopShortcut','CreateOrUpdateStartMenuShortcut']:
            body=SOURCE.split('Function '+name,1)[1].split('FunctionEnd',1)[0]
            self.assertLess(body.index('PLMS_REFRESH_OWNED_SHORTCUT'),body.index('$UpdateMode = 1'))
            self.assertIn('${FileExists}',body)
        self.assertIn('SHChangeNotify',SOURCE)
        self.assertNotIn('!insertmacro SetShortcutTarget',SOURCE)

    def test_approved_page_sequence_and_repair_flow(self):
        for callback in ['PLMSOptions','PLMSComplete','un.PLMSOptions','un.PLMSComplete']:
            self.assertIn('custom '+callback,SOURCE)
        self.assertIn('SHOW PLMSInstalling',SOURCE)
        self.assertIn('SHOW un.PLMSInstalling',SOURCE)
        self.assertIn('$PLMSRepairMode = 1',PAGES)
        self.assertIn('StrCpy $PLMSRepairMode 1',SOURCE)
        self.assertIn('EnableWindow $0 1',PAGES)
        uninstall=SOURCE.split('Section Uninstall',1)[1].split('SectionEnd',1)[0]
        self.assertIn('SetAutoClose true',uninstall)

    def test_storage_and_deletion_scope_stays_plms_only(self):
        for token in ['$PROGRAMFILES64\\Medicsoft\\PLMS','$PROGRAMFILES\\Medicsoft\\PLMS','Call RestorePreviousInstallLocation','$DeleteAppDataCheckboxState = 1','$UpdateMode <> 1','--delete-app-data']:
            self.assertIn(token,SOURCE)
        self.assertNotIn('RMDir /r "$APPDATA',SOURCE)
        self.assertIn('PLMS-only app data cleanup',SOURCE)
        self.assertLess(SOURCE.index('--delete-app-data'),SOURCE.index('; Delete resources'))

    def test_configuration_stays_separate_from_lis(self):
        config=json.loads((ROOT/'src-tauri/tauri.conf.json').read_text())
        self.assertEqual(config['productName'],'Medicsoft PLMS')
        self.assertEqual(config['bundle']['windows']['nsis']['installMode'],'perMachine')
        self.assertFalse(config['app']['windows'][0]['dragDropEnabled'])
        self.assertIn('.disable_drag_drop_handler()', (ROOT/'src-tauri/src/lib.rs').read_text())
        for name,path in config['bundle']['windows']['nsis'].items():
            if name in ['template','installerIcon','uninstallerIcon','sidebarImage','headerImage','uninstallerHeaderImage']:
                self.assertTrue((ROOT/'src-tauri'/path).is_file(),name)

if __name__=='__main__':unittest.main(verbosity=2)
