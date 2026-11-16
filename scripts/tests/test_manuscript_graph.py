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
        target.write_text(text)

    def graph(self):
        return MODULE.Graph(self.root)

    def test_both_manuscripts_share_preamble_fingerprints(self):
        self.write("draft/sections/first.tex", r"\begin{definition}\label[Fixture description.]{def:pl}PL.\end{definition}")
        self.write("draft/secondary/sections/first.tex", r"\begin{definition}\label[Fixture description.]{def:smooth}Smooth.\end{definition}")
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
\begin{definition}\label[Fixture description.]{def:base} Base.\end{definition}
\begin{lemma}\label[Fixture description.]{lem:test}\hiddenuse{def:base}Claim.\end{lemma}
\begin{proof}[label={prf:test}, proves={lem:test}, description={Proof of the fixture claim.}]
\hiddenuse{def:base}Proof.\end{proof}
""")
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.edges["lem:test"], {"def:base"})
        self.assertEqual(graph.order(support=True), ["def:base", "prf:test", "lem:test"])
        self.assertEqual(graph.closure("def:base", reverse=True), {"def:base", "prf:test", "lem:test"})
        self.accept(graph.nodes)
        self.assertEqual(self.graph().status("lem:test"), "accepted")

    def test_dependency_edit_invalidates_descendant(self):
        self.write("notes/base.tex", r"\label[Fixture description.]{def:base}Version one.")
        self.write("notes/use.tex", r"\begin{definition}\label[Fixture description.]{def:derived}\hiddenuse{def:base}Derived.\end{definition}")
        self.accept(["def:base", "def:derived"])
        self.assertEqual(self.graph().status("def:derived"), "accepted")
        self.write("notes/base.tex", r"\label[Fixture description.]{def:base}Version two.")
        graph = self.graph()
        self.assertEqual(graph.status("def:base"), "stale")
        self.assertEqual(graph.status("def:derived"), "stale")

    def test_moved_audit_remains_authored_and_retained_source_stays_separate(self):
        self.write("references/P/source.tex", r"\label{def:upstream}")
        source = r"""\documentclass{article}
\begin{lemma}\label[Fixture description.]{lem:audit}Claim.\end{lemma}
\begin{proof}[label={prf:audit}, proves={lem:audit}, description={Proof of the fixture claim.}]Proof.\end{proof}
"""
        self.write("notes/counterexamples/example.tex", source)
        self.write("notes/use.tex", r"\begin{remark}\label[Fixture description.]{rem:use}\mention{lem:audit}\end{remark}")
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
        archived.write_text(r"\label[Fixture description.]{lem:historical}")
        (destination.parent / "historical.tex").symlink_to(archived)
        self.assertEqual(list(MODULE.audit_tex_files(self.root)), [destination])

    def test_changed_dependency_status_revokes_descendant(self):
        self.write("notes/base.tex", r"\label[Fixture description.]{def:base}")
        self.write("notes/use.tex", r"\begin{definition}\label[Fixture description.]{def:derived}\hiddenuse{def:base}\end{definition}")
        self.accept(["def:base", "def:derived"])
        path = self.root / "workflow/reviews.json"
        data = json.loads(path.read_text())
        data["records"]["def:base"]["status"] = "disputed"
        path.write_text(json.dumps(data))
        self.assertEqual(self.graph().status("def:derived"), "stale")

    def test_source_evidence_and_preamble_edits_invalidate(self):
        self.write("references/example/audit/input.md", "source audit one")
        self.write("references/example/source.tex", "retained source")
        self.write("notes/source.tex", r"\begin{remark}\label[Fixture description.]{src:input}"
                   r"\cite[text={Source line}, file={source.tex}, line=1]{example}\end{remark}")
        self.write("references/example/audit/semantex.json", json.dumps({"schema_version": 1, "applications": {"src:input": "input.md"}}))
        self.accept(["src:input"])
        self.assertEqual(self.graph().status("src:input"), "accepted")
        self.write("references/example/audit/input.md", "source audit two")
        self.assertEqual(self.graph().status("src:input"), "stale")
        self.accept(["src:input"])
        self.write("preamble/agentmeta.sty", "preamble-v2")
        self.assertEqual(self.graph().status("src:input"), "stale")

    def test_cycle_unknown_duplicate_and_unlabelled_environment_fail(self):
        cases = [
            (r"\begin{definition}\label[Fixture description.]{def:a}\hiddenuse{def:a}\end{definition}", "dependency cycle"),
            (r"\label[Fixture description.]{def:a}\hiddenuse{def:missing}", "unresolved reference"),
            (r"\label[Fixture description.]{def:a}\label[Fixture description.]{def:a}", "duplicate node"),
            (r"\begin{lemma}No label.\end{lemma}", "unlabelled lemma"),
        ]
        for source, message in cases:
            with self.subTest(message=message):
                self.write("notes/test.tex", source)
                self.assertIn(message, "\n".join(self.graph().errors))

    def test_comments_and_verbatim_do_not_generate_nodes(self):
        self.write("notes/test.tex", r"""
