#!/usr/bin/env bash
# Package the Linux build as an AppImage that runs on virtually any distro.
# Runs build_linux.sh first, then wraps dist/XM-2-WAV into an AppImage.
set -euo pipefail
cd "$(dirname "$0")/../.."   # repo root

bash packaging/linux/build_linux.sh

APPDIR="dist/XM-2-WAV.AppDir"
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin" \
         "${APPDIR}/usr/share/applications" \
         "${APPDIR}/usr/share/icons/hicolor/512x512/apps"

cp dist/XM-2-WAV "${APPDIR}/usr/bin/xm-2-wav"
cp packaging/linux/xm-2-wav.desktop "${APPDIR}/xm-2-wav.desktop"
cp packaging/linux/xm-2-wav.desktop "${APPDIR}/usr/share/applications/xm-2-wav.desktop"
cp assets/xm2wav.png "${APPDIR}/usr/share/icons/hicolor/512x512/apps/xm-2-wav.png"
cp assets/xm2wav.png "${APPDIR}/xm-2-wav.png"

cat > "${APPDIR}/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "${HERE}/usr/bin/xm-2-wav" "$@"
EOF
chmod +x "${APPDIR}/AppRun"

if command -v appimagetool >/dev/null 2>&1; then
    APPIMAGETOOL=appimagetool
else
    echo "Downloading appimagetool…"
    # Use the AppImage/appimagetool build: its embedded runtime statically links libfuse,
    # so the resulting AppImage runs on distros without libfuse2 (Ubuntu 22.04+, Fedora, Arch).
    curl -fsSL -o /tmp/appimagetool \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x /tmp/appimagetool
    APPIMAGETOOL=/tmp/appimagetool
fi

# APPIMAGE_EXTRACT_AND_RUN lets appimagetool (itself an AppImage) run on build hosts that
# lack FUSE (modern CI runners), without needing libfuse2 installed.
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "${APPIMAGETOOL}" "${APPDIR}" "dist/XM-2-WAV-x86_64.AppImage"
echo
echo "Built: dist/XM-2-WAV-x86_64.AppImage"
