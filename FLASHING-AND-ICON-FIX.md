> Historical revision: the GDI drawing changes below are superseded by the direct HTML renderer. The shortcut/icon fixes remain active. See APPROVED-DIALOG-IMPLEMENTATION.md.

# Installer flashing and shortcut icon update

The previous native painter invalidated the complete wizard every 150 ms on all
seven screens and drew the background directly during both erase and paint.
This revision buffers the window, page and button painting; the completed frame
is copied to the screen in one operation. Background erase no longer exposes a
blank intermediate frame. Idle pages have no timer. Installation/removal poll
actual engine progress and invalidate only the percentage heading when its
integer value changes. The synchronous repaint before page layout is removed.

The app, setup, uninstall and resource icons now share the same official
Medicsoft PLMS artwork. All application PNG icons are RGBA. The installed
`Resources/Branding/medicsoft-plms-<content hash>.ico` is explicitly assigned to
shortcuts and the Installed Apps entry. A different icon asset gets a different
filename, avoiding reuse of the former executable icon location.

Existing PLMS desktop and Start Menu links are refreshed before any
update/no-new-shortcut checks. This includes owned links under the legacy
`PLMS.lnk` name. Per-machine installation also refreshes matching current-user
links left by older installations, without creating extra current-user links.
Ownership is checked against the current or recorded previous PLMS executable;
unrelated same-named links are left alone. Explorer receives an update notice
for each modified link. The application folder is the shortcut working folder.
No global icon-cache deletion or Explorer restart is performed.

Build a new installer from these source files, then install/repair PLMS with
that new build. Downloading the ZIP alone does not change an installed copy.

Validation in the preparation environment:

- 16 installer source/artwork/resource checks pass.
- The revised x86 painter and Windows smoke harness cross-compile with warnings
  treated as errors.
- The actual NSIS page and shortcut source compiles in isolated syntax harnesses
  for both grouped and root-level Start Menu paths. External Tauri helper
  functions are stubbed in those harnesses; the complete build remains in the
  GitHub Windows workflow.
- Every embedded ICO size matches the decoded official raster artwork.
- Added Windows smoke assertions cover idle repaint suppression, unchanged
  progress, heading-only invalidation, and background erase behavior.

Native smoke execution, visual flashing verification and Explorer shortcut
verification still require Windows. The earlier preview/layout differences are
outside this update; this revision does not claim an exact visual match.
