# PLMS Beta 0.1.1 — Windows Code-Signing Setup

This build is configured to publish only a **signed** Windows installer.

## Required certificate

Use a Windows code-signing certificate from a trusted Certificate Authority
that supports RSA/SHA-256 and provides an exportable `.pfx` containing the
private key.

If your provider uses a hardware token, HSM, cloud signing service, or
Microsoft Azure Artifact Signing / Trusted Signing instead of an exportable
PFX, the workflow must be adapted to that provider's signing command.

## Add the certificate to GitHub Secrets

In your repository:

Settings → Secrets and variables → Actions → New repository secret

Create:

1. `WINDOWS_CERTIFICATE_BASE64`
2. `WINDOWS_CERTIFICATE_PASSWORD`

### Convert the PFX to Base64 on Windows

Open PowerShell in the folder containing the PFX:

```powershell
[Convert]::ToBase64String(
  [IO.File]::ReadAllBytes(".\certificate.pfx")
) | Set-Content ".\certificate-base64.txt" -NoNewline
```

Open `certificate-base64.txt`, copy the entire text, and store it as the
`WINDOWS_CERTIFICATE_BASE64` GitHub secret.

Store the PFX export password as `WINDOWS_CERTIFICATE_PASSWORD`.

## Optional timestamp URL

Repository Settings → Secrets and variables → Actions → Variables

You can create:

`WINDOWS_TIMESTAMP_URL`

Use the timestamp URL recommended by your certificate provider. If omitted,
the workflow uses:

`http://timestamp.digicert.com`

## Build

Actions → Build Signed PLMS Windows Beta → Run workflow

The workflow:

- imports the trusted certificate into the GitHub Windows runner;
- injects its SHA-1 certificate thumbprint into Tauri;
- signs with SHA-256;
- timestamps the signatures;
- builds the NSIS installer;
- verifies both the PLMS application `.exe` and setup `.exe`;
- refuses to upload the artifact if either signature is invalid.

The uploaded artifact is:

`PLMS-Beta-0.1.1-SIGNED-Windows-Installer`
