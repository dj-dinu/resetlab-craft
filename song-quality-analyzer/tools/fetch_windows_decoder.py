"""Reuse only the reviewed, hash-verified MP3 decoder from the existing public beta."""
from pathlib import Path
import sys
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from tools.prepare_macos_test_package import download, sha


def main():
    target = PROJECT / '.work/release-decoder'
    target.mkdir(parents=True, exist_ok=True)
    archive = target / 'reviewed-alpha5.zip'
    download('https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-alpha.5/'
             'Spectracraft-0.1.0-alpha.5-windows-x64.zip', archive,
             '5d594c4d23f7fd29f360cb1d8a207b0c46c0f95b1512ebf25e31db523a0648d6')
    destination = target / 'libmpg123-0.dll'
    with zipfile.ZipFile(archive) as source:
        destination.write_bytes(source.read('Spectracraft/_internal/decoder/libmpg123-0.dll'))
    assert sha(destination) == '018e6833088b3fc7d9a97c3f45abb5f9f947f7c46de4f17fddf423f430fa70fa'
    print(destination)


if __name__ == '__main__':
    main()
