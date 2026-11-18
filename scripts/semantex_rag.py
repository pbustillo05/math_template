"""Local vector cache, exact nearest neighbors, and hybrid retrieval."""
from contextlib import closing
import hashlib
import json
import math
import re
import sqlite3
import struct

from semantex_links import equivalent_groups
from semantex_cache import stamp

INPUT_VERSION = 1


class StaleIndex(ValueError):
    pass


def input_digest(text):
    return hashlib.sha256(f"{INPUT_VERSION}\0{text}".encode()).hexdigest()


def embedding_nodes(graph, labels=None):
    from manuscript_graph import KINDS, NAVIGATION

    for label in sorted(graph.nodes if labels is None else labels):
        node = graph.nodes[label]
        if node["origin"] == "retained":
            if node.get("environment") in KINDS:
                yield label, node
        elif node["description"] and node["kind"] not in NAVIGATION:
            yield label, node


def embedding_text(graph, label, node):
    description = (node["description"] if node["origin"] != "retained" else
                   " ".join(graph.reviewed_source(label).split())[:1500])
    return f"{node.get('environment')}\n{description}"


def embedding_inputs(graph, labels=None):
    for label, node in embedding_nodes(graph, labels):
        yield label, embedding_text(graph, label, node)


def normalize(vector, length):
    if len(vector) != length or not all(isinstance(x, (float, int)) and math.isfinite(x) for x in vector):
        raise ValueError(f"embedding server returned invalid {length}-dimensional vector")
    norm = math.sqrt(math.fsum(x * x for x in vector))
    if not norm:
        raise ValueError("embedding server returned a zero vector")
    return tuple(x / norm for x in vector)


