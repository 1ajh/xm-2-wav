"""Tkinter GUI for XM-2-WAV: import .xm modules, preview transpositions, and render
lossless WAVs at a fixed BPM and any transposition.

Developed by ajh - https://ajh.wtf
"""

from __future__ import annotations

import os
import platform
import queue
import sys
import threading
import traceback
import webbrowser
from typing import List, Optional

import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

from . import __version__, convert, engine, theme, wavio, xmedit
from .player import Player

APP_NAME = "XM-2-WAV"
CREDIT_URL = "https://ajh.wtf"

SAMPLE_RATES = [44100, 48000, 96000, 192000]
FORMAT_CHOICES = [
    ("32-bit float  (lossless, no clipping)", wavio.FLOAT32),
    ("24-bit PCM", wavio.PCM24),
    ("16-bit PCM", wavio.PCM16),
]


def resource_path(*parts: str) -> str:
    """Locate a package resource in dev, an installed wheel, and a frozen build."""
    if getattr(sys, "frozen", False):
        base = os.path.join(sys._MEIPASS, "xmwav")  # type: ignore[attr-defined]
    else:
        base = os.path.dirname(os.path.abspath(__file__))  # the xmwav package dir
    return os.path.join(base, *parts)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.minsize(720, 780)

        self.files: List[str] = []
        self.events: "queue.Queue[tuple]" = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.cancel_event = threading.Event()
        self.preview_thread: Optional[threading.Thread] = None
        self.preview_cancel = threading.Event()
        self.player = Player()
        self.dark_var = tk.BooleanVar(value=True)
        self._after_id: Optional[str] = None

        self._set_window_icon()

        self.style = ttk.Style(self)
        self._tk_widgets = []  # (widget, role) pairs recoloured on theme change

        self._build_widgets()
        self._apply_theme()
        self._poll_events()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        ok, msg = engine.is_available()
        if ok:
            self._log(f"Engine ready: {msg}")
            if not self.player.available:
                self._log("Note: audio preview is unavailable on this system.")
                self.preview_btn.config(state="disabled")
        else:
            self._log(f"ERROR: rendering engine unavailable: {msg}")
            messagebox.showerror("Rendering engine missing",
                                 "libopenmpt could not be loaded, so rendering is disabled.\n\n" + msg)
            self.render_btn.config(state="disabled")
            self.preview_btn.config(state="disabled")

    # ---------- UI construction ----------
    def _build_widgets(self) -> None:
        pad = dict(padx=8, pady=4)
        self.root_frame = ttk.Frame(self, padding=12)
        self.root_frame.pack(fill="both", expand=True)
        self.root_frame.columnconfigure(0, weight=1)

        # Header: title + dark-mode toggle
        header = ttk.Frame(self.root_frame)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(0, 6))
        header.columnconfigure(0, weight=1)
        title = ttk.Label(header, text=APP_NAME, style="Header.TLabel")
        title.configure(font=tkfont.Font(family="Segoe UI", size=17, weight="bold"))
        title.grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=f"v{__version__}   ", style="Muted.TLabel").grid(row=0, column=1, sticky="e")
        ttk.Checkbutton(header, text="Dark mode", variable=self.dark_var,
                        command=self._apply_theme).grid(row=0, column=2, sticky="e")

        # 1. Files
        files_box = ttk.LabelFrame(self.root_frame, text="1.  Modules  (.xm)")
        files_box.grid(row=1, column=0, sticky="ew", **pad)
        files_box.columnconfigure(0, weight=1)
        self.listbox = tk.Listbox(files_box, height=5, activestyle="dotbox",
                                  highlightthickness=0, borderwidth=0, relief="flat")
        self.listbox.grid(row=0, column=0, rowspan=4, sticky="ew", padx=(8, 4), pady=8)
        self.listbox.bind("<<ListboxSelect>>", self._on_select_file)
        self._tk_widgets.append((self.listbox, "listbox"))
        ttk.Button(files_box, text="Add…", command=self._add_files).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(files_box, text="Remove", command=self._remove_file).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Button(files_box, text="Clear", command=self._clear_files).grid(row=2, column=1, sticky="ew", padx=4)
        self.info_var = tk.StringVar(value="No module selected.")
        ttk.Label(files_box, textvariable=self.info_var, style="Muted.TLabel", justify="left").grid(
            row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8))

        # 2. Settings
        s = ttk.LabelFrame(self.root_frame, text="2.  Settings")
        s.grid(row=2, column=0, sticky="ew", **pad)
        s.columnconfigure(1, weight=1)

        self.fix_bpm_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(s, text="Fix BPM", variable=self.fix_bpm_var, command=self._sync_bpm_state).grid(
            row=0, column=0, sticky="w", padx=8, pady=6)
        self.bpm_var = tk.IntVar(value=125)
        self.bpm_spin = ttk.Spinbox(s, from_=20, to=999, textvariable=self.bpm_var, width=8)
        self.bpm_spin.grid(row=0, column=1, sticky="w", pady=6)
        ttk.Label(s, text="(unchecked = keep the module's original tempo)", style="Muted.TLabel").grid(
            row=0, column=2, sticky="w")

        ttk.Label(s, text="Transpose (semitones)").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.transpose_var = tk.IntVar(value=0)
        ttk.Spinbox(s, from_=-48, to=48, textvariable=self.transpose_var, width=8).grid(
            row=1, column=1, sticky="w", pady=6)
        ttk.Label(s, text="(+12 = up one octave)", style="Muted.TLabel").grid(row=1, column=2, sticky="w")

        ttk.Label(s, text="Sample rate (Hz)").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        self.sr_var = tk.IntVar(value=48000)
        ttk.Combobox(s, textvariable=self.sr_var, values=SAMPLE_RATES, width=8, state="readonly").grid(
            row=2, column=1, sticky="w", pady=6)

        ttk.Label(s, text="WAV format").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        self.fmt_labels = [lbl for lbl, _ in FORMAT_CHOICES]
        self.fmt_var = tk.StringVar(value=self.fmt_labels[0])
        ttk.Combobox(s, textvariable=self.fmt_var, values=self.fmt_labels, width=34, state="readonly").grid(
            row=3, column=1, columnspan=2, sticky="w", pady=6)

        self.normalize_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(s, text="Normalize peak to 0 dBFS", variable=self.normalize_var).grid(
            row=4, column=0, columnspan=2, sticky="w", padx=8, pady=6)

        # 3. Preview (audio, before rendering)
        pv = ttk.LabelFrame(self.root_frame, text="3.  Preview  (listen before rendering — test transpositions)")
        pv.grid(row=3, column=0, sticky="ew", **pad)
        pv.columnconfigure(4, weight=1)
        self.preview_btn = ttk.Button(pv, text="▶  Play preview", command=self._start_preview)
        self.preview_btn.grid(row=0, column=0, padx=(8, 4), pady=8)
        self.stop_preview_btn = ttk.Button(pv, text="■  Stop", command=self._stop_preview, state="disabled")
        self.stop_preview_btn.grid(row=0, column=1, padx=4, pady=8)
        ttk.Label(pv, text="length (s)").grid(row=0, column=2, padx=(12, 2))
        self.preview_len_var = tk.IntVar(value=20)
        ttk.Spinbox(pv, from_=3, to=120, textvariable=self.preview_len_var, width=6).grid(row=0, column=3)
        self.preview_status = tk.StringVar(value="Uses the current transpose / BPM on the selected module.")
        ttk.Label(pv, textvariable=self.preview_status, style="Muted.TLabel").grid(
            row=1, column=0, columnspan=5, sticky="w", padx=8, pady=(0, 8))

        # 4. Output
        o = ttk.LabelFrame(self.root_frame, text="4.  Output folder")
        o.grid(row=4, column=0, sticky="ew", **pad)
        o.columnconfigure(0, weight=1)
        self.outdir_var = tk.StringVar(value="")
        ttk.Entry(o, textvariable=self.outdir_var).grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ttk.Button(o, text="Browse…", command=self._pick_outdir).grid(row=0, column=1, padx=8)
        ttk.Label(o, text="Leave blank to save each WAV next to its .xm.  Files get a _bpm_ / _t_ suffix.",
                  style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))

        # Action + progress
        act = ttk.Frame(self.root_frame)
        act.grid(row=5, column=0, sticky="ew", **pad)
        act.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(act, mode="determinate", maximum=1.0)
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=2)
        self.render_btn = ttk.Button(act, text="Render WAV", style="Accent.TButton", command=self._start_render)
        self.render_btn.grid(row=0, column=1)
        self.cancel_btn = ttk.Button(act, text="Cancel", command=self._cancel, state="disabled")
        self.cancel_btn.grid(row=0, column=2, padx=(6, 0))

        # Log
        logf = ttk.LabelFrame(self.root_frame, text="Log")
        logf.grid(row=6, column=0, sticky="nsew", **pad)
        self.root_frame.rowconfigure(6, weight=1)
        logf.columnconfigure(0, weight=1)
        logf.rowconfigure(0, weight=1)
        self.log = tk.Text(logf, height=7, wrap="word", state="disabled",
                           font=("Consolas", 9), relief="flat", borderwidth=6)
        self.log.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self._tk_widgets.append((self.log, "log"))
        sb = ttk.Scrollbar(logf, command=self.log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.log.config(yscrollcommand=sb.set)

        # Footer credit
        footer = ttk.Frame(self.root_frame)
        footer.grid(row=7, column=0, sticky="ew", padx=8, pady=(2, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, text="Developed by ", style="Muted.TLabel").grid(row=0, column=1, sticky="e")
        self.link = ttk.Label(footer, text="1ajh", style="Link.TLabel", cursor="hand2")
        self.link.grid(row=0, column=2, sticky="e")
        self.link.configure(font=tkfont.Font(family="Segoe UI", size=9, underline=True))
        self.link.bind("<Button-1>", lambda e: webbrowser.open(CREDIT_URL))
        ttk.Label(footer, text="   ·   built with Claude", style="Muted.TLabel").grid(row=0, column=3, sticky="e")

        self._sync_bpm_state()

    def _set_window_icon(self) -> None:
        """Set the window/taskbar icon (uses .ico on Windows, a PNG elsewhere)."""
        try:
            if platform.system() == "Windows":
                self.iconbitmap(default=resource_path("assets", "xm2wav.ico"))
            else:
                self._icon_img = tk.PhotoImage(file=resource_path("assets", "xm2wav.png"))
                self.iconphoto(True, self._icon_img)
        except Exception:  # noqa: BLE001
            pass

    # ---------- theming ----------
    def _apply_theme(self) -> None:
        p = theme.apply(self, self.style, self.dark_var.get())
        self.p = p
        for widget, role in self._tk_widgets:
            if role == "listbox":
                widget.configure(background=p.field, foreground=p.fg,
                                 selectbackground=p.select, selectforeground=p.fg)
            elif role == "log":
                widget.configure(background=p.log_bg, foreground=p.log_fg, insertbackground=p.fg)

    # ---------- helpers ----------
    def _log(self, msg: str) -> None:
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _sync_bpm_state(self) -> None:
        self.bpm_spin.config(state="normal" if self.fix_bpm_var.get() else "disabled")

    def _selected_subtype(self) -> str:
        for lbl, sub in FORMAT_CHOICES:
            if lbl == self.fmt_var.get():
                return sub
        return wavio.FLOAT32

    def _current_settings(self):
        fixed_bpm = int(self.bpm_var.get()) if self.fix_bpm_var.get() else None
        return (
            int(self.transpose_var.get()),
            fixed_bpm,
            int(self.sr_var.get()),
            self._selected_subtype(),
            bool(self.normalize_var.get()),
        )

    def _refresh_listbox(self) -> None:
        self.listbox.delete(0, "end")
        for pth in self.files:
            self.listbox.insert("end", os.path.basename(pth))

    def _selected_path(self) -> Optional[str]:
        sel = self.listbox.curselection()
        if sel:
            return self.files[sel[0]]
        return self.files[0] if self.files else None

    # ---------- file actions ----------
    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select .xm modules",
            filetypes=[("FastTracker II modules", "*.xm"), ("All files", "*.*")])
        added = 0
        for pth in paths:
            if pth in self.files:
                continue
            try:
                with open(pth, "rb") as f:
                    xmedit.parse_info(f.read(4096))
            except Exception as exc:  # noqa: BLE001
                self._log(f"Skipped {os.path.basename(pth)}: {exc}")
                continue
            self.files.append(pth)
            added += 1
        if added:
            self._refresh_listbox()
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(len(self.files) - 1)
            self._on_select_file()
            self._log(f"Added {added} file(s).")

    def _remove_file(self) -> None:
        for idx in reversed(list(self.listbox.curselection())):
            del self.files[idx]
        self._refresh_listbox()
        self.info_var.set("No module selected." if not self.files else "")

    def _clear_files(self) -> None:
        self.files.clear()
        self._refresh_listbox()
        self.info_var.set("No module selected.")

    def _on_select_file(self, _event=None) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        path = self.files[sel[0]]
        try:
            with open(path, "rb") as f:
                data = f.read()
            info = engine.probe(data)
            hdr = xmedit.parse_info(data)
            mins, secs = divmod(int(round(info["duration"])), 60)
            title = info["title"] or "(untitled)"
            self.info_var.set(
                f"{title}  —  {info['type_long']}\n"
                f"{info['channels']} channels · {hdr.num_patterns} patterns · "
                f"{hdr.num_instruments} instruments\n"
                f"original tempo: {info['bpm']:.0f} BPM, speed {info['speed']} · "
                f"length {mins}:{secs:02d}  ({'linear' if hdr.linear_frequency else 'Amiga'} freq.)")
        except Exception as exc:  # noqa: BLE001
            self.info_var.set(f"Could not read module: {exc}")

    def _pick_outdir(self) -> None:
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self.outdir_var.set(d)

    # ---------- preview ----------
    def _start_preview(self) -> None:
        if self.preview_thread is not None and self.preview_thread.is_alive():
            return
        path = self._selected_path()
        if not path:
            messagebox.showinfo("Nothing to preview", "Add and select an .xm file first.")
            return
        semitones, fixed_bpm, samplerate, _sub, normalize = self._current_settings()
        seconds = max(1, int(self.preview_len_var.get()))
        try:
            with open(path, "rb") as f:
                data = f.read()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Cannot read file", str(exc))
            return
        self.player.stop()
        self.preview_cancel.clear()
        self.preview_btn.config(state="disabled")
        self.stop_preview_btn.config(state="normal")
        self.preview_thread = threading.Thread(
            target=self._preview_worker,
            args=(os.path.basename(path), data, semitones, fixed_bpm, samplerate, normalize, seconds),
            daemon=True)
        self.preview_thread.start()

    def _preview_worker(self, name, data, semitones, fixed_bpm, samplerate, normalize, seconds) -> None:
        try:
            self.events.put(("preview_status", f"Rendering preview of {name}…"))
            edited = xmedit.edit(data, semitones=semitones, fixed_bpm=fixed_bpm)
            audio, dur = engine.render(edited, samplerate=samplerate, max_seconds=seconds,
                                       stop_flag=self.preview_cancel.is_set)
            if self.preview_cancel.is_set():
                self.events.put(("preview_done", "Preview cancelled."))
                return
            if normalize:
                pk = wavio.peak(audio)
                if pk > 0:
                    audio = audio / pk
            self.events.put(("play", (audio, samplerate)))
            played = min(seconds, dur) if dur and dur > 0 else seconds
            bpm_txt = f"BPM {fixed_bpm}" if fixed_bpm is not None else "original BPM"
            self.events.put(("preview_status",
                             f"▶ Playing ~{played:.0f}s — transpose {semitones:+d}, {bpm_txt}"))
            self.events.put(("preview_done", None))
        except Exception as exc:  # noqa: BLE001
            self.events.put(("preview_status", f"Preview failed: {exc}"))
            self.events.put(("preview_done", None))

    def _stop_preview(self) -> None:
        self.preview_cancel.set()
        self.player.stop()
        self.preview_status.set("Preview stopped.")
        self.stop_preview_btn.config(state="disabled")
        self.preview_btn.config(state="normal")

    # ---------- render ----------
    def _start_render(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        if not self.files:
            messagebox.showinfo("Nothing to render", "Add one or more .xm files first.")
            return
        semitones, fixed_bpm, samplerate, subtype, normalize = self._current_settings()
        if fixed_bpm is not None and fixed_bpm < 20:
            messagebox.showerror("Invalid BPM", "BPM must be at least 20.")
            return
        outdir = self.outdir_var.get().strip() or None
        if outdir and not os.path.isdir(outdir):
            messagebox.showerror("Invalid output folder", f"Folder does not exist:\n{outdir}")
            return

        self.cancel_event.clear()
        self.render_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress["value"] = 0
        files = list(self.files)
        self._log(f"\nRendering {len(files)} file(s): "
                  f"BPM={fixed_bpm if fixed_bpm is not None else 'original'}, transpose={semitones:+d}, "
                  f"{samplerate} Hz, {subtype}, normalize={normalize}")
        self.worker = threading.Thread(
            target=self._render_worker,
            args=(files, semitones, fixed_bpm, samplerate, subtype, normalize, outdir),
            daemon=True)
        self.worker.start()

    def _render_worker(self, files, semitones, fixed_bpm, samplerate, subtype, normalize, outdir) -> None:
        import math
        n = len(files)
        try:
            for i, path in enumerate(files):
                if self.cancel_event.is_set():
                    break
                name = os.path.basename(path)
                self.events.put(("log", f"[{i + 1}/{n}] {name} …"))
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    target_dir = outdir or os.path.dirname(os.path.abspath(path))
                    out_name = convert.suggest_output_name(path, semitones, fixed_bpm)
                    out_path = os.path.join(target_dir, out_name)

                    def prog(frac, base=i, total=n):
                        self.events.put(("progress", (base + frac) / total))

                    result = convert.convert(
                        data, out_path, semitones=semitones, fixed_bpm=fixed_bpm,
                        samplerate=samplerate, subtype=subtype, normalize=normalize,
                        progress_cb=prog, stop_flag=self.cancel_event.is_set)
                    if result.get("cancelled"):
                        self.events.put(("log", "   cancelled."))
                        break
                    peak = result["peak"]
                    peak_db = "-inf" if peak <= 0 else f"{20 * math.log10(peak):+.1f}"
                    self.events.put(("log", f"   → {out_name}  ({result['duration']:.2f}s, peak {peak_db} dBFS)"))
                except Exception as exc:  # noqa: BLE001
                    self.events.put(("log", f"   FAILED: {exc}"))
                    self.events.put(("log", traceback.format_exc(limit=2)))
            self.events.put(("progress", 1.0))
            self.events.put(("done", "Cancelled." if self.cancel_event.is_set() else "Done."))
        except Exception as exc:  # noqa: BLE001
            self.events.put(("log", f"Worker error: {exc}"))
            self.events.put(("done", "Failed."))

    def _cancel(self) -> None:
        self.cancel_event.set()
        self._log("Cancelling…")

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "progress":
                    self.progress["value"] = payload
                elif kind == "done":
                    self._log(payload)
                    self.render_btn.config(state="normal")
                    self.cancel_btn.config(state="disabled")
                elif kind == "preview_status":
                    self.preview_status.set(payload)
                elif kind == "play":
                    try:
                        audio, samplerate = payload
                        self.player.preview(audio, samplerate)
                    except Exception as exc:  # noqa: BLE001
                        self.preview_status.set(f"Playback failed: {exc}")
                elif kind == "preview_done":
                    if payload:
                        self.preview_status.set(payload)
                    self.preview_btn.config(state="normal")
                    self.stop_preview_btn.config(state="disabled")
        except queue.Empty:
            pass
        self._after_id = self.after(80, self._poll_events)

    def _on_close(self) -> None:
        self.preview_cancel.set()
        self.cancel_event.set()
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:  # noqa: BLE001
                pass
        try:
            self.player.stop()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
