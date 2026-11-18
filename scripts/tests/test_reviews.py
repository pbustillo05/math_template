"""Review registry writes from independent processes and failed publication."""
import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from reviews import update_review


class ReviewWriterTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        for name in ('notes', 'workflow', 'build/semantex'):
            (self.root / name).mkdir(parents=True)
        self.registry = self.root / 'workflow/reviews.json'
        self.registry.write_text('{"schema_version": 1, "records": {}}')
        for name in ('first', 'second'):
            (self.root / 'notes' / (name + '.tex')).write_text(
                r'\begin{definition}\label[A fixture.]{def:' + name + r'}Fixture.\end{definition}')

    def test_two_waiting_writers_keep_both_records(self):
        program = """import sys
from argparse import Namespace
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from reviews import update_review
print('ready', flush=True)
update_review(Path(sys.argv[2]), Namespace(command='author', label='def:' + sys.argv[3], identity=sys.argv[3]))
"""
        with (self.root / 'build/semantex/reviews.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            children = [subprocess.Popen([sys.executable, '-c', program, str(SCRIPTS), str(self.root), name],
                                         stdout=subprocess.PIPE, text=True) for name in ('first', 'second')]
            try:
                for child in children:
                    self.assertEqual(child.stdout.readline().strip(), 'ready')
                with self.assertRaises(subprocess.TimeoutExpired):
                    children[0].wait(timeout=0.2)
                fcntl.flock(lock, fcntl.LOCK_UN)
                for child in children:
                    child.communicate(timeout=20)
                    self.assertEqual(child.returncode, 0)
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                    child.communicate()
        records = json.loads(self.registry.read_text())['records']
        self.assertEqual({key: r['author'] for key, r in records.items()},
                         {'def:first': 'first', 'def:second': 'second'})

    def test_failed_replacement_preserves_previous_registry(self):
        original = self.registry.read_bytes()
        args = argparse.Namespace(command='author', label='def:first', identity='author')
        with patch.object(Path, 'replace', side_effect=OSError('write failed')), self.assertRaises(OSError):
            update_review(self.root, args)
        self.assertEqual(self.registry.read_bytes(), original)
        self.assertEqual(list(self.registry.parent.iterdir()), [self.registry])
