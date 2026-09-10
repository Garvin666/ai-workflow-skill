# AI Workflow env setup (idempotent). ASCII-only for Windows PowerShell 5.1 compat.
# Usage: powershell -ExecutionPolicy Bypass -File setup_env.ps1
$ErrorActionPreference = "Stop"

$managedPython = "C:\Users\26717\.workbuddy\binaries\python\versions\3.13.12\python.exe"
$venvDir       = "C:\Users\26717\.workbuddy\binaries\python\envs\ai-workflow"
$venvPython    = Join-Path $venvDir "Scripts\python.exe"
$deps          = @("requests", "openpyxl", "python-docx", "pypdf", "pyyaml", "duckdb", "ast-grep-cli")

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

# 3. install deps (idempotent). Success is judged by the import check below,
#    not by pip exit code (exit codes are unreliable in some hosted shells).
Write-Host "[....] pip install $($deps -join ' ')"
$pipLog = Join-Path $PSScriptRoot "pip_debug.log"
& $venvPython -m pip install --disable-pip-version-check $deps 1> $pipLog 2>&1
if (Test-Path $pipLog) {
    $errLines = (Get-Content $pipLog) | Where-Object { $_ -match "error|ERROR|Traceback" }
    if ($errLines) { Write-Host "[WARN] pip reported issues, see $pipLog" -ForegroundColor Yellow }
    Remove-Item $pipLog -ErrorAction SilentlyContinue
}

# 4. import check via site-packages dirs (no child process needed, host-proof)
$sitePkgs = Join-Path $venvDir "Lib\site-packages"
$pkgDir = @{ "requests" = "requests"; "openpyxl" = "openpyxl"; "python-docx" = "docx"; "pypdf" = "pypdf"; "pyyaml" = "yaml" }
$failedList = @()
foreach ($d in $deps) {
    $dirName = $pkgDir[$d]
    if (Test-Path (Join-Path $sitePkgs $dirName)) {
        Write-Host "[ OK ] $d"
    } else {
        Write-Host "[FAIL] $d not found under $sitePkgs" -ForegroundColor Red
        $failedList += $d
    }
}
if ($failedList.Count -gt 0) { exit 1 }

# 5. AI key hint
if ($env:AI_API_KEY) { Write-Host "[INFO] AI_API_KEY is set" } else { Write-Host "[INFO] AI_API_KEY not set (only needed for AI calls)" }

Write-Host "=== Setup complete ===" -ForegroundColor Green
