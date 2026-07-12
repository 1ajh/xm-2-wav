"""Dark / light theming for the Tkinter GUI, built on the 'clam' ttk theme (the only
built-in theme that fully honours custom colours on Windows)."""

from __future__ import annotations

from dataclasses import dataclass
from tkinter import ttk


@dataclass(frozen=True)
class Palette:
    bg: str
    panel: str
    fg: str
    muted: str
    field: str
    accent: str
    accent_active: str
    accent_fg: str
    select: str
    border: str
    btn: str
    btn_active: str
    link: str
    log_bg: str
    log_fg: str


DARK = Palette(
    bg="#1e1f26", panel="#262832", fg="#e6e8ee", muted="#9aa0aa",
    field="#2d2f3a", accent="#4e8cff", accent_active="#3f78e0", accent_fg="#ffffff",
    select="#2f5fb0", border="#3a3d4a", btn="#333747", btn_active="#3e4658",
    link="#6aa6ff", log_bg="#15161c", log_fg="#cfd3dc",
)

LIGHT = Palette(
    bg="#f2f3f5", panel="#ffffff", fg="#1c1e22", muted="#6b7280",
    field="#ffffff", accent="#0a66c2", accent_active="#0954a5", accent_fg="#ffffff",
    select="#cfe3ff", border="#cfd3d9", btn="#e7e9ee", btn_active="#dbdee6",
    link="#0a66c2", log_bg="#ffffff", log_fg="#1c1e22",
)


def apply(root, style: ttk.Style, dark: bool) -> Palette:
    p = DARK if dark else LIGHT
    style.theme_use("clam")

    style.configure(".", background=p.bg, foreground=p.fg, fieldbackground=p.field,
                    bordercolor=p.border, lightcolor=p.border, darkcolor=p.border,
                    focuscolor=p.accent, insertcolor=p.fg)
    style.configure("TFrame", background=p.bg)
    style.configure("TLabel", background=p.bg, foreground=p.fg)
    style.configure("Muted.TLabel", background=p.bg, foreground=p.muted)
    style.configure("Header.TLabel", background=p.bg, foreground=p.fg)
    style.configure("Link.TLabel", background=p.bg, foreground=p.link)

    style.configure("TLabelframe", background=p.bg, bordercolor=p.border)
    style.configure("TLabelframe.Label", background=p.bg, foreground=p.accent)

    style.configure("TButton", background=p.btn, foreground=p.fg, bordercolor=p.border,
                    focusthickness=1, focuscolor=p.accent, padding=6)
    style.map("TButton",
              background=[("active", p.btn_active), ("disabled", p.bg)],
              foreground=[("disabled", p.muted)])

    style.configure("Accent.TButton", background=p.accent, foreground=p.accent_fg, bordercolor=p.accent)
    style.map("Accent.TButton",
              background=[("active", p.accent_active), ("disabled", p.border)],
              foreground=[("disabled", p.muted)])

    style.configure("TCheckbutton", background=p.bg, foreground=p.fg)
    style.map("TCheckbutton",
              background=[("active", p.bg)],
              foreground=[("disabled", p.muted)],
              indicatorcolor=[("selected", p.accent), ("!selected", p.field)])

    for cls in ("TSpinbox", "TCombobox"):
        style.configure(cls, fieldbackground=p.field, foreground=p.fg, background=p.btn,
                        arrowcolor=p.fg, bordercolor=p.border, insertcolor=p.fg, padding=3)
    style.map("TCombobox",
              fieldbackground=[("readonly", p.field), ("disabled", p.bg)],
              foreground=[("readonly", p.fg), ("disabled", p.muted)],
              arrowcolor=[("disabled", p.muted)])
    style.map("TSpinbox",
              fieldbackground=[("disabled", p.bg)],
              foreground=[("disabled", p.muted)],
              arrowcolor=[("disabled", p.muted)])

    style.configure("TEntry", fieldbackground=p.field, foreground=p.fg,
                    bordercolor=p.border, insertcolor=p.fg, padding=3)
    style.map("TEntry", fieldbackground=[("disabled", p.bg)])

    style.configure("TProgressbar", background=p.accent, troughcolor=p.field, bordercolor=p.border)

    # ttk Combobox drop-down list is a classic tk Listbox styled via the option database.
    root.option_add("*TCombobox*Listbox.background", p.field)
    root.option_add("*TCombobox*Listbox.foreground", p.fg)
    root.option_add("*TCombobox*Listbox.selectBackground", p.select)
    root.option_add("*TCombobox*Listbox.selectForeground", p.fg)

    root.configure(background=p.bg)
    return p
