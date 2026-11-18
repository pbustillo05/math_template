"""Scoped runtime data and actual two-pass LaTeX integration regressions."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from manuscript_graph import Graph
from semantex_runtime import generate_runtime, plan_contexts, register_document, runtime_key, tex_identifier
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[2] / "preamble/semantex.sty"


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="semantex-runtime-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        for folder in ("draft", "notes", "workflow", "preamble"):
            (self.root / folder).mkdir()
        shutil.copy(PACKAGE, self.root / "preamble/semantex.sty")
        self.registry = {"schema_version": 1, "contexts": {}}
        for name in ("main", "a", "b", "child"):
            labels = {"def:host": "def:host"} if name == "main" else {
                "lem:x": f"lem:{name}:x", "prf:x": f"prf:{name}:x"}
            if name == "a":
                labels["eq:x"] = "eq:a:x"
            self.registry["contexts"][f"ctx:{name}"] = {
                "file": "draft/main.tex" if name == "main" else f"notes/{name}.tex",
                "labels": labels,
                "references": {"lem:new": "lem:b:x", "prf:new": "prf:b:x",
                               "def:lost": "gap:lost"} if name == "a" else {}}
        (self.root / "workflow/document-contexts.json").write_text(json.dumps(self.registry))
        (self.root / "workflow/unresolved.json").write_text(json.dumps({
            "schema_version": 1, "records": {"gap:lost": {
                "original_label": "def:lost", "source_document": "missing-version.tex",
                "source_sha256": "a" * 64, "reason": "The cited historical version is unavailable.",
                "status": "unresolved", "mathematical_statement": None, "candidates": []}}}))
        self.preamble = r"""\documentclass{article}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amsthm,subfiles,hyperref}
\usepackage{../preamble/semantex}
\newtheorem{lemma}{Lemma}
\newtheorem{definition}{Definition}
\providecommand{\lemmaautorefname}{Lemma}
\providecommand{\definitionautorefname}{Definition}
\pdfcompresslevel=0 \pdfobjcompresslevel=0
\input{../runtime.tex}
"""
        (self.root / "draft/main.tex").write_text(self.preamble + r"""
\begin{document}
\SemanTeXContext{ctx:main}
\begin{definition}\label[The host object.]{def:host}Host.\end{definition}
\subfile{../notes/a.tex}
\subfile{../notes/b.tex}
Host restored: \mention{def:host}.
\end{document}
""")
        for name in ("a", "b", "child"):
            extra = r"""
