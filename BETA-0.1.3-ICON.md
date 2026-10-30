# PLMS Beta 0.1.3 — SGRH Icon Update

The exact user-provided `SGRH.png` artwork is used as the source for the Windows/Tauri icon set.

Generated files:

- `src-tauri/icons/32x32.png`
- `src-tauri/icons/128x128.png`
- `src-tauri/icons/128x128@2x.png`
- `src-tauri/icons/icon.png`
- `src-tauri/icons/icon.ico`
- `src-tauri/icons/SGRH-source.png`

The Tauri bundle icon configuration points to these files, so the next GitHub
build uses the SGRH logo for the Windows executable, NSIS installer, installed
application, Start menu/shortcut icon, and taskbar/window icon.

Build a NEW workflow run:

Actions → Build PLMS Windows Beta 0.1.3 → Run workflow

Artifact:

`PLMS-Beta-0.1.3-UNSIGNED-Windows-Installer`
