# -*- mode: python ; coding: utf-8 -*-
# packaging/GetMediaFree.spec
#
# PyInstaller recipe of the Windows build ("onedir": GetMediaFree.exe + _internal/).
# Run it through packaging/build.ps1, or by hand from the repository root:
#   python -m PyInstaller packaging/GetMediaFree.spec --noconfirm --clean
#       --workpath packaging/out/work --distpath packaging/out/dist
#
# Why onedir and not onefile: faster start (nothing extracted to %TEMP% on
# every run), fewer antivirus false positives, and the Qt DLLs stay
# replaceable files, as the LGPL asks. The installer packs it in one Setup.exe.
#
# Embedded binaries come from packaging/fetch_deps.ps1. Inside the bundle
# they keep the same relative paths used at dev mode (see core/utils.py):
#   bin/yt-dlp.exe, bin/node/node.exe, tools/ffmpeg/bin/ffmpeg.exe + ffprobe.exe

import os
import re
import shutil
import sys
import importlib.metadata

from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct,
    VarFileInfo, VarStruct,
)

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(SPECPATH, "out")

APP_NAME = "GetMediaFree"


def required(*parts):
    path = os.path.join(*parts)
    if not os.path.exists(path):
        raise SystemExit(f"Missing: {path}\nRun packaging/fetch_deps.ps1 first.")
    return path


# single version source: APP_VERSION at src/services/updater.py
with open(os.path.join(SRC, "services", "updater.py"), encoding="utf-8") as f:
    APP_VERSION = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', f.read(), re.M).group(1)
version_numbers = tuple((list(map(int, re.findall(r"\d+", APP_VERSION))) + [0, 0, 0, 0])[:4])


# ---------------------------------------------------------------- licenses
# everything collected in one folder, shipped as _internal/licenses/
LICENSES = os.path.join(OUT, "licenses")
shutil.rmtree(LICENSES, ignore_errors=True)
os.makedirs(os.path.join(LICENSES, "python-packages"))

for name in os.listdir(os.path.join(ROOT, "licenses")):
    shutil.copy2(os.path.join(ROOT, "licenses", name), LICENSES)
shutil.copy2(os.path.join(ROOT, "LICENSE"), os.path.join(LICENSES, "GetMediaFree_LICENSE.txt"))
shutil.copy2(os.path.join(sys.base_prefix, "LICENSE.txt"), os.path.join(LICENSES, "python_LICENSE.txt"))
# texts of the exact binaries being shipped (replace the repository copies)
shutil.copy2(required(SRC, "tools", "ffmpeg", "LICENSE.txt"), os.path.join(LICENSES, "ffmpeg_LICENSE.txt"))
shutil.copy2(required(SRC, "tools", "ffmpeg", "README.txt"), os.path.join(LICENSES, "ffmpeg_README.txt"))
shutil.copy2(required(SRC, "tools", "ffmpeg", "SOURCE.txt"), os.path.join(LICENSES, "ffmpeg_SOURCE.txt"))
shutil.copy2(required(SRC, "bin", "node", "LICENSE"), os.path.join(LICENSES, "node_LICENSE.txt"))

# license / notice files from the wheels of the pure python dependencies
for dist_name in ("requests", "urllib3", "certifi", "idna", "charset_normalizer"):
    dist = importlib.metadata.distribution(dist_name)
    target = os.path.join(LICENSES, "python-packages", f"{dist_name}-{dist.version}")
    os.makedirs(target)
    for file in dist.files or []:
        if "/licenses/" in str(file).replace("\\", "/"):
            shutil.copy2(file.locate(), target)


# ---------------------------------------------------------------- bundle
datas = [
    (os.path.join(SRC, "assets"), "assets"),
    (required(SRC, "bin", "yt-dlp.exe"), "bin"),
    (required(SRC, "bin", "node", "node.exe"), os.path.join("bin", "node")),
    (required(SRC, "tools", "ffmpeg", "bin", "ffmpeg.exe"), os.path.join("tools", "ffmpeg", "bin")),
    (required(SRC, "tools", "ffmpeg", "bin", "ffprobe.exe"), os.path.join("tools", "ffmpeg", "bin")),
    (LICENSES, "licenses"),
]

a = Analysis(
    [os.path.join(SRC, "main.py")],
    pathex=[SRC],
    datas=datas,
    # dev / test only - keeps them out even if something imports them indirectly
    excludes=["tkinter", "pytest", "_pytest", "tests"],
    noarchive=False,
)

pyz = PYZ(a.pure)

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_numbers, prodvers=version_numbers),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("CompanyName", "Get Media Free"),
            StringStruct("FileDescription", "Get Media Free"),
            StringStruct("FileVersion", APP_VERSION),
            StringStruct("InternalName", APP_NAME),
            StringStruct("LegalCopyright", "MIT License"),
            StringStruct("OriginalFilename", f"{APP_NAME}.exe"),
            StringStruct("ProductName", "Get Media Free"),
            StringStruct("ProductVersion", APP_VERSION),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
    ],
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    icon=os.path.join(SRC, "assets", "icon.ico"),
    version=version_info,
    console=False,
    # UPX-packed executables trigger antivirus false positives
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name=APP_NAME,
    upx=False,
)
