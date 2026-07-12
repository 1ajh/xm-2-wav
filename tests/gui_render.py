"""Drive the real GUI render path (worker thread + event queue) without pixel clicking."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.make_test_xm import build_test_xm  # noqa: E402
from xmwav.app import App  # noqa: E402


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    xm_path = os.path.join(here, "_gui_test.xm")
    with open(xm_path, "wb") as f:
        f.write(build_test_xm(bpm_change_row=None))
    out_dir = os.path.join(here, "_gui_out")
    os.makedirs(out_dir, exist_ok=True)

    app = App()
    app.files = [xm_path]
    app._refresh_listbox()
    app.listbox.selection_set(0)
    app._on_select_file()
    app.fix_bpm_var.set(True)
    app.bpm_var.set(150)
    app._sync_bpm_state()
    app.transpose_var.set(-5)
    app.fmt_var.set(app.fmt_labels[0])  # 32-bit float
    app.outdir_var.set(out_dir)
    app._start_render()

    expected = os.path.join(out_dir, "_gui_test_bpm150_t-5.wav")
    deadline = time.time() + 30
    while time.time() < deadline:
        app.update()
        if app.worker is not None and not app.worker.is_alive() and app.events.empty():
            break
        time.sleep(0.03)
    app.update()

    ok = os.path.isfile(expected) and os.path.getsize(expected) > 1000
    # BPM 150 on a 7.68s@125 song -> 7.68 * 125/150 = 6.4s expected.
    print("output exists:", ok, "->", expected)
    if ok:
        print("size:", os.path.getsize(expected), "bytes")
    app.destroy()
    print("GUI render path OK" if ok else "GUI render path FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
