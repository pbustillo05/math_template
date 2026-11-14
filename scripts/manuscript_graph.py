#!/usr/bin/env python3
"""Index literal authored LaTeX, retrieve exact units, and navigate review dependencies.

No TeX expansion or mathematical dependency inference is performed. Source is the
single authority; every invocation rebuilds its index, including organized research notes.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import re
import sys
from semantex_sources import citation_source_is_retained

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r"[A-Za-z][A-Za-z0-9:._-]*\Z")
REFERENCE = {"xref": (False, True), "dxref": (True, True),
             "hxref": (False, False), "hdxref": (True, False),
             "ref": (False, True), "autoref": (False, True),
             "cref": (False, True), "Cref": (False, True), "eqref": (False, True)}
TOKEN = re.compile(r"\\(" + "|".join(REFERENCE) +
                   r"|cite|begin|end|label|uses|proves|evidence|sorry|section|subsection|subsubsection|chapter|item)\b")
SEMANTIC = {
    "definition", "convention", "notation", "conjecture", "assumption",
    "hypothesis", "example", "counterexample", "remark", "construction",
    "observation", "warning", "question", "theorem", "lemma", "proposition",
    "corollary", "blank", "exercise", "openquestion", "proof",
}
NAVIGATION = {"goal", "obl", "sec", "eq", "fig", "tab"}
STATES = {"unreviewed", "conditional", "accepted", "disputed", "refuted", "obsolete"}
ROLES = {"proof-verifier": "pass", "style-referee": "pass",
         "counterexample": "clear-for-review"}
METADATA = {"title", "sketch", "related", "supersedes", "sources", "tags", "proof"}
HEADINGS = {"chapter": 0, "section": 1, "subsection": 2, "subsubsection": 3}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_archived_source(root: Path, path: Path) -> bool:
    """Compatibility symlinks never reintroduce archived work into the active graph."""
    return path.resolve().is_relative_to((root / "archived").resolve())


def audit_tex_files(root: Path):
    """Authored audit overlays are distinct from the retained paper payloads."""
    for directory in sorted((root / "references").glob("*/audit")):
        for path in sorted(directory.rglob("*.tex")):
            if not is_archived_source(root, path):
                yield path


def literal_mask(text: str) -> str:
    chars = list(text)
    pattern = re.compile(
        r"\\begin\{(verbatim\*?|Verbatim|lstlisting|minted)\}.*?\\end\{\1\}"
        r"|\\verb\*?(?P<delimiter>[^\w\s]).*?(?P=delimiter)", re.S)
    for match in pattern.finditer(text):
        for i in range(match.start(), match.end()):
            if chars[i] != "\n":
                chars[i] = " "
    return "".join(chars)


def comment_start(text: str, pos: int) -> bool:
    i = pos - 1
    slashes = 0
    while i >= 0 and text[i] == "\\":
        slashes += 1
        i -= 1
    return slashes % 2 == 0


def masked(text: str) -> str:
    """Mask comments/literal regions without changing character offsets."""
    literal_free = literal_mask(text)
    chars = list(literal_free)
    for match in re.finditer(r"%", literal_free):
        if comment_start(literal_free, match.start()):
            end = literal_free.find("\n", match.start())
            end = len(chars) if end == -1 else end
            chars[match.start():end] = " " * (end - match.start())
    return "".join(chars)


def argument(text: str, pos: int) -> tuple[str, int]:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos == len(text) or text[pos] != "{":
        raise ValueError("annotation requires a literal brace argument")
    start, depth = pos + 1, 1
    pos += 1
    while pos < len(text):
        if text[pos] == "\\" and pos + 1 < len(text) and text[pos + 1] in "{}\\":
            pos += 2
            continue
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start:pos].strip(), pos + 1
        pos += 1
    raise ValueError("unclosed annotation argument")


def safe_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"evidence/report path must be repository-relative: {value}")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"path escapes repository: {value}")
    if not resolved.is_file():
        raise ValueError(f"missing evidence/report file: {value}")
    return resolved


class Graph:
    def __init__(self, root: Path, overlays=None):
        self.root = root
        self.overlays = overlays or {}
        self.nodes: dict[str, dict] = {}
        self.edges: dict[str, set[str]] = {}
        self.direct_edges: dict[str, set[str]] = {}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.holes: list[dict] = []
        self.occurrences: list[dict] = []
        self.attachments: dict[str, list[str]] = {}
        self.proofs: dict[str, str] = {}
        self.selected_proofs: dict[str, str] = {}
        self.records: dict[str, dict] = {}
        self.files: dict[str, bytes] = {}
        self.citations: list[dict] = []
        self._fingerprints: dict[str, str] = {}
        from semantex_sources import index_sources
        self.source_labels, self.papers = index_sources(root, masked, argument)
        pending: list[tuple[str, list[str], str]] = []
        for subtree in ("draft", "notes"):
            for path in sorted((root / subtree).rglob("*.tex")):
                if not is_archived_source(root, path):
                    self.scan(path, pending)
        for path in audit_tex_files(root):
            self.scan(path, pending)
        for owner, dependencies, locator in pending:
            if owner not in self.nodes:
                self.errors.append(f"{locator}: unknown annotation owner {owner}")
                continue
            for dependency in dependencies:
                if dependency not in self.nodes:
                    self.errors.append(f"{locator}: unknown dependency {dependency}")
                else:
                    self.direct_edges[owner].add(dependency)
        for occurrence in self.occurrences:
            target, owner = occurrence["target"], occurrence["owner"]
            locator = f"{occurrence['file']}:{occurrence['line']}:{occurrence['column']}"
            external = self.source_labels.get(target, []) if target not in self.nodes else []
            if target not in self.nodes and not external:
                self.errors.append(f"{locator}: unresolved reference {target}")
            if len(external) > 1:
                self.errors.append(f"{locator}: ambiguous source label {target}; matches " + ", ".join(r['file'] for r in external))
            if occurrence["dependency"]:
                if external:
                    self.errors.append(f"{locator}: external labels locate sources, not accepted premises; cite an authored checked src: application")
                if owner is None:
                    self.errors.append(f"{locator}: dependency reference has no mathematical owner")
                elif self.nodes[owner]['kind'] in NAVIGATION:
                    self.errors.append(f"{locator}: dependency reference has no mathematical owner; a planning/navigation anchor is not a claim")
                elif target in self.nodes:
                    if self.nodes[target]["kind"] in {"sec", "eq", "fig", "tab"}:
                        self.errors.append(f"{locator}: logical target {target} is only a navigation anchor; cite its owning mathematical unit")
                    else:
                        self.direct_edges[owner].add(target)
        for proof, claim in self.proofs.items():
            if proof not in self.nodes or not proof.startswith("prf:"):
                self.errors.append(f"invalid proof ID {proof}")
            if claim not in self.nodes or claim.split(":")[0] in NAVIGATION | {"prf"}:
                self.errors.append(f"invalid proof target {claim}")
        for claim in self.nodes:
            proofs = sorted(p for p, c in self.proofs.items() if c == claim)
            chosen = self.nodes[claim]["metadata"].get("proof")
            if chosen and chosen not in proofs:
                self.errors.append(f"{claim}: metadata selects an unattached proof {chosen}")
            elif len(proofs) > 1 and not chosen:
                self.errors.append(f"{claim}: multiple proofs require % @proof: prf:label")
            elif proofs:
                self.selected_proofs[claim] = chosen or proofs[0]
        self.edges = {node: set(deps) for node, deps in self.direct_edges.items()}
        for claim, proof in self.selected_proofs.items():
            if proof in self.direct_edges:
                self.edges[claim].update(self.direct_edges[proof])
        for owner, paths in self.attachments.items():
            if owner not in self.nodes:
                self.errors.append(f"unknown evidence owner {owner}")
            for value in paths:
                try:
                    self.files[value] = safe_path(root, value).read_bytes()
                except ValueError as exc:
                    self.errors.append(str(exc))
        try:
            self.order()
            self.order(support=True)
        except ValueError as exc:
            self.errors.append(str(exc))
        self.read_reviews()
        for citation in self.citations:
            for key in citation['keys']:
                if key not in self.papers:
                    self.errors.append(f"{citation['file']}:{citation['line']}: citation source unavailable: {key}")
                elif not any(len(self.source_labels.get(t, [])) == 1 and self.source_labels[t][0]['bib_key'] == key for t in citation['targets']):
                    self.errors.append(f"{citation['file']}:{citation['line']}: TeX citation {key} needs a hidden exact source label: \\cite[locator\\hxref{{{key}:SOURCE-LABEL}}]{{{key}}}")

    def read_reviews(self) -> None:
        ledger = self.root / "workflow" / "reviews.json"
        if not ledger.exists():
            return
        try:
            data = json.loads(ledger.read_text())
            if data.get("schema_version") != 1 or not isinstance(data.get("records"), dict):
                raise ValueError("invalid review registry schema")
            self.records = data["records"]
            for node, record in self.records.items():
                if node not in self.nodes:
                    self.errors.append(f"review for unknown node {node}")
                if not isinstance(record, dict) or record.get("status") not in STATES:
                    self.errors.append(f"invalid review state for {node}")
        except (ValueError, AttributeError) as exc:
            self.errors.append(f"invalid reviews.json: {exc}")

    def scan(self, path: Path, pending: list) -> None:
        relative = path.relative_to(self.root).as_posix()
        if path.is_symlink() and not path.resolve().is_relative_to(self.root.resolve()):
            self.errors.append(f"source path escapes repository: {relative}")
            return
        data = self.overlays.get(relative, path.read_bytes())
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.files[relative] = data
        if relative.startswith("notes/") and not re.search(rb"(?m)^%[ \t]*semantex:[ \t]*on[ \t]*$", data):
            return
        raw = data.decode("utf-8")
        text = masked(raw)
        stack: list[dict] = []
        frames: list[dict] = []
        anchors: list[dict] = []
        references: list[dict] = []
        citations: list[dict] = []
        heading = None
        item = None
        pos = 0
        document_end = len(raw)

        def location(offset):
            return {"file": relative, "line": raw.count("\n", 0, offset) + 1,
                    "column": offset - raw.rfind("\n", 0, offset)}

        def context():
            for frame in reversed(stack):
                if frame["environment"] in SEMANTIC:
                    return frame
            if item:
                return item
            return heading

        while match := TOKEN.search(text, pos):
            command = match[1]
            offset = match.start()
            loc = location(offset)
            locator = f"{relative}:{loc['line']}"
            try:
                if command == 'cite':
                    start = match.end()
                    while start < len(text) and text[start].isspace():
                        start += 1
                    note, note_start = '', start
                    if start < len(text) and text[start] == '[':
                        note_start = start + 1
                        level, braces, cursor = 1, 0, start + 1
                        while cursor < len(text) and level:
                            char = text[cursor]
                            if char == '\\':
                                cursor += 2
                                continue
                            if char == '{': braces += 1
                            if char == '}': braces -= 1
                            if not braces and char == '[': level += 1
                            if not braces and char == ']': level -= 1
                            cursor += 1
                        if level:
                            raise ValueError('unclosed citation optional argument')
                        note, start = text[note_start:cursor - 1], cursor
                    keys, pos = argument(text, start)
                    if len(keys.split(',')) != 1:
                        raise ValueError('split multi-paper citations so each citation has its own exact source destination')
                    targets = []
                    for ref in re.finditer(r'\\(hxref|hdxref)\s*\{([^{}]+)\}', note):
                        target = ref[2].strip()
                        if not ID.fullmatch(target) and target not in self.source_labels:
                            raise ValueError('citation requires a literal source label')
                        targets.append(target)
                        off = note_start + ref.start()
                        references.append(dict(location(off), target=target, dependency=ref[1] == 'hdxref',
                                               visible=False, command=ref[1], offset=off, frame=context(), relation='citation'))
                    for ref in re.finditer(r'\\(sourceat|sourcepage)\s*\{([^{}]+)\}\s*\{([^{}]+)\}\s*\{(\d+)\}', note):
                        key, file, number = ref[2].strip(), ref[3].strip(), int(ref[4])
                        source = safe_path(self.root, file)
                        if not citation_source_is_retained(self.root, key, file):
                            raise ValueError('citation locator must point into the cited retained paper or its hash-locked comparison payload, not its audit')
                        if number < 1 or (ref[1] == 'sourceat' and number > len(source.read_bytes().splitlines())):
                            raise ValueError('citation source line out of range')
                        if ref[1] == 'sourcepage' and source.suffix != '.pdf':
                            raise ValueError('sourcepage requires a retained PDF')
                        identifier = 'loc:' + key + ':' + file + ':' + str(number)
                        record = {'id': identifier, 'bib_key': key, 'source_label': None, 'file': file, 'line': number,
                                  'page': ref[1] == 'sourcepage', 'kind': 'external', 'status': 'source-unreviewed'}
                        self.source_labels[identifier] = [record]
                        targets.append(identifier)
                        off = note_start + ref.start()
                        references.append(dict(location(off), target=identifier, dependency=False, visible=False,
                                               command=ref[1], offset=off, frame=context(), relation='citation'))
                    citations.append(dict(loc, keys=[k.strip() for k in keys.split(',')], targets=targets,
                                          locator=re.sub(r'\\source(?:at|page)\s*\{[^{}]+\}\s*\{[^{}]+\}\s*\{[^{}]+\}', '',
                                              re.sub(r'\\(?:hxref|hdxref)\s*\{[^{}]+\}', '', note)).strip(), frame=context()))
                    continue
                if command == "item":
                    pos = match.end()
                    if not any(f["environment"] in SEMANTIC for f in stack):
                        enum = next((f for f in reversed(stack) if f["environment"] in {"enumerate", "itemize"}), None)
                        if item and item.get("container") is enum:
                            item["end"] = offset
                        item = {"start": offset, "end": document_end, "owner": None,
                                "container": enum, "environment": "item"}
                        frames.append(item)
                    continue
                star = match.end()
                if star < len(text) and text[star] == "*" and (command in HEADINGS or command in REFERENCE):
                    if command in REFERENCE:
                        raise ValueError('starred references suppress source links; use the four unstarred SemanTeX commands')
                    star += 1
                first, pos = argument(text, star)
                second = None
                if command in {"uses", "proves", "evidence", "sorry"}:
                    second, pos = argument(text, pos)
                if command in HEADINGS:
                    for frame in frames:
                        if frame.get("level", 99) >= HEADINGS[command] and frame.get("environment") in HEADINGS and frame["end"] == document_end:
                            frame["end"] = offset
                    heading = {"start": offset, "end": document_end, "owner": None,
                               "environment": command, "title": first, "level": HEADINGS[command]}
                    frames.append(heading)
                    item = None
                    continue
                if command == "begin":
                    frame = {"environment": first, "start": offset, "end": document_end,
                             "line": loc["line"], "labels": [], "owner": None}
                    stack.append(frame)
                    frames.append(frame)
                    continue
                if command == "end":
                    if not stack or stack[-1]["environment"] != first:
                        raise ValueError(f"unmatched environment end {first}")
                    frame = stack.pop()
                    frame["end"] = pos
                    if first in SEMANTIC and not frame["owner"]:
                        raise ValueError(f"unlabelled {first} beginning on line {frame['line']}")
                    if first == "document":
                        document_end = offset
                    if item and item.get("container") is frame:
                        item["end"] = offset
                        item = None
                    continue
                if command in REFERENCE:
                    dependency, visible = REFERENCE[command]
                    targets = [first] if command in {"xref", "dxref", "hxref", "hdxref"} else [t.strip() for t in first.split(",")]
                    if any(not ID.fullmatch(target) and target not in self.source_labels for target in targets):
                        raise ValueError("reference requires literal label(s); graph reference commands take one label")
                    if len(targets) != 1:
                        raise ValueError('use one label per visible reference so each click has an exact source destination')
                    for target in targets:
                        references.append(dict(loc, target=target, dependency=dependency,
                                               visible=visible, command=command, offset=offset,
                                               frame=context(), relation="reference"))
                    continue
                if not ID.fullmatch(first):
                    raise ValueError(f"invalid literal node ID {first!r}")
                if command in {"label", "sorry"}:
                    if first in self.nodes:
                        raise ValueError(f"duplicate node ID {first}")
                    frame = context()
                    kind = first.split(":")[0]
                    # An equation/navigation label never steals the enclosing claim's ownership.
                    if command == "label" and frame and frame["environment"] in SEMANTIC and kind not in {"eq", "fig", "tab", "sec"}:
                        if frame["owner"]:
                            raise ValueError(f"multiple principal labels in {frame['environment']}")
                        frame["owner"] = first
                    elif command == "label" and frame and frame["environment"] in set(HEADINGS) | {"item"} and not frame["owner"]:
                        frame["owner"] = first
                    node = dict(loc, id=first, kind=kind, metadata={}, offset=offset,
                                environment=frame["environment"] if frame else "anchor")
                    self.nodes[first] = node
                    self.direct_edges[first] = set()
                    anchors.append({"node": node, "frame": frame if frame and frame.get("owner") == first else None,
                                    "parent": frame, "start": offset, "end": pos})
                    if command == "label" and stack:
                        stack[-1]["labels"].append(first)
                    if command == "sorry":
                        if kind != "obl" or not second:
                            raise ValueError("sorry requires an obl: ID and precise reason")
                        self.holes.append(dict(loc, id=first, reason=second, offset=offset,
                                               owner=frame.get("owner") if frame else None))
                elif command == "uses":
                    dependencies = [x.strip() for x in second.split(",") if x.strip()]
                    if any(not ID.fullmatch(x) for x in dependencies):
                        raise ValueError("uses requires literal node IDs")
                    pending.append((first, dependencies, locator))
                    self.warnings.append(f"{locator}: legacy \\uses; place \\dxref or \\hdxref at each use instead")
                elif command == "proves":
                    if first in self.proofs:
                        raise ValueError(f"proof attachment repeated for {first}")
                    frame = context()
                    if not frame or frame['environment'] != 'proof' or frame.get('owner') != first:
                        raise ValueError('proves must occur in the labelled proof it attaches')
                    self.proofs[first] = second
                elif command == "evidence":
                    self.attachments.setdefault(first, []).extend(x.strip() for x in second.split(",") if x.strip())
            except ValueError as exc:
                self.errors.append(f"{locator}: {exc}")
                pos = max(pos, match.end())
        for frame in stack:
            self.errors.append(f"{relative}:{frame['line']}: unclosed {frame['environment']}")
        for index, anchor in enumerate(anchors):
            node, frame = anchor["node"], anchor["frame"]
            if frame:
                start, end = frame["start"], min(frame["end"], document_end)
                if "title" in frame:
                    node["metadata"]["title"] = frame["title"]
            elif node["kind"] in {"eq", "fig", "tab", "obl"}:
                start, end = anchor["start"], anchor["end"]
            else:
                # Bare anchors remain supported for checked source inputs and old notes.
                start = anchor["start"]
                end = next((a["start"] for a in anchors[index + 1:] if a["node"]["kind"] not in {"eq", "fig", "tab", "obl"}), document_end)
            node.update(start=start, end=end, start_line=raw.count("\n", 0, start) + 1,
                        end_line=raw.count("\n", 0, max(start, end - 1)) + 1)
        for ref in references:
            frame = ref.pop("frame")
            ref["owner"] = frame.get("owner") if frame else None
            self.occurrences.append(ref)
        for citation in citations:
            frame = citation.pop('frame')
            citation['owner'] = frame.get('owner') if frame else None
            self.citations.append(citation)
        # Metadata is a contiguous comment block immediately preceding a unit or its label.
        literal = literal_mask(raw)
        meta_lines = list(re.finditer(r"(?m)^[ \t]*%[ \t]*@([\w-]+):[ \t]*(.*)$", literal))
        for meta in meta_lines:
            key, value = meta[1], meta[2].strip()
            if key not in METADATA:
                self.errors.append(f"{relative}:{location(meta.start())['line']}: unknown metadata field {key}")
                continue
            target = next((a for a in anchors if a["node"]["kind"] not in {"eq", "fig", "tab", "obl"} and a["node"]["offset"] > meta.start()), None)
            if not target:
                self.errors.append(f"{relative}:{location(meta.start())['line']}: metadata has no following unit")
                continue
            node = target["node"]
            between = text[meta.end():node["offset"]]
            # Only whitespace and the unit's opening heading/environment may intervene.
            boundary = node["start"]
            if meta.start() < boundary and text[meta.end():boundary].strip():
                self.errors.append(f"{relative}:{location(meta.start())['line']}: metadata must immediately precede its unit")
                continue
            old = node["metadata"].get(key)
            if key in {"related", "supersedes", "tags"}:
                values = [v.strip() for v in value.split(",") if v.strip()]
                node["metadata"][key] = (old or []) + values
            elif old and key != "title":
                node["metadata"][key] = old + "\n" + value
            else:
                node["metadata"][key] = value
            node["start"] = min(node["start"], meta.start())
            node["start_line"] = raw.count("\n", 0, node["start"]) + 1
            if key in {"related", "supersedes"}:
                for label in node["metadata"][key] if not old else values:
                    if not ID.fullmatch(label) and label not in self.source_labels:
                        self.errors.append(f"{relative}:{location(meta.start())['line']}: invalid metadata label {label}")
                    else:
                        self.occurrences.append(dict(location(meta.start()), owner=node["id"], target=label,
                                                     dependency=False, visible=False, command="metadata",
                                                     relation=key, offset=meta.start()))

    def adjacency(self, reverse=False, support=False):
        edges = {node: set(deps) for node, deps in self.edges.items()}
        if support:
            for claim, proof in self.selected_proofs.items():
                if proof in edges:
                    edges[claim].add(proof)
        if reverse:
            result = {node: set() for node in edges}
            for node, deps in edges.items():
                for dep in deps:
                    result[dep].add(node)
            return result
        return edges

    def distances(self, node, reverse=False, depth=None, support=False):
        if node not in self.nodes:
            raise ValueError(f"unknown node {node}")
        edges = self.adjacency(reverse, support)
        distances = {node: 0}
        queue = deque([node])
        while queue:
            current = queue.popleft()
            if depth is not None and distances[current] >= depth:
                continue
            for target in sorted(edges[current]):
                if target not in distances:
                    distances[target] = distances[current] + 1
                    queue.append(target)
        return distances

    def closure(self, node, reverse=False, support=True):
        return set(self.distances(node, reverse=reverse, support=support))

    def order(self, subset=None, support=False):
        edges = self.adjacency(support=support)
        done, active, path, output = set(), set(), [], []
        for root in sorted(self.nodes if subset is None else subset):
            stack = [(root, False)]
            while stack:
                node, finished = stack.pop()
                if finished:
                    active.remove(node)
                    path.pop()
                    done.add(node)
                    output.append(node)
                elif node not in done:
                    if node in active:
                        raise ValueError('dependency cycle: ' + ' -> '.join(path + [node]))
                    active.add(node)
                    path.append(node)
                    stack.append((node, True))
                    stack.extend((dep, False) for dep in sorted(edges[node], reverse=True))
        return output

    def source(self, node):
        record = self.nodes[node]
        return self.files[record["file"]].decode("utf-8")[record["start"]:record["end"]]

    def blocks(self, node, proof=None):
        if node not in self.nodes:
            raise ValueError(f"unknown node {node}")
        attached = sorted(p for p, c in self.proofs.items() if c == node)
        selected = self.selected_proofs.get(node)
        if proof == "all":
            chosen = attached
        elif proof:
            if proof not in attached:
                raise ValueError(f"{proof} is not an attached proof of {node}")
            chosen = [proof]
        else:
            chosen = [selected] if selected else []
        result = []
        for key in [node] + chosen:
            record = self.nodes[key]
            result.append({"id": key, "file": record["file"], "start_line": record["start_line"],
                           "end_line": record["end_line"], "start_column": record["start"] - self.files[record["file"]].decode().rfind("\n", 0, record["start"]),
                           "latex": self.source(key)})
        return result

    def contained_holes(self, nodes):
        return [hole for hole in self.holes if any(
            self.nodes[n]["file"] == hole["file"] and self.nodes[n]["start"] <= hole["offset"] < self.nodes[n]["end"]
            for n in nodes)]

    def fingerprint(self, node):
        if node in self._fingerprints:
            return self._fingerprints[node]
        closure = self.closure(node)
        paths = {p for key in closure for p in self.attachments.get(key, [])}
        paths.update(path.relative_to(self.root).as_posix() for path in (self.root / "preamble").rglob("*")
                     if path.is_file() and path.suffix in {".sty", ".tex"})
        paths.update(p for p in ("AGENTS.md", "writing-style.md", "agents/roles/auditor.md", "agents/PROTOCOL.md",
                                  "agents/SEMANTEX.md", "references/README.md", "references/lock.json", "lean/ledger.json") if (self.root / p).is_file())
        payload = {"schema": 2, "target": node,
                   "units": [(key, self.nodes[key]["file"], sha(self.source(key).encode()),
                              sorted(self.edges[key]), self.selected_proofs.get(key)) for key in sorted(closure)],
                   "evidence": [(p, sha(safe_path(self.root, p).read_bytes())) for p in sorted(paths)]}
        value = sha(json.dumps(payload, sort_keys=True).encode())
        self._fingerprints[node] = value
        return value

    def status(self, node, cache=None):
        cache = {} if cache is None else cache
        if node not in cache:
            for key in self.order(self.closure(node), support=True):
                if key not in cache:
                    cache[key] = self._status_one(key, cache)
        return cache[node]

    def _status_one(self, node, cache):
        if node in cache:
            return cache[node]
        record = self.records.get(node, {})
        state = record.get("status", "unreviewed")
        if state != "accepted":
            return state
        current = self.fingerprint(node)
        reviews = record.get("reviews", [])
        valid = isinstance(reviews, list) and bool(record.get("author"))
        roles, reviewers = set(), set()
        for review in reviews if isinstance(reviews, list) else []:
            if not isinstance(review, dict):
                valid = False
                continue
            role, identity = review.get("role"), review.get("reviewer")
            if not isinstance(role, str) or not isinstance(identity, str):
                valid = False
                continue
            if (role not in ROLES or review.get("verdict") != ROLES.get(role)
                    or review.get("fingerprint") != current or not identity
                    or identity in reviewers or role in roles):
                valid = False
            if role == "proof-verifier" and identity == record.get("author"):
                valid = False
            roles.add(role)
            reviewers.add(identity)
            try:
                report = safe_path(self.root, review.get("report", ""))
                if sha(report.read_bytes()) != review.get("report_sha256"):
                    valid = False
            except (ValueError, TypeError):
                valid = False
        if roles != set(ROLES) or self.nodes[node]["kind"] in {"goal", "obl"}:
            valid = False
        if self.nodes[node]["kind"] == "src":
            paths = self.attachments.get(node, [])
            if not any(p.startswith("references/") and "/audit/" not in p for p in paths) or not any(
                    p.startswith("references/") and "/audit/" in p for p in paths):
                valid = False
        if self.contained_holes(self.closure(node)):
            valid = False
        if self.nodes[node]["kind"] in {"thm", "lem", "prop", "cor"} and node not in self.selected_proofs:
            valid = False
        deps = self.adjacency(support=True)[node]
        if any(cache[dep] != "accepted" for dep in deps):
            valid = False
        cache[node] = "accepted" if valid else "stale"
        return cache[node]

    def occurrence(self, occurrence):
        result = dict(occurrence)
        if occurrence["target"] in self.nodes:
            target = self.nodes[occurrence["target"]]
            result["target_location"] = {"file": target["file"], "line": target["line"]}
        elif len(self.source_labels.get(occurrence['target'], [])) == 1:
            record = self.source_labels[occurrence['target']][0]
            result['target_location'] = {k: record[k] for k in ('file', 'line', 'source_label', 'bib_key')}
        owner = occurrence["owner"]
        result["unit"] = self.proofs.get(owner, owner)
        return result

    def describe(self, node, cache=None):
        data = {k: v for k, v in self.nodes[node].items() if k not in {"offset", "start", "end"}}
        data.update(dependencies=sorted(self.edges[node]), direct_dependencies=sorted(self.direct_edges[node]),
                    dependents=sorted(self.adjacency(reverse=True)[node]),
                    proofs=sorted(p for p, c in self.proofs.items() if c == node),
                    selected_proof=self.selected_proofs.get(node), proof_of=self.proofs.get(node),
                    status=self.status(node, cache), fingerprint=self.fingerprint(node),
                    evidence=self.attachments.get(node, []))
        owners = {node, self.selected_proofs.get(node)} - {None}
        data['citations'] = [dict(c) for c in self.citations if c['owner'] in owners]
        return data

    def export(self):
        cache = {}
        return {"schema_version": 2, "edge_direction": "owner-uses-prerequisite",
                "nodes": [self.describe(node, cache) for node in sorted(self.nodes)],
                "references": [self.occurrence(o) for o in self.occurrences],
                "proof_attachments": self.proofs, "obligations": self.holes,
                "name": "SemanTeX",
                "citations": [dict(c, targets_resolved=[{k: v for k, v in self.source_labels[t][0].items() if k not in {'latex', 'proof'}} for t in c['targets'] if len(self.source_labels.get(t, [])) == 1]) for c in self.citations],
                "warnings": self.warnings}

    def references(self, node, reverse=False):
        if node not in self.nodes and not (reverse and node in self.source_labels):
            raise ValueError(f"unknown node {node}")
        owners = {node}
        if node in self.selected_proofs:
            owners.add(self.selected_proofs[node])
        return [self.occurrence(o) for o in self.occurrences if
                (o["target"] == node if reverse else o["owner"] in owners)]

    def why(self, start, target):
        if start not in self.nodes or target not in self.nodes:
            raise ValueError("why requires two existing labels")
        queue, paths = deque([start]), {start: [start]}
        while queue:
            node = queue.popleft()
            if node == target:
                path = paths[node]
                return {"path": path, "steps": [
                    {"owner": a, "target": b, "uses": [o for o in self.references(a) if o["dependency"] and o["target"] == b]}
                    for a, b in zip(path, path[1:])]}
            for dep in sorted(self.edges[node]):
                if dep not in paths:
                    paths[dep] = paths[node] + [dep]
                    queue.append(dep)
        raise ValueError(f"no logical dependency path from {start} to {target}")


def depth_value(value):
    if value == "all":
        return None
    try:
        depth = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("depth must be a nonnegative integer or all")
    if depth < 0:
        raise argparse.ArgumentTypeError("depth must be nonnegative")
    return depth


def dump(value):
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--overlays", type=Path, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="validate graph and current reviews; not a proof checker")
    check.add_argument("--release", action="store_true")
    check.add_argument("--target")
    for name in ("get", "show"):
        child = sub.add_parser(name, help="retrieve exact statement and selected proof")
        child.add_argument("node")
        formats = child.add_mutually_exclusive_group()
        formats.add_argument("--latex", action="store_true")
        formats.add_argument("--json", action="store_true")
        child.add_argument("--source", action="store_true", help="legacy alias for numbered exact-unit output")
        child.add_argument("--proof", help="attached proof label, or all")
    for name in ("deps", "rdeps", "ancestors", "descendants"):
        child = sub.add_parser(name, help="prerequisites or dependent results, with shortest distances")
        child.add_argument("node")
        child.add_argument("--depth", type=depth_value, default=None)
        child.add_argument("--tree", action="store_true")
        child.add_argument("--mentions", action="store_true", help="for upstream nodes: traverse literal mentions instead of explicit logical uses")
        child.add_argument("--json", action="store_true")
    for name in ("refs", "backrefs", "frontier", "fingerprint"):
        child = sub.add_parser(name)
        child.add_argument("node")
        child.add_argument("--json", action="store_true")
    locate = sub.add_parser('locate', help='resolve an authored or upstream label to its exact file and line')
    locate.add_argument('node')
    locate.add_argument('--json', action='store_true')
    why = sub.add_parser("why", help="shortest logical dependency path and exact use sites")
    why.add_argument("node")
    why.add_argument("target")
    why.add_argument("--json", action="store_true")
    order = sub.add_parser("order")
    order.add_argument("node", nargs="?")
    order.add_argument("--json", action="store_true")
    search = sub.add_parser("search", help="search labels, metadata, and literal mathematical source")
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--kind")
    search.add_argument("--status")
    search.add_argument("--json", action="store_true")
    export = sub.add_parser("export")
    export.add_argument("--output")
    diagram = sub.add_parser("graph", help="export a dependency diagram")
    diagram.add_argument("--format", choices=["dot", "mermaid"], default="mermaid")
    diagram.add_argument("--target")
    sub.add_parser("editor-index", help=argparse.SUPPRESS)
    for name in ("paper-graph", "source-labels", "reference-view"):
        child = sub.add_parser(name, help="read-only retained-source navigation")
        child.add_argument("key")
        if name == "reference-view":
            child.add_argument("--main", required=True)
        else:
            child.add_argument("--format", choices=["json", "dot", "mermaid"], default="json")
    args = parser.parse_args(argv)
    overlays = json.loads(args.overlays.read_text()) if args.overlays else {}
    if not isinstance(overlays, dict) or any(not isinstance(k, str) or not isinstance(v, str) or
            Path(k).is_absolute() or ".." in Path(k).parts or not k.endswith(".tex") or
            not k.startswith(("draft/", "notes/", "references/")) for k, v in overlays.items()):
        raise ValueError("invalid editor overlays")
    graph = Graph(args.root.resolve(), overlays)
    if args.command in {"paper-graph", "source-labels", "reference-view"}:
        from reference_views import paper_graph, render_graph, build_view
        if args.command == "reference-view":
            build_view(graph.root, args.key, args.main)
        else:
            data = paper_graph(graph, args.key)
            dump(data['nodes']) if args.command == "source-labels" else print(render_graph(data, args.format))
        return 0
    if args.command == "editor-index":
        if graph.errors:
            dump({"errors": graph.errors, "nodes": [], "references": []})
            return 0
        exported = graph.export()
        for node in exported['nodes']:
            node['blocks'] = graph.blocks(node['id'])
        for label, matches in sorted(graph.source_labels.items()):
            if len(matches) == 1:
                node = dict(matches[0])
                if 'latex' in node:
                    node['blocks'] = [{k: node[k] for k in ('file', 'start_line', 'end_line', 'latex')}]
                    if node.get('proof'):
                        node['blocks'].append(node['proof'])
                node['dependencies'] = [e['target'] for e in node.get('mentions', []) if e['dependency']]
                exported['nodes'].append(node)
                exported['references'].extend(node.get('mentions', []))
        exported['errors'] = []
        dump(exported)
        return 0
    if graph.errors:
        raise ValueError("\n".join(graph.errors))
    external = None
    if hasattr(args, 'node') and args.node not in graph.nodes and args.node in graph.source_labels:
        matches = graph.source_labels[args.node]
        if len(matches) != 1:
            raise ValueError(f'ambiguous upstream label {args.node}')
        external = matches[0]
    if hasattr(args, "node") and args.node and args.node not in graph.nodes and not (external and args.command in {'get', 'show', 'locate', 'refs', 'backrefs', 'deps', 'rdeps', 'ancestors', 'descendants'}):
        raise ValueError(f"unknown node {args.node}; try mg search")
    command = args.command
    if external and command in {'deps', 'rdeps', 'ancestors', 'descendants', 'refs', 'backrefs'}:
        from reference_views import paper_graph
        paper = paper_graph(graph, external['bib_key'])
        edges = paper['edges']
        reverse = command in {'rdeps', 'descendants', 'backrefs'}
        if command in {'refs', 'backrefs'}:
            result = [e for e in edges if e['target' if reverse else 'owner'] == args.node]
            if reverse:
                result += graph.references(args.node, reverse=True)
        else:
            adjacency = {n['id']: set() for n in paper['nodes']}
            for e in edges:
                if e['resolved'] and (e['dependency'] or args.mentions):
                    a, b = (e['target'], e['owner']) if reverse else (e['owner'], e['target'])
                    adjacency[a].add(b)
            distances, queue = {args.node: 0}, deque([args.node])
            while queue:
                node = queue.popleft()
                if args.depth is not None and distances[node] >= args.depth:
                    continue
                for target in sorted(adjacency[node]):
                    if target not in distances:
                        distances[target] = distances[node] + 1
                        queue.append(target)
            result = [dict(graph.source_labels[n][0], distance=d) for n, d in distances.items() if n != args.node]
            result = [{k: v for k, v in n.items() if k not in {'latex', 'proof', 'mentions'}} for n in result]
        if args.json:
            dump(result)
        else:
            print('Upstream literal ' + ('mention' if getattr(args, 'mentions', False) else 'explicit-reference') + ' navigation; no dependencies inferred.')
            for item in result:
                print(json.dumps(item, ensure_ascii=False))
        return 0
    if command == "check":
        errors = [f"{node}: acceptance is stale or incomplete" for node, record in graph.records.items()
                  if record["status"] == "accepted" and graph.status(node) != "accepted"]
        if args.release:
            if args.target and args.target not in graph.nodes:
                raise ValueError(f"unknown node {args.target}")
            if args.target and graph.nodes[args.target]["kind"] in NAVIGATION:
                raise ValueError("release target must be a mathematical unit, not a planning/navigation anchor")
            targets = graph.closure(args.target) if args.target else set(graph.nodes)
            errors.extend(f"unresolved obligation {h['id']}" for h in graph.contained_holes(targets))
            errors.extend(f"{node}: release requires current acceptance" for node in sorted(targets)
                          if graph.nodes[node]["kind"] not in NAVIGATION and graph.status(node) != "accepted")
        if errors:
            raise ValueError("\n".join(errors))
        print(f"checked {len(graph.nodes)} anchors, {sum(map(len, graph.edges.values()))} logical edges, "
              f"{len(graph.occurrences)} reference occurrences, {len(graph.holes)} visible obligations; mathematical validity is not checked")
        for warning in graph.warnings:
            print("warning: " + warning, file=sys.stderr)
    elif command in {"get", "show"}:
        if external:
            if external.get('page') or external['file'].endswith('.pdf'):
                raise ValueError('PDF-only source has no exact LaTeX block; use locate for the page destination')
            record = {k: v for k, v in external.items() if k not in {'latex', 'proof'}}
            blocks = [{k: external[k] for k in ('id', 'file', 'start_line', 'end_line', 'latex')}] if 'latex' in external else []
            if not blocks:
                raw = (graph.root / external['file']).read_text(errors='replace').splitlines()
                blocks = [dict(id=args.node, file=external['file'], start_line=external['line'], end_line=external['line'], latex=raw[external['line'] - 1])]
            if external.get('proof'):
                blocks.append(dict(external['proof'], id=args.node + ':proof'))
        else:
            record = graph.describe(args.node)
            blocks = graph.blocks(args.node, args.proof)
        if args.json:
            dump({"node": record, "blocks": blocks})
        elif args.latex:
            sys.stdout.write("\n".join(b["latex"] for b in blocks))
            if blocks and not blocks[-1]["latex"].endswith("\n"):
                print()
        else:
            print(f"{args.node} [{record['status']}] {record['file']}:{record['line']}")
            print("dependencies: " + (", ".join(record.get("dependencies", [])) or "none declared"))
            if record.get("metadata"):
                print("metadata: " + json.dumps(record["metadata"], ensure_ascii=False))
            for block in blocks:
                print(f"\n{block['id']} — {block['file']}:{block['start_line']}-{block['end_line']}")
                for number, line in enumerate(block["latex"].splitlines(), block["start_line"]):
                    print(f"{number:5} | {line}")
    elif command in {"deps", "rdeps", "ancestors", "descendants"}:
        reverse = command in {"rdeps", "descendants"}
        distances = graph.distances(args.node, reverse, args.depth)
        nodes = [dict(graph.describe(n), distance=d) for n, d in sorted(distances.items(), key=lambda p: (p[1], p[0])) if n != args.node]
        if args.json:
            dump(nodes)
        elif args.tree:
            edges = graph.adjacency(reverse)
            seen = {}
            stack = [(args.node, 0)]
            while stack:
                node, distance = stack.pop()
                repeated = node in seen and seen[node] <= distance
                print("  " * distance + node + (" [already shown]" if repeated else ""))
                if repeated or (args.depth is not None and distance >= args.depth):
                    continue
                seen[node] = distance
                stack.extend((dep, distance + 1) for dep in sorted(edges[node], reverse=True))
        else:
            for node in nodes:
                print(f"{node['distance']}\t{node['id']}\t{node['status']}\t{node['file']}:{node['line']}")
    elif command in {"refs", "backrefs"}:
        refs = graph.references(args.node, command == "backrefs")
        if args.json:
            dump(refs)
        else:
            for ref in refs:
                target = ref.get("target_location", {})
                print(f"{ref['owner'] or '(exposition)'} -> {ref['target']} "
                      f"[{ref['relation']}; {'dependency' if ref['dependency'] else 'mention'}; "
                      f"{'visible' if ref['visible'] else 'hidden'}] "
                      f"{ref['file']}:{ref['line']}:{ref['column']} -> {target.get('file')}:{target.get('line')}")
    elif command == "why":
        result = graph.why(args.node, args.target)
        if args.json:
            dump(result)
        else:
            print(" -> ".join(result["path"]))
            for step in result["steps"]:
                for ref in step["uses"]:
                    raw = graph.files[ref["file"]].decode().splitlines()[ref["line"] - 1]
                    print(f"  {ref['file']}:{ref['line']}:{ref['column']} | {raw}")
    elif command == "frontier":
        nodes = graph.closure(args.node)
        unresolved = [dict(graph.describe(n), reasons=(
            ["unresolved proof obligation"] if graph.nodes[n]["kind"] == "obl" else
            ["current review missing, disputed, or stale"])) for n in sorted(nodes)
            if graph.nodes[n]["kind"] == "obl" or graph.status(n) != "accepted"]
        if args.json:
            dump({"units": unresolved, "obligations": graph.contained_holes(nodes)})
        else:
            for node in unresolved:
                print(f"{node['id']}\t{node['status']}\t{node['file']}:{node['line']}")
            for hole in graph.contained_holes(nodes):
                print(f"{hole['id']}\t{hole['file']}:{hole['line']}\t{hole['reason']}")
    elif command == "fingerprint":
        dump({"id": args.node, "fingerprint": graph.fingerprint(args.node)}) if args.json else print(graph.fingerprint(args.node))
    elif command == 'locate':
        from semantex_sources import source_url
        record = external or graph.nodes[args.node]
        result = {k: record[k] for k in ('id', 'file', 'line', 'column') if k in record}
        result['url'] = source_url(graph.root, record['file'], record['line'], record.get('page', False))
        dump(result) if args.json else print(f"{record['file']}:{record['line']}\n{result['url']}")
    elif command == "order":
        nodes = graph.order(graph.closure(args.node, support=False) if args.node else None)
        dump(nodes) if args.json else print("\n".join(nodes))
    elif command == "search":
        result = [graph.describe(n) for n in sorted(graph.nodes) if
                  args.query.casefold() in (n + " " + json.dumps(graph.nodes[n]["metadata"]) + " " + graph.source(n)).casefold()
                  and (not args.kind or graph.nodes[n]["kind"] == args.kind)
                  and (not args.status or graph.status(n) == args.status)]
        if args.json:
            dump(result)
        else:
            for node in result:
                print(f"{node['id']}\t{node['status']}\t{node['file']}:{node['line']}\t{node['metadata'].get('title', '')}")
    elif command == "export":
        content = json.dumps(graph.export(), indent=2, ensure_ascii=False) + "\n"
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content)
        else:
            print(content, end="")
    elif command == "graph":
        if args.target and args.target not in graph.nodes:
            raise ValueError(f"unknown node {args.target}")
        nodes = sorted(graph.closure(args.target, support=False) if args.target else graph.nodes)
        ids = {n: f"n{i}" for i, n in enumerate(nodes)}
        print("digraph dependencies {" if args.format == "dot" else "flowchart TD")
        for n in nodes:
            print(f'  {ids[n]} [label="{n}"];' if args.format == "dot" else f'  {ids[n]}["{n}"]')
        for n in nodes:
            for dep in sorted(graph.edges[n]):
                print(f"  {ids[n]} -> {ids[dep]};" if args.format == "dot" else f"  {ids[n]} --> {ids[dep]}")
        if args.format == "dot":
            print("}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
