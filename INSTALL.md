# Installing XM-2-WAV

## For end users (prebuilt downloads)

| OS | Download | Run |
|----|----------|-----|
| **Windows 10/11** | `XM-2-WAV.exe` (or `XM-2-WAV-Setup.exe`) | Double-click. SmartScreen may warn (unsigned) → *More info → Run anyway*. |
| **macOS** | `XM-2-WAV-arm64.dmg` (Apple Silicon) / `XM-2-WAV-x86_64.dmg` (Intel) | Drag to Applications. First launch: **right-click → Open** (unsigned/un-notarised). |
| **Linux (any distro)** | `XM-2-WAV-x86_64.AppImage` | `chmod +x XM-2-WAV-x86_64.AppImage && ./XM-2-WAV-x86_64.AppImage` |

### Arch Linux (AUR)

```bash
yay -S xm-2-wav        # or: paru -S xm-2-wav
```

### Any OS with Python — pip / pipx

The Windows wheel bundles libopenmpt; on **macOS/Linux install libopenmpt + Tk first**:

```bash
# macOS:         brew install libopenmpt
# Arch:          sudo pacman -S libopenmpt tk python-numpy
# Debian/Ubuntu: sudo apt install libopenmpt0 python3-tk
# Fedora:        sudo dnf install libopenmpt python3-tkinter

pipx install "xm-2-wav[preview]"     # [preview] adds sounddevice for audio preview
xm-2-wav                             # launch the GUI
xm-2-wav-cli song.xm --bpm 140       # command line
```

> If libopenmpt can't be found, set `XMWAV_LIBOPENMPT=/path/to/libopenmpt.so` (or `.dylib`).

---

## For packagers / developers (building the downloads)

You need each OS (or the GitHub Actions CI, which builds all three automatically — see
`.github/workflows/build.yml`). From a checkout:

### Windows → `dist\XM-2-WAV.exe` (+ installer)

```powershell
pip install -r requirements.txt
./build.ps1
# Optional installer: compile packaging\windows\xm-2-wav.iss with Inno Setup 6 (ISCC.exe)
```

### macOS → `dist/XM-2-WAV.app` + `dist/XM-2-WAV.dmg`

```bash
brew install libopenmpt
pip install pyinstaller pillow numpy sounddevice
bash packaging/macos/build_app.sh
```

To ship without the Gatekeeper warning, code-sign + notarise with an Apple Developer ID
(commands are in `packaging/macos/build_app.sh`).

### Linux → `dist/XM-2-WAV-x86_64.AppImage`

```bash
sudo pacman -S libopenmpt tk portaudio        # or the apt/dnf equivalents
pip install pyinstaller pillow numpy sounddevice
bash packaging/linux/build_appimage.sh        # or build_linux.sh for a bare binary
```

Build on the **oldest glibc** you want to support (e.g. Ubuntu 22.04) for the widest
compatibility.

### Python wheel / sdist (for PyPI or the AUR)

```bash
pip install build
python -m build          # -> dist/*.whl and dist/*.tar.gz
```

### Publishing

- **GitHub Releases:** push a tag `vX.Y.Z`; the CI builds all platforms and attaches them
  to a Release automatically. Link downloads to `…/releases/latest/download/<file>`.
- **AUR:** update `source`/`sha256sums` in `packaging/linux/PKGBUILD`, run
  `makepkg --printsrcinfo > .SRCINFO`, and push to the AUR.
