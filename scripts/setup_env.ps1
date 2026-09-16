# AI Workflow env setup (idempotent). ASCII-only for Windows PowerShell 5.1 compat.
# Usage: powershell -ExecutionPolicy Bypass -File setup_env.ps1
$ErrorActionPreference = "Stop"

$managedPython = "C:\Users\26717\.workbuddy\binaries\python\versions\3.13.12\python.exe"
$venvDir       = "C:\Users\26717\.workbuddy\binaries\python\envs\ai-workflow"
$venvPython    = Join-Path $venvDir "Scripts\python.exe"
$deps          = @("requests", "openpyxl", "python-docx", "pypdf", "pyyaml", "duckdb", "ast-grep-cli")

# Marker definitions (N8): shared by the "skip pip when deps are present" pre-check below
# and the final import check, so they are defined only once. ASCII ONLY - Windows PowerShell 5.1
# reads this file as ANSI (cp936); non-ASCII comments merge with the next code line and null it.
$sitePkgs = Join-Path $venvDir "Lib\site-packages"
# Importable packages: marker is relative to site-packages. CLI-only packages: marker is the
# executable path relative to the venv root.
$pkgDir = @{ "requests" = "requests"; "openpyxl" = "openpyxl"; "python-docx" = "docx"; "pypdf" = "pypdf"; "pyyaml" = "yaml"; "duckdb" = "duckdb" }
# ast-grep-cli ships Scripts\ast-grep.exe only; a dist-info can survive a partial uninstall,
# so the executable is the stronger marker.
$cliDir = @{ "ast-grep-cli" = "Scripts\ast-grep.exe" }

Write-Host "=== AI Workflow env setup ==="

# 1. managed python
if (-not (Test-Path $managedPython)) {
    Write-Host "[FAIL] managed python not found: $managedPython" -ForegroundColor Red
    exit 1
}
Write-Host "[ OK ] managed python found"

# 2. create venv if missing
if (-not (Test-Path $venvPython)) {
    Write-Host "[....] creating venv: $venvDir"
    & $managedPython -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] venv creation failed" -ForegroundColor Red; exit 1 }
} else {
    Write-Host "[ OK ] venv exists, skip"
}

# 3. install deps (idempotent). Success is judged by the import check below (step 4),
#    not by pip exit code (exit codes are unreliable in some hosted shells).
# N8: fast marker pre-check; if every marker is present, skip pip install entirely
#     (avoids a slow child process and a needless network round trip on every run).
$allPresent = $true
foreach ($d in $deps) {
    $marker = $null
    if (-not [string]::IsNullOrEmpty($pkgDir[$d]))     { $marker = Join-Path $sitePkgs $pkgDir[$d] }
    elseif (-not [string]::IsNullOrEmpty($cliDir[$d])) { $marker = Join-Path $venvDir  $cliDir[$d] }
    if ([string]::IsNullOrEmpty($marker) -or -not (Test-Path $marker)) { $allPresent = $false; break }
}
if ($allPresent) {
    Write-Host "[ OK ] all deps present, skipping pip install" -ForegroundColor Green
} else {
    Write-Host "[....] pip install $($deps -join ' ')"
    $pipLog = Join-Path ([System.IO.Path]::GetTempPath()) "aiwf_pip_debug.log"
    & $venvPython -m pip install --disable-pip-version-check $deps 1> $pipLog 2>&1
    if (Test-Path $pipLog) {
        $errLines = (Get-Content $pipLog) | Where-Object { $_ -match "error|ERROR|Traceback" }
        if ($errLines) { Write-Host "[WARN] pip reported issues, see $pipLog" -ForegroundColor Yellow }
        Remove-Item $pipLog -ErrorActionSilentlyContinue
    }
}

# 4. import check via site-packages dirs (no child process needed, host-proof).
#    marker definitions moved to the top of this script (shared with the N8 pre-check).
$failedList = @()
foreach ($d in $deps) {
    $marker = $null
    if (-not [string]::IsNullOrEmpty($pkgDir[$d]))     { $marker = Join-Path $sitePkgs $pkgDir[$d] }
    elseif (-not [string]::IsNullOrEmpty($cliDir[$d])) { $marker = Join-Path $venvDir  $cliDir[$d] }
    # A dependency with no marker must fail loudly. Previously duckdb / ast-grep-cli had no
    # mapping, so the child path was empty; Join-Path returns the PARENT path when the child
    # path is empty, making Test-Path always True -> a fake [ OK ].
    # [v2.5.1] Fixed: unmapped entries are a hard failure, never a silent pass.
    if ([string]::IsNullOrEmpty($marker)) {
        Write-Host "[FAIL] $d has no marker in pkgDir/cliDir (add one; silent pass is forbidden)" -ForegroundColor Red
        $failedList += $d
        continue
    }
    if (Test-Path $marker) {
        Write-Host "[ OK ] $d"
    } else {
        Write-Host "[FAIL] $d not found: $marker" -ForegroundColor Red
        $failedList += $d
    }
}
if ($failedList.Count -gt 0) { exit 1 }

# 5. AI key hint
if ($env:AI_API_KEY) { Write-Host "[INFO] AI_API_KEY is set" } else { Write-Host "[INFO] AI_API_KEY not set (only needed for AI calls)" }

Write-Host "=== Setup complete ===" -ForegroundColor Green
