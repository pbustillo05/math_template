"""Virtual labels and derived views never alter retained papers or infer proof edges."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from manuscript_graph import Graph, main
from reference_views import flatten, paper_graph


class ReferenceViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paper = self.root / 'references/P'
        self.paper.mkdir(parents=True)
        (self.paper / 'main.tex').write_text(r'''\documentclass{article}
% \input{fake}
\begin{document}
\input{claims}
\end{document}
''')
        (self.paper / 'claims.tex').write_text(r'''\begin{thm}\label{claim}Statement.\end{thm}
\begin{proof}Use \ref{other}.\end{proof}
\begin{lemma}An unlabelled lemma with \begin{equation}\label{eq:x}x=x\end{equation}.\end{lemma}
\begin{remark}\label{other}Compare \ref{claim}.\end{remark}
\begin{verbatim}\begin{fake}ignored\end{fake}\end{verbatim}
''')

    def test_native_and_virtual_labels_retrieve_exact_original_environments(self):
        before = (self.paper / 'claims.tex').read_bytes()
        graph = Graph(self.root)
        self.assertEqual(graph.errors, [])
        nodes = paper_graph(graph, 'P')['nodes']
        virtual = next(n for n in nodes if n['virtual'] and n['environment'] == 'lemma')
        self.assertNotIn('P:fake', graph.source_labels)
        self.assertEqual(len([n for n in nodes if n['environment'] == 'lemma']), 1)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            main(['--root', str(self.root), 'get', virtual['id'], '--json'])
        record = json.loads(out.getvalue())
        self.assertIn('An unlabelled lemma', record['blocks'][0]['latex'])
        self.assertEqual((self.paper / 'claims.tex').read_bytes(), before)
        self.assertIn('Use \\ref{other}', graph.source_labels['P:claim'][0]['proof']['latex'])
        self.assertTrue(all(not e['dependency'] for e in paper_graph(graph, 'P')['edges']))

    def test_virtual_ids_are_deterministic_and_survive_line_shifts(self):
        first = {n['id'] for n in paper_graph(Graph(self.root), 'P')['nodes'] if n['virtual']}
        source = self.paper / 'claims.tex'
        source.write_text('\n% ordinary header\n' + source.read_text())
        after = {n['id'] for n in paper_graph(Graph(self.root), 'P')['nodes'] if n['virtual']}
        self.assertEqual(first, after)

    def test_flatten_maps_original_spans_and_retains_unsupported_constructs(self):
        (self.paper / 'main.tex').write_text((self.paper / 'main.tex').read_text() + '\n\\input{missing}\n\\import{x}{y}\n')
        text, mapping = flatten(self.root, 'P', 'main.tex')
        self.assertIn('An unlabelled lemma', text)
        self.assertIn('\\import{x}{y}', text)
        self.assertIn('virtual:', text)
        self.assertTrue(any('missing include' in d for d in mapping['diagnostics']))
        self.assertTrue(any('unsupported' in d for d in mapping['diagnostics']))
        self.assertNotIn('missing include left unchanged: fake', '\n'.join(mapping['diagnostics']))
        for segment in mapping['segments']:
            if segment['file']:
                original = (self.root / segment['file']).read_text()
                span = text[segment['start']:segment['end']]
                self.assertEqual(span, original[segment['source_start']:segment['source_start'] + len(span)])

    def test_cycle_and_external_entry_are_bounded(self):
        (self.paper / 'claims.tex').write_text('\\input{main}')
        _, mapping = flatten(self.root, 'P', 'main.tex')
        self.assertTrue(any('cycle' in d for d in mapping['diagnostics']))
        with self.assertRaisesRegex(ValueError, 'escapes'):
            flatten(self.root, 'P', '../../outside.tex')

    def test_same_cli_distinguishes_mentions_from_logical_dependencies(self):
        for extra, expected in [([], []), (['--mentions'], ['P:claim'])]:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                main(['--root', str(self.root), 'deps', 'P:other', '--json'] + extra)
            self.assertEqual([n['id'] for n in json.loads(out.getvalue())], expected)

    def test_scratch_notes_are_freeform_unless_explicitly_opted_in(self):
        notes = self.root / 'notes/scratch.tex'
        notes.parent.mkdir()
        notes.write_text(r'\begin{lemma}An incomplete idea.\end{lemma}')
        self.assertEqual(Graph(self.root).errors, [])
        notes.write_text('% semantex: on\n' + notes.read_text())
        self.assertTrue(any('unlabelled' in e for e in Graph(self.root).errors))

    def test_unsaved_overlay_retrieval_uses_new_text_without_writing_source(self):
        draft = self.root / 'draft/test.tex'
        draft.parent.mkdir()
        draft.write_text('\\begin{definition}\\label{def:x}Saved.\\end{definition}')
        graph = Graph(self.root, {'draft/test.tex': '\\begin{definition}\\label{def:x}Unsaved.\\end{definition}'})
        self.assertIn('Unsaved.', graph.source('def:x'))
        self.assertIn('Saved.', draft.read_text())


if __name__ == '__main__':
    unittest.main()
