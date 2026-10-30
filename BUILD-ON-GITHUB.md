# Build Medicsoft PLMS on GitHub

1. Extract this package into your repository, replacing the previous package files. Include `.github/workflows/build-windows.yml` and `scripts/publish-release.cjs`. Use GitHub Desktop or `git add -A` to include the hidden `.github` folder.
2. Push the files to GitHub.
3. Open **Actions → Build Medicsoft PLMS → Run workflow**.
4. Once successful, open the download link in the run’s **Summary**, or open the repository’s **Releases** page.
5. Open **Medicsoft PLMS 1.0.2 - Build …**, expand **Assets**, and download the setup EXE and its `.sha256` checksum.

The installer is delivered through GitHub Releases; the Actions Artifacts section is not used. Each successful run/attempt creates a separate release for its exact commit. Existing releases are not replaced or deleted. No personal access token is required; the workflow requests `contents: write` for its built-in token. Organization/repository policy must permit that permission.

For a local Windows build, use `BUILD PLMS.bat` as before. The source ZIP itself is not a compiled installer.

For every edited app package, run `node scripts/bump-version.cjs` once before
building. It increments the patch number and updates the installer configuration,
Node package/lock metadata, Rust package version and About build together.
Rebuilding the same unchanged source retains its version.
