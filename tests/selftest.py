"""End-to-end self-test: builds a known .xm, then verifies the editor + libopenmpt engine.

Checks:
  * the synthetic module loads and reports the expected BPM/speed/channels;
  * transposition shifts pitch by the correct ratio (octave, fifth, down-octave);
  * a fixed BPM scales duration inversely;
  * in-song BPM changes are neutralised when a fixed BPM is forced;
  * edited modules still load and keep their channel count;
  * the WAV writer produces readable files of the right format.
"""

from __future__ import annotations

import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.make_test_xm import build_test_xm  # noqa: E402
from xmwav import convert, engine, wavio, xmedit  # noqa: E402

SR = 48000
PASS, FAIL = 0, 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}" + (f"  ({detail})" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL  {name}" + (f"  ({detail})" if detail else ""))


def dominant_freq(audio: np.ndarray, sr: int) -> float:
    """Peak frequency of the steady middle segment of the left channel."""
    x = audio[:, 0]
    n = len(x)
    a, b = int(n * 0.2), int(n * 0.8)
    seg = x[a:b]
    if len(seg) < 1024:
        seg = x
    seg = seg - np.mean(seg)
    win = np.hanning(len(seg))
    spec = np.abs(np.fft.rfft(seg * win))
    freqs = np.fft.rfftfreq(len(seg), 1.0 / sr)
    return float(freqs[int(np.argmax(spec[1:]) + 1)])


def main() -> int:
    ok, msg = engine.is_available()
    print(f"engine: {msg}")
    if not ok:
        print("libopenmpt not available; cannot run engine tests.")
        return 2

    clean = build_test_xm(bpm_change_row=None)          # constant tempo
    with_change = build_test_xm(bpm_change_row=32, bpm_change_value=200)

    # --- Probe the original module ---
    info = engine.probe(clean)
    print(f"probe: {info}")
    check("loads & reports BPM ~125", abs(info["bpm"] - 125) < 1.0, f"bpm={info['bpm']:.2f}")
    check("reports speed 6", info["speed"] == 6, f"speed={info['speed']}")
    check("reports 2 channels", info["channels"] == 2, f"ch={info['channels']}")

    # --- Baseline render (no edits) ---
    base_audio, base_dur = engine.render(clean, samplerate=SR)
    check("baseline renders audio", base_audio.shape[0] > SR, f"frames={base_audio.shape[0]}")
    check("baseline not silent", wavio.peak(base_audio) > 0.01, f"peak={wavio.peak(base_audio):.3f}")
    f0 = dominant_freq(base_audio, SR)
    print(f"  base freq  = {f0:.1f} Hz, duration = {base_dur:.3f}s")
    expected_dur = 64 * 6 * 2.5 / 125.0
    check("baseline duration ~7.68s", abs(base_dur - expected_dur) < expected_dur * 0.05,
          f"{base_dur:.3f} vs {expected_dur:.3f}")

    # --- Transposition ---
    for semis, ratio, tol in [(12, 2.0, 0.03), (7, 2 ** (7 / 12), 0.03), (-12, 0.5, 0.03)]:
        ed = xmedit.edit(clean, semitones=semis)
        aud, _ = engine.render(ed, samplerate=SR)
        f = dominant_freq(aud, SR)
        got = f / f0
        check(f"transpose {semis:+d} -> ratio {ratio:.3f}", abs(got - ratio) < ratio * tol,
              f"got {got:.4f} ({f:.1f} Hz)")

    # --- Fixed BPM scales duration inversely ---
    _, dur125 = engine.render(xmedit.edit(clean, fixed_bpm=125), samplerate=SR)
    _, dur250 = engine.render(xmedit.edit(clean, fixed_bpm=250), samplerate=SR)
    ratio = dur250 / dur125
    check("fixed BPM 250 halves duration", abs(ratio - 0.5) < 0.03,
          f"dur125={dur125:.3f} dur250={dur250:.3f} ratio={ratio:.3f}")

    # --- Neutralising an in-song BPM change ---
    _, dur_change = engine.render(with_change, samplerate=SR)                 # speeds up at row 32
    _, dur_fixed = engine.render(xmedit.edit(with_change, fixed_bpm=125), samplerate=SR)
    check("in-song BPM change speeds song up", dur_change < expected_dur * 0.95,
          f"dur_change={dur_change:.3f}")
    check("fixed BPM neutralises the change", abs(dur_fixed - expected_dur) < expected_dur * 0.05,
          f"dur_fixed={dur_fixed:.3f} vs {expected_dur:.3f}")

    # --- Edits preserve loadability & structure ---
    edited = xmedit.edit(with_change, semitones=5, fixed_bpm=140)
    check("edited size unchanged", len(edited) == len(with_change),
          f"{len(edited)} vs {len(with_change)}")
    info2 = engine.probe(edited)
    check("edited BPM now 140", abs(info2["bpm"] - 140) < 1.0, f"bpm={info2['bpm']:.2f}")
    check("edited keeps 2 channels", info2["channels"] == 2)

    # --- WAV writer round-trips (16-bit is readable by stdlib wave) ---
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selftest_out")
    os.makedirs(tmp, exist_ok=True)
    for sub, tag in [(wavio.PCM16, "pcm16"), (wavio.PCM24, "pcm24"), (wavio.FLOAT32, "float32")]:
        p = os.path.join(tmp, f"out_{tag}.wav")
        convert.convert(clean, p, semitones=0, fixed_bpm=150, samplerate=44100, subtype=sub)
        check(f"wrote {tag} WAV", os.path.getsize(p) > 44, f"{os.path.getsize(p)} bytes")
    with wave.open(os.path.join(tmp, "out_pcm16.wav"), "rb") as w:
        check("pcm16 header sane", w.getnchannels() == 2 and w.getsampwidth() == 2 and w.getframerate() == 44100,
              f"ch={w.getnchannels()} width={w.getsampwidth()} sr={w.getframerate()}")

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
