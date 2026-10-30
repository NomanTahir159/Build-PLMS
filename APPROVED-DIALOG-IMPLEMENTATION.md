# Approved PLMS installer dialogs

This revision replaces the approximate GDI dialog renderer with a WebView2 host
that loads the approved dialog HTML/CSS directly. NSIS still performs the file,
registry, shortcut, repair and PLMS-only data-removal operations.

`src-tauri/installer/ui/approved-preview.html` is the retained design source.
`build_installer_ui.py` copies its window markup and full product stylesheet
without redrawing them. The official logo is embedded as SVG. Microscope and
test-tube artwork uses Lucide 1.17.0, matching the preview runtime. No remote
styles, scripts, fonts or images are required by the installed interface.

The actual interface is `ui/dialog.html`, built with `ui/host.js`. It has all
seven approved states. The native host supplies actual progress and operation
results, rather than the preview's simulated progress timer.

- Custom HTML title bar and 952 × 998 logical-pixel window geometry.
- The approved gradients, typography, spacing, green option controls and buttons.
- One DOM layout block for the success mark, success message and supporting text.
- Complete, proportional 144 × 144 logo; native page controls cannot cover it.
- The approved progress view, without a visible raw file-operation/log table.
- Decorative artwork stays within the body, above the footer.
- Cancel is present on the approved options/progress screens. During installation
  it uses NSIS cancellation and may leave partially copied program files; it
  does not claim to roll back a partially completed installation. Reinstall/repair
  can replace those files. Uninstall progress has no Cancel action.
- Repair proceeds directly with the stored installation directory.
- Successful removal advances automatically to the uninstall completion screen.
- Existing official shortcut/icon fixes are retained.

The UI is revealed only after the actual NSIS state has reached the HTML
renderer. Native NSIS pages stay hidden beneath one opaque HTML surface. This
removes the conflicting content layers responsible for the cropped completion
logo and displaced message in the uploaded screenshot.

## Build and runtime

The build uses the official Microsoft.Web.WebView2 SDK 1.0.3485.44, with a pinned
SHA-256 checksum. The x86 loader matches the NSIS process; the installed PLMS
application remains x64. The host is built with the static C++ runtime.

WebView2 must exist before displaying the HTML UI. If missing, setup prepares
it using the same bundled offline runtime already configured for PLMS. Normal
Windows 10/11 systems with WebView2 skip this step. If the runtime has been
removed before uninstallation, reinstall it for the visual uninstaller or use
`uninstall.exe /S` for unattended removal. Neither path changes data-deletion
scope or makes data deletion the default.

The host module is pinned for the setup process lifetime so asynchronous COM
callbacks cannot execute in an unloaded DLL. The UI cache is temporary to setup;
it is separate from the PLMS application database and its WebView profile.

## Validation and limits

The preparation environment passed 16 installer/design/resource checks, all
seven DOM/interaction states and host-message checks, and the existing 22
frontend suites. The x86 host and Windows integration executable cross-compile
with warnings treated as errors. NSIS page/resource/shortcut syntax checks also
pass in an isolated harness.

A real graphical browser could not run here because local socket creation is
blocked. There is no claim of a completed pixel-by-pixel Windows comparison.

The Windows build runs the real WebView2 integration program before packaging.
It checks every state, logo and layout bounds, native-page isolation, progress,
and option transfer. It captures seven native screenshots under
`src-tauri/installer/theme/build/screenshots/` during a local Windows build.
Those tests still need to execute on Windows, followed by a full installer /
uninstaller walkthrough. Only that visual review can confirm a 100% match on
the target Windows version and display scaling.


## Installer browser data location correction

WebView2 data now lives in `%LOCALAPPDATA%\Medicsoft\PLMS\InstallerWebView-Admin`
(or `-User` for a non-admin host), with the directory created before starting
WebView2. It no longer inherits the restrictive permissions or lifetime of
NSIS's `$PLUGINSDIR`. Admin and non-admin installer hosts use separate browser
profiles. This is browser cache only; patient records and application backups
remain at their existing paths. No cache is placed in the extraction folder.
The Windows native smoke checks its location and write access in addition to
opening the real WebView2 interface. Running the final NSIS setup on the user's
Windows machine is still required to confirm this reported startup failure.


## Installer startup and console visibility

NSIS now compresses files independently instead of using a single solid block.
This avoids solid-block extraction seeking before the first HTML dialog; it may
increase package size. Startup also includes archive verification, Windows
security scanning and WebView2 process startup, so there is no fixed instant-open
time guarantee.

The explicit data-removal worker runs through nsExec with no visible console.
Both its output and exit result are consumed, and failure/timeout handling still
reports retained data rather than falsely reporting deletion. Normal application
worker startup already requests CREATE_NO_WINDOW in Rust. Required Windows UAC
approval remains because the package installs/uninstalls in Program Files.

Source/frontend checks pass. Actual startup timing and console visibility still
require testing the rebuilt setup/uninstaller on Windows.
