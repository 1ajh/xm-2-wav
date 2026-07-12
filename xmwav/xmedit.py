"""In-place editing of FastTracker II (.xm) modules.

Two operations, both musically lossless (they mutate the tracker score, not audio):

  * transpose(semitones): add N semitones to every note event in every pattern.
  * fix_bpm(bpm):         force a single constant BPM for the whole song by writing the
                          header's default-BPM field and neutralising every in-song
                          "set tempo (BPM)" effect (Fxx with xx >= 0x20).

Everything else in the file - instruments, samples, envelopes, panning, speed
(ticks/row) automation - is left byte-for-byte untouched, so libopenmpt renders the
module exactly as authored apart from the two intended changes.

XM format reference: the original "xm.txt" spec by Mr.H / Triton, as implemented by
FastTracker II, MilkyTracker and OpenMPT.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

XM_SIGNATURE = b"Extended Module: "  # 17 bytes, offset 0

# XM note values: 0 = no note, 1..96 = C-0..B-7, 97 = key off.
NOTE_MIN = 1
NOTE_MAX = 96
KEY_OFF = 97

# Effect 0x0F ("Fxx"): xx < 0x20 sets speed (ticks/row); xx >= 0x20 sets BPM.
EFFECT_SET_TEMPO = 0x0F
BPM_EFFECT_THRESHOLD = 0x20

# Header field offsets (absolute, from start of file).
OFF_VERSION = 58
OFF_HEADER_SIZE = 60
OFF_SONG_LENGTH = 64
OFF_RESTART = 66
OFF_NUM_CHANNELS = 68
OFF_NUM_PATTERNS = 70
OFF_NUM_INSTRUMENTS = 72
OFF_FLAGS = 74
OFF_DEFAULT_SPEED = 76  # ticks per row
OFF_DEFAULT_BPM = 78    # beats per minute


class XMError(ValueError):
    """Raised when the input is not a parseable .xm file."""


@dataclass
class XMInfo:
    version: int
    header_size: int
    song_length: int
    num_channels: int
    num_patterns: int
    num_instruments: int
    linear_frequency: bool
    default_speed: int
    default_bpm: int
    pattern_data_start: int


def _u16(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off + 2], "little")


def _u32(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off + 4], "little")


def parse_info(data: bytes) -> XMInfo:
    """Parse the XM header. Raises XMError if the data is not a valid .xm."""
    if len(data) < 80:
        raise XMError("File is too small to be an .xm module.")
    if data[:17] != XM_SIGNATURE:
        raise XMError('Not an .xm file (missing "Extended Module: " signature).')
    if data[37] != 0x1A:
        # Byte 37 must be 0x1A in a well-formed XM; warn by rejecting to avoid mis-parsing.
        raise XMError("Malformed .xm header (byte 37 is not 0x1A).")

    header_size = _u32(data, OFF_HEADER_SIZE)
    pattern_data_start = OFF_HEADER_SIZE + header_size
    info = XMInfo(
        version=_u16(data, OFF_VERSION),
        header_size=header_size,
        song_length=_u16(data, OFF_SONG_LENGTH),
        num_channels=_u16(data, OFF_NUM_CHANNELS),
        num_patterns=_u16(data, OFF_NUM_PATTERNS),
        num_instruments=_u16(data, OFF_NUM_INSTRUMENTS),
        linear_frequency=bool(_u16(data, OFF_FLAGS) & 0x1),
        default_speed=_u16(data, OFF_DEFAULT_SPEED),
        default_bpm=_u16(data, OFF_DEFAULT_BPM),
        pattern_data_start=pattern_data_start,
    )
    if pattern_data_start > len(data):
        raise XMError("Malformed .xm header (pattern data begins past end of file).")
    if not (0 < info.num_channels <= 128):
        raise XMError(f"Unreasonable channel count ({info.num_channels}).")
    return info


def _edit_pattern_cells(
    buf: bytearray,
    data_start: int,
    packed_size: int,
    num_cells: int,
    semitones: int,
    fix_bpm: bool,
) -> None:
    """Walk one pattern's packed cell stream and edit note/effect bytes in place.

    The stream length never changes: notes stay one byte, effect+param stay one byte
    each, so no size/offset fields need rewriting.
    """
    i = data_start
    end = data_start + packed_size
    cells_done = 0
    while cells_done < num_cells and i < end:
        first = buf[i]
        note_pos = inst_pos = vol_pos = eff_pos = par_pos = -1
        if first & 0x80:
            mask = first & 0x1F  # bits 0..4 = presence of note/inst/vol/effect/param
            i += 1
            if mask & 0x01:
                note_pos = i; i += 1
            if mask & 0x02:
                inst_pos = i; i += 1
            if mask & 0x04:
                vol_pos = i; i += 1
            if mask & 0x08:
                eff_pos = i; i += 1
            if mask & 0x10:
                par_pos = i; i += 1
        else:
            # Uncompressed cell: note, instrument, volume, effect, param (5 bytes).
            note_pos, inst_pos, vol_pos, eff_pos, par_pos = i, i + 1, i + 2, i + 3, i + 4
            i += 5

        if i > end:
            # Truncated/garbled cell stream - stop rather than corrupt trailing bytes.
            break

        if semitones and note_pos >= 0:
            n = buf[note_pos]
            if NOTE_MIN <= n <= NOTE_MAX:
                shifted = n + semitones
                if shifted < NOTE_MIN:
                    shifted = NOTE_MIN
                elif shifted > NOTE_MAX:
                    shifted = NOTE_MAX
                buf[note_pos] = shifted

        if fix_bpm and eff_pos >= 0 and buf[eff_pos] == EFFECT_SET_TEMPO:
            param = buf[par_pos] if par_pos >= 0 else 0
            if param >= BPM_EFFECT_THRESHOLD:
                buf[eff_pos] = 0  # arpeggio 0 == no effect
                if par_pos >= 0:
                    buf[par_pos] = 0

        cells_done += 1


def edit(
    data: bytes,
    semitones: int = 0,
    fixed_bpm: Optional[int] = None,
) -> bytes:
    """Return an edited copy of the .xm bytes.

    semitones: transpose every note by this many semitones (notes are clamped to the
               valid 1..96 range; empty cells and key-offs are left alone).
    fixed_bpm: if given, force this constant BPM (header default-BPM is rewritten and
               all in-song Fxx BPM changes are neutralised). Speed (ticks/row) automation
               is preserved. If None, tempo is left exactly as authored.
    """
    info = parse_info(data)
    buf = bytearray(data)

    if fixed_bpm is not None:
        if fixed_bpm < 1:
            raise ValueError("Fixed BPM must be a positive integer.")
        value = min(fixed_bpm, 0xFFFF)
        buf[OFF_DEFAULT_BPM:OFF_DEFAULT_BPM + 2] = value.to_bytes(2, "little")

    do_transpose = semitones != 0
    do_fix = fixed_bpm is not None
    if not do_transpose and not do_fix:
        return bytes(buf)  # nothing to change in pattern data

    pos = info.pattern_data_start
    for _ in range(info.num_patterns):
        if pos + 9 > len(buf):
            break
        pat_header_len = _u32(buf, pos)
        packing_type = buf[pos + 4]
        num_rows = _u16(buf, pos + 5)
        packed_size = _u16(buf, pos + 7)
        data_start = pos + pat_header_len
        if data_start + packed_size > len(buf):
            break  # malformed; stop before touching out-of-range bytes
        # packing_type must be 0 (the only defined value). Skip editing unknown packings
        # rather than risk corrupting them, but still advance correctly.
        if packing_type == 0 and packed_size > 0:
            _edit_pattern_cells(
                buf,
                data_start,
                packed_size,
                num_rows * info.num_channels,
                semitones if do_transpose else 0,
                do_fix,
            )
        pos = data_start + packed_size

    return bytes(buf)
