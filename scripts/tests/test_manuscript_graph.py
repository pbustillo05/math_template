"""Adapted from stratified: regression checks for dependency direction, review gates, and invalidation."""

import importlib.util
import argparse
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "manuscript_graph", Path(__file__).resolve().parents[1] / "manuscript_graph.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ManuscriptGraphTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("notes", "preamble", "workflow"):
            (self.root / name).mkdir(parents=True)
        self.write("preamble/agentmeta.sty", "preamble-v1")

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.startswith("notes/") and path.endswith(".tex"):
            text = "% semantex: on\n" + text
        target.write_text(text)

    def graph(self):
        return MODULE.Graph(self.root)

    def test_both_manuscripts_share_preamble_fingerprints(self):
        self.write("draft/sections/first.tex", r"\begin{definition}\label{def:pl}PL.\end{definition}")
        self.write("draft/secondary/sections/first.tex", r"\begin{definition}\label{def:smooth}Smooth.\end{definition}")
        before = self.graph()
        self.assertEqual(before.errors, [])
        fingerprints = {label: before.fingerprint(label) for label in ("def:pl", "def:smooth")}
        self.write("preamble/agentmeta.sty", "preamble-v2")
        after = self.graph()
        self.assertEqual(after.nodes["def:pl"]["file"], "draft/sections/first.tex")
        self.assertEqual(after.nodes["def:smooth"]["file"], "draft/secondary/sections/first.tex")
        for label, fingerprint in fingerprints.items():
            self.assertNotEqual(after.fingerprint(label), fingerprint)

    def accept(self, nodes):
        graph = self.graph()
        records = {}
        for node in nodes:
            reviews = []
            for role, verdict in MODULE.ROLES.items():
                path = f"workflow/{node.replace(':', '-')}-{role}.md"
                self.write(path, "independent report for " + node)
                reviews.append({"role": role, "reviewer": role + "-agent", "verdict": verdict,
                                "fingerprint": graph.fingerprint(node), "report": path,
                                "report_sha256": MODULE.sha((self.root / path).read_bytes())})
            records[node] = {"status": "accepted", "author": "author-agent", "reviews": reviews}
        self.write("workflow/reviews.json", json.dumps({"schema_version": 1, "records": records}))

    def test_proof_attachment_dependency_direction_and_order(self):
        self.write("notes/unit.tex", r"""
\begin{definition}\label{def:base} Base.\end{definition}
\begin{lemma}\label{lem:test}\uses{lem:test}{def:base}Claim.\end{lemma}
\begin{proof}\label{prf:test}\proves{prf:test}{lem:test}
\uses{prf:test}{def:base}Proof.\end{proof}
""")
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.edges["lem:test"], {"def:base"})
        self.assertEqual(graph.order(support=True), ["def:base", "prf:test", "lem:test"])
        self.assertEqual(graph.closure("def:base", reverse=True), {"def:base", "prf:test", "lem:test"})
        self.accept(graph.nodes)
        self.assertEqual(self.graph().status("lem:test"), "accepted")

    def test_dependency_edit_invalidates_descendant(self):
        self.write("notes/base.tex", r"\label{def:base}Version one.")
        self.write("notes/use.tex", r"\label{def:derived}\uses{def:derived}{def:base}Derived.")
        self.accept(["def:base", "def:derived"])
        self.assertEqual(self.graph().status("def:derived"), "accepted")
        self.write("notes/base.tex", r"\label{def:base}Version two.")
        graph = self.graph()
        self.assertEqual(graph.status("def:base"), "stale")
        self.assertEqual(graph.status("def:derived"), "stale")

    def test_moved_audit_remains_authored_and_retained_source_stays_separate(self):
        self.write("references/P/source.tex", r"\label{def:upstream}")
        source = r"""\documentclass{article}
\begin{lemma}\label{lem:audit}Claim.\end{lemma}
\begin{proof}\label{prf:audit}\proves{prf:audit}{lem:audit}Proof.\end{proof}
"""
        self.write("notes/counterexamples/example.tex", source)
        self.write("notes/use.tex", r"\begin{remark}\label{rem:use}\xref{lem:audit}\end{remark}")
        self.assertEqual(self.graph().errors, [])
        destination = self.root / "references/P/audit/report.tex"
        destination.parent.mkdir(parents=True)
        (self.root / "notes/counterexamples/example.tex").rename(destination)
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.nodes["lem:audit"]["file"], "references/P/audit/report.tex")
        self.assertEqual(graph.selected_proofs["lem:audit"], "prf:audit")
        self.assertEqual(len(graph.references("lem:audit", reverse=True)), 1)
        self.assertNotIn("P:lem:audit", graph.source_labels)
        self.assertIn("P:def:upstream", graph.source_labels)
        self.assertNotIn("def:upstream", graph.nodes)
        self.assertEqual(list(MODULE.audit_tex_files(self.root)), [destination])
        archived = self.root / "archived/old-audit.tex"
        archived.parent.mkdir()
        archived.write_text(r"\label{lem:historical}")
        (destination.parent / "historical.tex").symlink_to(archived)
        self.assertEqual(list(MODULE.audit_tex_files(self.root)), [destination])

    def test_changed_dependency_status_revokes_descendant(self):
        self.write("notes/base.tex", r"\label{def:base}")
        self.write("notes/use.tex", r"\label{def:derived}\uses{def:derived}{def:base}")
        self.accept(["def:base", "def:derived"])
        path = self.root / "workflow/reviews.json"
        data = json.loads(path.read_text())
        data["records"]["def:base"]["status"] = "disputed"
        path.write_text(json.dumps(data))
        self.assertEqual(self.graph().status("def:derived"), "stale")

    def test_source_evidence_and_preamble_edits_invalidate(self):
        self.write("references/example/audit/input.md", "source audit one")
        self.write("references/example/source.tex", "retained source")
        self.write("notes/source.tex", r"\label{src:input}\evidence{src:input}{references/example/source.tex,references/example/audit/input.md}")
        self.accept(["src:input"])
        self.assertEqual(self.graph().status("src:input"), "accepted")
        self.write("references/example/audit/input.md", "source audit two")
        self.assertEqual(self.graph().status("src:input"), "stale")
        self.accept(["src:input"])
        self.write("preamble/agentmeta.sty", "preamble-v2")
        self.assertEqual(self.graph().status("src:input"), "stale")

    def test_cycle_unknown_duplicate_and_unlabelled_environment_fail(self):
        cases = [
            (r"\label{def:a}\uses{def:a}{def:a}", "dependency cycle"),
            (r"\label{def:a}\uses{def:a}{def:missing}", "unknown dependency"),
            (r"\label{def:a}\label{def:a}", "duplicate node"),
            (r"\begin{lemma}No label.\end{lemma}", "unlabelled lemma"),
        ]
        for source, message in cases:
            with self.subTest(message=message):
                self.write("notes/test.tex", source)
                self.assertIn(message, "\n".join(self.graph().errors))

    def test_comments_and_verbatim_do_not_generate_nodes(self):
        self.write("notes/test.tex", r"""
% \label{def:ignored}
\begin{verbatim}\label{def:ignored}\end{verbatim}
\verb|\label{def:ignored}|
\label{def:real}
""")
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(set(graph.nodes), {"def:real"})

    def test_leanref_metadata_does_not_create_references_or_dependencies(self):
        source = r"""
\begin{definition}\label{def:base}Base.\end{definition}
\begin{lemma}\label{lem:test}Claim.\end{lemma}
\begin{proof}\label{prf:test}\proves{prf:test}{lem:test}
Use \dxref{def:base}.\end{proof}
"""
        self.write("draft/sections/metadata.tex", source)
        before = self.graph()
        annotated = source.replace(r"\label{def:base}",
                                   r"\label{def:base}\leanref{ledger:definition-only}{verified}")
        annotated = annotated.replace(r"\label{lem:test}",
                                      r"\label{lem:test}\leanref{ledger:lemma-only}{partial}")
        self.write("draft/sections/metadata.tex", annotated)
        after = self.graph()
        self.assertEqual(before.errors, [])
        self.assertEqual(after.errors, [])
        self.assertEqual(set(before.nodes), set(after.nodes))
        self.assertEqual(before.direct_edges, after.direct_edges)
        self.assertEqual(before.edges, after.edges)
        self.assertEqual(before.selected_proofs, after.selected_proofs)
        self.assertEqual([(r["target"], r["owner"], r["dependency"], r["command"])
                          for r in before.occurrences],
                         [(r["target"], r["owner"], r["dependency"], r["command"])
                          for r in after.occurrences])
        self.assertNotIn("ledger:definition-only", after.nodes)
        self.assertNotIn("ledger:lemma-only", after.nodes)






    def test_escaped_percent_does_not_hide_later_comment(self):
        self.write("notes/test.tex", "\\label{def:real}\\% % \\label{def:ignored}\n")
        self.assertEqual(set(self.graph().nodes), {"def:real"})

    def test_hole_and_missing_proof_prevent_acceptance(self):
        self.write("notes/test.tex", r"\label{lem:test}\sorry{obl:gap}{Nested {missing} argument.}")
        self.accept(["lem:test"])
        graph = self.graph()
        self.assertEqual(graph.holes[0]["reason"], "Nested {missing} argument.")
        self.assertEqual(graph.status("lem:test"), "stale")
        self.write("notes/test.tex", r"\label{lem:test}Apparently complete.")
        self.accept(["lem:test"])
        self.assertEqual(self.graph().status("lem:test"), "stale")

    def test_independence_and_changed_report_prevent_acceptance(self):
        self.write("notes/test.tex", r"\label{def:test}")
        self.accept(["def:test"])
        path = self.root / "workflow/reviews.json"
        data = json.loads(path.read_text())
        data["records"]["def:test"]["reviews"][0]["reviewer"] = "author-agent"
        path.write_text(json.dumps(data))
        self.assertEqual(self.graph().status("def:test"), "stale")
        self.accept(["def:test"])
        self.write("workflow/def-test-proof-verifier.md", "edited after acceptance")
        self.assertEqual(self.graph().status("def:test"), "stale")

    def test_paths_must_not_escape_repository(self):
        self.write("notes/test.tex", r"\label{src:test}\evidence{src:test}{../outside.md}")
        self.assertIn("repository-relative", "\n".join(self.graph().errors))

    def test_source_acceptance_requires_retained_original_and_audit(self):
        self.write("notes/source.tex", r"\label{src:input}")
        self.accept(["src:input"])
        self.assertEqual(self.graph().status("src:input"), "stale")


    def test_release_rejects_holes_and_planning_targets(self):
        self.write("notes/test.tex", r"\begin{definition}\label{def:test}\sorry{obl:gap}{Missing argument.}\end{definition}\label{goal:test}")
        with mock.patch.object(MODULE, "ROOT", self.root):
            with mock.patch("sys.argv", ["manuscript_graph.py", "check", "--release", "--target", "def:test"]):
                with self.assertRaisesRegex(ValueError, "unresolved obligation"):
                    MODULE.main()
            with mock.patch("sys.argv", ["manuscript_graph.py", "check", "--release", "--target", "goal:test"]):
                with self.assertRaisesRegex(ValueError, "planning/navigation"):
                    MODULE.main()


