#!/usr/bin/env bash
# Build XM-2-WAV.app (and a .dmg) on macOS with PyInstaller.
# Bundles libopenmpt.dylib from Homebrew so the .app is self-contained.
#
# Requires: Homebrew, Python 3 (python.org build recommended for a portable .app).
#
# NOTE ON GATEKEEPER: an unsigned .app shows "unidentified developer" on first launch.
# Users can right-click the app > Open to run it. To ship without that warning you must
# code-sign and notarize with an Apple Developer ID (see the comment block at the bottom).
set -euo pipefail
cd "$(dirname "$0")/../.."   # repo root

python3 -m pip install --upgrade pyinstaller pillow numpy sounddevice >/dev/null
python3 tools/make_icon.py

if ! command -v brew >/dev/null 2>&1; then
    echo "ERROR: Homebrew is required (https://brew.sh)."; exit 1
fi
brew list libopenmpt >/dev/null 2>&1 || brew install libopenmpt
LIBMPT="$(brew --prefix libopenmpt)/lib/libopenmpt.dylib"
echo "Bundling libopenmpt: ${LIBMPT}"

pyinstaller --noconfirm --clean --windowed --name "XM-2-WAV" \
    --icon assets/xm2wav.icns \
    --osx-bundle-identifier wtf.ajh.xm2wav \
    --add-data "xmwav/assets/xm2wav.png:xmwav/assets" \
    --add-data "xmwav/assets/xm2wav.ico:xmwav/assets" \
    --add-binary "${LIBMPT}:xmwav/libs" \
    xm_to_wav.py

APP="dist/XM-2-WAV.app"
DMG="dist/XM-2-WAV.dmg"
rm -f "${DMG}"
hdiutil create -volname "XM-2-WAV" -srcfolder "${APP}" -ov -format UDZO "${DMG}"

echo
echo "Built: ${APP}  and  ${DMG}"

# ---- Optional: sign & notarize (requires an Apple Developer ID) ----
# codesign --deep --force --options runtime \
#     --sign "Developer ID Application: Your Name (TEAMID)" "${APP}"
# xcrun notarytool submit "${DMG}" --apple-id you@example.com \
#     --team-id TEAMID --password APP_SPECIFIC_PASSWORD --wait
# xcrun stapler staple "${APP}"
