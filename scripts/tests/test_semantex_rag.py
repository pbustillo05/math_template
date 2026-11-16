"""Exercise retrieval, caching, and scope selection without downloading weights."""
from contextlib import nullcontext, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from manuscript_graph import Graph, main
from semantex_links import add_link
from semantex_rag import VectorIndex, context_bundle


class FakeEmbedder:
    signature = {"fixture": 1}

    def __init__(self, dimensions=3):
        self.dimensions = dimensions
        self.calls = []
        self.invalid = False

    def running(self):
        return nullcontext(self)

    def vector(self, text, query=False):
        self.calls.append((text, query))
        if self.invalid:
            return [float("nan")] * self.dimensions
        prefix = [0.9, 0.1, 0.0] if "projection" in text else [0.0, 0.0, 1.0]
        return prefix + [0.0] * (self.dimensions - 3)


class RagTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.write("draft/main.tex", r"""\begin{lemma}\label[A projection fixes its image.]{lem:target}
Use \hiddenuse{def:premise}. Statement.
\end{lemma}
\begin{proof}[label={prf:target}, proves={lem:target}, description={Uses a projection identity.}]
Proof body.
\end{proof}
""")
        self.write("notes/premise.tex", r"\begin{definition}\label[A projection identity.]{def:premise}Premise.\end{definition}")
        self.write("references/P/paper.tex", r"\begin{theorem}\label{source}A source theorem about projection.\end{theorem}")
        for n in range(20):
            self.write(f"notes/n{n}.tex", rf"\begin{{lemma}}\label[A projection variant {n}.]{{lem:n{n:02}}}Example.\end{{lemma}}")

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        return target

    def cli_json(self, *args):
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(main(["--root", str(self.root), *args]), 0)
        return json.loads(output.getvalue())

    def test_neighbors_top_16_filters_and_equivalence(self):
        add_link(Graph(self.root), "lem:target", "lem:n00", "equivalent")
        backend = FakeEmbedder(1024)
        with patch("manuscript_graph.EmbeddingServer", return_value=backend):
            self.cli_json("rag", "build")
            neighbors = self.cli_json("neighbors", "lem:target", "--scope", "notes", "--kind", "lem",
                                      "--show", "content", "--json")
            self.assertEqual(len(neighbors), 16)
            self.assertEqual(neighbors[0]["id"], "lem:n01")
            self.assertTrue(neighbors[0]["description"])
            self.assertIn("Example.", neighbors[0]["blocks"][0]["latex"])
            self.assertTrue(all(row["scope"] == "notes" for row in neighbors))
            other = self.cli_json("neighbors", "lem:target", "--scope", "references", "--paper", "P", "--json")
            self.assertEqual([row["id"] for row in other], ["P:source"])
            search = self.cli_json("search", "projection", "--mode", "hybrid", "--scope", "draft",
                                   "--show", "content", "--json")
            self.assertEqual(search[0]["id"], "lem:target")
            self.assertEqual(len(search[0]["blocks"]), 2)

    def test_incremental_reuse_on_move_and_rebuild_on_profile_change(self):
        index = VectorIndex(self.root, "fixture", 3)
        backend = FakeEmbedder()
        first = index.build(Graph(self.root), backend)
        self.assertEqual(first["units"], first["embedded"])
        (self.root / "notes/n12.tex").rename(self.root / "notes/moved.tex")
        (self.root / "notes/n13.tex").unlink()
        path = self.root / "notes/n14.tex"
        path.write_text(path.read_text().replace("variant", "revised"))
        self.assertEqual(index.build(Graph(self.root), backend)["embedded"], 1)
        _, inventory = index.inventory()
        self.assertNotIn("lem:n13", inventory)
        self.assertEqual(Graph(self.root).nodes["lem:n12"]["file"], "notes/moved.tex")
        backend.signature = {"fixture": 2}
        backend.invalid = True
        with self.assertRaisesRegex(ValueError, "invalid"):
            index.build(Graph(self.root), backend)
        self.assertEqual(index.inventory()[0], {"fixture": 1})
        backend.invalid = False
        rebuilt = index.build(Graph(self.root), backend)
        self.assertEqual(rebuilt["units"], rebuilt["embedded"])

    def test_stale_index_and_context_budget(self):
        index = VectorIndex(self.root, "fixture", 3)
        index.build(Graph(self.root), FakeEmbedder())
        path = self.root / "notes/n14.tex"
        path.write_text(path.read_text().replace("variant", "revised"))
        graph = Graph(self.root)
        with self.assertRaisesRegex(ValueError, "stale"):
            index.rank(graph, set(graph.nodes), label="lem:target")
        bundle = context_bundle(graph, ["lem:target"], 1, 400, set(graph.nodes))
        self.assertIn("prf:target", {block["id"] for block in bundle["blocks"]})
        self.assertLessEqual(bundle["source_chars"], 400)
        self.assertEqual(self.cli_json("context", "lem:target", "--max-chars", "1", "--json")["blocks"], [])