\begin{equation}\label[A local equation.]{eq:x}1=1\end{equation}
Equation reference: \mention{eq:x}.
New version: \mention{lem:new}.
New proof: \mention{prf:new}.
Missing version: \mention{def:lost}.
\subfile{child.tex}
Context restored: \mention{lem:x}.
""" if name == "a" else ""
            text = (r"\documentclass[../draft/main.tex]{subfiles}" + "\n" +
                    r"\begin{document}" + "\n" + f"\\SemanTeXContext{{ctx:{name}}}\n" +
                    f"% @title: Version {name}\n" +
                    r"\begin{lemma}\label[A version-specific claim.]{lem:x}Claim." +
                    r"\end{lemma}" + "\n" +
                    r"\begin{proof}[label={prf:x},proves={lem:x},description={The direct argument.}]" +
                    r"Immediate.\end{proof}" + "\n" +
                    f"Local {name}: " + r"\mention{lem:x}. Proof: \mention{prf:x}." + "\n" +
                    extra + r"\end{document}" + "\n")
            (self.root / f"notes/{name}.tex").write_text(text)

    def generate(self):
        graph = Graph(self.root)
        self.assertEqual(graph.errors, [])
        result = generate_runtime(graph, self.registry)
        (self.root / "runtime.tex").write_text(result)
        return graph, result

    def test_register_add_edit_move_retry_and_idempotence(self):
        source = self.root / "notes/new.tex"
        body = r"\begin{definition}\label[An input.]{def:new}Input.\end{definition}"
        source.write_text(body)
        registry = self.root / "workflow/document-contexts.json"
        from semantex_runtime import replace_document
        def interrupted(path, data):
            if path == source:
                raise OSError("interrupted insertion")
            replace_document(path, data)
        with patch("semantex_runtime.replace_document", side_effect=interrupted), self.assertRaises(OSError):
            register_document(self.root, "notes/new.tex")
        saved = json.loads(registry.read_text())["contexts"]
        identity = next(key for key, record in saved.items() if record["file"] == "notes/new.tex")
        register_document(self.root, "notes/new.tex")
        self.assertIn(identity, source.read_text())
        self.assertIn(body, source.read_text())
        original = registry.read_bytes(), source.read_bytes()
        register_document(self.root, "notes/new.tex")
        self.assertEqual(original, (registry.read_bytes(), source.read_bytes()))
        moved = source.rename(self.root / "notes/moved.tex")
        moved.write_text(moved.read_text().replace(body, body + body.replace("def:new", "def:next")))
        register_document(self.root, "notes/moved.tex")
        updated = json.loads(registry.read_text())
        self.assertEqual(updated["contexts"].pop(identity),
                         {"file": "notes/moved.tex", "labels": {"def:next": "def:next", "def:new": "def:new"},
                          "references": {}})
        self.assertEqual(updated, self.registry)
        generate_runtime(Graph(self.root), json.loads(registry.read_text()))
        with self.assertRaises(ValueError):
            register_document(self.root, "references/Retained/source.tex")

    def test_generator_and_immutable_labels(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*.tex")}
        graph, runtime = self.generate()
        self.assertIn(f"\\SemanTeXDeclareReferenceKey{{ctx:a}}{{{runtime_key('lem:new')}}}{{{runtime_key('lem:b:x')}}}", runtime)
        self.assertIn(f"\\SemanTeXDeclareProofTargetKey{{{runtime_key('prf:a:x')}}}{{{runtime_key('lem:a:x')}}}", runtime)
        self.assertIn(f"\\SemanTeXDeclareGapKey{{{runtime_key('gap:lost')}}}", runtime)
        self.assertIn((self.root / "notes/b.tex").as_uri(), runtime)
        self.assertIn(r"\#L", runtime)
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)
        self.assertEqual(graph.proofs["prf:a:x"], "lem:a:x")

    def test_move_keeps_context_and_updates_url(self):
        before, _ = self.generate()
        old = self.root / "notes/b.tex"
        new = self.root / "notes/relocated.tex"
        old.rename(new)
        after, runtime = self.generate()
        self.assertEqual(before.proofs, after.proofs)
        self.assertEqual(before.edges, after.edges)
        self.assertIn(new.as_uri(), runtime)
        self.assertNotIn(old.as_uri(), runtime)
        self.assertEqual(after.nodes["lem:b:x"]["source_label"], "lem:x")

    def test_reject_structural_errors_stale_registry_and_missing_sources(self):
        graph, _ = self.generate()
        incomplete = dict(self.registry, diagnostic_status='incomplete-do-not-apply')
        with self.assertRaisesRegex(ValueError, 'incomplete diagnostic'):
            generate_runtime(graph, incomplete)
        graph.errors.append("a real structural defect")
        with self.assertRaisesRegex(ValueError, "structural errors"):
            generate_runtime(graph, self.registry)
        graph.errors.clear()
        self.registry["contexts"]["ctx:a"]["labels"]["lem:x"] = "lem:b:x"
        with self.assertRaisesRegex(ValueError, "disagree"):
            generate_runtime(graph, self.registry)
        self.registry["contexts"]["ctx:a"]["labels"]["lem:x"] = "lem:a:x"
        (self.root / "notes/b.tex").unlink()
        with self.assertRaisesRegex(ValueError, "absent"):
            generate_runtime(graph, self.registry)

    def test_plan_is_insert_only_hash_guarded_and_reusable(self):
        graph, _ = self.generate()
        for path in graph.files:
            text = graph.files[path].decode()
            text = re.sub(r"\\SemanTeXContext\{[^}]+\}", "", text)
            graph.files[path] = text.encode()
        proposed, manifest = plan_contexts(graph, self.registry)
        self.assertEqual(proposed, self.registry)
        self.assertEqual(len(manifest["files"]), 4)
        for entry in manifest["files"]:
            data = graph.files[entry["file"]]
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry["before_sha256"])
            text = data.decode()
            for edit in sorted(entry["insertions"], key=lambda x: x["offset"], reverse=True):
                text = text[:edit["offset"]] + edit["text"] + text[edit["offset"]:]
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), entry["after_sha256"])
            self.assertEqual(text.count(r"\SemanTeXContext"), 1)
            self.assertIn(r"\label[", text)

    def test_fragment_plan_scopes_context_and_preserves_proposed_uuid(self):
        graph, _ = self.generate()
        graph.files["notes/fragment.tex"] = b"A fragment.\n"
        proposed, manifest = plan_contexts(graph, self.registry)
        self.assertEqual(len(manifest["files"]), 1)
        edits = manifest["files"][0]["insertions"]
        self.assertTrue(edits[0]["text"].startswith("\\begingroup\n\\SemanTeXContext"))
        self.assertEqual(edits[1]["text"], "\n\\endgroup\n")
        proposed_again, repeated = plan_contexts(graph, proposed)
        self.assertEqual(proposed, proposed_again)
        self.assertEqual(manifest, repeated)

    def test_runtime_hash_collisions_are_rejected(self):
        graph, _ = self.generate()
        with patch('semantex_runtime.runtime_key', return_value='A' * 32):
            with self.assertRaisesRegex(ValueError, 'collision'):
                generate_runtime(graph, self.registry)

    def test_identifier_data_is_escaped_not_executed(self):
        original = r'Paper:bad\input{DO-NOT-READ}%#$&^'
        shown = tex_identifier(original)
        self.assertNotIn(r'\input{DO-NOT-READ}', shown)
        self.assertIn(r'\textbackslash{}', shown)
        self.assertIn(r'\{', shown)
        self.assertIn(r'\%', shown)
        self.assertIn(r'\$', shown)
        self.assertRegex(runtime_key(original), r'^[0-9A-F]{32}$')

    def test_citation_targets_kept_and_unreferenced_retained_metadata_omitted(self):
        graph, _ = self.generate()
        for identity in ('Paper:cited', 'Paper:unused'):
            graph.nodes[identity] = dict(graph.nodes['lem:b:x'], id=identity, origin='retained')
        graph.citations.append({'targets': ['Paper:cited']})
        runtime = generate_runtime(graph, self.registry)
        self.assertIn(f'\\SemanTeXDeclareExternalKey{{{runtime_key("Paper:cited")}}}', runtime)
        self.assertNotIn(f'\\SemanTeXDeclareExternalKey{{{runtime_key("Paper:unused")}}}', runtime)

    def install_alias_fixture(self):
        for name in ('a', 'b', 'child'):
            record = self.registry['contexts'][f'ctx:{name}']
            record['labels'].update({'lem:old': f'lem:{name}:old',
                                     'current-prf:x': f'current-prf:{name}:x'})
            record['aliases'] = {'lem:old': 'lem:x', 'current-prf:x': 'prf:x'}
            path = self.root / f'notes/{name}.tex'
            text = path.read_text()
            text = text.replace(r'{lem:x}Claim.', r'{lem:x}\label{lem:old}Claim.')
            text = text.replace(r'Immediate.\end{proof}',
                                r'\phantomsection\label{current-prf:x}Immediate.\end{proof}')
            extra = f'\nAlias {name}: ' + r'\mention{lem:old}. Alias proof: \mention{current-prf:x}.'
            if name == 'a':
                extra += r'\par Qualified external alias: \mention{lem:b:old}.'
                extra += r' Qualified external proof alias: \mention{current-prf:b:x}.'
            path.write_text(text.replace(r'\end{document}', extra + '\n' + r'\end{document}'))
        (self.root / 'workflow/document-contexts.json').write_text(json.dumps(self.registry))

    def test_alias_context_plan_and_move_preserve_native_declarations(self):
        self.install_alias_fixture()
        graph, runtime = self.generate()
        self.assertEqual(graph.aliases['current-prf:b:x'], 'prf:b:x')
        self.assertEqual(graph.declarations_by_file['notes/b.tex']['current-prf:x'], 'current-prf:b:x')
        proposed, manifest = plan_contexts(graph, self.registry)
        self.assertEqual(proposed, self.registry)
        self.assertEqual(manifest['files'], [])
        self.assertIn(f'\\SemanTeXDeclareAliasKey{{{runtime_key("current-prf:b:x")}}}{{{runtime_key("prf:b:x")}}}', runtime)
        (self.root / 'notes/b.tex').rename(self.root / 'notes/moved-b.tex')
        moved, updated = self.generate()
        self.assertEqual(moved.aliases, graph.aliases)
        self.assertEqual(moved.proofs, graph.proofs)
        self.assertIn((self.root / 'notes/moved-b.tex').as_uri(), updated)
        self.assertIn(r'\label{current-prf:x}', (self.root / 'notes/moved-b.tex').read_text())

    @unittest.skipUnless(shutil.which('pdflatex') and shutil.which('pdftotext'), 'TeX and Poppler required')
    def test_aliases_have_distinct_anchors_and_canonical_proof_display(self):
        self.install_alias_fixture()
        originals = {path: path.read_bytes() for path in self.root.rglob('*.tex')}
        self.generate()
        for relative in ('notes/a.tex', 'draft/main.tex'):
            path = self.root / relative
            for _ in range(2):
                result = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error', path.name],
                                        cwd=path.parent, text=True, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout[-6000:])
            aux = path.with_suffix('.aux').read_text()
            for identity in ('lem:a:x', 'lem:a:old', 'prf:a:x', 'current-prf:a:x'):
                self.assertEqual(aux.count(f'\\newlabel{{semantex@{runtime_key(identity)}}}'), 1)
            proof_lines = [line for line in aux.splitlines() if line.startswith(
                tuple(f'\\newlabel{{semantex@{runtime_key(identity)}}}' for identity in ('prf:a:x', 'current-prf:a:x')))]
            anchors = [re.findall(r'\{(section\*\.\d+)\}', line)[0] for line in proof_lines]
            self.assertEqual(len(set(anchors)), 2, 'The inherited phantomsection alias anchor is retained.')
            log = path.with_suffix('.log').read_text()
            self.assertNotIn('multiply defined', log)
            text = subprocess.check_output(['pdftotext', '-layout', str(path.with_suffix('.pdf')), '-'], text=True)
            text = re.sub(r'([a-z])-\s*\n\s*([a-z])', r'\1\2', text)
            text = ' '.join(text.split())
            self.assertIn('Alias a: Lemma 1. Alias proof: Proof of Lemma 1.', text)
            self.assertNotIn('??', text)
            if relative.startswith('notes'):
                self.assertIn('Qualified external alias: Lemma:', text)
                self.assertIn('Qualified external proof alias: Proof of Lemma:', text)
            else:
                self.assertIn('Qualified external alias: Lemma 3.', text)
                self.assertIn('Qualified external proof alias: Proof of Lemma 3.', text)
        for path, data in originals.items():
            self.assertEqual(path.read_bytes(), data)

    @unittest.skipUnless(shutil.which("pdflatex") and shutil.which("pdftotext"), "TeX and Poppler required")
    def test_two_pass_standalone_and_assembly(self):
        self.generate()

        def compile_file(relative, stale_aux=False):
            path = self.root / relative
            for _ in range(2):
                process = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", path.name],
                                         cwd=path.parent, text=True, capture_output=True, timeout=60)
                self.assertEqual(process.returncode, 0, process.stdout[-6000:])
                if stale_aux and _ == 0:
                    with path.with_suffix(".aux").open("a") as handle:
                        handle.write("\n\\SemanTeXProofTarget{prf:a:x}{lem:b:x}\n")
                        handle.write(f"\n\\SemanTeXProofTargetKey{{{runtime_key('prf:a:x')}}}{{{runtime_key('lem:b:x')}}}\n")
                        handle.write(f"\\newlabel{{semantex@{runtime_key('gap:lost')}}}{{{{99}}{{1}}{{}}{{lemma.99}}{{}}}}\n")
            text = subprocess.check_output(["pdftotext", "-layout", str(path.with_suffix(".pdf")), "-"], text=True)
            text = re.sub(r"([a-z])-\s*\n\s*([a-z])", r"\1\2", text)
            log = path.with_suffix(".log").read_text()
            aux = path.with_suffix(".aux").read_text()
            return " ".join(text.split()), log, aux, path.with_suffix(".pdf").read_bytes()

        standalone, log, aux, pdf = compile_file("notes/a.tex", stale_aux=True)
        self.assertIn("Local a: Lemma 1. Proof: Proof of Lemma 1.", standalone)
        self.assertIn("Local child: Lemma 2. Proof: Proof of Lemma 2.", standalone)
        self.assertIn("Context restored: Lemma 1.", standalone)
        self.assertIn("Equation reference: Equation 1.", standalone)
        self.assertIn("New version: Lemma:", standalone)
        self.assertIn("New proof: Proof of Lemma:", standalone)
        self.assertIn("lem:b:x", standalone)
        self.assertIn("Unavailable source: def:lost", standalone)
        self.assertNotIn("??", standalone)
        self.assertIn(f"\\newlabel{{semantex@{runtime_key('lem:a:x')}}}", aux)
        self.assertIn(f"\\SemanTeXProofTargetKey{{{runtime_key('prf:a:x')}}}{{{runtime_key('lem:a:x')}}}", aux)
        self.assertNotIn(r"\newlabel{lem:x}", aux)
        self.assertNotIn("multiply defined", log)
        self.assertIn(b"notes/b.tex", pdf)
        self.assertIn(b"/Subtype/Link", pdf)
        assembly, log, aux, _ = compile_file("draft/main.tex")
        self.assertIn("New version: Lemma 3.", assembly)
        self.assertIn("Local b: Lemma 3. Proof: Proof of Lemma 3.", assembly)
        self.assertIn("Host restored: Definition 1.", assembly)
        self.assertIn("Context restored: Lemma 1.", assembly)
        self.assertNotIn("??", assembly)
        self.assertNotIn("multiply defined", log)
        # Unknown references remain conspicuous, and citation locators retain
        # the original citation implementation and key-value semantics.
        (self.root / "draft/citecheck.tex").write_text(self.preamble + r"""
