"""Synthesise a minimal but fully valid FastTracker II v1.04 .xm for testing.

The module has one instrument whose sample is a single-cycle sine looped forever, so a
held note produces a clean steady tone. That lets the self-test verify pitch (via FFT)
and duration (via BPM) with simple ratio checks.
"""

from __future__ import annotations

import math


def _padded(s: bytes, n: int) -> bytes:
    return s[:n] + b"\x00" * max(0, n - len(s))


def build_test_xm(
    num_channels: int = 2,
    rows: int = 64,
    note: int = 61,            # C-5
    default_speed: int = 6,
    default_bpm: int = 125,
    bpm_change_row: int | None = 32,
    bpm_change_value: int = 200,
    loop_len: int = 64,
    amplitude: int = 90,
) -> bytes:
    data = bytearray()

    # --- Main header ---
    data += b"Extended Module: "                     # 0..17
    data += _padded(b"SELFTEST", 20)                  # module name
    data += b"\x1a"                                   # offset 37
    data += _padded(b"xmwav selftest", 20)            # tracker name
    data += (0x0104).to_bytes(2, "little")            # version, offset 58..60

    hdr = bytearray()
    hdr += (276).to_bytes(4, "little")                # header size
    hdr += (1).to_bytes(2, "little")                  # song length (orders)
    hdr += (0).to_bytes(2, "little")                  # restart position
    hdr += (num_channels).to_bytes(2, "little")       # channels
    hdr += (1).to_bytes(2, "little")                  # patterns
    hdr += (1).to_bytes(2, "little")                  # instruments
    hdr += (1).to_bytes(2, "little")                  # flags: linear freq table
    hdr += (default_speed).to_bytes(2, "little")      # default speed (ticks/row)
    hdr += (default_bpm).to_bytes(2, "little")        # default BPM
    order = bytearray(256)                            # order table, order[0] = 0
    hdr += order
    assert len(hdr) == 276
    data += hdr
    assert len(data) == 336

    # --- Pattern 0 ---
    packed = bytearray()
    for r in range(rows):
        for c in range(num_channels):
            if r == 0 and c == 0:
                packed += bytes([0x83, note, 1])          # note + instrument 1
            elif bpm_change_row is not None and r == bpm_change_row and c == 0:
                packed += bytes([0x98, 0x0F, bpm_change_value])  # effect Fxx set BPM
            else:
                packed += bytes([0x80])                   # empty cell
    pat = bytearray()
    pat += (9).to_bytes(4, "little")                  # pattern header length
    pat += bytes([0])                                 # packing type
    pat += (rows).to_bytes(2, "little")               # rows
    pat += (len(packed)).to_bytes(2, "little")        # packed size
    pat += packed
    data += pat

    # --- Instrument 1 ---
    inst = bytearray()
    inst += (263).to_bytes(4, "little")               # instrument header size
    inst += _padded(b"sine", 22)                      # instrument name
    inst += bytes([0])                                # instrument type
    inst += (1).to_bytes(2, "little")                 # number of samples
    inst += (40).to_bytes(4, "little")                # sample header size
    inst += bytes(96)                                 # keymap: all -> sample 0
    inst += bytes(48)                                 # volume envelope points
    inst += bytes(48)                                 # panning envelope points
    inst += bytes(8)                                  # 8 point-count/loop bytes
    inst += bytes([0, 0])                             # volume type, panning type (off)
    inst += bytes([0, 0, 0, 0])                       # vibrato type/sweep/depth/rate
    inst += (0).to_bytes(2, "little")                 # volume fadeout
    inst += bytes(22)                                 # reserved
    assert len(inst) == 263
    data += inst

    # Sample header (40 bytes)
    L = loop_len
    samp = bytearray()
    samp += (L).to_bytes(4, "little")                 # sample length in bytes (8-bit)
    samp += (0).to_bytes(4, "little")                 # loop start (bytes)
    samp += (L).to_bytes(4, "little")                 # loop length (bytes)
    samp += bytes([64])                               # volume 64
    samp += (0).to_bytes(1, "little", signed=True)    # finetune
    samp += bytes([0x01])                             # type: forward loop, 8-bit
    samp += bytes([128])                              # panning centre
    samp += (0).to_bytes(1, "little", signed=True)    # relative note
    samp += bytes([0])                                # reserved
    samp += _padded(b"sine", 22)                      # sample name
    assert len(samp) == 40
    data += samp

    # Sample data: single-cycle sine, delta-encoded 8-bit signed (XM stores deltas).
    values = [max(-127, min(127, round(amplitude * math.sin(2 * math.pi * i / L)))) for i in range(L)]
    prev = 0
    deltas = bytearray()
    for v in values:
        d = (v - prev) & 0xFF
        deltas.append(d)
        prev = v
    data += deltas

    return bytes(data)


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "test.xm"
    with open(out, "wb") as f:
        f.write(build_test_xm())
    print(f"wrote {out}")
