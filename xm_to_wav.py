"""PyInstaller / direct-run entry point for XM-2-WAV.

Run with no arguments to open the GUI, or pass .xm files and options to render on the
command line (see `xm-2-wav --help`). The real logic lives in `xmwav.cli`.
"""

import sys

from xmwav.cli import main

if __name__ == "__main__":
    sys.exit(main())
