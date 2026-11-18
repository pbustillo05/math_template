"""Selected authored builds and persistent manuscript publication."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve()
spec = importlib.util.spec_from_file_location('entrypoint_builder', HERE.parents[1] / 'build_latex.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='entrypoint-build-')
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name).resolve()
        for directory in ('draft/sections', 'notes/topic', 'references', 'preamble'):
            (self.root / directory).mkdir(parents=True)
        for name in ('draft/main.tex', 'draft/sections/aaa.tex', 'notes/topic/main.tex'):
            (self.root / name).write_text(r'\documentclass{article}\begin{document}Fixture.\end{document}')
        self.addCleanup(patch.stopall)
        patch.object(builder.shutil, 'which', return_value='/test/latexmk').start()
        self.graph = patch('manuscript_graph.Graph', return_value=types.SimpleNamespace(errors=[])).start()

    def compiler(self, command, **kwargs):
        output = Path(next(arg.split('=', 1)[1] for arg in command if arg.startswith('-outdir=')))
        stem = Path(command[-1]).stem
        (output / (stem + '.log')).write_text('No unresolved references.')
        (output / (stem + '.pdf')).write_bytes(b'%PDF-fixture-success')
        return subprocess.CompletedProcess(command, 0, 'Synthetic compiler success')

    def test_selected_note_has_separate_output_and_never_publishes_main(self):
        destination = self.root / 'draft/main.pdf'
        destination.write_bytes(b'last-good')
        with patch.object(builder.subprocess, 'run', side_effect=self.compiler) as run:
            builder.build(self.root, source='notes/topic/main.tex')
        self.assertEqual(run.call_count, 1)
        self.graph.assert_called_once_with(self.root)
        self.assertEqual(run.call_args.kwargs['cwd'], self.root / 'notes/topic')
        self.assertTrue((self.root / 'build/latex/notes/topic/main.pdf').exists())
        self.assertEqual(destination.read_bytes(), b'last-good')

    def test_default_main_is_first_and_failed_compile_preserves_publication(self):
        destination = self.root / 'draft/main.pdf'
        with patch.object(builder.subprocess, 'run', side_effect=self.compiler) as run:
            builder.build(self.root)
        self.assertEqual(run.call_args_list[0].kwargs['cwd'], self.root / 'draft')
        self.assertEqual(destination.read_bytes(), b'%PDF-fixture-success')
        def fail(command, **kwargs):
            self.compiler(command, **kwargs)
            return subprocess.CompletedProcess(command, 1, 'Failure after writing output')
        with patch.object(builder.subprocess, 'run', side_effect=fail):
            with self.assertRaisesRegex(ValueError, 'LaTeX failed'):
                builder.build(self.root, source='draft/main.tex')
        self.assertEqual(destination.read_bytes(), b'%PDF-fixture-success')
        shutil.rmtree(self.root / 'build/latex')
        self.assertEqual(destination.read_bytes(), b'%PDF-fixture-success')
        self.assertEqual(list(destination.parent.glob('.main-*.pdf')), [])

    def test_validation_failure_preserves_publication(self):
        destination = self.root / 'draft/main.pdf'
        destination.write_bytes(b'last-good')
        self.graph.return_value.errors = ['invalid graph']
        with patch.object(builder.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'invalid graph'):
                builder.build(self.root, source='draft/main.tex')
        run.assert_not_called()
        self.assertEqual(destination.read_bytes(), b'last-good')

    def test_rejects_retained_outside_nonentrypoint_and_symlink_escape(self):
        outside = self.root.parent / (self.root.name + '-outside.tex')
        outside.write_text(r'\documentclass{article}')
        self.addCleanup(outside.unlink)
        (self.root / 'references/paper.tex').write_text(r'\documentclass{article}')
        (self.root / 'notes/fragment.tex').write_text('No document class.')
        (self.root / 'notes/escape.tex').symlink_to(outside)
        for source in (outside, 'references/paper.tex', 'notes/fragment.tex', 'notes/escape.tex'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                builder.build(self.root, source=source)
        self.graph.assert_not_called()

    def test_selected_audit_isolated_and_retained_payloads_still_rejected(self):
        audit = self.root / 'references/Test/audit/nested/main.tex'
        audit.parent.mkdir(parents=True)
        audit.write_text(r'\documentclass{article}\begin{document}Audit fixture.\end{document}')
        retained = self.root / 'references/Test/paper.tex'
        retained.write_text(r'\documentclass{article}\begin{document}Retained fixture.\end{document}')
        (audit.parent / 'retained-link.tex').symlink_to(retained)
        outside = self.root.parent / (self.root.name + '-audit-outside.tex')
        outside.write_text(retained.read_text())
        self.addCleanup(outside.unlink)
        (audit.parent / 'outside-link.tex').symlink_to(outside)
        nested_payload = self.root / 'references/Test/payload/audit/paper.tex'
        nested_payload.parent.mkdir(parents=True)
        nested_payload.write_text(retained.read_text())
        destination = self.root / 'draft/main.pdf'
        destination.write_bytes(b'last-good-manuscript')
        with patch.object(builder.subprocess, 'run', side_effect=self.compiler) as run:
            builder.build(self.root, source=audit)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.kwargs['cwd'], audit.parent)
        self.assertTrue((self.root / 'build/latex/references/Test/audit/nested/main.pdf').exists())
        self.assertEqual(destination.read_bytes(), b'last-good-manuscript')
        self.graph.reset_mock()
        for path in (retained, audit.parent / 'retained-link.tex', audit.parent / 'outside-link.tex', nested_payload):
            with self.subTest(path=path), self.assertRaises(ValueError):
                builder.build(self.root, source=path)
        self.graph.assert_not_called()

    def test_bibliography_source_exclusion(self):
        with self.assertRaisesRegex(ValueError, 'cannot be combined'):
            builder.build(self.root, bibliography=True, source='draft/main.tex')

    @unittest.skipUnless(shutil.which('make'), 'make required')
    def test_actual_make_clean_preserves_manuscript_and_semantic_assets(self):
        shutil.copyfile(HERE.parents[2] / 'Makefile', self.root / 'Makefile')
        persistent = [self.root / 'draft/main.pdf',
                      self.root / 'build/semantex/semantex-runtime.tex',
                      self.root / 'build/semantex/rag/index.json',
                      self.root / 'build/semantex/models/weights.gguf',
                      self.root / 'build/unrelated/sentinel']
        temporary = [self.root / 'build/latex/sentinel',
                     self.root / 'build/bibliography-source/sentinel',
                     self.root / 'build/blueprint-source/sentinel']
        for path in persistent + temporary:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'preserve-or-remove-fixture')
        import sys
        result = subprocess.run(['make', 'clean', 'PYTHON=' + sys.executable],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for path in persistent:
            self.assertEqual(path.read_bytes(), b'preserve-or-remove-fixture')
        for path in temporary:
            self.assertFalse(path.parent.exists())

    def test_editor_routes_to_checked_builder_and_matching_output(self):
        root = HERE.parents[2]
        settings = json.loads((root / '.vscode/settings.json').read_text())
        tool = settings['latex-workshop.latex.tools'][0]
        self.assertEqual(tool['args'], ['%WORKSPACE_FOLDER%/scripts/build_latex.py', '--source', '%DOC_EXT%'])
        self.assertEqual(settings['latex-workshop.latex.outDir'], '%WORKSPACE_FOLDER%/build/latex/%RELATIVE_DIR%')
        self.assertTrue(settings['latex-workshop.latex.rootFile.useSubFile'])
        self.assertFalse(settings['latex-workshop.latex.rootFile.doNotPrompt'])
        tasks = json.loads((root / '.vscode/tasks.json').read_text())['tasks']
        active = next(t for t in tasks if t['label'] == 'Math: build active TeX')
        self.assertEqual(active['args'][-2:], ['--source', '${file}'])
        self.assertIn("'build/latex'", (root / 'Makefile').read_text())


@unittest.skipUnless(all(shutil.which(x) for x in ('latexmk', 'pdflatex', 'pdftotext')), 'TeX and Poppler required')
class RealSelectedBuildTests(unittest.TestCase):
    def test_audit_subfile_compiles_without_touching_payload_or_manuscript(self):
        with tempfile.TemporaryDirectory(prefix='selected-audit-tex-') as directory:
            root = Path(directory).resolve()
            for name in ('draft', 'references/Test/audit/nested', 'preamble'):
                (root / name).mkdir(parents=True)
            (root / 'preamble/research.sty').write_text(r'\ProvidesPackage{research}\RequirePackage{subfiles}')
            (root / 'draft/main.tex').write_text('\n'.join([r'\documentclass{article}', r'\usepackage{research}', r'\begin{document}', 'Manuscript fixture.', r'\end{document}']))
            audit = root / 'references/Test/audit/nested/main.tex'
            audit.write_text('\n'.join([r'\documentclass[../../../../draft/main.tex]{subfiles}', r'\begin{document}', 'Authored audit fixture.', r'\end{document}']))
            payload = root / 'references/Test/paper.tex'
            payload.write_text(r'\documentclass{article}\errmessage{Retained payload must never execute}')
            published = root / 'draft/main.pdf'
            published.write_bytes(b'last-good-manuscript')
            original = {p: p.read_bytes() for p in (audit, payload, published)}
            builder.build(root, source=audit)
            pdf = root / 'build/latex/references/Test/audit/nested/main.pdf'
            self.assertIn('Authored audit fixture.', subprocess.check_output(['pdftotext', str(pdf), '-'], text=True))
            with self.assertRaisesRegex(ValueError, 'authored entry point'):
                builder.build(root, source=payload)
            for path, content in original.items():
                self.assertEqual(path.read_bytes(), content)
            self.assertFalse(list(payload.parent.glob('*.aux')))
            self.assertFalse(list(audit.parent.glob('*.aux')))

    def test_subfile_and_main_load_project_preamble_and_preserve_last_good(self):
        with tempfile.TemporaryDirectory(prefix='selected-tex-') as directory:
            root = Path(directory).resolve()
            for name in ('draft', 'notes/topic', 'preamble'):
                (root / name).mkdir(parents=True)
            (root / 'preamble/research.sty').write_text(r'\ProvidesPackage{research}\RequirePackage{subfiles}')
            main = root / 'draft/main.tex'
            note = root / 'notes/topic/note.tex'
            main.write_text('\n'.join([r'\documentclass{article}', r'\usepackage{research}', r'\begin{document}', r'Main fixture.\subfile{../notes/topic/note}', r'\end{document}']))
            note.write_text('\n'.join([r'\documentclass[../../draft/main.tex]{subfiles}', r'\begin{document}', 'Standalone note fixture.', r'\end{document}']))
            original = {p: p.read_bytes() for p in (main, note)}
            builder.build(root, source=note)
            note_pdf = root / 'build/latex/notes/topic/note.pdf'
            self.assertIn('Standalone note fixture.', subprocess.check_output(['pdftotext', str(note_pdf), '-'], text=True))
            self.assertFalse((root / 'draft/main.pdf').exists())
            builder.build(root, source=main)
            published = root / 'draft/main.pdf'
            last_good = published.read_bytes()
            note.write_text(note.read_text().replace('Standalone note fixture.', r'\IntentionalUndefinedCommand'))
            with self.assertRaisesRegex(ValueError, 'LaTeX failed'):
                builder.build(root, source=main)
            self.assertEqual(published.read_bytes(), last_good)
            self.assertEqual(main.read_bytes(), original[main])
            shutil.rmtree(root / 'build/latex')
            self.assertEqual(published.read_bytes(), last_good)


if __name__ == '__main__':
    unittest.main()
