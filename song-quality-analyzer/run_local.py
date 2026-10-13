"""Launch the local analyzer with the current Python interpreter."""
from pathlib import Path
import sys

dependencies = Path(__file__).parent / ".localdeps"
if dependencies.is_dir():
    sys.path.insert(0, str(dependencies))

from music_library_lab.server import main

if __name__ == "__main__":
    main()
