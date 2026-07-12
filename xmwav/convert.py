"""High-level convert step: edit .xm bytes, render with libopenmpt, write a WAV."""

from __future__ import annotations

import os
from typing import Callable, Optional

from . import engine, wavio, xmedit


def suggest_output_name(xm_path: str, semitones: int, fixed_bpm: Optional[int]) -> str:
    stem = os.path.splitext(os.path.basename(xm_path))[0]
    bpm_tag = f"bpm{fixed_bpm}" if fixed_bpm is not None else "bpmorig"
    trans_tag = f"t{semitones:+d}" if semitones else "t0"
    return f"{stem}_{bpm_tag}_{trans_tag}.wav"


def convert(
    xm_data: bytes,
    out_path: str,
    semitones: int = 0,
    fixed_bpm: Optional[int] = None,
    samplerate: int = 48000,
    subtype: str = wavio.FLOAT32,
    normalize: bool = False,
    progress_cb: Optional[Callable[[float], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
) -> dict:
    """Edit -> render -> write. Returns a small info dict about the render."""
    edited = xmedit.edit(xm_data, semitones=semitones, fixed_bpm=fixed_bpm)
    audio, duration = engine.render(
        edited,
        samplerate=samplerate,
        progress_cb=progress_cb,
        stop_flag=stop_flag,
    )
    if stop_flag is not None and stop_flag():
        return {"cancelled": True}
    wavio.write_wav(out_path, audio, samplerate, subtype=subtype, normalize=normalize)
    return {
        "cancelled": False,
        "frames": int(audio.shape[0]),
        "duration": duration,
        "peak": wavio.peak(audio),
        "out_path": out_path,
    }
