"""Allow ``python -m xmwav`` to run the app."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
