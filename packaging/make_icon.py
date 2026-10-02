# packaging/make_icon.py
#
# Builds src/assets/icon.ico from the high resolution artwork
# website/assets/app-icon.png, with every size Windows uses (taskbar,
# Explorer, shortcuts, installer). An .ico with only 256px gets scaled down by
# Windows itself and looks blurry at 16/32px.
#
# Run again whenever the artwork changes:
#   python packaging/make_icon.py

import os
import struct
import sys

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QImage

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCE = os.path.join(ROOT, "website", "assets", "app-icon.png")
TARGET = os.path.join(ROOT, "src", "assets", "icon.ico")
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def png_bytes(image, size):
    scaled = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    scaled.save(buffer, "PNG")
    return scaled.width(), scaled.height(), bytes(data)


def main():
    image = QImage(SOURCE)
    if image.isNull():
        sys.exit(f"Could not read {SOURCE}")
    image = image.convertToFormat(QImage.Format_ARGB32)

    entries = [png_bytes(image, size) for size in SIZES]

    # ICO = header + one 16 byte directory entry per image + PNG data
    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = len(header) + 16 * len(entries)
    directory, blobs = b"", b""
    for width, height, data in entries:
        # 256 is written as 0 in the one byte width/height fields
        directory += struct.pack("<BBBBHHII", width % 256, height % 256, 0, 0, 1, 32, len(data), offset)
        blobs += data
        offset += len(data)

    with open(TARGET, "wb") as f:
        f.write(header + directory + blobs)
    print(f"{TARGET}: {', '.join(str(s) for s in SIZES)} px")


if __name__ == "__main__":
    main()
