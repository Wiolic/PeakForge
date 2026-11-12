<#
Build script shared by this machine and CI. Run from the repo root:
    powershell -ExecutionPolicy Bypass -File packaging\build.ps1 [-SkipTests] [-SkipInstaller] [-LimitMB 450] [-Python python]
Steps:
  1. separate build environment .venv-build (the everyday environment is untouched): pip install -e .[dev] pyinstaller;
     MKL is removed (numpy/scipy fall back to their bundled BLAS)
  2. pytest in the build environment (proves the numbers do not depend on what was removed)
  3. PyInstaller build, then the size guard (size_report.py)
  4. smoke test of the packaged program (packaging\smoke.py: selftest, a fit compared with reference values, exports,
     diagnostics, MCP handshake)
  5. Inno Setup (iscc) -> installer, plus a portable zip and SHA256SUMS.txt
Any failing step stops the script with a non-zero exit code.
#>
param(
    [switch]$SkipTests,
    [switch]$SkipInstaller,
    [double]$LimitMB = 450,
    [string]$Python = "python",
    [string]$Iscc = ""          # path of ISCC.exe; otherwise searched on PATH, in Program Files and $env:INNO_SETUP_DIR
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Run($exe, [string[]]$a) {
    $ErrorActionPreference = "Continue"      # native programs writing to stderr (pip warnings) are not errors; the exit code decides
    & $exe @a
    if ($LASTEXITCODE -ne 0) { throw "failed ($LASTEXITCODE): $exe $($a -join ' ')" }
}

Step "1/5 build environment .venv-build"
$venv = Join-Path $root ".venv-build"
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) { Run $Python @("-m", "venv", $venv) }
$py = Join-Path $venv "Scripts\python.exe"
Run $py @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel", "--quiet")
Run $py @("-m", "pip", "install", "-e", ".[dev]", "pyinstaller", "--quiet")
$ErrorActionPreference = "Continue"; & $py -m pip uninstall -y mkl_fft mkl 2>$null; $ErrorActionPreference = "Stop"   # fails harmlessly when absent
$left = & $py -m pip list --format=freeze | Select-String -Pattern "^(mkl|mkl_fft)=="
if ($left) { throw "mkl is still in the build environment: $left" }

if (-not $SkipTests) {
    Step "2/5 pytest (offscreen)"
    $env:QT_QPA_PLATFORM = "offscreen"
    Run $py @("-m", "pytest", "-q")
} else { Write-Host "tests skipped (-SkipTests): numbers not verified" -ForegroundColor Yellow }

Step "3/5 PyInstaller + size guard"
Run $py @("-m", "PyInstaller", "packaging\peakforge.spec", "--noconfirm", "--distpath", "dist", "--workpath", "build\pyi")
Run $py @("packaging\size_report.py", "dist\PeakForge", "--limit-mb", "$LimitMB")

Step "4/5 smoke test (packaged program)"
Run $py @("packaging\smoke.py", "dist\PeakForge")

$ver = (& $py -c "import peakforge;print(peakforge.__version__)").Trim()
if (-not $SkipInstaller) {
    Step "5/5 installer and portable zip (version $ver)"
    $isccCmd = Get-Command iscc -ErrorAction SilentlyContinue
    $cand = @($Iscc, "$env:INNO_SETUP_DIR\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "${env:ProgramFiles}\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")
    $isccPath = if ($isccCmd) { $isccCmd.Source } else { $cand | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1 }
    if (-not $isccPath) { throw "Inno Setup (ISCC.exe) not found. Install Inno Setup 6 or pass -SkipInstaller." }
    Run $isccPath @("/DAppVersion=$ver", "packaging\peakforge.iss")
    $zip = "dist\PeakForge-$ver-win64-portable.zip"
    if (Test-Path $zip) { Remove-Item $zip }
    Compress-Archive -Path "dist\PeakForge" -DestinationPath $zip
    Get-ChildItem dist\PeakForge-* | ForEach-Object { "{0,8:N1} MB  {1}" -f ($_.Length / 1MB), $_.Name }
    Get-ChildItem dist\PeakForge-$ver-* | Get-FileHash -Algorithm SHA256 | ForEach-Object { "$($_.Hash.ToLower())  $(Split-Path $_.Path -Leaf)" } | Set-Content dist\SHA256SUMS.txt -Encoding ascii
}
Write-Host "`nBuild finished." -ForegroundColor Green
