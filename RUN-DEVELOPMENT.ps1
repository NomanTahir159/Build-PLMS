$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) { throw "Install Rust/Cargo first." }
& cargo tauri --version
if ($LASTEXITCODE -ne 0) {
  & cargo install tauri-cli --version 2.12.0 --locked
  if ($LASTEXITCODE -ne 0) { throw "Tauri CLI installation failed." }
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Install Python 3.13 first." }
python backend/build_resources.py
if ($LASTEXITCODE -ne 0) { throw "PLMS backend resource packaging failed." }
Push-Location (Join-Path $PSScriptRoot "src-tauri")
try {
  & cargo tauri dev
  if ($LASTEXITCODE -ne 0) { throw "PLMS development launch failed." }
} finally { Pop-Location }
