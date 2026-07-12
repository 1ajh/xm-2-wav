#!/usr/bin/env bash
# Build a self-contained Linux binary (dist/XM-2-WAV) with PyInstaller.
# Bundles the system libopenmpt.so and its codecs so the result runs without libopenmpt
# installed on the target. Build on the OLDEST glibc you want to support (e.g. Ubuntu 22.04)
# for the widest distro compatibility.
#
# Requires: python3, pip, and a system libopenmpt (+ tk, portaudio for preview):
#   Arch:          sudo pacman -S libopenmpt tk portaudio python-numpy
#   Debian/Ubuntu: sudo apt install libopenmpt0 tk portaudio19-dev python3-tk
set -euo pipefail
cd "$(dirname "$0")/../.."   # repo root

python3 -m pip install --upgrade pyinstaller pillow numpy sounddevice >/dev/null
python3 tools/make_icon.py

LIBMPT=$(ldconfig -p 2>/dev/null | grep -oE '/[^ ]*libopenmpt\.so[^ ]*' | head -n1 || true)
if [ -z "${LIBMPT}" ]; then
    echo "ERROR: libopenmpt not found. Install it, e.g.:"
    echo "  Arch: sudo pacman -S libopenmpt   |   Debian/Ubuntu: sudo apt install libopenmpt0"
    exit 1
fi
echo "Bundling libopenmpt: ${LIBMPT}"

pyinstaller --noconfirm --clean --onefile --name XM-2-WAV \
    --add-data "xmwav/assets/xm2wav.png:xmwav/assets" \
    --add-data "xmwav/assets/xm2wav.ico:xmwav/assets" \
    --add-binary "${LIBMPT}:xmwav/libs" \
    xm_to_wav.py

echo
echo "Built: dist/XM-2-WAV"
