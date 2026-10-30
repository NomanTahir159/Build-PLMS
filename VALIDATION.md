# Validation — Medicsoft PLMS 1.0.13

Source: PLMS-1.0.13-Collapsible-Main-Menu.html, merged with the existing
Windows database, login, cloud backup and installer integration.

- 120 backend tests passed.
- 25 frontend regression suites passed, including hidden Google Drive backup
  controls, native authentication, sessions, report workflows and chronology.
- All frontend suites passed again with simulated Windows CRLF source endings.
- 114 host inline scripts compile. Report/letter checks compile 130 scripts
  including embedded management documents.
- 16 installer source checks and all seven installer DOM states passed.
- Rich letter save/reopen/print, safe paste and rollback checks passed.
- Actual AMH rules passed template grouping and pagination regressions.
- Full application startup with mocked native transport passed authentication,
  persisted migration of an existing template library, 12 Files report rows,
  collapsible menu controls and Backup & Restore opening.
- Installer naming helper produced Medicsoft.PLMS_1.0.13_x64-setup.exe and
  passed repeat invocation checks.
- Node, npm lock, Tauri, Cargo and About all use version 1.0.13.

The Windows installer was not compiled or interactively run in this Linux
session. Use the included GitHub Windows workflow. Live Google account consent
and Windows DPAPI are exercised on Windows; backend Google API tests use fakes.
No account tokens, personal runtime database or test output is included.
