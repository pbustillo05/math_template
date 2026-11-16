#!/usr/bin/env python3
"""Evaluate locally installed profiles on the small mathematical retrieval fixture."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import resource
from statistics import median
import sys
import tempfile
import time

from manuscript_graph import Graph
from semantex_embeddings import DEFAULT, PROFILES, EmbeddingServer
from semantex_rag import VectorIndex, hybrid_rank, lexical_rank

ROOT = Path(__file__).resolve().parents[1]


def fixture(root):
    examples = json.loads((ROOT / "scripts/tests/fixtures/embedding_queries.json").read_text())
    sources = defaultdict(list)
    queries = []
    for scope, label, statement, query in examples:
        env = {"lem": "lemma", "def": "definition", "cex": "counterexample"}[label.split(":")[0]]
        if scope == "references":
            sources["references/Fixture/paper.tex"].append(
                rf"\begin{{{env}}}\label{{{label}}}{statement}\end{{{env}}}")
            label = "Fixture:" + label
        else:
            sources[f"{scope}/fixture.tex"].append(
                rf"\begin{{{env}}}\label[{statement}]{{{label}}}{statement}\end{{{env}}}")
        if query:
            queries.append((query, label))
    for file, units in sources.items():
        path = root / file
        path.parent.mkdir(parents=True)
        path.write_text("\n".join(units) + "\n")
    return queries


def benchmark(profile):
    with tempfile.TemporaryDirectory(prefix="semantex-bench-") as scratch:
        root = Path(scratch).resolve()
        queries = fixture(root)
        graph = Graph(root)
        if graph.errors:
            raise ValueError("\n".join(graph.errors))
        backend = EmbeddingServer(ROOT, profile)
        index = VectorIndex(root, profile, PROFILES[profile]["dimensions"])
        timing = {}
        for mode in ("cold", "cached"):
            start = time.monotonic()
            counts = index.build(graph, backend)
            timing[mode] = dict(counts, seconds=round(time.monotonic() - start, 3))

        ranks, query_times = defaultdict(list), []
        with backend.running():
            for query, expected in queries:
                start = time.monotonic()
                semantic = index.rank(graph, set(graph.nodes), query=query, backend=backend)
                query_times.append(time.monotonic() - start)
                lexical = lexical_rank(graph, query, set(graph.nodes))
                for mode, ranking in (("lexical", lexical), ("semantic", semantic),
                                      ("hybrid", hybrid_rank(lexical, semantic))):
                    position = next((i for i, (label, _) in enumerate(ranking, 1) if label == expected), None)
                    ranks[mode].append(position)
        scores = {}
        for mode, values in ranks.items():
            scores[mode] = {"recall_at_16": round(sum(p is not None and p <= 16 for p in values) / len(values), 4),
                            "mrr_at_5": round(sum(1/p for p in values if p is not None and p <= 5) / len(values), 4),
                            "ranks": values}
        rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        return dict(profile=profile, queries=len(queries), scores=scores, build=timing,
                    warm_query_median_s=round(median(query_times), 3),
                    max_child_rss_mib=round(rss / (1024 ** (2 if sys.platform == "darwin" else 1)), 1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default=DEFAULT)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.profile), indent=2))
