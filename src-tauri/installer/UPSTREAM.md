# Installer template provenance

The custom installer template is based on Tauri CLI v2.12.0's NSIS template:
https://github.com/tauri-apps/tauri/blob/tauri-cli-v2.12.0/crates/tauri-bundler/src/bundle/windows/nsis/installer.nsi

Upstream template SHA-256: dabed59013b1d78b879a1a85bc7f2eed2993b33a9a90cdabe5946de3d3950597.

Tauri is licensed under MIT OR Apache-2.0. Branding changes are limited to native wizard artwork, typography, page text, file company metadata, and preservation of a previous installation path when changing Publisher from org to Medicsoft Corporation. Upstream install/uninstall sections and hooks are retained. When upgrading Tauri CLI, compare this custom template against that version's upstream template.

0.2.7 additionally uses proportional high-resolution logo artwork, native sidebar labels with font cleanup, and a custom post-install account page that invokes the bundled GUI helper and prevents finishing after cancellation. Upstream install/uninstall resource sections remain intact.
0.2.7 removes account setup and oversized header artwork, uses a fixed sidebar background with a native square icon, and cleans up the obsolete helper executable on upgrade. Native install/uninstall sections are retained.
