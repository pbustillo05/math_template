"""Virtual labels and derived views never alter retained papers or infer proof edges."""
import contextlib
import io
import json
import hashlib
from pathlib import Path
import shutil
import subprocess
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

    def test_active_latex_notes_are_indexed(self):
        notes = self.root / 'notes/scratch.tex'
        notes.parent.mkdir()
        notes.write_text(r'\begin{lemma}An incomplete idea.\end{lemma}')
        self.assertTrue(any('unlabelled' in e for e in Graph(self.root).errors))
        notes.write_text(r'\begin{lemma}\label[A candidate assertion.]{lem:idea}An incomplete idea.\end{lemma}')
        self.assertIn('lem:idea', Graph(self.root).nodes)

    def test_unsaved_overlay_retrieval_uses_new_text_without_writing_source(self):
        draft = self.root / 'draft/test.tex'
        draft.parent.mkdir()
        draft.write_text('\\begin{definition}\\label[A fixture definition.]{def:x}Saved.\\end{definition}')
        graph = Graph(self.root, {'draft/test.tex': '\\begin{definition}\\label[A fixture definition.]{def:x}Unsaved.\\end{definition}'})
        self.assertIn('Unsaved.', graph.source('def:x'))
        self.assertIn('Saved.', draft.read_text())

    def test_overlay_locators_and_exact_original_are_distinct(self):
        audit = self.paper / "audit"
        audit.mkdir()
        original = self.paper / "claims.tex"
        digest = hashlib.sha256(original.read_bytes()).hexdigest()
        record = {"representation": "restatement", "coverage": "statement",
                  "dependencies": "partial", "source_sha256": digest}
        manifest = audit / "semantex.json"
        manifest.write_text(json.dumps({"schema_version": 1, "units": {"ref:P:claim": record}}))
        (audit / "units.tex").write_text(r"\begin{theorem}\label[A statement from the paper.]{ref:P:claim}"
                                        r"Restated claim. \cite[text={Theorem 1}, label={claim}]{P}\end{theorem}")
        graph = Graph(self.root)
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.nodes["ref:P:claim"]["provenance"]["id"], "P:claim")
        self.assertIn("Statement.", graph.blocks("P:claim")[0]["latex"])
        self.assertIn("Restated claim.", graph.blocks("ref:P:claim")[0]["latex"])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            main(["--root", str(self.root), "locate", "ref:P:claim", "--json"])
        self.assertEqual(json.loads(out.getvalue())["origin"]["file"], "references/P/claims.tex")
        original.write_text(original.read_text() + "\n% modified payload")
        self.assertIn("origin hash differs", "\n".join(Graph(self.root).errors))

    @unittest.skipUnless(shutil.which("pdflatex") and shutil.which("pdfinfo"), "TeX and Poppler required")
    def test_pdf_only_overlay_resolves_physical_page(self):
        generation = self.root / "build"
        generation.mkdir()
        (generation / "original.tex").write_text(r"\documentclass{article}\begin{document}"
                                                  r"Fixture first page.\newpage Printed locator. \end{document}")
        subprocess.run(["pdflatex", "-interaction=batchmode", "-halt-on-error", "original.tex"],
                       cwd=generation, check=True, stdout=subprocess.DEVNULL)
        pdf_dir = self.root / "references/PDF"
        audit = pdf_dir / "audit"
        audit.mkdir(parents=True)
        pdf = pdf_dir / "original.pdf"
        shutil.copyfile(generation / "original.pdf", pdf)
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        overlay = audit / "units.tex"
        overlay.write_text(r"\begin{definition}\label[A PDF-only unit.]{ref:PDF:unit}"
                           r"Transcribed. \cite[text={Printed locator}, page=2]{PDF}\end{definition}")
        (audit / "semantex.json").write_text(json.dumps({"schema_version": 1, "units": {
            "ref:PDF:unit": {"source_sha256": digest, "representation": "transcription",
                             "coverage": "statement", "dependencies": "partial"},
        }}))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            main(["--root", str(self.root), "locate", "ref:PDF:unit", "--json"])
        self.assertTrue(json.loads(out.getvalue())["origin"]["url"].endswith("original.pdf#page=2"))
        self.assertEqual(hashlib.sha256(pdf.read_bytes()).hexdigest(), digest)
        overlay.write_text(overlay.read_text().replace("page=2", "page=3"))
        self.assertIn("physical page out of range", "\n".join(Graph(self.root).errors))

    def test_promotion_uses_checked_application_of_retained_result(self):
        original = self.paper / "claims.tex"
        original.write_text(r"\begin{definition}\label{idempotent}A self-map $p$ is idempotent if $p^2=p$.\end{definition}"
                            "\n" r"\begin{lemma}\label{fixed}For $p$ idempotent, $p(x)$ is fixed by $p$.\end{lemma}"
                            "\n" r"\begin{proof}By \ref{idempotent}, $p(p(x))=p(x)$.\end{proof}")
        digest = hashlib.sha256(original.read_bytes()).hexdigest()
        audit = self.paper / "audit"
        audit.mkdir()
        (audit / "support.md").write_text(
            "The retained lemma assumes a self-map with p²=p. We set p(x)=r(x) and apply it to every x.")
        (audit / "units.tex").write_text(r"\begin{lemma}\label[An idempotent map fixes its values.]{ref:P:fixed}"
                                        r"Every value of an idempotent self-map is fixed. \cite[label={fixed}]{P}\end{lemma}"
                                        "\n" r"\begin{proof}[label={prf:ref:P:fixed}, proves={ref:P:fixed},"
                                        r" description={Evaluates the idempotent identity at x.}]"
                                        r"Use \hiddenuse{P:idempotent}; $p(p(x))=p(x)$.\end{proof}")
        manifest = audit / "semantex.json"
        manifest.write_text(json.dumps({"schema_version": 1, "units": {
            "ref:P:fixed": {"representation": "restatement", "coverage": "statement-and-proof",
                            "dependencies": "inspected", "source_sha256": digest},
        }}))
        candidate = r"""\begin{lemma}\label[The range of a retraction lies in its fixed points.]{lem:range}
Let $r\colon X\to X$ satisfy $r^2=r$. If $y=r(x)$, then $r(y)=y$.
\end{lemma}
\begin{proof}[label={prf:range}, proves={lem:range}, description={Applies the retained lemma to r.}]
Apply the fixed-value result \hiddenuse{ref:P:fixed} to $r$.
\end{proof}
"""
        notes = self.root / "notes/range.tex"
        notes.parent.mkdir()
        notes.write_text(candidate)
        graph = Graph(self.root)
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.why("lem:range", "P:idempotent")["path"],
                         ["lem:range", "ref:P:fixed", "P:idempotent"])
        self.assertEqual(graph.blocks("ref:P:fixed")[1]["id"], "prf:ref:P:fixed")
        draft = self.root / "draft/main.tex"
        draft.parent.mkdir()
        notes.rename(draft)
        self.assertIn("ref:P:fixed: manuscript support", "\n".join(Graph(self.root).release_errors("lem:range")))
        application = r"""\begin{remark}\label[Applies the published fixed-value result to the map r.]{src:range}
The map $r$ is an idempotent self-map, so every value $r(x)$ is fixed \cite[text={Lemma 1}, label={fixed}]{P}.
\end{remark}
"""
        draft.write_text(application + candidate.replace("ref:P:fixed", "src:range"))
        metadata = json.loads(manifest.read_text())
        metadata["applications"] = {"src:range": "support.md"}
        manifest.write_text(json.dumps(metadata))
        graph = Graph(self.root)
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.nodes["lem:range"]["scope"], "draft")
        self.assertEqual(graph.why("lem:range", "src:range")["path"], ["lem:range", "src:range"])
        self.assertTrue(all("current acceptance" in error for error in graph.release_errors("lem:range")))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            main(["--root", str(self.root), "context", "lem:range", "--json"])
        self.assertEqual({unit["id"] for unit in json.loads(out.getvalue())["units"]}, {"lem:range", "src:range"})
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), digest)


if __name__ == '__main__':
    unittest.main()
