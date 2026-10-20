$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Fail([string]$Message) {
  Write-Host ""
  Write-Host "[ERROR] $Message" -ForegroundColor Red
  exit 1
}

function Run-Native([string]$Exe, [string[]]$Arguments) {
  & $Exe @Arguments
  if ($LASTEXITCODE -ne 0) {
    Fail "$Exe failed with exit code $LASTEXITCODE."
  }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "      Medicsoft PLMS 1.0.0 - Cargo/Tauri Windows Builder" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The installer is built with Rust/Cargo; Node is optional for frontend verification." -ForegroundColor Green
Write-Host ""

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
  Fail "Rust/Cargo is not installed. Install Rust from https://rustup.rs/ and run this file again."
}
if (-not (Get-Command rustup -ErrorAction SilentlyContinue)) {
  Fail "rustup is not available."
}
if (-not (Get-Command rustc -ErrorAction SilentlyContinue)) {
  Fail "rustc is not available."
}

Write-Host "Rust:" -NoNewline
rustc -V
Write-Host "Cargo:" -NoNewline
cargo -V
Write-Host ""

Write-Host "[1/4] Selecting Windows MSVC Rust toolchain..." -ForegroundColor Yellow
Run-Native "rustup" @("default","stable-x86_64-pc-windows-msvc")

Write-Host ""
Write-Host "[2/4] Checking Tauri Cargo CLI..." -ForegroundColor Yellow

$tauriOK = $false
try {
  & cargo tauri --version
  if ($LASTEXITCODE -eq 0) {
    $tauriOK = $true
  }
} catch {
  $tauriOK = $false
}

if (-not $tauriOK) {
  Write-Host ""
  Write-Host "Tauri CLI is not installed for Cargo." -ForegroundColor Yellow
  Write-Host "Installing tauri-cli 2.12.0. This one-time step can take several minutes..." -ForegroundColor Yellow
  Run-Native "cargo" @("install","tauri-cli","--version","2.12.0","--locked")
}

Write-Host ""
Write-Host "[3/4] Verifying Tauri CLI..." -ForegroundColor Yellow
Run-Native "cargo" @("tauri","--version")

Write-Host ""
Write-Host "[4/4] Building PLMS Windows installer..." -ForegroundColor Yellow
Write-Host "The first build can take several minutes because Rust compiles dependencies." -ForegroundColor DarkGray
Write-Host ""

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Fail "Install Python 3.13 first." }
if (Get-Command node -ErrorAction SilentlyContinue) { Run-Native "node" @("frontend/verify.cjs") }
else { Write-Host "Frontend verification runs automatically in GitHub Actions." -ForegroundColor Yellow }
Run-Native "python" @("backend/verify.py")
Run-Native "python" @("backend/build_resources.py")

# Build from project root. Tauri automatically uses src-tauri/tauri.conf.json.
Run-Native "cargo" @("tauri","build","--bundles","nsis")

$bundle = ".\src-tauri\target\release\bundle\nsis"
if (-not (Test-Path $bundle)) {
  Fail "Tauri completed but the NSIS installer output folder was not found."
}

$installers = Get-ChildItem $bundle -Filter "*.exe" -File -ErrorAction SilentlyContinue
if (-not $installers) {
  Fail "The NSIS folder exists but no .exe installer was created."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "                    BUILD SUCCESSFUL" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Installer:" -ForegroundColor Green
foreach ($installer in $installers) {
  Write-Host ("  " + $installer.FullName)
}
Write-Host ""

exit 0
