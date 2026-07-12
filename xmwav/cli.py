"""Command-line entry point and GUI dispatcher for XM-2-WAV.

With no arguments it launches the GUI; with arguments it renders on the command line.
This function backs the ``xm-2-wav`` / ``xm-2-wav-cli`` console scripts and ``python -m xmwav``.
"""

from __future__ import annotations

import argparse
import os
import sys

from . import convert, engine, wavio


def _run_cli(argv) -> int:
    fmt_map = {"float32": wavio.FLOAT32, "pcm24": wavio.PCM24, "pcm16": wavio.PCM16}
    p = argparse.ArgumentParser(prog="xm-2-wav", description="Render .xm modules to WAV.")
    p.add_argument("files", nargs="+", help="Input .xm file(s).")
    p.add_argument("--bpm", type=int, default=None, help="Force a fixed BPM (default: keep original).")
    p.add_argument("--transpose", type=int, default=0, help="Transpose in semitones (default 0).")
    p.add_argument("--samplerate", type=int, default=48000, help="Output sample rate (default 48000).")
    p.add_argument("--format", choices=list(fmt_map), default="float32", help="WAV format (default float32).")
    p.add_argument("--normalize", action="store_true", help="Normalize peak to 0 dBFS.")
    p.add_argument("--outdir", default=None, help="Output folder (default: next to each input).")
    p.add_argument("--out", default=None, help="Explicit output path (only valid for a single input).")
    args = p.parse_args(argv)

    ok, msg = engine.is_available()
    if not ok:
        print(f"error: rendering engine unavailable:\n{msg}", file=sys.stderr)
        return 2
    if args.out and len(args.files) > 1:
        print("error: --out can only be used with a single input file.", file=sys.stderr)
        return 2

    rc = 0
    for path in args.files:
        try:
            with open(path, "rb") as f:
                data = f.read()
            if args.out:
                out_path = args.out
            else:
                target_dir = args.outdir or os.path.dirname(os.path.abspath(path))
                out_path = os.path.join(target_dir, convert.suggest_output_name(path, args.transpose, args.bpm))
            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
            res = convert.convert(
                data, out_path, semitones=args.transpose, fixed_bpm=args.bpm,
                samplerate=args.samplerate, subtype=fmt_map[args.format], normalize=args.normalize)
            print(f"{os.path.basename(path)} -> {out_path}  ({res['duration']:.2f}s)")
        except Exception as exc:  # noqa: BLE001
            print(f"{os.path.basename(path)}: FAILED: {exc}", file=sys.stderr)
            rc = 1
    return rc


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv:
        return _run_cli(argv)
    from .app import main as gui_main
    gui_main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
