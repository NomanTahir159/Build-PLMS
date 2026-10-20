# Validation

Preparation checks passed:

- 64 existing backend security, authentication, session, restore, workflow and resource-build tests.
- Four new backend checks: persisted catalog projection and restart; real backup files with unrelated-file preservation; repeat orders using stable patient IDs and direct test codes; Administrator deletion of an order's report archive.
- All frontend test suites, including native login, navigation history, flush-before-close, sample transitions, result completeness, date chronology and processing bypass.
- Executable script syntax, offline asset paths, exact catalog preservation, removed Catalog controls and installer resource configuration.

No compiled Windows installer is included. GitHub Actions compiles the Rust host and Python worker, builds the NSIS installer, generates a SHA-256 checksum and uploads the installer artifact. On Windows, verify normal-user first launch, upgrade of an existing installation, printing, title-bar dragging/window controls and both themes before production use.
