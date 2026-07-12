"""Thin ctypes wrapper around the bundled libopenmpt for faithful module rendering.

We only expose what this app needs: probe a module's tempo/geometry, and render the
whole song once to 32-bit float stereo samples.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import platform
import sys
from ctypes import c_char_p, c_double, c_int, c_int32, c_size_t, c_void_p, byref
from typing import Callable, List, Optional, Tuple

import numpy as np

# Render-parameter indices (from libopenmpt.h).
RENDER_MASTERGAIN_MILLIBEL = 1
RENDER_STEREOSEPARATION_PERCENT = 2
RENDER_INTERPOLATIONFILTER_LENGTH = 3
RENDER_VOLUMERAMPING_STRENGTH = 4

# Interpolation filter lengths: 1 = none/nearest, 2 = linear, 4 = cubic, 8 = 8-tap sinc.
INTERP_SINC8 = 8

_lib: Optional[ctypes.CDLL] = None
_load_error: Optional[str] = None

_SYSTEM = platform.system()


def bundled_lib_dir() -> str:
    """Directory that may hold a bundled libopenmpt (Windows DLLs / frozen builds)."""
    if getattr(sys, "frozen", False):
        base = os.path.join(sys._MEIPASS, "xmwav", "libs")  # type: ignore[attr-defined]
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")
    return base


def _lib_filenames() -> List[str]:
    if _SYSTEM == "Windows":
        return ["libopenmpt.dll"]
    if _SYSTEM == "Darwin":
        return ["libopenmpt.dylib", "libopenmpt.0.dylib"]
    return ["libopenmpt.so", "libopenmpt.so.0"]


def _system_lib_dirs() -> List[str]:
    if _SYSTEM == "Darwin":
        return ["/opt/homebrew/lib", "/usr/local/lib", "/usr/lib"]
    if _SYSTEM == "Linux":
        return ["/usr/lib", "/usr/lib64", "/usr/local/lib",
                "/usr/lib/x86_64-linux-gnu", "/usr/lib/aarch64-linux-gnu"]
    return []


def _candidate_paths() -> List[str]:
    """Ordered libopenmpt candidates: explicit override, bundled, then system-installed."""
    cands: List[str] = []
    override = os.environ.get("XMWAV_LIBOPENMPT")
    if override:
        cands.append(override)
    d = bundled_lib_dir()
    for name in _lib_filenames():
        cands.append(os.path.join(d, name))
    found = ctypes.util.find_library("openmpt")
    if found:
        cands.append(found)
    for sd in _system_lib_dirs():
        for name in _lib_filenames():
            cands.append(os.path.join(sd, name))
    return cands


def _install_hint() -> str:
    if _SYSTEM == "Darwin":
        return "Install it with Homebrew:  brew install libopenmpt"
    if _SYSTEM == "Linux":
        return ("Install it with your package manager, e.g.:\n"
                "  Arch:          sudo pacman -S libopenmpt\n"
                "  Debian/Ubuntu: sudo apt install libopenmpt0\n"
                "  Fedora:        sudo dnf install libopenmpt")
    return "The bundled libopenmpt.dll appears to be missing from this build."


def _configure(lib: ctypes.CDLL) -> None:
    lib.openmpt_module_create_from_memory2.restype = c_void_p
    lib.openmpt_module_create_from_memory2.argtypes = [
        c_void_p, c_size_t, c_void_p, c_void_p, c_void_p, c_void_p,
        ctypes.POINTER(c_int), ctypes.POINTER(c_char_p), c_void_p,
    ]
    lib.openmpt_module_destroy.restype = None
    lib.openmpt_module_destroy.argtypes = [c_void_p]
    lib.openmpt_module_get_duration_seconds.restype = c_double
    lib.openmpt_module_get_duration_seconds.argtypes = [c_void_p]
    lib.openmpt_module_set_render_param.restype = c_int
    lib.openmpt_module_set_render_param.argtypes = [c_void_p, c_int, c_int32]
    lib.openmpt_module_read_interleaved_float_stereo.restype = c_size_t
    lib.openmpt_module_read_interleaved_float_stereo.argtypes = [
        c_void_p, c_int32, c_size_t, ctypes.POINTER(ctypes.c_float),
    ]
    lib.openmpt_module_get_current_tempo2.restype = c_double
    lib.openmpt_module_get_current_tempo2.argtypes = [c_void_p]
    lib.openmpt_module_get_current_speed.restype = c_int32
    lib.openmpt_module_get_current_speed.argtypes = [c_void_p]
    lib.openmpt_module_get_num_channels.restype = c_int32
    lib.openmpt_module_get_num_channels.argtypes = [c_void_p]
    lib.openmpt_module_get_metadata.restype = c_void_p  # must be freed
    lib.openmpt_module_get_metadata.argtypes = [c_void_p, c_char_p]
    lib.openmpt_free_string.restype = None
    lib.openmpt_free_string.argtypes = [c_void_p]
    lib.openmpt_get_library_version.restype = c_int32
    lib.openmpt_get_library_version.argtypes = []


def _load() -> ctypes.CDLL:
    global _lib, _load_error
    if _lib is not None:
        return _lib

    # On Windows, make the dependent codec DLLs resolve from the bundled dir.
    if _SYSTEM == "Windows":
        d = bundled_lib_dir()
        if hasattr(os, "add_dll_directory") and os.path.isdir(d):
            os.add_dll_directory(d)

    last_err: Optional[Exception] = None
    for path in _candidate_paths():
        # Absolute paths that don't exist are skipped; bare names go through the OS loader.
        if os.path.isabs(path) and not os.path.exists(path):
            continue
        try:
            lib = ctypes.CDLL(path)
            _configure(lib)  # inside the try: an old lib missing a symbol raises AttributeError
        except (OSError, AttributeError) as exc:
            last_err = exc
            continue
        _lib = lib
        return lib

    # Last resort: let the OS loader resolve a bare library name.
    for name in _lib_filenames():
        try:
            lib = ctypes.CDLL(name)
            _configure(lib)
        except (OSError, AttributeError) as exc:
            last_err = exc
            continue
        _lib = lib
        return lib

    _load_error = f"Could not load libopenmpt.\n\n{_install_hint()}"
    if last_err is not None:
        _load_error += f"\n\n(last error: {last_err})"
    raise OSError(_load_error)


def is_available() -> Tuple[bool, str]:
    """Return (ok, message). Never raises; used at startup to show a clear error."""
    try:
        lib = _load()
        v = lib.openmpt_get_library_version()
        return True, f"libopenmpt {(v >> 24) & 0xFF}.{(v >> 16) & 0xFF}.{v & 0xFFFF}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _take_string(lib: ctypes.CDLL, ptr: int) -> str:
    """Read a libopenmpt-owned UTF-8 string pointer and free it."""
    if not ptr:
        return ""
    try:
        value = ctypes.cast(ptr, c_char_p).value or b""
        return value.decode("utf-8", "replace")
    finally:
        lib.openmpt_free_string(ptr)


class _Module:
    """RAII holder for an openmpt_module handle."""

    def __init__(self, lib: ctypes.CDLL, data: bytes):
        self.lib = lib
        err = c_int(0)
        errmsg = c_char_p()
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        self.handle = lib.openmpt_module_create_from_memory2(
            buf, len(data), None, None, None, None, byref(err), byref(errmsg), None
        )
        if not self.handle:
            msg = errmsg.value.decode("utf-8", "replace") if errmsg.value else f"error code {err.value}"
            if errmsg.value is not None:
                lib.openmpt_free_string(ctypes.cast(errmsg, c_void_p))
            raise RuntimeError(f"libopenmpt could not load the module: {msg}")

    def metadata(self, key: str) -> str:
        ptr = self.lib.openmpt_module_get_metadata(self.handle, key.encode("utf-8"))
        return _take_string(self.lib, ptr)

    def close(self) -> None:
        if self.handle:
            self.lib.openmpt_module_destroy(self.handle)
            self.handle = None

    def __enter__(self) -> "_Module":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def probe(data: bytes) -> dict:
    """Load a module and report basic playback geometry (does not render audio)."""
    lib = _load()
    with _Module(lib, data) as mod:
        return {
            "title": mod.metadata("title").strip(),
            "type_long": mod.metadata("type_long").strip(),
            "tracker": mod.metadata("tracker").strip(),
            "bpm": lib.openmpt_module_get_current_tempo2(mod.handle),
            "speed": lib.openmpt_module_get_current_speed(mod.handle),
            "channels": lib.openmpt_module_get_num_channels(mod.handle),
            "duration": lib.openmpt_module_get_duration_seconds(mod.handle),
        }


def render(
    data: bytes,
    samplerate: int = 48000,
    interpolation: int = INTERP_SINC8,
    progress_cb: Optional[Callable[[float], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
    max_seconds: Optional[float] = None,
) -> Tuple[np.ndarray, float]:
    """Render the module once through to a float32 stereo array, shape (frames, 2).

    Values are libopenmpt's native float output and are NOT clamped, so a 32-bit float
    WAV preserves the full dynamic range with no clipping.

    max_seconds: if given, stop after this many seconds of audio (used for quick previews).
    """
    lib = _load()
    with _Module(lib, data) as mod:
        lib.openmpt_module_set_render_param(mod.handle, RENDER_INTERPOLATIONFILTER_LENGTH, interpolation)
        lib.openmpt_module_set_render_param(mod.handle, RENDER_STEREOSEPARATION_PERCENT, 100)
        lib.openmpt_module_set_render_param(mod.handle, RENDER_MASTERGAIN_MILLIBEL, 0)

        duration = float(lib.openmpt_module_get_duration_seconds(mod.handle))
        # Hard safety cap so a module that never reports end-of-song can't render forever.
        cap_frames = None
        if duration and duration > 0:
            cap_frames = int((duration + 2.0) * samplerate)
        if max_seconds is not None and max_seconds > 0:
            preview_cap = int(max_seconds * samplerate)
            cap_frames = preview_cap if cap_frames is None else min(cap_frames, preview_cap)

        chunk = 8192
        cbuf = (ctypes.c_float * (chunk * 2))()
        cview = np.ctypeslib.as_array(cbuf)
        pieces = []
        total = 0
        while True:
            if stop_flag is not None and stop_flag():
                break
            n = lib.openmpt_module_read_interleaved_float_stereo(mod.handle, samplerate, chunk, cbuf)
            if n == 0:
                break
            pieces.append(cview[: n * 2].copy())
            total += n
            if progress_cb and duration and duration > 0:
                progress_cb(min(1.0, total / (duration * samplerate)))
            if cap_frames is not None and total >= cap_frames:
                break

        if pieces:
            audio = np.concatenate(pieces).reshape(-1, 2)
        else:
            audio = np.zeros((0, 2), dtype=np.float32)
        if progress_cb:
            progress_cb(1.0)
        return audio, duration
