"""Compiler diagnostics may contain non-UTF8 bytes without invalidating a PDF."""
from pathlib import Path
import importlib.util
import os
import stat
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve()
spec = importlib.util.spec_from_file_location('log_decoding_builder', HERE.parents[1] / 'build_latex.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class CompilerLogDecodingTests(unittest.TestCase):
    def test_real_compiler_subprocess_invalid_utf8_preserves_logging_and_publication(self):
        with tempfile.TemporaryDirectory(prefix='compiler-decoding-') as temporary:
            root = Path(temporary).resolve()
            (root / 'draft').mkdir()
            source = root / 'draft/main.tex'
            original = b'\\documentclass{article}\n\\begin{document}Fixture.\\end{document}\n'
            source.write_bytes(original)
            binary = root / 'bin'
            binary.mkdir()
            compiler = binary / 'latexmk'
            compiler.write_text('#!' + sys.executable + '\n' + r'''
import os, pathlib, sys
out = pathlib.Path(next(arg.split('=', 1)[1] for arg in sys.argv if arg.startswith('-outdir=')))
(out / 'main.pdf').write_bytes(b'%PDF-fixture-success')
(out / 'main.log').write_bytes(b'Compiler diagnostic: caf\xe9\n')
os.write(1, b'Compiler stdout: caf\xe9\n')
os.write(2, b'Compiler stderr: caf\xe9\n')
''')
            compiler.chmod(compiler.stat().st_mode | stat.S_IXUSR)
            env = {'PATH': str(binary) + os.pathsep + os.environ.get('PATH', '')}
            # Only corpus construction is stubbed; launching the fake executable
            # and decoding both real OS pipes are exercised without mocks.
            with patch.dict(os.environ, env), patch('semantex_cache.load_graph', return_value=types.SimpleNamespace(errors=[])):
                builder.build(root, source=source)
            output = root / 'build/latex/draft'
            self.assertEqual((root / 'draft/main.pdf').read_bytes(), b'%PDF-fixture-success')
            for name in ('build.log', 'main.build.log'):
                log = (output / name).read_text(encoding='utf-8')
                self.assertIn('Compiler stdout: caf\ufffd', log)
                self.assertIn('Compiler stderr: caf\ufffd', log)
            self.assertEqual(source.read_bytes(), original)
            self.assertFalse(list(source.parent.glob('.main-*.pdf')))


if __name__ == '__main__':
    unittest.main()
