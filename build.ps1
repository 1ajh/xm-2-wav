# Build a standalone Windows .exe with PyInstaller.
# Produces dist\XM-2-WAV.exe (single file, no Python install needed to run).
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$libs = Join-Path $PSScriptRoot 'xmwav\libs'
if (-not (Test-Path $libs)) { throw "Missing bundled DLL folder: $libs" }

$icon = Join-Path $PSScriptRoot 'assets\xm2wav.ico'
if (-not (Test-Path $icon)) { python tools\make_icon.py }

# Bundle libopenmpt.dll and its codec DLLs into xmwav/libs inside the exe.
$addbin = @()
Get-ChildItem $libs -Filter *.dll | ForEach-Object {
    $addbin += @('--add-binary', ($_.FullName + ';xmwav/libs'))
}

$pkgAssets = Join-Path $PSScriptRoot 'xmwav\assets'
python -m PyInstaller --noconfirm --clean --onefile --windowed --name 'XM-2-WAV' `
    --icon $icon `
    --add-data ((Join-Path $pkgAssets 'xm2wav.ico') + ';xmwav/assets') `
    --add-data ((Join-Path $pkgAssets 'xm2wav.png') + ';xmwav/assets') `
    @addbin `
    xm_to_wav.py

Write-Output ''
Write-Output 'Built: dist\XM-2-WAV.exe'
