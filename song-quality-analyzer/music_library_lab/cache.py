"""Retain three finished, explicitly owned analysis caches; preserve music.

Legacy/unmarked folders, active jobs, links, hard links and unexpected content
are never removed. Reports exported by the user live outside this cache.
"""
import json
from pathlib import Path
import re
import stat
import time

from .inventory import linked

JOB_ID = re.compile(r'^[0-9a-f]{32}$')
MARKER = '.spectracraft-cache.json'
OWNER = 'Spectracraft generated analysis cache v1'
KEEP_FINISHED = 3


def generated_file(relative, path):
    return relative.parts == (MARKER,) or (len(relative.parts) == 2 and relative.parts[0] == 'analysis'
        and (path.name == 'report.json' or re.fullmatch(r'batch-\d+\.json', path.name))) or (
        len(relative.parts) == 3 and relative.parts[0] == 'analysis'
        and re.fullmatch(r'spectra-\d+', relative.parts[1]) and path.suffix == '.npz')


class AnalysisCache:
    def __init__(self, work: Path):
        self.root = Path(work).absolute() / 'analysis-cache-v1'

    def _root(self):
        if linked(self.root) or linked(self.root.parent):
            raise ValueError('The analysis cache must use an ordinary local directory.')
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root.resolve()

    def prepare(self, identifier):
        if not isinstance(identifier, str) or not JOB_ID.fullmatch(identifier):
            raise ValueError('Invalid analysis cache identifier.')
        root = self._root()
        job = root / identifier
        job.mkdir(exist_ok=False)
        (job / MARKER).write_text(json.dumps({'owner': OWNER, 'job_id': identifier,
            'status': 'active', 'finished_at': None}), encoding='utf-8')
        return job / 'analysis'

    def _owned(self, job):
        """Check the complete target tree before any recursive removal."""
        root = self._root()
        if not JOB_ID.fullmatch(job.name) or linked(job) or not job.is_dir():
            return None
        target = job.resolve()
        if target.parent != root or not target.is_relative_to(root):
            return None
        marker = target / MARKER
        try:
            info = marker.stat(follow_symlinks=False)
            if linked(marker) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 4096:
                return None
            value = json.loads(marker.read_text(encoding='utf-8'))
            if value.get('owner') != OWNER or value.get('job_id') != job.name or value.get('status') != 'finished':
                return None
            pending = [target]; checked = 0
            while pending:
                for path in pending.pop().iterdir():
                    checked += 1
                    if checked > 1000 or linked(path) or not path.resolve().is_relative_to(target):
                        return None
                    relative = path.relative_to(target)
                    info = path.stat(follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode):
                        if relative.parts == ('analysis',) or (len(relative.parts) == 2 and relative.parts[0] == 'analysis'
                                and re.fullmatch(r'spectra-\d+', relative.parts[1])):
                            pending.append(path)
                        else:
                            return None
                    elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                        if not generated_file(relative, path):
                            return None
                    else:
                        return None
            finished = value.get('finished_at')
            return (float(finished), target) if isinstance(finished, (int, float)) else None
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    def finish(self, identifier):
        if not isinstance(identifier, str) or not JOB_ID.fullmatch(identifier):
            raise ValueError('Invalid analysis cache identifier.')
        job = self._root() / identifier
        marker = job / MARKER
        # Never follow a replaced directory/marker when finishing a job.
        if not JOB_ID.fullmatch(identifier) or linked(job) or linked(marker) or job.resolve().parent != self._root():
            raise ValueError('The analysis cache changed during processing.')
        info = marker.stat(follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 4096:
            raise ValueError('The analysis cache ownership cannot be verified.')
        value = json.loads(marker.read_text(encoding='utf-8'))
        if value.get('owner') != OWNER or value.get('job_id') != identifier:
            raise ValueError('The analysis cache ownership cannot be verified.')
        value.update(status='finished', finished_at=time.time())
        marker.write_text(json.dumps(value), encoding='utf-8')
        candidates = []
        for path in self._root().iterdir():
            owned = self._owned(path)
            if owned is not None:
                candidates.append(owned)
        for _, target in sorted(candidates, reverse=True)[KEEP_FINISHED:]:
            # Final absolute target/tree check: remain in this dedicated cache.
            # Only decoder JSON/NPZ and the ownership marker are permitted.
            if self._owned(target) is not None:
                self._remove_generated(target)

    def _remove_generated(self, target):
        # Snapshot only recognized generated files. A new file arriving during
        # cleanup is never recursively removed; nonempty directories survive.
        if self._owned(target) is None:
            return
        pending = [target]; files = []; directories = []
        while pending:
            directory = pending.pop()
            directories.append(directory)
            for path in directory.iterdir():
                if linked(path) or not path.resolve().is_relative_to(target):
                    return
                if path.is_dir():
                    pending.append(path)
                elif generated_file(path.relative_to(target), path):
                    files.append(path)
                else:
                    return
        if self._owned(target) is None:
            return
        try:
            for path in files:
                if path.name == MARKER:
                    continue
                if linked(path) or not path.resolve().is_relative_to(target) or path.stat().st_nlink != 1:
                    return
                path.unlink()
            for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
                if directory == target:
                    continue
                if linked(directory) or not directory.resolve().is_relative_to(target):
                    return
                directory.rmdir()
            marker = target / MARKER
            if linked(marker) or marker.stat().st_nlink != 1 or target.resolve().parent != self._root():
                return
            marker.unlink()
            target.rmdir()
        except OSError:
            # In-use/replaced/new content is preserved. Cleanup failure must not
            # make a successfully measured source appear to have failed.
            return
