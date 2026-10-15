"""Generate owned audio for qualification; contains no quality-grading logic."""
from fractions import Fraction
from pathlib import Path
import shutil
import wave

CASES = [('01 HQ.wav', 'wav', 'pcm_s16le', 22000, 'HQ'),
         ('02 MQ.aiff', 'aiff', 'pcm_s16be', 18500, 'MQ'),
         ('03 LQ.flac', 'flac', 'flac', 1000, 'LQ'),
         ('04 ALAC.m4a', 'ipod', 'alac', 22000, 'HQ'),
         ('05 AAC.m4a', 'ipod', 'aac', 18500, None),
         ('06 MP3.mp3', 'mp3', 'libmp3lame', 18500, None)]


def create_audio(folder: Path, *, gui=False):
    import av
    import numpy as np
    folder.mkdir(parents=True, exist_ok=True)
    rate = 48000
    t = np.arange(rate * 3, dtype=np.float64) / rate
    for name, container, codec, frequency, _ in CASES:
        values = .18 * np.sin(2 * np.pi * 1000 * t) + .18 * np.sin(2 * np.pi * frequency * t)
        pcm = np.round(values * 32767).astype(np.int16).reshape(1, -1)
        with av.open(str(folder / name), 'w', format=container) as output:
            stream = output.add_stream(codec, rate=rate)
            stream.layout = 'mono'
            if codec in {'aac', 'libmp3lame'}:
                stream.bit_rate = 256000
            frame = av.AudioFrame.from_ndarray(pcm, format='s16', layout='mono')
            frame.sample_rate = rate
            frame.time_base = Fraction(1, rate)
            frame.pts = 0
            for packet in stream.encode(frame):
                output.mux(packet)
            for packet in stream.encode(None):
                output.mux(packet)
    if gui:
        batch = folder.parent / 'Batch 103 café % తెలుగు'
        batch.mkdir(exist_ok=True)
        # Reverse creation order makes accidental filesystem-order analysis visible.
        for index in reversed(range(103)):
            shutil.copyfile(folder / '01 HQ.wav', batch / f'{index:03d} Track.wav')
        slow = folder.parent / 'Pause and close'
        slow.mkdir(exist_ok=True)
        with wave.open(str(slow / 'Long synthetic HQ.wav'), 'wb') as output:
            output.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
            block = np.round((.18 * np.sin(2 * np.pi * 1000 * t[:rate]) +
                              .18 * np.sin(2 * np.pi * 22000 * t[:rate])) * 32767).astype('<i2').tobytes()
            # A five-minute file can finish before the native UI sends Pause
            # on fast Apple Silicon runners. Keep real decoding active long
            # enough to exercise pause, resume, stop and window-close cleanup.
            for _ in range(3600):
                output.writeframesraw(block)
        return batch, slow


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--gui', action='store_true')
    args = parser.parse_args()
    create_audio(args.folder.resolve(), gui=args.gui)
