# packaging/build.ps1
#
# Full Windows build: dependencies -> tests -> PyInstaller -> checks -> installer.
#   powershell -ExecutionPolicy Bypass -File packaging\build.ps1
#
# Output:
#   packaging/out/dist/GetMediaFree/                    app folder (runs without installing)
#   packaging/out/installer/GetMediaFree-<ver>-Setup.exe
#
# Needs: Python with src/requirements.txt installed, and Inno Setup 6 for the
# installer step (winget install JRSoftware.InnoSetup).
# Keep this file ASCII only: Windows PowerShell 5.1 reads BOM-less files as ANSI.

param(
    [switch]$SkipFetch,
    [switch]$SkipTests,
    [switch]$SkipInstaller,
    # also refresh src/bin/yt-dlp.exe to the latest release before packing
    [switch]$UpdateYtDlp
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Out = Join-Path $PSScriptRoot "out"
$Dist = Join-Path $Out "dist\GetMediaFree"

function Step([string]$Name) { Write-Host ""; Write-Host "==> $Name" -ForegroundColor Cyan }

function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed (exit code $LASTEXITCODE)" }
}

Push-Location $Root
try {
    $version = [regex]::Match(
        (Get-Content -Raw "src\services\updater.py"), '(?m)^APP_VERSION\s*=\s*"([^"]+)"'
    ).Groups[1].Value
    if (-not $version) { throw "APP_VERSION not found at src\services\updater.py" }
    Write-Host "Get Media Free $version"

    if (-not $SkipFetch) {
        Step "Third-party binaries"
        $fetchArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "fetch_deps.ps1"))
        if ($UpdateYtDlp) { $fetchArgs += "-UpdateYtDlp" }
        Invoke-Checked "powershell" $fetchArgs
    }

    if (-not $SkipTests) {
        Step "Unit tests"
        Invoke-Checked "python" @("-m", "pytest", "src/tests", "-q", "-p", "no:cacheprovider")
    }

    Step "PyInstaller"
    Invoke-Checked "python" @(
        "-m", "PyInstaller", "packaging\GetMediaFree.spec", "--noconfirm", "--clean",
        "--workpath", (Join-Path $Out "work"), "--distpath", (Join-Path $Out "dist")
    )

    Step "Checking embedded binaries"
    $internal = Join-Path $Dist "_internal"
    $checks = @(
        @{ Name = "yt-dlp";  Exe = "bin\yt-dlp.exe";              Arg = "--version" },
        @{ Name = "node";    Exe = "bin\node\node.exe";           Arg = "--version" },
        @{ Name = "ffmpeg";  Exe = "tools\ffmpeg\bin\ffmpeg.exe";  Arg = "-version" },
        @{ Name = "ffprobe"; Exe = "tools\ffmpeg\bin\ffprobe.exe"; Arg = "-version" }
    )
    foreach ($c in $checks) {
        $path = Join-Path $internal $c.Exe
        if (-not (Test-Path $path)) { throw "$($c.Name) missing from the bundle: $path" }
        # full output first: "| Select-Object -First 1" would stop the process early
        $output = @(& $path $c.Arg)
        if ($LASTEXITCODE -ne 0) { throw "$($c.Name) does not run: $path" }
        $line = $output[0]
        Write-Host ("  {0,-8} {1}" -f $c.Name, $line)
    }
    $size = (Get-ChildItem -Recurse $Dist | Measure-Object -Sum Length).Sum / 1MB
    Write-Host ("  app folder: {0:N0} MB" -f $size)

    if (-not $SkipInstaller) {
        Step "Installer (Inno Setup)"
        $iscc = (Get-Command "iscc.exe" -ErrorAction SilentlyContinue).Source
        if (-not $iscc) {
            $iscc = @(
                "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
                "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
                "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
            ) | Where-Object { Test-Path $_ } | Select-Object -First 1
        }
        if (-not $iscc) {
            throw "Inno Setup 6 not found. Install it (winget install JRSoftware.InnoSetup) or use -SkipInstaller."
        }
        Invoke-Checked $iscc @("/Q", "/DAppVersion=$version", (Join-Path $PSScriptRoot "installer.iss"))
        $setup = Join-Path $Out "installer\GetMediaFree-$version-Setup.exe"
        Write-Host ("  {0} ({1:N0} MB)" -f $setup, ((Get-Item $setup).Length / 1MB))
    }

    Write-Host ""
    Write-Host "Build finished." -ForegroundColor Green
}
finally {
    Pop-Location
}
