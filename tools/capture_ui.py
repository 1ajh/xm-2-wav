"""Render the GUI to a PNG by having it screenshot its own window (PIL ImageGrab).
Used only to show the finished UI; not part of the app or tests."""

import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Make the process DPI-aware so Tk logical coords match physical screen pixels.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

from PIL import ImageGrab  # noqa: E402

from tests.make_test_xm import build_test_xm  # noqa: E402
from xmwav.app import App  # noqa: E402


def capture(dark: bool, out_png: str) -> None:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xm_path = os.path.join(here, "assets", "_demo_module.xm")
    with open(xm_path, "wb") as f:
        f.write(build_test_xm(bpm_change_row=None))

    app = App()
    app.dark_var.set(dark)
    app._apply_theme()
    app.files = [xm_path]
    app._refresh_listbox()
    app.listbox.selection_set(0)
    app._on_select_file()
    app.fix_bpm_var.set(True)
    app.bpm_var.set(140)
    app._sync_bpm_state()
    app.transpose_var.set(2)
    app.preview_status.set("▶ Playing ~20s — transpose +2, BPM 140")
    app._log("Engine ready: libopenmpt 0.8.7")
    app._log("Tip: set a transpose, click Play preview, then Render WAV.")
    app.update_idletasks()
    app.geometry("")  # let it size to content
    app.update_idletasks()
    app.lift()
    app.attributes("-topmost", True)
    app.update()
    time.sleep(0.4)
    app.update()

    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    img.save(out_png)
    print(f"saved {out_png}  ({img.size[0]}x{img.size[1]})")
    app._on_close()


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    capture(True, os.path.join(here, "assets", "ui_dark.png"))
    capture(False, os.path.join(here, "assets", "ui_light.png"))