\begin{document}
Unknown: \mention{lem:never-existed}.
\par
Citation: \cite[text={Theorem 3.2},label={lem:upstream}]{sample}.
\begin{thebibliography}{1}\bibitem{sample}Source.\end{thebibliography}
\end{document}
""")
        extra, log, _, _ = compile_file("draft/citecheck.tex")
        self.assertIn("Unresolved reference: lem:never-existed", extra)
        self.assertIn("Unresolved reference lem:never-existed", log)
        self.assertIn("[1, Theorem 3.2]", extra)
        self.assertNotIn("??", extra)
        (self.root / "draft/unknowncontext.tex").write_text(self.preamble +
            r"\begin{document}\SemanTeXContext{ctx:unknown}Text.\end{document}")
        rejected = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "unknowncontext.tex"],
                                  cwd=self.root / "draft", text=True, capture_output=True, timeout=60)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("Unregistered document context ctx:unknown", rejected.stdout)

    @unittest.skipUnless(shutil.which("pdflatex") and shutil.which("pdftotext"), "TeX and Poppler required")
    def test_actual_native_identifier_alphabet_and_safe_rendering(self):
        # Native spellings sampled from the pinned source index. Fixture
        # statements are synthetic; this test makes no claim about the papers.
        labels = {
            'CHH+24': 'sec:introduction',
            'DFM+24': 'garner_lifting',
            'CŠ25': 'defn: Cube p,q operads',
            'Mnë07': 'pic1',
            'JPR22': 'Transformation:eta^1',
            'Lou23': 'lemma:object is $S$ local if fibrant',
            'KSW26': 'eq:"functoriality"-on-hyprefinements',
            'AF20b': "main.thm'",
            'AFT17': 'pull-back<=k',
        }
        for paper, label in labels.items():
            directory = self.root / 'references' / paper
            directory.mkdir(parents=True)
            (directory / 'paper.tex').write_text(r'\begin{lemma}\label{' + label + r'}Fixture.\end{lemma}')
        full_ids = [paper + ':' + label for paper, label in labels.items()]
        bindings = self.registry['contexts']['ctx:a']['references']
        for index, identity in enumerate(full_ids):
            bindings[f'native:{index}'] = identity
        (self.root / 'workflow/document-contexts.json').write_text(json.dumps(self.registry))
        source = self.root / 'notes/a.tex'
        original = source.read_text()
        references = '\n'.join(r'\par Direct: \mention{' + identity + r'}. Bound: \mention{native:' + str(index) + '}.'
                               for index, identity in enumerate(full_ids))
        source.write_text(original.replace(r'\end{document}', references + '\n' + r'\end{document}'))
        graph, runtime = self.generate()
        # Unreferenced upstream virtual nodes need no runtime metadata. Actual
        # authored mentions and citation targets remain eligible.
        for identity in full_ids:
            self.assertIn(f'\\SemanTeXDeclareExternalKey{{{runtime_key(identity)}}}', runtime)
        for _ in range(2):
            result = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'a.tex'],
                                    cwd=source.parent, text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout[-6000:])
        text = subprocess.check_output(['pdftotext', '-layout', str(source.with_suffix('.pdf')), '-'], text=True)
        text = ' '.join(text.split())
        for identity in full_ids:
            self.assertIn(identity, text)
        self.assertNotIn('??', text)
        self.assertNotIn('CÅ', text)
        self.assertNotIn('Unresolved reference', text)
        self.assertEqual(source.read_text(), original.replace(r'\end{document}', references + '\n' + r'\end{document}'))
        malicious = r'Paper:bad\input{DO-NOT-READ}%#$&^'
        (self.root / 'draft/DO-NOT-READ.tex').write_text(r'\errmessage{NATIVE IDENTIFIER EXECUTED AS TEX}')
        safe = self.root / 'draft/safeidentifier.tex'
        safe.write_text(self.preamble +
            f'\\SemanTeXDeclareReferenceKey{{ctx:a}}{{{runtime_key("native:unsafe")}}}{{{runtime_key(malicious)}}}\n' +
            f'\\SemanTeXDeclareExternalKey{{{runtime_key(malicious)}}}{{{tex_identifier(malicious)}}}{{file:///tmp/source.tex}}\n' +
            r'\begin{document}\SemanTeXContext{ctx:a}\mention{native:unsafe}' +
            r'\par Unknown: \mention{Paper:\input{DO-NOT-READ}}\end{document}')
        result = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error', safe.name],
                                cwd=safe.parent, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout[-6000:])
        self.assertNotIn('NATIVE IDENTIFIER EXECUTED AS TEX', result.stdout)


if __name__ == "__main__":
    unittest.main()
