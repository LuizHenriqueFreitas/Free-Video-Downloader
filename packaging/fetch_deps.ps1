# packaging/fetch_deps.ps1
#
# Downloads the third-party binaries embedded in the Windows build and checks
# their SHA256 against the checksums published by each project:
#   - Node.js  (node.exe)            -> src/bin/node/
#   - FFmpeg   (ffmpeg.exe/ffprobe)  -> src/tools/ffmpeg/bin/
#   - yt-dlp   (yt-dlp.exe)          -> src/bin/   (only if missing or -UpdateYtDlp)
#
# Usage (from any folder):
#   powershell -ExecutionPolicy Bypass -File packaging\fetch_deps.ps1
#   powershell -ExecutionPolicy Bypass -File packaging\fetch_deps.ps1 -NodeVersion latest -FfmpegVersion latest -Force
#
# Keep this file ASCII only: Windows PowerShell 5.1 reads BOM-less files as ANSI.

param(
    # exact version ("24.21.0") or "latest" (latest release of NodeMajor)
    [string]$NodeVersion = "24.21.0",
    [int]$NodeMajor = 24,
    # exact version ("9.0.2") or "latest" - gyan.dev "essentials" build (GPLv3)
    [string]$FfmpegVersion = "9.0.2",
    # download yt-dlp.exe even when src/bin/yt-dlp.exe already exists
    [switch]$UpdateYtDlp,
    # download Node and FFmpeg again even when already present
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # Invoke-WebRequest is very slow with the progress bar
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = Split-Path -Parent $PSScriptRoot
$Src = Join-Path $Root "src"
$Cache = Join-Path $PSScriptRoot "out\cache"
New-Item -ItemType Directory -Force $Cache | Out-Null

function Get-File([string]$Url, [string]$Dest) {
    Write-Host "  downloading $Url"
    Invoke-WebRequest -Uri $Url -OutFile $Dest -UseBasicParsing
}

function Assert-Sha256([string]$Path, [string]$Expected) {
    $actual = (Get-FileHash -Algorithm SHA256 $Path).Hash.ToLower()
    if ($actual -ne $Expected.ToLower()) {
        Remove-Item $Path -Force
        throw "SHA256 mismatch for $(Split-Path -Leaf $Path): expected $Expected, got $actual"
    }
    Write-Host "  sha256 ok"
}

function Expand-Zip([string]$Zip) {
    $dest = Join-Path $Cache ([IO.Path]::GetFileNameWithoutExtension($Zip))
    if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
    Expand-Archive -Path $Zip -DestinationPath $dest
    return $dest
}

# ---------------------------------------------------------------- Node.js
$NodeDir = Join-Path $Src "bin\node"
$NodeExe = Join-Path $NodeDir "node.exe"
if ($Force -or -not (Test-Path $NodeExe)) {
    Write-Host "Node.js"
    $release = if ($NodeVersion -eq "latest") { "latest-v$NodeMajor.x" } else { "v$NodeVersion" }
    $base = "https://nodejs.org/dist/$release"
    $sums = (Invoke-WebRequest -Uri "$base/SHASUMS256.txt" -UseBasicParsing).Content
    if ($sums -is [byte[]]) { $sums = [Text.Encoding]::UTF8.GetString($sums) }
    $line = ($sums -split "`n") | Where-Object { $_ -match "\snode-v[\d.]+-win-x64\.zip\s*$" } | Select-Object -First 1
    if (-not $line -or $line -notmatch "(node-v[\d.]+-win-x64\.zip)") { throw "node win-x64 zip not found at $base" }
    $zipName = $Matches[1]
    $sha = ($line -split "\s+")[0]
    $zip = Join-Path $Cache $zipName
    if (-not (Test-Path $zip)) { Get-File "$base/$zipName" $zip }
    Assert-Sha256 $zip $sha
    $extracted = Expand-Zip $zip
    $inner = Get-ChildItem $extracted -Directory | Select-Object -First 1
    New-Item -ItemType Directory -Force $NodeDir | Out-Null
    # yt-dlp only needs node.exe as JS runtime, npm & co. are not shipped
    Copy-Item (Join-Path $inner.FullName "node.exe") $NodeDir -Force
    Copy-Item (Join-Path $inner.FullName "LICENSE") (Join-Path $NodeDir "LICENSE") -Force
    Write-Host "  -> $NodeExe ($(& $NodeExe --version))"
} else {
    Write-Host "Node.js: already present ($(& $NodeExe --version)), use -Force to replace"
}

# ---------------------------------------------------------------- FFmpeg
$FfDir = Join-Path $Src "tools\ffmpeg"
$FfBin = Join-Path $FfDir "bin"
if ($Force -or -not (Test-Path (Join-Path $FfBin "ffmpeg.exe")) -or -not (Test-Path (Join-Path $FfBin "ffprobe.exe"))) {
    Write-Host "FFmpeg"
    # gyan.dev builds are mirrored on GitHub, where the API publishes each file's sha256
    $api = if ($FfmpegVersion -eq "latest") {
        "https://api.github.com/repos/GyanD/codexffmpeg/releases/latest"
    } else {
        "https://api.github.com/repos/GyanD/codexffmpeg/releases/tags/$FfmpegVersion"
    }
    $rel = Invoke-RestMethod -Uri $api -Headers @{ "User-Agent" = "GetMediaFree-build" }
    $asset = $rel.assets | Where-Object { $_.name -like "*-essentials_build.zip" } | Select-Object -First 1
    if (-not $asset) { throw "essentials_build.zip not found at release $($rel.tag_name)" }
    if (-not $asset.digest) { throw "GitHub did not return a sha256 digest for $($asset.name)" }
    $zip = Join-Path $Cache $asset.name
    if (-not (Test-Path $zip)) { Get-File $asset.browser_download_url $zip }
    Assert-Sha256 $zip ($asset.digest -replace "^sha256:", "")
    $extracted = Expand-Zip $zip
    $inner = Get-ChildItem $extracted -Directory | Select-Object -First 1
    if (Test-Path $FfDir) { Remove-Item -Recurse -Force $FfDir }
    New-Item -ItemType Directory -Force $FfBin | Out-Null
    Copy-Item (Join-Path $inner.FullName "bin\ffmpeg.exe") $FfBin
    Copy-Item (Join-Path $inner.FullName "bin\ffprobe.exe") $FfBin
    # GPLv3 text + build README (lists the libraries and where the sources are)
    Copy-Item (Join-Path $inner.FullName "LICENSE") (Join-Path $FfDir "LICENSE.txt")
    Copy-Item (Join-Path $inner.FullName "README.txt") (Join-Path $FfDir "README.txt")
    @(
        "FFmpeg $($rel.tag_name) - essentials build by Gyan Doshi (https://www.gyan.dev/ffmpeg/builds/)",
        "License: GNU GPL v3 (see ffmpeg_LICENSE.txt). Built with libx264 and other GPL libraries.",
        "Binary: $($asset.browser_download_url)",
        "FFmpeg source code: https://ffmpeg.org/releases/ffmpeg-$($rel.tag_name).tar.xz",
        "Build scripts and library sources: https://github.com/GyanD/codexffmpeg and ffmpeg_README.txt",
        "Get Media Free runs ffmpeg.exe / ffprobe.exe unmodified, as separate programs."
    ) | Set-Content -Encoding ascii (Join-Path $FfDir "SOURCE.txt")
    Write-Host "  -> $FfBin (FFmpeg $($rel.tag_name))"
} else {
    Write-Host "FFmpeg: already present, use -Force to replace"
}

# ---------------------------------------------------------------- yt-dlp
$YtDlp = Join-Path $Src "bin\yt-dlp.exe"
if ($UpdateYtDlp -or -not (Test-Path $YtDlp)) {
    Write-Host "yt-dlp"
    $base = "https://github.com/yt-dlp/yt-dlp/releases/latest/download"
    $sums = (Invoke-WebRequest -Uri "$base/SHA2-256SUMS" -UseBasicParsing).Content
    if ($sums -is [byte[]]) { $sums = [Text.Encoding]::UTF8.GetString($sums) }
    $line = ($sums -split "`n") | Where-Object { $_ -match "\syt-dlp\.exe\s*$" } | Select-Object -First 1
    if (-not $line) { throw "yt-dlp.exe checksum not found" }
    $tmp = Join-Path $Cache "yt-dlp.exe"
    Get-File "$base/yt-dlp.exe" $tmp
    Assert-Sha256 $tmp (($line -split "\s+")[0])
    Move-Item $tmp $YtDlp -Force
    Write-Host "  -> $YtDlp ($(& $YtDlp --version))"
} else {
    Write-Host "yt-dlp: already present ($(& $YtDlp --version)), use -UpdateYtDlp to replace"
}

Write-Host "Done."
