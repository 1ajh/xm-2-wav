"""Cross-platform preview playback.

Backends, in order of preference:
  * Windows  -> winsound (standard library, zero extra dependencies)
  * elsewhere -> sounddevice (PortAudio) if installed

If no backend is available the preview button is disabled; rendering still works fully.
"""

from __future__ import annotations

import platform
from typing import Optional

import numpy as np

from . import wavio

_SYSTEM = platform.system()


class Player:
    def __init__(self) -> None:
        self._buf = None            # keep WAV bytes alive during async winsound playback
        self._backend: Optional[str] = None
        self._winsound = None
        self._sd = None

        if _SYSTEM == "Windows":
            try:
                import winsound
                self._winsound = winsound
                self._backend = "winsound"
            except Exception:  # noqa: BLE001
                pass
        if self._backend is None:
            try:
                import sounddevice as sd
                self._sd = sd
                self._backend = "sounddevice"
            except Exception:  # noqa: BLE001
                pass

    @property
    def available(self) -> bool:
        return self._backend is not None

    @property
    def backend(self) -> Optional[str]:
        return self._backend

    def preview(self, audio: np.ndarray, samplerate: int) -> None:
        """Play a float32 (frames, channels) array asynchronously."""
        if self._backend == "winsound":
            wav = wavio.encode_wav(audio, samplerate, subtype=wavio.PCM16)
            self._buf = wav
            self._winsound.PlaySound(wav, self._winsound.SND_MEMORY | self._winsound.SND_ASYNC)
        elif self._backend == "sounddevice":
            self._sd.stop()
            self._sd.play(np.ascontiguousarray(audio, dtype=np.float32), int(samplerate))
        else:
            raise RuntimeError("Audio playback is not available on this system.")

    def stop(self) -> None:
        try:
            if self._backend == "winsound":
                self._winsound.PlaySound(None, self._winsound.SND_PURGE)
            elif self._backend == "sounddevice":
                self._sd.stop()
        except Exception:  # noqa: BLE001
            pass
        self._buf = None