% \label[Fixture description.]{def:ignored}
\begin{verbatim}\label[Fixture description.]{def:ignored}\end{verbatim}
\verb|\label[Fixture description.]{def:ignored}|
\label[Fixture description.]{def:real}
""")
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(set(graph.nodes), {"def:real"})

    def test_descriptions_do_not_change_review_hashes(self):
        source = r"""\begin{lemma}\label[Previous description.]{lem:test}Claim.\end{lemma}
\begin{proof}[label={prf:test}, proves={lem:test}, description={Previous description.}]
Proof.\end{proof}
"""
        self.write("draft/test.tex", source)
        before = self.graph()
        self.write("draft/test.tex", source.replace("Previous description.", "New searchable description."))
        after = self.graph()
        self.assertEqual(before.errors + after.errors, [])
        self.assertEqual(before.fingerprint("lem:test"), after.fingerprint("lem:test"))
        self.assertEqual(after.nodes["prf:test"]["description"], "New searchable description.")

    def test_escaped_percent_does_not_hide_later_comment(self):
        self.write("notes/test.tex", "\\label[Fixture description.]{def:real}\\% % \\label[Fixture description.]{def:ignored}\n")
        self.assertEqual(set(self.graph().nodes), {"def:real"})

    def test_missing_proof_prevents_acceptance(self):
        self.write("notes/test.tex", r"\begin{lemma}\label[Fixture description.]{lem:test}Claim.\end{lemma}")
        self.accept(["lem:test"])
        self.assertEqual(self.graph().status("lem:test"), "stale")

    def test_independence_and_changed_report_prevent_acceptance(self):
        self.write("notes/test.tex", r"\label[Fixture description.]{def:test}")
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
        self.write("notes/test.tex", r"\label[Fixture description.]{src:test}\cite[file={../outside.tex}, line=1]{P}")
        self.write("references/P/source.tex", "retained")
        self.assertIn("retained paper payload", "\n".join(self.graph().errors))

    def test_source_acceptance_requires_retained_original_and_audit(self):
        self.write("notes/source.tex", r"\label[Fixture description.]{src:input}")
        self.accept(["src:input"])
        self.assertEqual(self.graph().status("src:input"), "stale")


    def test_release_rejects_planning_targets(self):
        self.write("notes/test.tex", r"\label{goal:test}")
        with self.assertRaisesRegex(ValueError, "planning/navigation"):
            MODULE.main(["--root", str(self.root), "check", "--release", "--target", "goal:test"])


class LocalReferenceTests(unittest.TestCase):
    setUp = ManuscriptGraphTests.setUp
    write = ManuscriptGraphTests.write
    graph = ManuscriptGraphTests.graph
    accept = ManuscriptGraphTests.accept

    def fixture(self):
        self.write("draft/main.tex", r"\input{sections/units}")
        self.write('draft/sections/units.tex', r'''\begin{definition}\label[Fixture description.]{def:base}Base.\end{definition}
% @title: Test result
% @sketch: Use the base convention.
% @related: cex:test
\begin{lemma}\label[Fixture description.]{lem:local}
Claim in the sense of \hiddenuse{def:base}.
\end{lemma}
\begin{proof}[label={prf:local}, proves={lem:local}, description={Proof of the fixture claim.}]
By \use{def:base}, the claim follows.
Compare \mention{cex:test} and \hiddenmention{cex:test}.
\end{proof}
\begin{remark}\label[Fixture description.]{rem:unrelated}Unrelated text.\end{remark}
''')
        self.write('notes/counterexamples/test.tex', r'''\documentclass[../bestiary.tex]{subfiles}
\begin{document}
% @related: lem:local
\section{A test counterexample}
\label[Fixture description.]{cex:test}
A complete construction. See \mention{lem:local}.
\end{document}
''')

    def test_four_flags_occurrences_and_selected_proof_edges(self):
        self.fixture()
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.edges['lem:local'], {'def:base'})
        refs = [o for o in graph.references('lem:local') if o['command'] != 'metadata']
        self.assertEqual([(o['command'], o['dependency'], o['visible']) for o in refs],
                         [('hiddenuse', True, False), ('use', True, True),
                          ('mention', False, True), ('hiddenmention', False, False)])
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
        self.write('notes/nested.tex', r'''\begin{definition}\label[Fixture description.]{def:base}Base.\end{definition}
\begin{lemma}[By \mention{def:base}]\label[Fixture description.]{lem:outer}
Outer. \begin{lemma}\label[Fixture description.]{lem:inner}Inner \use{def:base}.\end{lemma}
Outer again \hiddenmention{def:base}.\end{lemma}
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
            (r'\label[Fixture description.]{def:base}\use{def:base}', 'no mathematical owner'),
            (r'\begin{definition}\label[Fixture description.]{def:base}\mention{def:missing}\end{definition}', 'unresolved reference'),
            (r'\begin{definition}\label[Fixture description.]{def:base}\use{def:base}\end{definition}', 'dependency cycle'),
            (r'\begin{definition}\label[Fixture description.]{def:base}\use{def:a,def:b}\end{definition}', 'literal label'),
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
        self.write('notes/dag.tex', r'''\begin{definition}\label[Fixture description.]{def:a}A.\end{definition}
\begin{definition}\label[Fixture description.]{def:b}\use{def:a}.\end{definition}
\begin{definition}\label[Fixture description.]{def:c}\hiddenuse{def:a}.\end{definition}
\begin{definition}\label[Fixture description.]{def:d}\use{def:b}, \use{def:c}.\end{definition}
''')
        graph = self.graph()
        self.assertEqual(graph.distances('def:d', depth=1), {'def:d': 0, 'def:b': 1, 'def:c': 1})
        self.assertEqual(graph.distances('def:d')['def:a'], 2)
        self.assertEqual(graph.distances('def:a', reverse=True)['def:d'], 2)
        self.assertEqual(graph.order(['def:d'])[-1], 'def:d')
        self.assertEqual(len(graph.why('def:d', 'def:a')['path']), 3)

    def test_alternative_proofs_require_selection_and_do_not_merge_dependencies(self):
        self.write('notes/proofs.tex', r'''\begin{definition}\label[Fixture description.]{def:a}A.\end{definition}
\begin{definition}\label[Fixture description.]{def:b}B.\end{definition}
% @proof: prf:two
\begin{lemma}\label[Fixture description.]{lem:test}Claim.\end{lemma}
\begin{proof}[label={prf:one}, proves={lem:test}, description={Proof of the fixture claim.}]\use{def:a}.\end{proof}
\begin{proof}[label={prf:two}, proves={lem:test}, description={Proof of the fixture claim.}]\use{def:b}.\end{proof}
''')
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.edges['lem:test'], {'def:b'})
        self.assertEqual([b['id'] for b in graph.blocks('lem:test')], ['lem:test', 'prf:two'])
        self.assertEqual(len(graph.blocks('lem:test', 'all')), 3)
        path = self.root / 'notes/proofs.tex'
        path.write_text(path.read_text().replace('% @proof: prf:two\n', ''))
        self.assertIn('multiple proofs require', '\n'.join(self.graph().errors))

    def test_retired_commands_fail_in_authored_units(self):
        self.fixture()
        self.write("notes/retired.tex", r"\ref{lem:local}")
        self.assertIn("retired authored command", "\n".join(self.graph().errors))

    def test_metadata_in_verbatim_ignored_and_invalid_metadata_rejected(self):
        self.write('notes/meta.tex', r'''\begin{verbatim}
% @unknown: ignored
\end{verbatim}
% @sketch: First line.
% @sketch: Second line.
\begin{definition}\label[Fixture description.]{def:test}Text.\end{definition}
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
        release = ['--root', str(self.root), 'check', '--release', '--target', 'lem:local']
        with self.assertRaisesRegex(ValueError, 'visible reference cex:test is outside'):
            MODULE.main(release)
        path = self.root / 'draft/sections/units.tex'
        path.write_text(path.read_text().replace(r'\mention{cex:test}', r'\hiddenmention{cex:test}'))
        self.accept(['def:base', 'lem:local', 'prf:local'])
        with contextlib.redirect_stdout(io.StringIO()):
            MODULE.main(release)
        with self.assertRaisesRegex(argparse.ArgumentTypeError, 'depth|literal'):
            MODULE.depth_value('wrong')

    def test_scope_traversal_across_draft_notes_and_retained_sources(self):
        self.write("references/P/original.tex", r"\begin{theorem}\label{origin}An original theorem.\end{theorem}")
        self.write("notes/input.tex", r"\begin{definition}\label[A notes definition.]{def:notes}"
                   r"\hiddenuse{P:origin}\end{definition}")
        self.write("draft/main.tex", r"\begin{definition}\label[A manuscript definition.]{def:paper}"
                   r"\hiddenuse{def:notes}\end{definition}")
        graph = self.graph()
        self.assertEqual(graph.errors, [])
        self.assertEqual(graph.why("def:paper", "P:origin")["path"], ["def:paper", "def:notes", "P:origin"])
        self.assertEqual(graph.distances("def:paper", within={"def:paper"}), {"def:paper": 0})
        self.assertIn("def:notes: manuscript support", "\n".join(graph.release_errors("def:paper")))
        self.assertEqual({n["id"] for n in graph.export({"P:origin"})["nodes"]}, {"P:origin"})

    def test_equivalence_is_explicit_and_stales_after_text_change(self):
        from semantex_links import add_link, equivalent_groups, visible_links

        self.write("draft/main.tex", r"\begin{definition}\label[A definition.]{def:paper}Text.\end{definition}")
        note = r"\begin{definition}\label[Another description.]{def:notes}Text.\end{definition}"
        self.write("notes/definition.tex", note)
        add_link(self.graph(), "def:paper", "def:notes", "equivalent")
        self.assertEqual(equivalent_groups(self.graph()), {"def:paper": "def:notes"})
        self.write("notes/definition.tex", note.replace("Another description.", "Revised description."))
        self.assertEqual(visible_links(self.graph())[0]["status"], "current")
        self.write("notes/definition.tex", note.replace("Text.", "New hypothesis."))
        self.assertEqual(visible_links(self.graph())[0]["status"], "stale")
        self.assertEqual(equivalent_groups(self.graph()), {})


if __name__ == "__main__":
    unittest.main()
