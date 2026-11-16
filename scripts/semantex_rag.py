"""Local vector cache, exact nearest neighbors, and hybrid retrieval."""
from contextlib import closing
import hashlib
import json
import math
import re
import sqlite3
import struct

from semantex_links import equivalent_groups

INPUT_VERSION = 1


def input_digest(text):
    return hashlib.sha256(f"{INPUT_VERSION}\0{text}".encode()).hexdigest()


def embedding_inputs(graph, labels=None):
    for label in sorted(graph.nodes if labels is None else labels):
        node = graph.nodes[label]
        category = node.get("environment")
        if node["origin"] == "retained":
            from manuscript_graph import KINDS
            if category not in KINDS:
                continue
            excerpt = " ".join(graph.reviewed_source(label).split())[:1500]
            yield label, f"{category}\n{excerpt}"
        elif node["description"]:
            from manuscript_graph import NAVIGATION
            if node["kind"] not in NAVIGATION:
                yield label, f"{category}\n{node['description']}"


def normalize(vector, length):
    if len(vector) != length or not all(isinstance(x, (float, int)) and math.isfinite(x) for x in vector):
        raise ValueError(f"embedding server returned invalid {length}-dimensional vector")
    norm = math.sqrt(math.fsum(x * x for x in vector))
    if not norm:
        raise ValueError("embedding server returned a zero vector")
    return tuple(x / norm for x in vector)


