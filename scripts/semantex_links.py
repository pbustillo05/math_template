"""Explicit relationships between independently retrievable mathematical units."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile

RELATIONS = ("equivalent", "derived-from")


def statement_hash(graph, label):
    return hashlib.sha256(graph.reviewed_source(label).encode()).hexdigest()


def read_links(root):
    path = root / "workflow/links.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("links"), list):
        raise ValueError("invalid workflow/links.json schema")
    seen = set()
    for link in data["links"]:
        if not isinstance(link, dict) or link.get("relation") not in RELATIONS:
            raise ValueError("invalid relationship in workflow/links.json")
        labels = [link.get("from"), link.get("to")]
        if not all(isinstance(label, str) and label for label in labels) or labels[0] == labels[1]:
            raise ValueError("a relationship requires two different label IDs")
        if link["relation"] == "equivalent":
            labels.sort()
            hashes = link.get("statement_sha256")
            if not isinstance(hashes, dict) or set(hashes) != set(labels) or not all(
                    isinstance(value, str) and len(value) == 64 for value in hashes.values()):
                raise ValueError("an equivalence needs both statement hashes")
        key = (link["relation"], *labels)
        if key in seen:
            raise ValueError("duplicate relationship in workflow/links.json")
        seen.add(key)
    return data["links"]


def visible_links(graph):
    result = []
    for link in graph.links:
        labels = [link["from"], link["to"]]
        if not all(label in graph.nodes for label in labels):
            status = "missing"
        elif link["relation"] == "equivalent" and any(
                statement_hash(graph, label) != link["statement_sha256"][label] for label in labels):
            status = "stale"
        else:
            status = "current"
        result.append(dict(link, status=status))
    return result


def equivalent_groups(graph):
    parents = {}

    def root(label):
        while label in parents:
            label = parents[label]
        return label

    for link in visible_links(graph):
        if link["relation"] == "equivalent" and link["status"] == "current":
            a, b = sorted((root(link["from"]), root(link["to"])))
            if a != b:
                parents[b] = a
    return {label: root(label) for label in parents}


def add_link(graph, first, second, relation):
    if first == second or any(label not in graph.nodes for label in (first, second)):
        raise ValueError("link requires two different indexed units")
    from manuscript_graph import NAVIGATION
    if any(graph.nodes[label]["kind"] in NAVIGATION or not graph.source(label) for label in (first, second)):
        raise ValueError("link requires mathematical units with exact content")
    labels = sorted((first, second)) if relation == "equivalent" else [first, second]
    link = {"from": labels[0], "to": labels[1], "relation": relation}
    if relation == "equivalent":
        link["statement_sha256"] = {label: statement_hash(graph, label) for label in labels}
    lock_dir = graph.root / "build/semantex"
    lock_dir.mkdir(parents=True, exist_ok=True)
    path = graph.root / "workflow/links.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with (lock_dir / "links.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        links = read_links(graph.root)
        links = [item for item in links if (item["relation"], item["from"], item["to"]) !=
                 (relation, *labels) and not (relation == "equivalent" and item["relation"] == relation
                                            and {item["from"], item["to"]} == set(labels))]
        links.append(link)
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
            temporary = output.name
            try:
                json.dump({"schema_version": 1, "links": links}, output, indent=2)
                output.write("\n")
                output.flush()
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
    return dict(link, status="current")
