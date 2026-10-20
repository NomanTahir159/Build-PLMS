from pathlib import Path
import json, re, struct, unittest, xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'src-tauri' / 'installer'
SOURCE = (ART / 'installer.nsi').read_text(encoding='utf-8')

class InstallerSourceTests(unittest.TestCase):
    def test_uploaded_svg(self):
        svg = ET.parse(ART / 'medicsoft-logo.svg').getroot()
        self.assertEqual(svg.attrib.get('viewBox'), '0 0 512 512')
        self.assertTrue(list(svg.iter('{http://www.w3.org/2000/svg}path')))

    def test_bitmap_assets(self):
        for filename, size in [('sidebar.bmp', (328, 628)), ('sidebar-dark.bmp', (328, 628)), ('header-light.bmp', (300, 114)), ('header-dark.bmp', (300, 114))]:
            raw = (ART / filename).read_bytes()
            self.assertEqual(raw[:2], b'BM')
            self.assertEqual(struct.unpack_from('<ii', raw, 18), size)
            self.assertEqual(struct.unpack_from('<H', raw, 28)[0], 24)
        raw = (ART / 'medicsoft-installer.ico').read_bytes()
        self.assertEqual(raw[:4], b'\x00\x00\x01\x00')
        self.assertGreaterEqual(struct.unpack_from('<H', raw, 4)[0], 6)

    def test_no_overlaid_icon(self):
        self.assertNotIn('Function PLMSDrawLogo', SOURCE)
        self.assertNotIn('plms-logo.ico', SOURCE)
        self.assertNotIn('0x50000003', SOURCE)
        self.assertIn('Push $mui.WelcomePage.Image', SOURCE)
        self.assertIn('Push $mui.FinishPage.Image', SOURCE)
        self.assertIn('SendMessage $1 0x0172 0 $5', SOURCE)

    def test_page_coverage(self):
        for page in ['MUI_PAGE_LICENSE', 'MULTIUSER_PAGE_INSTALLMODE', 'MUI_PAGE_DIRECTORY', 'MUI_PAGE_STARTMENU', 'MUI_PAGE_INSTFILES']:
            self.assertRegex(SOURCE, r'!define MUI_PAGE_CUSTOMFUNCTION_SHOW PLMSPageShow\s+!insertmacro '+page)
        self.assertIn('Call PLMSPageShow\n    nsDialogs::Show', SOURCE)
        self.assertIn('Call un.PLMSPageShow\nFunctionEnd', SOURCE)
        self.assertRegex(SOURCE, r'!define MUI_PAGE_CUSTOMFUNCTION_SHOW un.PLMSPageShow\s+!insertmacro MUI_UNPAGE_INSTFILES')
        for callback in ['GUIINIT PLMSGuiInit', 'UNGUIINIT un.PLMSGuiInit']:
            self.assertIn('!define MUI_CUSTOMFUNCTION_'+callback, SOURCE)

    def test_windows_theme(self):
        self.assertIn('"AppsUseLightTheme"', SOURCE)
        self.assertIn('DarkMode_Explorer', SOURCE)
        self.assertIn('DwmSetWindowAttribute', SOURCE)
        self.assertIn('!insertmacro PLMS_WIZARD_FUNCTIONS "un."', SOURCE)
        self.assertIn('gdi32::DeleteObject', SOURCE)

    def test_color_arguments_are_compile_time_literals(self):
        # Regression: NSIS silently converts runtime color variables into black.
        commands=re.findall(r'^\s*SetCtlColors\s+(.+)$',SOURCE,re.M)
        self.assertTrue(commands)
        for command in commands:
            parts=command.split()
            self.assertGreaterEqual(len(parts),2)
            for color in parts[1:]:
                self.assertNotIn('$',color,command)
                self.assertRegex(color.strip('"'),r'^(?:[0-9A-Fa-f]{6}|transparent|/BRANDING)$')
        for palette in ['SetCtlColors $0 F2F2F2 202020','SetCtlColors $0 F2F2F2 2D2D2D','SetCtlColors $0 202020 FFFFFF']:
            self.assertIn(palette,SOURCE)

    def test_dpi_geometry(self):
        self.assertIn('user32::MapDialogRect', SOURCE)
        self.assertIn('i 60,i 14', SOURCE)
        self.assertIn('i 8,i 12', SOURCE)
        for scale in [1, 1.25, 1.5, 1.75, 2]:
            # The same mapped width, height and gap is used for all three slots.
            width, height, gap = [round(v * scale) for v in (96, 24, 13)]
            right = round(640 * scale)
            rects = []
            for _ in range(3):
                rects.append((right-width, 0, right, height))
                right -= width + gap
            self.assertEqual({r[2]-r[0] for r in rects}, {width})
            self.assertEqual({r[3]-r[1] for r in rects}, {height})
            self.assertEqual(rects[0][0]-rects[1][2], gap)
            self.assertEqual(rects[1][0]-rects[2][2], gap)

    def test_app_configuration_scope(self):
        config=json.loads((ROOT / 'src-tauri/tauri.conf.json').read_text())
        nsis=config['bundle']['windows']['nsis']
        for key in ['template', 'installerIcon', 'uninstallerIcon', 'sidebarImage', 'headerImage', 'uninstallerHeaderImage']:
            self.assertTrue((ROOT / 'src-tauri' / nsis[key]).is_file(),key)
        self.assertEqual(config['productName'],'Medicsoft PLMS')
        self.assertEqual(nsis['installMode'],'perMachine')

if __name__ == '__main__':
    unittest.main(verbosity=2)