class VectorIndex:
    def __init__(self, root, profile, dimensions):
        self.path = root / "build/semantex/rag" / profile / "index.sqlite3"
        self.format = struct.Struct(f"<{dimensions}f")
        self.dimensions = dimensions

    def connect(self, write=False):
        if write:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        elif not self.path.is_file() or not self.path.stat().st_size:
            raise ValueError("no semantic index for this profile; run semantex rag build")
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA mmap_size=134217728")
        return closing(db)

    def build(self, graph, backend):
        inputs = dict(embedding_inputs(graph))
        digests = {n: input_digest(s) for n, s in inputs.items()}
        signature = json.dumps(backend.signature, sort_keys=True)
        new = 0
        with self.connect(write=True) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS model (signature TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS vectors (digest TEXT PRIMARY KEY, v BLOB NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS units (id TEXT PRIMARY KEY, digest TEXT NOT NULL)")
            current = db.execute("SELECT signature FROM model").fetchone()
            if not current or current[0] != signature:
                db.execute("DELETE FROM model")
                db.execute("INSERT INTO model VALUES (?)", (signature,))
                db.execute("DELETE FROM vectors")
            cached = {row[0] for row in db.execute("SELECT digest FROM vectors")}
            pending = {digests[label]: text for label, text in inputs.items() if digests[label] not in cached}
            if pending:
                with backend.running():
                    for digest, text in pending.items():
                        vector = normalize(backend.vector(text), self.dimensions)
                        db.execute("INSERT INTO vectors VALUES (?, ?)", (digest, self.format.pack(*vector)))
                        new += 1
            db.execute("DELETE FROM units")
            db.executemany("INSERT INTO units VALUES (?, ?)", digests.items())
            db.execute("DELETE FROM vectors WHERE digest NOT IN (SELECT digest FROM units)")
        return {"units": len(inputs), "embedded": new, "reused_inputs": len(set(digests.values())) - new}

    def inventory(self):
        if not self.path.is_file() or not self.path.stat().st_size:
            return None, {}
        with self.connect() as db:
            signature = db.execute("SELECT signature FROM model").fetchone()
            return json.loads(signature[0]) if signature else None, dict(db.execute("SELECT * FROM units"))

    def status(self, graph, focused, scopes, paper=None):
        model, indexed = self.inventory()
        coverage = {scope: {"eligible": 0, "current": 0, "papers": {}} for scope in sorted(scopes)}
        if "references" in coverage:
            for key in sorted([paper] if paper else graph.papers):
                coverage["references"]["papers"][key] = {"eligible": 0, "current": 0, "described": 0}
        for label, text in embedding_inputs(graph, focused):
            node = graph.nodes[label]
            counts = coverage.setdefault(node["scope"], {"eligible": 0, "current": 0, "papers": {}})
            current = int(indexed.get(label) == input_digest(text))
            counts["eligible"] += 1
            counts["current"] += current
            if node.get("bib_key"):
                paper = counts["papers"].setdefault(node["bib_key"], {"eligible": 0, "current": 0, "described": 0})
                paper["eligible"] += 1
                paper["current"] += current
                paper["described"] += bool(node["description"])
        return {"model": model, "coverage": coverage,
                "removed": sorted(indexed.keys() - dict(embedding_inputs(graph)).keys())}

    def rank(self, graph, focused, *, query=None, label=None, backend=None, all_versions=False):
        included = dict(embedding_inputs(graph, focused | ({label} if label else set())))
        with self.connect() as db:
            db.execute("BEGIN")
            model = db.execute("SELECT signature FROM model").fetchone()
            if query is not None and (not model or json.loads(model[0]) != backend.signature):
                raise ValueError("the local embedding runtime has changed; run semantex rag build")
            indexed = dict(db.execute("SELECT * FROM units"))
            if any(indexed.get(n) != input_digest(text) for n, text in included.items()):
                raise ValueError("semantic index is stale in this scope; run semantex rag build")
            sql = "SELECT units.id, vectors.v FROM units JOIN vectors USING (digest)"
            if label:
                if label not in included:
                    raise ValueError(f"{label} has no indexed mathematical content")
                anchor = db.execute(sql + " WHERE units.id = ?", (label,)).fetchone()
                vector = self.format.unpack(anchor[1])
            else:
                with backend.running():
                    vector = normalize(backend.vector(query, query=True), self.dimensions)
            groups = {} if all_versions else equivalent_groups(graph)
            selected = groups.get(label, label)
            results = []
            for node, stored in db.execute(sql):
                if node in included and node in focused and groups.get(node, node) != selected:
                    score = math.fsum(a * b for a, b in zip(vector, self.format.unpack(stored)))
                    results.append((node, score))
        return sorted(results, key=lambda item: (-item[1], item[0]))


def lexical_rank(graph, query, focused):
    normalized = query.casefold()
    terms = set(re.findall(r"\w+", normalized))
    results = []
    for node in sorted(focused):
        record = graph.nodes[node]
        description = " ".join((node, record["description"], str(record["metadata"]))).casefold()
        body = graph.source(node).casefold()
        if not terms:
            if not normalized or normalized in description or normalized in body:
                results.append((node, 0.0))
            continue
        mentioned = set(re.findall(r"\w+", description))
        content = set(re.findall(r"\w+", body))
        score = len(content & terms) + 3 * len(mentioned & terms) + 8 * (normalized in description)
        if score:
            results.append((node, score))
    return sorted(results, key=lambda item: (-item[1], item[0]))


def hybrid_rank(lexical, semantic):
    scores = {}
    for weight, ranking in ((1, lexical), (2, semantic)):
        for rank, (label, _) in enumerate(ranking, 1):
            scores[label] = scores.get(label, 0) + weight / (10 + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def hits(graph, ranking, k, show, all_versions=False):
    groups = {} if all_versions else equivalent_groups(graph)
    seen, result, statuses = set(), [], {}
    for label, score in ranking:
        group = groups.get(label, label)
        if group in seen:
            continue
        seen.add(group)
        node = graph.nodes[label]
        row = {key: node[key] for key in ("id", "kind", "scope", "file", "line")}
        row.update(rank=len(result) + 1, score=score, status=graph.status(label, statuses))
        versions = sorted(n for n in {group, *groups.keys()} if n != label and groups.get(n, n) == group)
        if versions:
            row["versions"] = versions
        if show != "labels":
            row["description"] = node["description"]
        if show == "content":
            row["blocks"] = graph.blocks(label)
            if "provenance" in node:
                row["provenance"] = node["provenance"]
        result.append(row)
        if len(result) == k:
            break
    return result


def context_bundle(graph, roots, depth, limit, focused):
    distances = {}
    for root in roots:
        if root not in graph.nodes:
            raise ValueError(f"unknown context seed {root}")
        for node, distance in graph.distances(root, depth=depth).items():
            distances[node] = min(distance, distances.get(node, distance))
    blocks, omitted, added, units = [], [], set(), []
    remaining = limit
    ranked = list(dict.fromkeys(roots + sorted(distances, key=lambda n: (distances[n], n))))
    for node in ranked:
        if node not in focused:
            omitted.append({"id": node, "reason": "outside scope"})
            continue
        record = graph.nodes[node]
        source = [block for block in graph.blocks(node) if block["id"] not in added]
        cost = sum(len(block["latex"]) for block in source)
        if cost > remaining:
            omitted.append({"id": node, "reason": "budget"})
            continue
        remaining -= cost
        blocks.extend(source)
        added.update(block["id"] for block in source)
        units.append({"id": node, "scope": record["scope"], "file": record["file"],
                      "line": record["line"], "description": record["description"],
                      "provenance": record.get("provenance"),
                      "citations": [ref for ref in graph.references(node) if ref["relation"] == "citation"]})
    return {"blocks": blocks, "units": units, "omitted": omitted, "source_chars": limit - remaining}
