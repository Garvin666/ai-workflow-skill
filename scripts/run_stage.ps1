# AI Workflow runner: status check + invoke venv python via &. ASCII-only for PS 5.1.
# Usage: powershell -ExecutionPolicy Bypass -File run_stage.ps1 <script.py> [args...]
# Example: run_stage.ps1 http_fetch.py https://example.com --out page.html
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$ScriptArgs
)
$ErrorActionPreference = "Stop"

$venvPython = "C:\Users\26717\.workbuddy\binaries\python\envs\ai-workflow\Scripts\python.exe"
$skillDir   = Split-Path -Parent $PSScriptRoot
$target     = if (Test-Path $Script) { (Resolve-Path $Script).Path } else { Join-Path $skillDir "scripts\$Script" }

Write-Host "=== AI Workflow status check ==="
$venvOk   = Test-Path $venvPython
$scriptOk = Test-Path $target
$keyOk    = [bool]$env:AI_API_KEY
Write-Host ("[ {0} ] venv: {1}" -f $(if ($venvOk) {"OK"} else {"FAIL"}), $venvPython)
Write-Host ("[ {0} ] script: {1}" -f $(if ($scriptOk) {"OK"} else {"FAIL"}), $target)
Write-Host ("[ {0} ] AI_API_KEY (only needed for AI calls)" -f $(if ($keyOk) {"OK"} else {"--"}))
if (-not $venvOk)   { Write-Host "venv not ready, run setup_env.ps1 first" -ForegroundColor Red; exit 1 }
if (-not $scriptOk) { Write-Host "script not found: $target" -ForegroundColor Red; exit 1 }

# Execute with a post-flight check. In some hosts a native child process never runs,
# and $LASTEXITCODE keeps a stale value -> the wrapper would report success for a no-op.
# Clear it first, then treat "still empty after the call" as a hard failure.
$global:LASTEXITCODE = $null
& $venvPython $target @ScriptArgs
$code = $LASTEXITCODE
if ($null -eq $code) {
    Write-Host "[FAIL] child produced no exit code - the native process probably did not run." -ForegroundColor Red
    Write-Host "       Do NOT trust this run. Call the venv interpreter directly instead (ops.md section 1)." -ForegroundColor Red
    exit 1
}
if ($code -ne 0) { Write-Host "[FAIL] $target exited with code $code" -ForegroundColor Red }
exit $code
