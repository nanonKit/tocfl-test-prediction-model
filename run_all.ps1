<#
.SYNOPSIS
  Rebuild everything in data/interim from raw files: runs src/01 ... src/07 in order.
.EXAMPLE
  .\run_all.ps1            # all steps
  .\run_all.ps1 -From 04   # start at step 04 (earlier outputs must already exist)
#>
param([string]$From = "01")

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot      # repo root, whatever folder you call it from

$steps = @(
    "01_extract_text.py",
    "02_parse_listening.py",
    "03_parse_answer_keys.py",
    "04_parse_booklets.py",
    "05_ocr_images.py",
    "05b_check_ocr.py",
    "06_clean_vocab.py",
    "07_segment.py",
    "08_build_db.py"
)

uv run ruff check src/
if ($LASTEXITCODE -ne 0) { throw "ruff failed - fix lint errors first" }

foreach ($step in $steps | Where-Object { $_ -ge $From }) {
    Write-Host "`n=== $step ===" -ForegroundColor Cyan
    $timer = [Diagnostics.Stopwatch]::StartNew()
    uv run python "src/$step"
    if ($LASTEXITCODE -ne 0) { throw "$step failed (exit $LASTEXITCODE) - later steps not run" }
    Write-Host ("done in {0:n0} s" -f $timer.Elapsed.TotalSeconds) -ForegroundColor DarkGray
}
Write-Host "`nAll steps finished." -ForegroundColor Green