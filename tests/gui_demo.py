"""Launch the GUI pre-populated with a demo module, for a screenshot. Not part of tests."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.make_test_xm import build_test_xm  # noqa: E402
from xmwav.app import App  # noqa: E402


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    xm_path = os.path.join(here, "_demo_module.xm")
    with open(xm_path, "wb") as f:
        f.write(build_test_xm(bpm_change_row=None))

    app = App()
    app.files = [xm_path]
    app._refresh_listbox()
    app.listbox.selection_set(0)
    app._on_select_file()
    app.fix_bpm_var.set(True)
    app.bpm_var.set(140)
    app._sync_bpm_state()
    app.transpose_var.set(2)
    app._log("Load .xm files, pick BPM + transpose, then Render WAV.")
    app.mainloop()


if __name__ == "__main__":
    main()
