# PLMS Beta 0.1.2 — No Console Window Fix

This build fixes the black Windows Terminal/console window that appeared
together with PLMS.

## Cause

The Rust entry executable was compiled as a Windows console-subsystem program,
so Windows Terminal attached to it. Closing that console terminated PLMS.

## Fix

`src-tauri/src/main.rs` now contains:

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
```

For release builds, PLMS is now compiled as a Windows GUI application.

Expected behavior:

- PLMS opens without a black console/Terminal window.
- Only the main PLMS window appears at startup.
- The main PLMS window starts maximized.
- Report Designer opens only when requested.
- Closing Report Designer does not close the main PLMS application.
- Reopening Report Designer restores/creates its child window.
- The username autofill blue-background fix remains included.

## GitHub build

Upload/replace the Beta 0.1.2 project files in your repository, then start a
NEW workflow run:

Actions → Build PLMS Windows Beta 0.1.2 → Run workflow

Artifact:

`PLMS-Beta-0.1.2-UNSIGNED-Windows-Installer`
