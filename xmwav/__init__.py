"""xmwav - render FastTracker II .xm modules to lossless WAV at a fixed BPM and any transposition.

The rendering is done by libopenmpt (bundled). BPM and transposition are applied by
editing the .xm bytes in place before rendering, which is musically lossless and leaves
all instrument/sample data byte-for-byte intact.
"""

__version__ = "1.2.0"
