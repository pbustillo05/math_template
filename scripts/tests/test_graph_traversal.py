"""Forward traversal preserves selected-proof semantics without a full graph copy."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from manuscript_graph import Graph

class TraversalTests(unittest.TestCase):
    def setUp(self):
        g = self.g = Graph.__new__(Graph)
        g.edges = {"claim": {"base"}, "base": {"leaf"}, "leaf": set(),
                   "prf:selected": {"leaf"}, "prf:alternate": {"isolated"}, "isolated": set()}
        g.nodes = {n: {} for n in g.edges}
        g.aliases = {"historical": "claim"}
        g.selected_proofs = {"claim": "prf:selected"}
        g.occurrences = [{"owner": "claim", "target": "prf:alternate"}]

    def test_forward_support_depth_and_alias_without_global_copy(self):
        with patch.object(self.g, "adjacency", side_effect=AssertionError("whole graph copy")):
            self.assertEqual(self.g.distances("historical", support=True),
                             {"claim": 0, "base": 1, "prf:selected": 1, "leaf": 2})
            self.assertEqual(self.g.distances("claim", depth=1, support=True),
                             {"claim": 0, "base": 1, "prf:selected": 1})
            self.assertEqual(self.g.distances("claim"), {"claim": 0, "base": 1, "leaf": 2})

    def test_successive_walks_observe_edge_and_proof_changes(self):
        before = self.g.distances("claim", support=True)
        self.g.selected_proofs["claim"] = "prf:alternate"
        self.g.edges["claim"].add("isolated")
        after = self.g.distances("claim", support=True)
        self.assertNotIn("isolated", before)
        self.assertEqual(after["isolated"], 1)
        self.assertIn("prf:alternate", after)
        self.assertNotIn("prf:selected", after)
        self.assertEqual(self.g.edges["claim"], {"base", "isolated"})

    def test_reverse_mentions_scope_and_public_errors(self):
        self.assertEqual(self.g.distances("leaf", reverse=True),
                         {"leaf": 0, "base": 1, "prf:selected": 1, "claim": 2})
        self.assertIn("prf:alternate", self.g.distances("claim", mentions=True))
        self.assertEqual(self.g.distances("historical", within={"claim", "base"}),
                         {"claim": 0, "base": 1})
        with self.assertRaisesRegex(ValueError, "outside the requested scope"):
            self.g.distances("claim", within={"base"})
        with self.assertRaisesRegex(ValueError, "unknown node"):
            self.g.distances("missing")
