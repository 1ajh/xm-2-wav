"""Construct the GUI, pump the event loop briefly, and exit. Verifies widget wiring
without needing a human to click anything."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xmwav.app import App  # noqa: E402


def main() -> int:
    app = App()
    # Exercise a few interactions programmatically.
    app.fix_bpm_var.set(True)
    app._sync_bpm_state()
    app.transpose_var.set(7)
    app.fmt_var.set(app.fmt_labels[1])
    assert app._selected_subtype() == "pcm24"
    for _ in range(20):
        app.update_idletasks()
        app.update()
    app.destroy()
    print("GUI smoke test OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
