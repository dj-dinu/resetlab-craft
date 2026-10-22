"""Desktop entry point and frozen subprocess entry for the one canonical engine."""
from pathlib import Path
import runpy
import sys

project = Path(__file__).resolve().parent
local_deps = project / ".localdeps"
if local_deps.is_dir():
    sys.path.insert(0, str(local_deps))


def _worker_streams():
    """Restore redirected pipes in a Windows GUI executable's worker mode."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    import ctypes
    from ctypes import wintypes
    import msvcrt
    import os
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.DuplicateHandle.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
                                      ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD,
                                      wintypes.BOOL, wintypes.DWORD]
    kernel.DuplicateHandle.restype = wintypes.BOOL
    for name, number in (("stdin", -10), ("stdout", -11), ("stderr", -12)):
        if getattr(sys, name) is not None:
            continue
        handle = kernel.GetStdHandle(number & 0xffffffff)
        duplicate = wintypes.HANDLE()
        process = kernel.GetCurrentProcess()
        if handle and handle != wintypes.HANDLE(-1).value and kernel.DuplicateHandle(
                process, handle, process, ctypes.byref(duplicate), 0, False, 2):
            mode = "r" if name == "stdin" else "w"
            fd = msvcrt.open_osfhandle(duplicate.value, (os.O_RDONLY if name == "stdin" else os.O_WRONLY) | os.O_BINARY)
            stream = os.fdopen(fd, mode, buffering=1, encoding="utf-8", errors="replace")
        else:
            stream = open(os.devnull, "r" if name == "stdin" else "w", encoding="utf-8")
        setattr(sys, name, stream)


def main():
    if sys.argv[1:] == ["--desktop-self-test"]:
        _worker_streams()
        from music_library_lab.desktop_check import main as desktop_check
        return desktop_check()
    if sys.argv[1:] == ["--runtime-info"]:
        _worker_streams()
        import json
        import platform
        import pyexpat
        import ssl
        print(json.dumps({"python": platform.python_version(), "openssl": ssl.OPENSSL_VERSION,
                          "expat": pyexpat.EXPAT_VERSION}))
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--scanner-worker":
        # A frozen executable is not a general Python interpreter. Dispatch its
        # worker mode to the mechanically copied canonical source instead.
        _worker_streams()
        if getattr(sys, "frozen", False):
            scanner = Path(sys._MEIPASS) / "canonical" / "scan_quality.py"
            # A worker launched directly must also use the shipped decoder,
            # rather than a developer's Homebrew installation or environment.
            import os
            decoder_name = "libmpg123.0.dylib" if sys.platform == "darwin" else "libmpg123-0.dll"
            decoder = Path(sys._MEIPASS) / "decoder" / decoder_name
            if decoder.is_file():
                os.environ["SONG_AUDIT_MPG123_PATH"] = str(decoder)
        else:
            from music_library_lab.server import State
            scanner = State().scanner
        sys.argv = [str(scanner), *sys.argv[2:]]
        try:
            runpy.run_path(str(scanner), run_name="__main__")
        except Exception:
            # A windowed worker must report failures to its captured pipe rather
            # than trigger the bootloader's modal error dialog.
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise SystemExit(1)
        return
    from music_library_lab.desktop import main as desktop_main
    desktop_main()


if __name__ == "__main__":
    main()