class LocalReferenceTests(unittest.TestCase):
    setUp = ManuscriptGraphTests.setUp
    write = ManuscriptGraphTests.write
    graph = ManuscriptGraphTests.graph
    accept = ManuscriptGraphTests.accept

    def fixture(self):
        self.write('draft/sections/units.tex', r'''\begin{definition}\label{def:base}Base.\end{definition}
% @title: Test result
% @sketch: Use the base convention.
% @related: cex:test
\begin{lemma}\label{lem:local}
Claim in the sense of \hdxref{def:base}.
\end{lemma}
\begin{proof}
\phantomsection\label{prf:local}
\proves{prf:local}{lem:local}
By \dxref{def:base}, the claim follows.
Compare \xref{cex:test} and \hxref{cex:test}.
\end{proof}
\begin{remark}\label{rem:unrelated}Unrelated text.\end{remark}
''')
        self.write('notes/counterexamples/test.tex', r'''\documentclass[../bestiary.tex]{subfiles}
\begin{document}
% @related: lem:local
\section{A test counterexample}
\label{cex:test}
A complete construction. See \xref{lem:local}.
\end{document}
''')

    def test_four_flags_occurrences_and_selected_proof_edges(self):
        self.fixture()
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.edges['lem:local'], {'def:base'})
        refs = [o for o in graph.references('lem:local') if o['command'] != 'metadata']
        self.assertEqual([(o['command'], o['dependency'], o['visible']) for o in refs],
                         [('hdxref', True, False), ('dxref', True, True),
                          ('xref', False, True), ('hxref', False, False)])
        self.assertEqual(len(graph.references('def:base', reverse=True)), 2)
        self.assertEqual(graph.references('def:base'), [])
        self.assertEqual(graph.nodes['lem:local']['metadata']['sketch'], 'Use the base convention.')
        self.assertEqual(graph.why('lem:local', 'def:base')['steps'][0]['uses'][0]['file'], 'draft/sections/units.tex')

    def test_exact_retrieval_excludes_neighbors_and_document_boilerplate(self):
        self.fixture()
        graph = self.graph()
        blocks = graph.blocks('lem:local')
        self.assertEqual([b['id'] for b in blocks], ['lem:local', 'prf:local'])
        self.assertNotIn('Unrelated text', ''.join(b['latex'] for b in blocks))
        self.assertNotIn('Base.\\end{definition}', ''.join(b['latex'] for b in blocks))
        self.assertTrue(blocks[0]['latex'].endswith(r'\end{lemma}'))
        self.assertTrue(blocks[1]['latex'].endswith(r'\end{proof}'))
        self.assertNotIn(r'\documentclass', graph.source('cex:test'))
        self.assertNotIn(r'\end{document}', graph.source('cex:test'))
        self.assertEqual(len(graph.blocks('prf:local')), 1)
        self.assertEqual(graph.blocks('def:base')[0]['start_line'], 1)
        self.assertGreater(blocks[1]['start_line'], blocks[0]['end_line'])

    def test_unrelated_same_file_edit_does_not_stale_review(self):
        self.fixture()
        graph = self.graph()
        self.accept(['def:base', 'lem:local', 'prf:local'])
        self.assertEqual(self.graph().status('lem:local'), 'accepted')
        path = self.root / 'draft/sections/units.tex'
        path.write_text(path.read_text().replace('Unrelated text.', 'Different unrelated text.'))
        self.assertEqual(self.graph().status('lem:local'), 'accepted')
        path.write_text('% New heading comment shifting line numbers.\n' + path.read_text())
        self.assertEqual(self.graph().status('lem:local'), 'accepted')
        path.write_text(path.read_text().replace('the claim follows', 'an altered claim follows'))
        self.assertEqual(self.graph().status('lem:local'), 'stale')

    def test_nested_ownership_and_reference_before_label(self):
        self.write('notes/nested.tex', r'''\begin{definition}\label{def:base}Base.\end{definition}
\begin{lemma}[By \xref{def:base}]\label{lem:outer}
Outer. \begin{lemma}\label{lem:inner}Inner \dxref{def:base}.\end{lemma}
Outer again \hxref{def:base}.\end{lemma}
''')
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.edges['lem:inner'], {'def:base'})
        self.assertEqual(graph.edges['lem:outer'], set())
        refs = graph.references('lem:outer')
        self.assertEqual(len(refs), 2)
        self.assertTrue(all(o['owner'] == 'lem:outer' for o in refs))

    def test_dependency_without_owner_unknown_target_and_self_cycle_fail(self):
        for text, error in [
            (r'\label{def:base}\dxref{def:base}', 'no mathematical owner'),
            (r'\begin{definition}\label{def:base}\xref{def:missing}\end{definition}', 'unresolved reference'),
            (r'\begin{definition}\label{def:base}\dxref{def:base}\end{definition}', 'dependency cycle'),
            (r'\begin{definition}\label{def:base}\dxref{def:a,def:b}\end{definition}', 'literal label'),
        ]:
            with self.subTest(error=error):
                self.write('notes/bad.tex', text)
                self.assertIn(error, '\n'.join(self.graph().errors))

    def test_nonlogical_cycles_and_bestiary_reverse_links_are_allowed(self):
        self.fixture()
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.edges['cex:test'], set())
        refs = graph.references('lem:local', reverse=True)
        self.assertEqual(len(refs), 2)
        self.assertTrue(all(o['owner'] == 'cex:test' for o in refs))
        self.assertEqual(refs[0]['target_location']['file'], 'draft/sections/units.tex')

    def test_diamond_distances_and_reverse_traversal(self):
        self.write('notes/dag.tex', r'''\begin{definition}\label{def:a}A.\end{definition}
\begin{definition}\label{def:b}\dxref{def:a}.\end{definition}
\begin{definition}\label{def:c}\hdxref{def:a}.\end{definition}
\begin{definition}\label{def:d}\dxref{def:b}, \dxref{def:c}.\end{definition}
''')
        graph = self.graph()
        self.assertEqual(graph.distances('def:d', depth=1), {'def:d': 0, 'def:b': 1, 'def:c': 1})
        self.assertEqual(graph.distances('def:d')['def:a'], 2)
        self.assertEqual(graph.distances('def:a', reverse=True)['def:d'], 2)
        self.assertEqual(graph.order(['def:d'])[-1], 'def:d')
        self.assertEqual(len(graph.why('def:d', 'def:a')['path']), 3)

    def test_alternative_proofs_require_selection_and_do_not_merge_dependencies(self):
        self.write('notes/proofs.tex', r'''\begin{definition}\label{def:a}A.\end{definition}
\begin{definition}\label{def:b}B.\end{definition}
% @proof: prf:two
\begin{lemma}\label{lem:test}Claim.\end{lemma}
\begin{proof}\label{prf:one}\proves{prf:one}{lem:test}\dxref{def:a}.\end{proof}
\begin{proof}\label{prf:two}\proves{prf:two}{lem:test}\dxref{def:b}.\end{proof}
''')
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.edges['lem:test'], {'def:b'})
        self.assertEqual([b['id'] for b in graph.blocks('lem:test')], ['lem:test', 'prf:two'])
        self.assertEqual(len(graph.blocks('lem:test', 'all')), 3)
        path = self.root / 'notes/proofs.tex'
        path.write_text(path.read_text().replace('% @proof: prf:two\n', ''))
        self.assertIn('multiple proofs require', '\n'.join(self.graph().errors))

    def test_holes_are_local_to_owning_unit(self):
        self.fixture()
        path = self.root / 'draft/sections/units.tex'
        path.write_text(path.read_text().replace('Unrelated text.', r'\sorry{obl:unrelated}{Other missing argument.}'))
        self.accept(['def:base', 'lem:local', 'prf:local'])
        self.assertEqual(self.graph().status('lem:local'), 'accepted')
        path.write_text(path.read_text().replace('the claim follows.', r'\sorry{obl:local}{Required argument.}'))
        self.accept(['def:base', 'lem:local', 'prf:local'])
        self.assertEqual(self.graph().status('lem:local'), 'stale')

    def test_metadata_in_verbatim_ignored_and_invalid_metadata_rejected(self):
        self.write('notes/meta.tex', r'''\begin{verbatim}
% @unknown: ignored
\end{verbatim}
% @sketch: First line.
% @sketch: Second line.
\begin{definition}\label{def:test}Text.\end{definition}
''')
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.nodes['def:test']['metadata']['sketch'], 'First line.\nSecond line.')
        path = self.root / 'notes/meta.tex'
        path.write_text(path.read_text() + '\n% @status: accepted\n')
        self.assertIn('unknown metadata field', '\n'.join(self.graph().errors))

    def test_cli_json_raw_source_depth_and_release_are_live(self):
        import contextlib
        import io
        self.fixture()
        for command in [
            ['get', 'lem:local', '--json'], ['deps', 'lem:local', '--depth', '1', '--json'],
            ['rdeps', 'def:base', '--depth', 'all', '--json'], ['refs', 'lem:local', '--json'],
            ['backrefs', 'cex:test', '--json'], ['why', 'lem:local', 'def:base', '--json'],
            ['frontier', 'lem:local', '--json'], ['search', 'Test result', '--kind', 'lem', '--json'],
            ['export'],
        ]:
            with self.subTest(command=command), contextlib.redirect_stdout(io.StringIO()) as out:
                MODULE.main(['--root', str(self.root)] + command)
                json.loads(out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()) as out:
            MODULE.main(['--root', str(self.root), 'get', 'lem:local', '--latex'])
            self.assertNotIn('Unrelated text', out.getvalue())
            self.assertIn(r'\begin{proof}', out.getvalue())
        self.assertFalse((self.root / 'build/graph-links.tex').exists())
        self.accept(['def:base', 'lem:local', 'prf:local'])
        with contextlib.redirect_stdout(io.StringIO()):
            MODULE.main(['--root', str(self.root), 'check', '--release', '--target', 'lem:local'])
        with self.assertRaisesRegex(argparse.ArgumentTypeError, 'depth|literal'):
            MODULE.depth_value('wrong')


if __name__ == "__main__":
    unittest.main()
