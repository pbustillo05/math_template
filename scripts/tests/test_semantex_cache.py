"""The disk snapshot and file cache stay live across source edits."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from manuscript_graph import Graph, main
from semantex_cache import load_graph, signature
from semantex_service import Worker
import semantex_sources


class GraphCacheTests(unittest.TestCase):
    def test_worker_fingerprint_detects_shared_files_added_edited_and_removed(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch).resolve()
            (root / "notes").mkdir()
            (root / "notes/unit.tex").write_text(r"\begin{definition}\label[A fixture.]{def:x}Input.\end{definition}")
            worker = Worker(root)
            def fingerprint():
                result = worker.graph(Graph, root).fingerprint("def:x")
                self.assertEqual(result, Graph(root).fingerprint("def:x"))
                return result
            baseline = fingerprint()
            policy = root / ".agents/skills/author/SKILL.md"
            policy.parent.mkdir(parents=True)
            policy.write_text("Initial guidance.")
            added = fingerprint()
            self.assertNotEqual(added, baseline)
            policy.write_text("Changed guidance.")
            self.assertNotEqual(fingerprint(), added)
            policy.unlink()
            self.assertEqual(fingerprint(), baseline)

    def test_edited_markdown_matches_a_full_scan_on_disk_and_in_worker(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch).resolve()
            notes = root / "notes"
            notes.mkdir()
            (notes / "claim.tex").write_text(
                r"\begin{lemma}\label[A claim.]{lem:claim}Text.\end{lemma}")
            guide = notes / "README.md"
            guide.write_text(r"See \mention{lem:claim}.")
            worker = Worker(root)
            previous = worker.graph(Graph, root)
            for content in ("\nNew prose.\n", "\nFirst\n" + r"\hiddenmention{lem:claim}",
                            r"\mention{lem:missing}", r"\use{lem:claim}", r"Fixed \mention{lem:claim}"):
                guide.write_text(content)
                expected = Graph(root)
                with patch.object(Graph, "__init__", side_effect=AssertionError("unnecessary rebuild")):
                    disk = load_graph(Graph, root)
                    resident = worker.graph(Graph, root)
                for graph in (disk, resident):
                    self.assertEqual(graph.errors, expected.errors)
                    self.assertEqual(graph.occurrences, expected.occurrences)
                    self.assertEqual(graph.decoded_file("notes/README.md"), content)
                    self.assertEqual(graph.export(), expected.export())
                if content.startswith("\n"):
                    self.assertIs(resident, previous)

    def test_markdown_backrefs_follow_moves_and_distinguish_scope(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch).resolve()
            notes = root / "notes"
            notes.mkdir()
            (notes / "claim.tex").write_text(r"\begin{lemma}\label[A claim.]{lem:claim}\end{lemma}")
            guide = notes / "README.md"
            guide.write_text((r"See \mention{lem:claim}." + "\n") * 2)
            draft = root / "draft"
            draft.mkdir()
            (draft / "guide.md").write_text(r"\mention{lem:claim}")

            def backrefs(*options):
                output = io.StringIO()
                with redirect_stdout(output):
                    main(["--root", str(root), "backrefs", "lem:claim", "--markdown", *options])
                return output.getvalue()

            self.assertEqual(backrefs("--scope", "notes"), "notes/README.md:1\n")
            self.assertEqual(len(json.loads(backrefs("--json"))), 3)
            moved = guide.rename(notes / "roadmap.md")
            self.assertEqual(backrefs("--scope", "notes"), "notes/roadmap.md:1\n")
            moved.unlink()
            self.assertEqual(backrefs(), "draft/guide.md:1\n")

    def test_markdown_named_as_registry_evidence_invalidates_the_structure(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch).resolve()
            path = root / "notes/evidence.md"
            path.parent.mkdir()
            path.write_text("Old evidence")
            with patch("semantex_cache.external_inputs", return_value={path}):
                before = signature(root)
                path.write_text("New evidence")
                self.assertNotEqual(before.structure, signature(root).structure)

    def test_snapshot_and_single_file_reparse(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch).resolve()
            files = {
                "draft/main.tex": r"\begin{lemma}\label[A claim.]{lem:claim}\hiddenuse{def:base}\end{lemma}",
                "notes/base.tex": r"\begin{definition}\label[An input.]{def:base}Before.\end{definition}",
                "references/P/paper.tex": r"\begin{theorem}\label{upstream}Source.\end{theorem}",
            }
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            first = load_graph(Graph, root)
            self.assertEqual(first.errors, [])
            with patch.object(Graph, "__init__", side_effect=AssertionError("warm cache parsed the graph")):
                warm = load_graph(Graph, root)
                self.assertEqual(warm.export(), first.export())
                self.assertEqual(warm.blocks("lem:claim"), first.blocks("lem:claim"))
            changed = root / "notes/base.tex"
            stamp = changed.stat()
            changed.write_text(files["notes/base.tex"].replace("Before", "Edited"))
            os.utime(changed, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            scan = Graph.scan
            with patch.object(Graph, "scan", autospec=True, side_effect=scan) as authored, \
                    patch.object(semantex_sources, "scan_source", wraps=semantex_sources.scan_source) as retained:
                after = load_graph(Graph, root)
                self.assertEqual(after.errors, [])
                self.assertEqual(authored.call_args.args[1], changed)
                self.assertEqual(authored.call_count, 1)
                retained.assert_not_called()
            self.assertIn("Edited", after.source("def:base"))
            self.assertEqual(after.export(), Graph(root).export())
            changed.unlink()
            self.assertTrue(any("unresolved reference" in error for error in load_graph(Graph, root).errors))

    def test_overlay_does_not_replace_the_disk_snapshot(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch).resolve()
            notes = root / "notes"
            notes.mkdir()
            source = r"\begin{lemma}\label[A claim.]{lem:claim}Saved.\end{lemma}"
            (notes / "claim.tex").write_text(source)
            load_graph(Graph, root)
            overlay = load_graph(Graph, root, {"notes/claim.tex": source.replace("Saved", "Unsaved")})
            self.assertIn("Unsaved", overlay.source("lem:claim"))
            self.assertIn("Saved", load_graph(Graph, root).source("lem:claim"))
