"""Minimal, dependency-free WAV writer supporting 32-bit float and 16/24-bit PCM.

32-bit float (WAVE_FORMAT_IEEE_FLOAT) is the default because it stores libopenmpt's
native output verbatim - no quantisation, no clipping, fully lossless.
"""

from __future__ import annotations

import struct
from typing import Tuple

import numpy as np

FLOAT32 = "float32"
PCM24 = "pcm24"
PCM16 = "pcm16"

_WAVE_FORMAT_PCM = 1
_WAVE_FORMAT_IEEE_FLOAT = 3

SUBTYPES = {
    FLOAT32: (_WAVE_FORMAT_IEEE_FLOAT, 32),
    PCM24: (_WAVE_FORMAT_PCM, 24),
    PCM16: (_WAVE_FORMAT_PCM, 16),
}


def peak(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.max(np.abs(audio)))


def _to_bytes(audio: np.ndarray, subtype: str) -> Tuple[bytes, int, int]:
    """Convert float32 (frames, channels) audio to raw PCM/float bytes.

    Returns (raw_bytes, format_tag, bits_per_sample).
    """
    fmt_tag, bits = SUBTYPES[subtype]
    data = np.ascontiguousarray(audio, dtype=np.float32)

    if subtype == FLOAT32:
        return data.tobytes(), fmt_tag, bits

    # Integer PCM: clamp to [-1, 1] to avoid wrap-around on loud modules.
    clamped = np.clip(data, -1.0, 1.0)
    if subtype == PCM16:
        ints = np.round(clamped * 32767.0).astype("<i2")
        return ints.tobytes(), fmt_tag, bits
    if subtype == PCM24:
        ints = np.round(clamped * 8388607.0).astype("<i4")
        flat = ints.reshape(-1)
        # Pack the low 3 bytes of each little-endian int32.
        b = flat.astype("<u4").view(np.uint8).reshape(-1, 4)[:, :3]
        return np.ascontiguousarray(b).tobytes(), fmt_tag, bits
    raise ValueError(f"Unknown subtype: {subtype}")


def encode_wav(
    audio: np.ndarray,
    samplerate: int,
    subtype: str = FLOAT32,
    normalize: bool = False,
) -> bytes:
    """Encode a stereo/mono float32 array (frames, channels) into WAV file bytes.

    normalize: scale so the peak sits at 0 dBFS (only if there is signal). Off by default
    so the render keeps the module's authored level.
    """
    if subtype not in SUBTYPES:
        raise ValueError(f"Unsupported subtype {subtype!r}")
    if audio.ndim == 1:
        audio = audio.reshape(-1, 1)
    frames, channels = audio.shape

    if normalize:
        pk = peak(audio)
        if pk > 0:
            audio = audio / pk

    raw, fmt_tag, bits = _to_bytes(audio, subtype)

    block_align = channels * (bits // 8)
    byte_rate = samplerate * block_align
    data_size = len(raw)

    if data_size + 100 > 0xFFFFFFFF:
        raise ValueError("Rendered audio exceeds the 4 GB WAV limit; use a lower sample rate.")

    include_fact = fmt_tag == _WAVE_FORMAT_IEEE_FLOAT
    fmt_chunk = struct.pack(
        "<HHIIHH", fmt_tag, channels, samplerate, byte_rate, block_align, bits
    )
    chunks = b"WAVE"
    chunks += b"fmt " + struct.pack("<I", len(fmt_chunk)) + fmt_chunk
    if include_fact:
        chunks += b"fact" + struct.pack("<I", 4) + struct.pack("<I", frames)
    chunks += b"data" + struct.pack("<I", data_size)

    pad = data_size & 1
    riff_size = len(chunks) + data_size + pad  # everything after "RIFF"+size field
    out = bytearray()
    out += b"RIFF"
    out += struct.pack("<I", riff_size)
    out += chunks
    out += raw
    if pad:  # pad byte to keep chunks word-aligned
        out += b"\x00"
    return bytes(out)


def write_wav(
    path: str,
    audio: np.ndarray,
    samplerate: int,
    subtype: str = FLOAT32,
    normalize: bool = False,
) -> None:
    """Write a stereo/mono float32 array (frames, channels) to a WAV file."""
    with open(path, "wb") as f:
        f.write(encode_wav(audio, samplerate, subtype=subtype, normalize=normalize))