class VectorIndex:
    def __init__(self, root, profile, dimensions, *, resident=False):
        self.path = root / "build/semantex/rag" / profile / "index.sqlite3"
        self.format = struct.Struct(f"<{dimensions}f")
        self.dimensions = dimensions
        self.resident = resident
        self._input_graph = None
        self._inputs = {}
        self._matrix = None

    def connect(self, write=False):
        if write:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        elif not self.path.is_file() or not self.path.stat().st_size:
            raise ValueError("no semantic index for this profile; run semantex rag build")
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA mmap_size=134217728")
        return closing(db)

    def build(self, graph, backend, *, rebuild=False, require_current_model=False):
        inputs = self.inputs(graph, graph.nodes)
        digests = {label: digest for label, (digest, _) in inputs.items()}
        signature = json.dumps(backend.signature, sort_keys=True)
        new = 0
        with self.connect(write=True) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS model (signature TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS vectors (digest TEXT PRIMARY KEY, v BLOB NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS units (id TEXT PRIMARY KEY, digest TEXT NOT NULL)")
            current = db.execute("SELECT signature FROM model").fetchone()
            if require_current_model and (not current or current[0] != signature):
                raise ValueError("the local embedding runtime has changed; run semantex rag build")
            if rebuild or not current or current[0] != signature:
                db.execute("DELETE FROM model")
                db.execute("INSERT INTO model VALUES (?)", (signature,))
                db.execute("DELETE FROM vectors")
            previous = dict(db.execute("SELECT id, digest FROM units"))
            cached = {row[0] for row in db.execute("SELECT digest FROM vectors")}
            pending = {digest: text for digest, text in inputs.values() if digest not in cached}
            if pending:
                with backend.running():
                    for digest, text in pending.items():
                        vector = normalize(backend.vector(text), self.dimensions)
                        db.execute("INSERT INTO vectors VALUES (?, ?)", (digest, self.format.pack(*vector)))
                        new += 1
            db.executemany("DELETE FROM units WHERE id = ?", ((label,) for label in previous.keys() - digests.keys()))
            db.executemany("INSERT OR REPLACE INTO units VALUES (?, ?)",
                           ((label, digest) for label, digest in digests.items() if previous.get(label) != digest))
            obsolete = cached - set(digests.values())
            db.executemany("DELETE FROM vectors WHERE digest = ?", ((digest,) for digest in obsolete))
        return {"units": len(inputs), "embedded": new, "reused_inputs": len(set(digests.values())) - new}

    def inputs(self, graph, labels):
        if not self.resident:
            return {label: (input_digest(text), text) for label, text in embedding_inputs(graph, labels)}
        if self._input_graph is not graph:
            self._input_graph = graph
            self._inputs.clear()
        missing = labels - self._inputs.keys()
        self._inputs.update((label, None) for label in missing)
        self._inputs.update((label, (input_digest(text), text))
                            for label, text in embedding_inputs(graph, missing))
        return {label: self._inputs[label] for label in labels if self._inputs[label] is not None}

    def clear_inputs(self):
        self._input_graph = None
        self._inputs.clear()

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
        removed = set(indexed)
        for label, node in embedding_nodes(graph):
            removed.discard(label)
            if label not in focused:
                continue
            counts = coverage.setdefault(node["scope"], {"eligible": 0, "current": 0, "papers": {}})
            current = int(indexed.get(label) == input_digest(embedding_text(graph, label, node)))
            counts["eligible"] += 1
            counts["current"] += current
            if node.get("bib_key"):
                paper = counts["papers"].setdefault(node["bib_key"], {"eligible": 0, "current": 0, "described": 0})
                paper["eligible"] += 1
                paper["current"] += current
                paper["described"] += bool(node["description"])
        return {"model": model, "coverage": coverage,
                "removed": sorted(removed)}

    def rank(self, graph, focused, *, query=None, label=None, backend=None, all_versions=False):
        included = self.inputs(graph, focused | ({label} if label else set()))
        with self.connect() as db:
            db.execute("BEGIN")
            model = db.execute("SELECT signature FROM model").fetchone()
            if query is not None and (not model or json.loads(model[0]) != backend.signature):
                raise ValueError("the local embedding runtime has changed; run semantex rag build")
            indexed = dict(db.execute("SELECT * FROM units"))
            if any(indexed.get(n) != digest for n, (digest, _) in included.items()):
                raise StaleIndex("semantic index is stale in this scope; run semantex rag build")
            if label:
                if label not in included:
                    raise ValueError(f"{label} has no indexed mathematical content")
                anchor = db.execute("SELECT v FROM vectors WHERE digest = ?", (indexed[label],)).fetchone()
                vector = self.format.unpack(anchor[0])
            else:
                with backend.running():
                    vector = normalize(backend.vector(query, query=True), self.dimensions)
            groups = {} if all_versions else equivalent_groups(graph)
            selected = groups.get(label, label)
            candidates = {node: indexed[node] for node in included
                          if node in focused and groups.get(node, node) != selected}
            digests = sorted(set(candidates.values()))
            scores = (self.resident_scores(db, vector, digests) if self.resident else None)
            if scores is None:
                scores = self.scalar_scores(db, vector, digests, indexed)
            results = [(node, scores[digest]) for node, digest in candidates.items() if digest in scores]
        return sorted(results, key=lambda item: (-item[1], item[0]))

    def resident_scores(self, db, vector, digests):
        if not digests:
            return {}
        try:
            import numpy
        except ImportError:
            return None
        version = stamp(self.path)
        if self._matrix is None or self._matrix[0] != version:
            positions = {}
            count = db.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
            matrix = numpy.empty((count, self.dimensions), dtype=numpy.float32)
            for i, (digest, stored) in enumerate(db.execute("SELECT digest, v FROM vectors")):
                positions[digest] = i
                matrix[i] = numpy.frombuffer(stored, dtype="<f4")
            self._matrix = version, positions, matrix
        _, positions, matrix = self._matrix
        included = [digest for digest in digests if digest in positions]
        if len(included) == len(positions):
            dots = numpy.einsum("ij,j->i", matrix, vector, dtype=numpy.float64)
            return {digest: float(dots[positions[digest]]) for digest in included}
        rows = [positions[digest] for digest in included]
        if not rows:
            return {}
        dots = numpy.einsum("ij,j->i", matrix[rows], vector, dtype=numpy.float64)
        return dict(zip(included, map(float, dots)))

    def scalar_scores(self, db, vector, digests, indexed):
        if digests:
            if len(digests) * 2 >= len(set(indexed.values())):
                vectors = db.execute("SELECT digest, v FROM vectors")
            else:
                vectors = self.vectors_for(db, digests)
            wanted = set(digests)
            return {digest: math.fsum(a * b for a, b in zip(vector, self.format.unpack(stored)))
                    for digest, stored in vectors if digest in wanted}
        return {}

    @staticmethod
    def vectors_for(db, digests):
        # Stay below SQLite's variable limit on older Python/SQLite builds.
        for start in range(0, len(digests), 500):
            batch = digests[start:start + 500]
            placeholders = ",".join("?" for _ in batch)
            yield from db.execute(f"SELECT digest, v FROM vectors WHERE digest IN ({placeholders})", batch)


def contains_word(text, term):
    start = text.find(term)
    while start >= 0:
        end = start + len(term)
        if ((start == 0 or not (text[start - 1].isalnum() or text[start - 1] == "_"))
                and (end == len(text) or not (text[end].isalnum() or text[end] == "_"))):
            return True
        start = text.find(term, start + 1)
    return False


def lexical_rank(graph, query, focused, cache=None):
    normalized = query.casefold()
    terms = set(re.findall(r"\w+", normalized))
    results = []
    for node in sorted(focused):
        if cache is not None and node in cache:
            description, body = cache[node]
        else:
            record = graph.nodes[node]
            description = " ".join((node, record["description"], str(record["metadata"]))).casefold()
            body = graph.source(node).casefold()
            if cache is not None:
                cache[node] = description, body
        if not terms:
            if not normalized or normalized in description or normalized in body:
                results.append((node, 0.0))
            continue
        score = (sum(contains_word(body, term) for term in terms)
                 + 3 * sum(contains_word(description, term) for term in terms)
                 + 8 * (normalized in description))
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
