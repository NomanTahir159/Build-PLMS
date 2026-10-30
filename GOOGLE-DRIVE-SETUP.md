# Hidden Google Drive backups for Medicsoft PLMS

This package includes the owner's validated Google **Desktop app** OAuth JSON in
`backend/google-drive-client.json`. The Windows build embeds it in the private
backend executable. No per-computer JSON selection or Set Up Connection is needed.
This identifies the application; it does not connect users to the owner's account.
No Google account access token or refresh token is included in the package.

## Build and connect

1. Upload the complete contents of `PLMS-Build/` to the Windows build repository,
   including `backend/google-drive-client.json`.
2. Run the included Build Windows workflow. It validates the bundled client and
   packages it with the backend. A repository secret is not needed for this ZIP.
   `PLMS_GOOGLE_CLIENT_JSON` remains an optional fallback if the file is absent.
3. Install the resulting Windows setup EXE.
4. Sign into PLMS as an Administrator. Open Tools → Backup & Restore and click
   **Connect Google Drive**. Sign in and grant permission in the system browser.
5. Select the shared Schedule and Backups to keep values, then **Save Schedule**.
   **Backup Now** uploads immediately, including when Schedule is **Off**.

The Google Cloud project must have Drive API enabled and its OAuth audience must
allow the account signing in. For Testing mode, add intended accounts as test users.
Testing refresh tokens with Drive scopes can expire after seven days; configure
publishing/audience appropriately for sustained use. Use the same Google project
and Desktop client on computers that should see the same cloud backups.

## One backup screen

Export, local restore selection and Google connection are on one screen. The
recovery table includes a **Backup Type** column with **Local** and **Cloud** rows.
Cloud rows load when the screen is open and refresh after uploads/deletions.

- Export downloads a verified JSON backup.
- Select for restore validates and stages the backup. The existing **Restore
  Selected Backup** button and confirmation still own replacement of current data.
- Delete requires confirmation and removes the selected local or cloud backup.
- Create Snapshot creates a local recovery snapshot.
- Backup Now creates an immediate verified hidden Google upload and keeps a local
  Google recovery copy before attempting the network operation.

Local and connected cloud automatic backups share Hourly, Daily, Weekly or Off
and retain 3, 7, 14 or 30 copies. Cloud uploads retry after failures, independently
of local snapshot success. The five most recent local pre-restore copies are
retained separately. Retention cleanup only removes this installation's cloud
copies; manual deletion targets the explicitly selected hidden PLMS backup.

## Storage and operation

Backups use Google's private `appDataFolder`, hidden from normal My Drive files.
They contain full PLMS data, including catalog/profiles, patients/orders/results,
employees/trainees, users/credential hashes, templates, settings and audit events.
Google connection tokens are excluded. Cloud copies are compressed JSON bundles.
Upload is downloaded again and SHA-256 checked before success is recorded.

Google OAuth uses the system browser, a temporary loopback listener, random state
and PKCE S256. Each Windows user connects independently. Account refresh tokens
are protected with CurrentUser DPAPI under
`%LOCALAPPDATA%\Medicsoft\PLMS\GoogleDrive\`, outside application backups.
Disconnect forgets local authorization and disables cloud uploads. Local backups
and previously uploaded cloud copies remain; other computers are not disconnected.

The worker checks automatic schedules while PLMS is running, including minimized
or signed out of PLMS. It retries upload failures after five minutes. No Windows
service/task is installed, and uploads stop when the app is closed.

Cloud and local Google recovery copies use PLMS_BACKUP v3 / SHA-256 /
plms-value-v1. Use this updated build to restore them; existing v2 backups remain
supported. Downloads/expanded backup data are capped at 64 MiB. Google account
storage and HTTPS protect transport/storage; this feature does not add a separate
backup encryption password.

## Validation limits

The bundled JSON was validated locally. Automated tests cover bundled-client
loading, real loopback callbacks with mocked token responses, hidden-folder
upload/readback integrity, offline recovery, retention/retry, mixed Local/Cloud
table actions, immediate backup with schedule Off, safe restore staging and access
checks. Real Windows execution, Google authorization and a live upload were not
performed in this environment. The ZIP contains build-ready source, not a compiled
Windows setup EXE. Use the included GitHub Windows workflow to build it.

References:
- https://developers.google.com/identity/protocols/oauth2/native-app
- https://developers.google.com/workspace/drive/api/guides/appdata
