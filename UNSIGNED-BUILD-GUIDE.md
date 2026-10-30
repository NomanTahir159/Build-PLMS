# PLMS Beta 0.1.1 — Unsigned Internal Test Build

This package intentionally skips Windows code signing for now.

## What is included

- only the main PLMS window opens at startup
- main PLMS window starts maximized
- Report Designer opens only when requested
- closing Report Designer does not close the main PLMS app
- reopening Report Designer creates or focuses the Designer child window
- selected template and logged-in user route are passed into the Designer
- username autofill blue background is removed
- GitHub Actions builds the Windows NSIS installer

## Build on GitHub

1. Upload/replace this package's files in your PLMS GitHub repository.
2. Confirm:
   `.github/workflows/build-windows.yml`
3. Open:
   Actions → Build PLMS Windows Beta 0.1.1
4. Click:
   Run workflow
5. Wait for the job to finish.
6. Download the artifact:
   `PLMS-Beta-0.1.1-UNSIGNED-Windows-Installer`

## Important

The installer is unsigned. Windows Smart App Control or other organization
security policy may block it. This package is intended only for controlled
internal beta testing until a trusted code-signing certificate is added.
