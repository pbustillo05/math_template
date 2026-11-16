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
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
from semantex_sources import citation_source_is_retained
from semantex_links import RELATIONS, add_link, read_links, visible_links
from semantex_embeddings import DEFAULT, PROFILES, EmbeddingServer, model_setup
from semantex_rag import VectorIndex, context_bundle, hits, hybrid_rank, lexical_rank

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r"[A-Za-z][A-Za-z0-9:._-]*\Z")
REFERENCE = {"mention": (False, True), "use": (True, True),
             "hiddenmention": (False, False), "hiddenuse": (True, False)}
RETIRED = {"xref", "dxref", "hxref", "hdxref", "ref", "eqref", "autoref", "cref", "Cref",
           "uses", "proves", "evidence", "sorry", "leanref", "sourceat", "sourcepage"}
TOKEN = re.compile(r"\\(" + "|".join(sorted(set(REFERENCE) | RETIRED)) +
                   r"|cite|begin|end|label|section|subsection|subsubsection|chapter|item)(?![A-Za-z@])")
SEMANTIC = {
    "definition", "convention", "notation", "conjecture", "assumption",
    "hypothesis", "example", "counterexample", "remark", "construction",
    "observation", "warning", "question", "theorem", "lemma", "proposition",
    "corollary", "blank", "exercise", "openquestion", "proof",
}
NAVIGATION = {"goal", "sec", "eq", "fig", "tab"}
STATES = {"unreviewed", "conditional", "accepted", "disputed", "refuted", "obsolete"}
ROLES = {"proof-verifier": "pass", "style-referee": "pass",
         "counterexample": "clear-for-review"}
METADATA = {"title", "sketch", "related", "supersedes", "sources", "tags", "proof"}
HEADINGS = {"chapter": 0, "section": 1, "subsection": 2, "subsubsection": 3}
KINDS = dict(theorem="thm", lemma="lem", proposition="prop", corollary="cor", definition="def",
             convention="conv", notation="not", proof="prf", example="ex", counterexample="cex",
             remark="rem", conjecture="conj", assumption="assumption", hypothesis="hypothesis",
             construction="construction", observation="observation", question="question",
             openquestion="question", exercise="exercise", warning="warning",
             thm="thm", lem="lem", prop="prop", cor="cor")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_archived_source(root: Path, path: Path) -> bool:
    relative = path.relative_to(root)
    root = root.resolve()
    resolved = path.resolve()
    return "archived" in relative.parts or (
        resolved.is_relative_to(root) and "archived" in resolved.relative_to(root).parts
    )


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


def optional_argument(text, pos):
    """Return the inner span and end of a LaTeX optional argument."""
    start = pos
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos == len(text) or text[pos] != "[":
        return None, start
    inner = pos + 1
    pos = inner
    while pos < len(text):
        if text[pos] == "\\":
            pos += 2
        elif text[pos] == "{":
            _, pos = argument(text, pos)
        elif text[pos] == "]":
            return (inner, pos), pos + 1
        elif text[pos] == "}":
            raise ValueError("unmatched brace in optional argument")
        else:
            pos += 1
    raise ValueError("unclosed optional argument")


def key_options(text, span, allowed):
    """Read explicit key=value options and retain their source spans."""
    values, spans = {}, {}
    if span is None:
        return values, spans
    pos, limit = span
    while pos < limit:
        if text[pos].isspace():
            pos += 1
            continue
        match = re.match(r"([a-z]+)\s*=\s*", text[pos:limit])
        if not match:
            raise ValueError("expected key=value in optional argument")
        key = match[1]
        if key not in allowed or key in values:
            raise ValueError(f"unknown or repeated option {key}")
        start = pos + match.end()
        if start < limit and text[start] == "{":
            value, end = argument(text, start)
        else:
            comma = text.find(",", start, limit)
            end = limit if comma == -1 else comma
            value = text[start:end].strip()
        spans[key] = (start, end)
        values[key] = value
        pos = end
        while pos < limit and text[pos].isspace():
            pos += 1
        if pos < limit:
            if text[pos] != ",":
                raise ValueError(f"expected comma after {key}")
            pos += 1
    return values, spans


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
        self.occurrences: list[dict] = []
        self.description_spans: dict[str, list[tuple[int, int]]] = {}
        self.source_audits: dict[str, set[str]] = {}
        self.proofs: dict[str, str] = {}
        self.selected_proofs: dict[str, str] = {}
        self.records: dict[str, dict] = {}
        self.files: dict[str, bytes] = {}
        self.citations: list[dict] = []
        self.citations_by_owner: dict[str, list[dict]] = {}
        self.pdf_pages: dict[str, int] = {}
        self.file_hashes: dict[str, str] = {}
        self._fingerprints: dict[str, str] = {}
        from semantex_sources import index_sources
        self.source_labels, self.papers = index_sources(root, masked, argument)
        for subtree in ("draft", "notes"):
            for path in sorted((root / subtree).rglob("*.tex")):
                if not is_archived_source(root, path):
                    self.scan(path)
        for path in audit_tex_files(root):
            self.scan(path)
        authored_count = len(self.occurrences)
        self.add_retained_nodes()
        for index, occurrence in enumerate(self.occurrences):
            target, owner = occurrence["target"], occurrence["owner"]
            locator = f"{occurrence['file']}:{occurrence['line']}:{occurrence['column']}"
            if target not in self.nodes:
                if index < authored_count:
                    external = self.source_labels.get(target, [])
                    error = "ambiguous source label" if len(external) > 1 else "unresolved reference"
                    self.errors.append(f"{locator}: {error} {target}")
                continue
            if occurrence["dependency"]:
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
        self.dependents = self.adjacency(reverse=True)
        for citation in self.citations:
            self.citations_by_owner.setdefault(citation["owner"], []).append(citation)
        try:
            self.order()
            self.order(support=True)
        except ValueError as exc:
            self.errors.append(str(exc))
        self.read_source_audits()
        self.read_reviews()
        self.links = []
        try:
            self.links = read_links(root)
        except (ValueError, OSError) as exc:
            self.errors.append(str(exc))

    def add_retained_nodes(self):
        occurrences = set()
        for label, matches in self.source_labels.items():
            if len(matches) != 1:
                continue
            original = matches[0]
            self.nodes[label] = {k: v for k, v in original.items() if k not in {"latex", "proof", "mentions"}}
            self.nodes[label].update(scope="references", origin="retained", description="", metadata={},
                                     kind=KINDS.get(original.get("environment"), "external"))
            self.direct_edges[label] = set()
            for reference in original.get("mentions", []):
                item = tuple(reference.items())
                if item not in occurrences and len(self.source_labels.get(reference["owner"], [])) == 1:
                    occurrences.add(item)
                    self.occurrences.append(reference)

    def read_source_audits(self):
        for index in sorted((self.root / "references").glob("*/audit/semantex.json")):
            directory = index.parent
            if is_archived_source(self.root, index):
                continue
            try:
                safe_path(self.root, index.relative_to(self.root).as_posix())
                data = json.loads(index.read_text())
                applications, units = data.get("applications", {}), data.get("units", {})
                if data.get("schema_version") != 1 or not all(isinstance(m, dict) for m in (applications, units)):
                    raise ValueError("expected schema version 1 with applications and units maps")
                key = directory.parent.name
                for label, file in applications.items():
                    if label not in self.nodes or self.nodes[label]["kind"] != "src":
                        raise ValueError(f"unknown source application {label}")
                    if not any(c["targets"] and c["keys"] == [key]
                               for c in self.citations_by_owner.get(label, [])):
                        raise ValueError(f"{label} needs an exact citation to {key}")
                    path = (directory / file).relative_to(self.root).as_posix()
                    if Path(file).is_absolute() or not safe_path(self.root, path).is_relative_to(directory.resolve()):
                        raise ValueError(f"audit path for {label} must stay inside {directory.name}")
                    self.source_audits.setdefault(label, set()).add(path)
                for label, annotation in units.items():
                    self.register_source_annotation(label, annotation, key, index)
            except (ValueError, OSError, AttributeError, TypeError) as exc:
                self.errors.append(f"{index.relative_to(self.root)}: {exc}")

    def register_source_annotation(self, label, annotation, key, index):
        node = self.nodes.get(label, {})
        directory = index.parent.relative_to(self.root)
        prefix = f"prf:ref:{key}:" if node.get("environment") == "proof" else f"ref:{key}:"
        if not label.startswith(prefix) or not Path(node.get("file", "")).is_relative_to(directory):
            raise ValueError(f"{label}: annotations must use {prefix} IDs in this audit directory")
        if not isinstance(annotation, dict) or annotation.get("representation") not in {"transcription", "restatement"}:
            raise ValueError(f"{label}: specify a transcription or restatement")
        if annotation.get("coverage") not in {"statement", "proof", "statement-and-proof"}:
            raise ValueError(f"{label}: specify statement, proof, or statement-and-proof coverage")
        if annotation.get("dependencies") not in {"partial", "inspected"}:
            raise ValueError(f"{label}: specify partial or inspected dependency coverage")
        targets = {target for citation in self.citations_by_owner.get(label, []) if citation["keys"] == [key]
                   for target in citation["targets"]}
        if "source" in annotation:
            targets &= {annotation["source"]}
        if len(targets) != 1:
            raise ValueError(f"{label}: the annotation requires exactly one exact origin in {key}")
        target = self.nodes[targets.pop()]
        if self.hash_file(target["file"]) != annotation.get("source_sha256"):
            raise ValueError(f"{label}: origin hash differs from the retained file")
        node["provenance"] = dict(annotation, id=target["id"], file=target["file"],
                                  line=target["line"], page=target.get("page", False))
        node["kind"] = KINDS.get(node["environment"], node["kind"])
        self.source_audits.setdefault(label, set()).add(index.relative_to(self.root).as_posix())

    def citation_target(self, key, options):
        if key not in self.papers:
            raise ValueError(f"citation source unavailable: {key}")
        locator_types = set(options) & {"label", "line", "page"}
        if not locator_types and not options.get("file"):
            return None  # A citation of the whole paper.
        if len(locator_types) != 1:
            raise ValueError("citation requires exactly one of label, line or page")
        locator = locator_types.pop()
        if locator == "label":
            if "file" in options:
                raise ValueError("label locators use a unique native or virtual label")
            target = f"{key}:{options['label']}"
            if len(self.source_labels.get(target, [])) != 1:
                raise ValueError(f"unknown or ambiguous source label {target}")
            return target

        path = options.get("file")
        if not path and locator == "page":
            base = self.root / "references" / key
            pdfs = [p.relative_to(base).as_posix() for p in base.rglob("*.pdf")
                    if citation_source_is_retained(self.root, key, p.relative_to(self.root).as_posix())]
            if len(pdfs) == 1:
                path = pdfs[0]
        if not path or Path(path).is_absolute():
            raise ValueError(f"{locator} locator requires a file relative to the retained paper")
        file = (Path("references") / key / path).as_posix()
        if not citation_source_is_retained(self.root, key, file):
            raise ValueError("citation locator must point into the cited retained paper payload")
        value = options[locator]
        if not re.fullmatch(r"[1-9][0-9]*", value):
            raise ValueError(f"citation {locator} must be a positive integer")
        number = int(value)
        source = self.root / file
        if (source.suffix.lower() == ".pdf") != (locator == "page"):
            raise ValueError("use page for PDF sources and line for text sources")
        if locator == "line" and number > len(source.read_bytes().splitlines()):
            raise ValueError("citation source line out of range")
        if locator == "page" and number > self.pdf_page_count(file):
            raise ValueError("citation physical page out of range")
        identifier = f"loc:{key}:{file}:{number}"
        self.source_labels[identifier] = [dict(id=identifier, bib_key=key, source_label=None,
                                              file=file, line=number, page=locator == "page",
                                              kind="external", status="source-unreviewed")]
        return identifier

    def pdf_page_count(self, file):
        if file not in self.pdf_pages:
            executable = shutil.which("pdfinfo")
            if not executable:
                raise ValueError("pdfinfo (Poppler) is required to validate physical PDF locators")
            result = subprocess.run([executable, str(self.root / file)], capture_output=True, text=True,
                                    env=dict(os.environ, LC_ALL="C"), timeout=30)
            pages = re.search(r"(?m)^Pages:\s+([0-9]+)$", result.stdout)
            if result.returncode or not pages:
                raise ValueError(f"could not read physical page count of {file}")
            self.pdf_pages[file] = int(pages[1])
        return self.pdf_pages[file]

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

    def scan(self, path: Path) -> None:
        relative = path.relative_to(self.root).as_posix()
        if not path.resolve().is_relative_to(self.root.resolve()):
            self.errors.append(f"source path escapes repository: {relative}")
            return
        data = self.overlays.get(relative, path.read_bytes())
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.files[relative] = data
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

        def register_label(label, description, frame, offset, end):
            if not ID.fullmatch(label):
                raise ValueError(f"invalid literal node ID {label!r}")
            if label in self.nodes or label in self.source_labels:
                raise ValueError(f"duplicate node ID {label}")
            kind = label.split(":")[0]
            if kind not in NAVIGATION and not description.strip():
                raise ValueError(f"{label}: add a description to the mathematical label")
            if frame and frame["environment"] in SEMANTIC and kind not in NAVIGATION:
                if frame["owner"]:
                    raise ValueError(f"multiple principal labels in {frame['environment']}")
                frame["owner"] = label
            elif frame and frame["environment"] in set(HEADINGS) | {"item"} and not frame["owner"]:
                frame["owner"] = label
            node = dict(location(offset), id=label, kind=kind, metadata={}, offset=offset, origin="authored",
                        description=" ".join(description.split()), scope=relative.split("/")[0],
                        environment=frame["environment"] if frame else "anchor")
            if node["scope"] == "references":
                node["bib_key"] = path.relative_to(self.root).parts[1]
            self.nodes[label] = node
            self.direct_edges[label] = set()
            anchors.append({"node": node, "frame": frame if frame and frame["owner"] == label else None,
                            "start": offset, "end": end})

        while match := TOKEN.search(text, pos):
            command = match[1]
            offset = match.start()
            loc = location(offset)
            locator = f"{relative}:{loc['line']}"
            try:
                if command in RETIRED:
                    raise ValueError(f"retired authored command \\{command}; see agents/SEMANTEX.md")
                if command == "cite":
                    span, pos = optional_argument(text, match.end())
                    key, pos = argument(text, pos)
                    options, _ = key_options(text, span, {"text", "label", "file", "line", "page"})
                    target = self.citation_target(key, options)
                    if target:
                        references.append(dict(loc, target=target, dependency=False, visible=True,
                                               command=command, offset=offset, end_offset=pos,
                                               frame=context(), relation="citation"))
                    citations.append(dict(loc, keys=[key], targets=[target] if target else [],
                                          locator=options.get("text", ""), frame=context()))
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
                description_span = None
                if command == "label":
                    description_span, star = optional_argument(text, star)
                first, pos = argument(text, star)
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
                             "line": loc["line"], "owner": None}
                    stack.append(frame)
                    frames.append(frame)
                    if first == "proof":
                        span, pos = optional_argument(text, pos)
                        options, spans = key_options(text, span, {"label", "proves", "heading", "description"})
                        proof, claim = options.get("label", ""), options.get("proves", "")
                        if not proof.startswith("prf:") or not ID.fullmatch(claim):
                            raise ValueError("proof requires label=prf:ID and proves=RESULT")
                        register_label(proof, options.get("description", ""), frame, offset, pos)
                        self.proofs[proof] = claim
                        self.description_spans.setdefault(relative, []).append(spans["description"])
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
                    if not ID.fullmatch(first) and first not in self.source_labels:
                        raise ValueError("reference requires one literal label")
                    references.append(dict(loc, target=first, dependency=dependency,
                                           visible=visible, command=command, offset=offset,
                                           frame=context(), relation="reference"))
                    continue
                description = text[slice(*description_span)] if description_span else ""
                register_label(first, description, context(), offset, pos)
                if description_span:
                    self.description_spans.setdefault(relative, []).append(description_span)
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
            elif node["kind"] in {"eq", "fig", "tab"}:
                start, end = anchor["start"], anchor["end"]
            else:
                # Bare anchors remain supported for checked source inputs and old notes.
                start = anchor["start"]
                end = next((a["start"] for a in anchors[index + 1:] if a["node"]["kind"] not in {"eq", "fig", "tab"}), document_end)
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
            target = next((a for a in anchors if a["node"]["kind"] not in {"eq", "fig", "tab"} and a["node"]["offset"] > meta.start()), None)
            if not target:
                self.errors.append(f"{relative}:{location(meta.start())['line']}: metadata has no following unit")
                continue
            node = target["node"]
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

    def adjacency(self, reverse=False, support=False, mentions=False, within=None):
        edges = {node: set(deps) for node, deps in self.edges.items()}
        if support:
            for claim, proof in self.selected_proofs.items():
                if proof in edges:
                    edges[claim].add(proof)
        if mentions:
            for occurrence in self.occurrences:
                owner, target = occurrence["owner"], occurrence["target"]
                if owner in edges and target in edges:
                    edges[owner].add(target)
        if within is not None:
            edges = {node: deps & within for node, deps in edges.items() if node in within}
        if reverse:
            result = {node: set() for node in edges}
            for node, deps in edges.items():
                for dep in deps:
                    result[dep].add(node)
            return result
        return edges

    def distances(self, node, reverse=False, depth=None, support=False, mentions=False, within=None):
        if node not in self.nodes:
            raise ValueError(f"unknown node {node}")
        edges = self.adjacency(reverse, support, mentions, within)
        if node not in edges:
            raise ValueError(f"{node} is outside the requested scope")
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

    def focused_paths(self, root, distances, focused, reverse=False, mentions=False):
        """Keep focused hits and intervening vertices on their shortest paths."""
        selected = set(distances) & focused
        if selected == distances.keys():
            return selected
        parents = self.adjacency(reverse=not reverse, mentions=mentions)
        pending = list(selected)
        while pending:
            node = pending.pop()
            for parent in parents[node]:
                if parent not in selected and distances.get(parent) == distances[node] - 1:
                    selected.add(parent)
                    pending.append(parent)
        return selected | {root}

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
        if record["origin"] == "retained":
            original = self.source_labels[node][0]
            if "latex" in original:
                return original["latex"]
            if record.get("page"):
                return ""
            from semantex_sources import source_text
            text, _ = source_text(self.root / record["file"])
            return text.splitlines()[record["line"] - 1]
        return self.files[record["file"]].decode("utf-8")[record["start"]:record["end"]]

    def blocks(self, node, proof=None):
        if node not in self.nodes:
            raise ValueError(f"unknown node {node}")
        record = self.nodes[node]
        if record["origin"] == "retained":
            original = self.source_labels[node][0]
            if record.get("page"):
                return []
            line = record["line"]
            result = [dict(id=node, file=record["file"], start_line=record.get("start_line", line),
                           end_line=record.get("end_line", line), latex=self.source(node))]
            if original.get("proof"):
                result.append(original["proof"].copy())
            return result
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

    def reviewed_source(self, node):
        """Hash the argument independently of its retrieval descriptions."""
        record = self.nodes[node]
        text = self.source(node)
        if record["origin"] == "retained":
            return text
        for start, end in reversed(self.description_spans.get(record["file"], [])):
            if record["start"] <= start < end <= record["end"]:
                left, right = start - record["start"], end - record["start"]
                text = text[:left] + text[right:]
        return text

    def source_support(self, node):
        files = {self.source_labels[target][0]["file"]
                for citation in self.citations_by_owner.get(node, [])
                for target in citation["targets"]}
        if self.nodes[node]["origin"] == "retained":
            files.add(self.nodes[node]["file"])
        return files

    def hash_file(self, path):
        if path not in self.file_hashes:
            self.file_hashes[path] = sha(safe_path(self.root, path).read_bytes())
        return self.file_hashes[path]

    def fingerprint(self, node):
        if node in self._fingerprints:
            return self._fingerprints[node]
        closure = self.closure(node)
        paths = set().union(*(self.source_support(key) | self.source_audits.get(key, set()) for key in closure))
        paths.update(path.relative_to(self.root).as_posix() for path in (self.root / "preamble").rglob("*")
                     if path.is_file() and path.suffix in {".sty", ".tex"})
        paths.update(p for p in ("AGENTS.md", "writing-style.md", "agents/roles/auditor.md", "agents/PROTOCOL.md",
                                  "agents/SEMANTEX.md", "references/README.md", "references/lock.json") if (self.root / p).is_file())
        payload = {"schema": 3, "target": node,
                   "units": [(key, self.nodes[key]["file"], sha(self.reviewed_source(key).encode()),
                              sorted(self.edges[key]), self.selected_proofs.get(key)) for key in sorted(closure)],
                   "evidence": [(p, self.hash_file(p)) for p in sorted(paths)]}
        value = sha(json.dumps(payload, sort_keys=True).encode())
        self._fingerprints[node] = value
        return value

    def status(self, node, cache=None):
        cache = {} if cache is None else cache
        if self.nodes[node]["origin"] == "retained":
            return "source-unreviewed"
        state = self.records.get(node, {}).get("status", "unreviewed")
        if state != "accepted":
            return state
        if node not in cache:
            for key in self.order(self.closure(node), support=True):
                if key not in cache:
                    cache[key] = self._status_one(key, cache)
        return cache[node]

    def _status_one(self, node, cache):
        if node in cache:
            return cache[node]
        if self.nodes[node]["origin"] == "retained":
            return "source-unreviewed"
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
        if roles != set(ROLES) or self.nodes[node]["kind"] in NAVIGATION:
            valid = False
        if self.nodes[node]["kind"] == "src":
            if not self.source_support(node) or not self.source_audits.get(node):
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

    def assembled_files(self):
        """Follow the literal input commands of the main manuscript."""
        seen, pending = set(), ["draft/main.tex"]
        while pending:
            file = pending.pop()
            if file in seen or file not in self.files:
                continue
            seen.add(file)
            content = masked(self.files[file].decode())
            for match in re.finditer(r"\\(?:input|include|subfile)\s*\{([^{}]+)\}", content):
                relative = Path(match[1].strip())
                if relative.is_absolute() or re.search(r"[\\#]", str(relative)):
                    continue
                if not relative.suffix:
                    relative = relative.with_suffix(".tex")
                for directory in ((self.root / file).parent, self.root / "draft", self.root):
                    resolved = (directory / relative).resolve()
                    if resolved.is_relative_to(self.root.resolve()):
                        path = resolved.relative_to(self.root.resolve()).as_posix()
                        if path in self.files:
                            pending.append(path)
                            break
        return seen

    def release_errors(self, target):
        assembled = self.assembled_files()
        if not assembled:
            return ["release requires the assembled draft/main.tex"]
        roots = {n for n, d in self.nodes.items() if d["file"] in assembled and d["kind"] not in NAVIGATION}
        if target and target not in roots:
            return [f"{target}: release target must be a mathematical unit in the assembled manuscript"]
        support = self.closure(target) if target else set().union(*(self.closure(root) for root in roots))
        errors, cache = [], {}
        for node in sorted(support):
            record = self.nodes[node]
            if record["file"] not in assembled:
                errors.append(f"{node}: manuscript support must be in the assembly or handled by a cited src: application")
            if record["kind"] not in NAVIGATION and self.status(node, cache) != "accepted":
                errors.append(f"{node}: release requires current acceptance")
        for occurrence in self.occurrences:
            if occurrence["file"] not in assembled or not occurrence["visible"] or occurrence["relation"] != "reference":
                continue
            destination = self.nodes[occurrence["target"]]
            if destination["file"] not in assembled:
                errors.append(f"{occurrence['file']}:{occurrence['line']}: visible reference "
                              f"{occurrence['target']} is outside the assembled manuscript")
        return errors

    def describe(self, node, cache=None):
        data = {k: v for k, v in self.nodes[node].items() if k not in {"offset", "start", "end"}}
        data.update(dependencies=sorted(self.edges[node]), direct_dependencies=sorted(self.direct_edges[node]),
                    dependents=sorted(self.dependents[node]),
                    proofs=sorted(p for p, c in self.proofs.items() if c == node),
                    selected_proof=self.selected_proofs.get(node), proof_of=self.proofs.get(node),
                    status=self.status(node, cache), fingerprint=self.fingerprint(node),
                    source_audits=sorted(self.source_audits.get(node, ())))
        owners = [node]
        if node in self.selected_proofs:
            owners.append(self.selected_proofs[node])
        data["citations"] = [dict(c) for owner in owners for c in self.citations_by_owner.get(owner, [])]
        return data

    def export(self, focused=None):
        cache = {}
        focused = self.nodes.keys() if focused is None else focused
        return {"schema_version": 3, "edge_direction": "owner-uses-prerequisite",
                "nodes": [self.describe(node, cache) for node in sorted(focused)],
                "references": [self.occurrence(o) for o in self.occurrences
                               if o["owner"] in focused or o["target"] in focused],
                "links": [link for link in visible_links(self)
                          if link["from"] in focused or link["to"] in focused],
                "proof_attachments": self.proofs,
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

    def why(self, start, target, within=None):
        if start not in self.nodes or target not in self.nodes:
            raise ValueError("why requires two existing labels")
        edges = self.adjacency(within=within)
        if start not in edges or target not in edges:
            raise ValueError("both labels must be within the requested scope")
        queue, paths = deque([start]), {start: [start]}
        while queue:
            node = queue.popleft()
            if node == target:
                path = paths[node]
                return {"path": path, "steps": [
                    {"owner": a, "target": b, "uses": [o for o in self.references(a) if o["dependency"] and o["target"] == b]}
                    for a, b in zip(path, path[1:])]}
            for dep in sorted(edges[node]):
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


def positive_int(value):
    try:
        integer = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("expected a positive integer") from None
    if integer < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return integer


def print_hits(result, as_json):
    if as_json:
        dump(result)
        return
    for item in result:
        print(f"{item['rank']}\t{item['score']:.6f}\t{item['id']}\t"
              f"{item['scope']}\t{item['file']}:{item['line']}")
        if item.get("description"):
            print("   " + item["description"])
        if item.get("versions"):
            print("   versions: " + ", ".join(item["versions"]))
        for block in item.get("blocks", []):
            print(block["latex"])


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
        child.add_argument("--show", choices=["description", "statement", "proof", "content"], default="content")
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
    search.add_argument("--mode", choices=["lexical", "semantic", "hybrid"], default="lexical")
    neighbors = sub.add_parser("neighbors", help="nearest mathematical units to a known label")
    neighbors.add_argument("node")
    neighbors.add_argument("--kind")
    neighbors.add_argument("--status")
    neighbors.add_argument("--json", action="store_true")
    for command in (search, neighbors):
        command.add_argument("--k", type=positive_int, default=16)
        command.add_argument("--show", choices=["labels", "description", "content"],
                             default="labels" if command is neighbors else "description")
        command.add_argument("--all-versions", action="store_true")
        command.add_argument("--profile", choices=PROFILES, default=DEFAULT)
    context = sub.add_parser("context", help="bundle exact snippets and declared support for an agent")
    context.add_argument("seeds", metavar="ID", nargs="+")
    context.add_argument("--depth", type=depth_value, default=1)
    context.add_argument("--max-chars", type=positive_int, default=8000)
    context.add_argument("--json", action="store_true")
    rag = sub.add_parser("rag", help="manage the local semantic index")
    actions = rag.add_subparsers(dest="action", required=True)
    for action in ("setup", "build", "status", "profiles"):
        child = actions.add_parser(action)
        if action != "profiles":
            child.add_argument("--profile", choices=PROFILES, default=DEFAULT)
        child.add_argument("--json", action="store_true")
    for flag, help_text in (("--scope", "focus coverage on draft, notes, or references"),
                            ("--paper", "focus coverage on one retained paper")):
        actions.choices["status"].add_argument(flag, help=help_text)
    link = sub.add_parser("link", help="record a relationship between inspected units")
    link.add_argument("node")
    link.add_argument("other")
    link.add_argument("--relation", choices=RELATIONS, required=True)
    link.add_argument("--json", action="store_true")
    links = sub.add_parser("links", help="show versions and provenance relationships")
    links.add_argument("node")
    links.add_argument("--json", action="store_true")
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
    for name in ("get", "show", "locate", "deps", "rdeps", "ancestors", "descendants",
                 "refs", "backrefs", "why", "order", "frontier", "search", "neighbors", "context", "graph", "export"):
        child = sub.choices[name]
        child.add_argument("--scope", help="comma-separated draft, notes, references")
        child.add_argument("--paper", help="focus on a retained paper by bibliography key")
        if name in {"deps", "rdeps", "ancestors", "descendants", "why", "graph"}:
            child.add_argument("--within", action="store_true", help="restrict traversal to the selected scope")
    args = parser.parse_args(argv)
    if args.command == "rag":
        if args.action == "profiles":
            dump({"default": DEFAULT, "profiles": PROFILES})
            return 0
        if args.action == "setup":
            path = model_setup(args.root.resolve(), args.profile)
            dump({"profile": args.profile, "path": str(path)}) if args.json else print(path)
            return 0
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
        exported['errors'] = []
        dump(exported)
        return 0
    if graph.errors:
        raise ValueError("\n".join(graph.errors))
    command = args.command
    if hasattr(args, "node") and args.node and args.node not in graph.nodes:
        if len(graph.source_labels.get(args.node, [])) > 1:
            raise ValueError(f"ambiguous upstream label {args.node}")
        raise ValueError(f"unknown node {args.node}; try semantex search")
    scope = getattr(args, "scope", None)
    scopes = set(scope.split(",")) if scope else {"draft", "notes", "references"}
    if scopes - {"draft", "notes", "references"}:
        raise ValueError("scope must be draft, notes, references, or a comma-separated list")
    paper = getattr(args, "paper", None)
    if paper and paper not in graph.papers:
        raise ValueError(f"unknown or unavailable paper {paper}")
    if paper and not scope:
        scopes = {"references"}
    focused = {n for n, record in graph.nodes.items()
               if record["scope"] in scopes and (not paper or record.get("bib_key") == paper)}
    within = focused if getattr(args, "within", False) else None
    if command == "link":
        relation = add_link(graph, args.node, args.other, args.relation)
        if args.json:
            dump(relation)
        else:
            print(f"{relation['from']} {relation['relation']} {relation['to']}")
    elif command == "links":
        relations = [link for link in visible_links(graph) if args.node in (link["from"], link["to"])]
        if args.json:
            dump(relations)
        else:
            for link in relations:
                print(f"{link['from']} {link['relation']} {link['to']} [{link['status']}]")
    elif command == "check":
        errors = [f"{node}: acceptance is stale or incomplete" for node, record in graph.records.items()
                  if record["status"] == "accepted" and graph.status(node) != "accepted"]
        if args.release:
            if args.target and args.target not in graph.nodes:
                raise ValueError(f"unknown node {args.target}")
            if args.target and graph.nodes[args.target]["kind"] in NAVIGATION:
                raise ValueError("release target must be a mathematical unit, not a planning/navigation anchor")
            errors.extend(graph.release_errors(args.target))
        if errors:
            raise ValueError("\n".join(errors))
        print(f"checked {len(graph.nodes)} anchors, {sum(map(len, graph.edges.values()))} logical edges, "
              f"{len(graph.occurrences)} reference occurrences; mathematical validity is not checked")
        for warning in graph.warnings:
            print("warning: " + warning, file=sys.stderr)
    elif command in {"get", "show"}:
        if args.node not in focused:
            raise ValueError(f"{args.node} is outside the requested scope")
        record = graph.describe(args.node)
        blocks = graph.blocks(args.node, args.proof)
        if args.show == "description":
            if args.json:
                dump({"id": args.node, "description": record["description"]})
            else:
                print(record["description"])
            return 0
        if args.show == "statement":
            blocks = blocks[:1]
        elif args.show == "proof":
            blocks = blocks if record["kind"] == "prf" else blocks[1:]
        if not blocks and record.get("page") and not args.json:
            raise ValueError("PDF source has no exact LaTeX block; use locate for the page")
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
        distances = graph.distances(args.node, reverse, args.depth, mentions=args.mentions, within=within)
        selected = graph.focused_paths(args.node, distances, focused, reverse, args.mentions)
        nodes = [dict(graph.describe(n), distance=d, in_scope=n in focused)
                 for n, d in sorted(distances.items(), key=lambda p: (p[1], p[0])) if n != args.node and n in selected]
        if args.json:
            dump(nodes)
        elif args.tree:
            edges = graph.adjacency(reverse, mentions=args.mentions, within=within)
            seen = {}
            stack = [(args.node, 0)]
            while stack:
                node, distance = stack.pop()
                repeated = node in seen and seen[node] <= distance
                print("  " * distance + node + (" [already shown]" if repeated else "")
                      + (" [outside scope]" if node not in focused else ""))
                if repeated or (args.depth is not None and distance >= args.depth):
                    continue
                seen[node] = distance
                stack.extend((dep, distance + 1) for dep in sorted(edges[node] & selected, reverse=True))
        else:
            for node in nodes:
                suffix = "" if node["in_scope"] else "\t[outside scope]"
                print(f"{node['distance']}\t{node['id']}\t{node['status']}\t{node['file']}:{node['line']}{suffix}")
    elif command in {"refs", "backrefs"}:
        reverse = command == "backrefs"
        refs = graph.references(args.node, reverse)
        if scope or paper:
            endpoint = "owner" if reverse else "target"
            refs = [ref for ref in refs if ref[endpoint] in focused]
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
        result = graph.why(args.node, args.target, within=within)
        if scope or paper:
            result["outside_scope"] = [node for node in result["path"] if node not in focused]
        if args.json:
            dump(result)
        else:
            print(" -> ".join(node if node in focused else node + " [outside scope]" for node in result["path"]))
            for step in result["steps"]:
                for ref in step["uses"]:
                    from semantex_sources import source_text
                    raw = source_text(graph.root / ref["file"])[0].splitlines()[ref["line"] - 1]
                    print(f"  {ref['file']}:{ref['line']}:{ref['column']} | {raw}")
    elif command == "frontier":
        nodes = graph.closure(args.node)
        unresolved = [dict(graph.describe(n), reasons=["current review missing, disputed, or stale"])
                      for n in sorted(nodes) if n in focused and graph.status(n) != "accepted"]
        if args.json:
            dump({"units": unresolved})
        else:
            for node in unresolved:
                print(f"{node['id']}\t{node['status']}\t{node['file']}:{node['line']}")
    elif command == "fingerprint":
        dump({"id": args.node, "fingerprint": graph.fingerprint(args.node)}) if args.json else print(graph.fingerprint(args.node))
    elif command == 'locate':
        from semantex_sources import source_url
        record = graph.nodes[args.node]
        if args.node not in focused:
            raise ValueError(f"{args.node} is outside the requested scope")
        result = {k: record[k] for k in ('id', 'file', 'line', 'column') if k in record}
        result['url'] = source_url(graph.root, record['file'], record['line'], record.get('page', False))
        if "provenance" in record:
            origin = record["provenance"]
            result["origin"] = dict(origin, url=source_url(graph.root, origin["file"], origin["line"], origin["page"]))
        if args.json:
            dump(result)
        else:
            print(f"{record['file']}:{record['line']}\n{result['url']}")
            if "origin" in result:
                print(f"original {result['origin']['id']}\n{result['origin']['url']}")
    elif command == "order":
        nodes = [n for n in graph.order(graph.closure(args.node, support=False) if args.node else None) if n in focused]
        dump(nodes) if args.json else print("\n".join(nodes))
    elif command == "rag":
        model = PROFILES[args.profile]
        index = VectorIndex(graph.root, args.profile, model["dimensions"])
        result = (index.build(graph, EmbeddingServer(graph.root, args.profile)) if args.action == "build"
                  else index.status(graph, focused, scopes, paper))
        dump(dict(result, profile=args.profile))
    elif command in {"search", "neighbors"}:
        candidates = {n for n in focused if (not args.kind or graph.nodes[n]["kind"] == args.kind)
                      and (not args.status or graph.status(n) == args.status)}
        index = VectorIndex(graph.root, args.profile, PROFILES[args.profile]["dimensions"])
        if command == "neighbors":
            ranking = index.rank(graph, candidates, label=args.node, all_versions=args.all_versions)
        elif args.mode == "lexical":
            ranking = lexical_rank(graph, args.query, candidates)
        else:
            if not args.query.strip():
                raise ValueError("semantic and hybrid search require a query")
            backend = EmbeddingServer(graph.root, args.profile)
            ranking = index.rank(graph, candidates, query=args.query, backend=backend)
            if args.mode == "hybrid":
                ranking = hybrid_rank(lexical_rank(graph, args.query, candidates), ranking)
        print_hits(hits(graph, ranking, args.k, args.show, args.all_versions), args.json)
    elif command == "context":
        bundle = context_bundle(graph, args.seeds, args.depth, args.max_chars, focused)
        if args.json:
            dump(bundle)
        else:
            for block in bundle["blocks"]:
                print(f"% {block['id']} | {block['file']}:{block['start_line']}\n{block['latex']}\n")
            for unit in bundle["omitted"]:
                print(f"% omitted {unit['id']} ({unit['reason']})")
    elif command == "export":
        content = json.dumps(graph.export(focused), indent=2, ensure_ascii=False) + "\n"
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content)
        else:
            print(content, end="")
    elif command == "graph":
        if args.target and args.target not in graph.nodes:
            raise ValueError(f"unknown node {args.target}")
        edges = graph.adjacency(within=within)
        if args.target:
            destinations = graph.distances(args.target, within=within)
            nodes = sorted(graph.focused_paths(args.target, destinations, focused))
        else:
            nodes = sorted(focused)

        ids = {n: f"n{i}" for i, n in enumerate(nodes)}
        print("digraph dependencies {" if args.format == "dot" else "flowchart TD")
        for n in nodes:
            label = n if n in focused else n + " (outside scope)"
            if args.format == "dot":
                print(f"  {ids[n]} [label={json.dumps(label, ensure_ascii=False)}];")
            else:
                print(f'  {ids[n]}["{label.replace(chr(34), "#quot;")}"]')
        for n in nodes:
            for dep in sorted(edges[n] & ids.keys()):
                print(f"  {ids[n]} -> {ids[dep]};" if args.format == "dot" else f"  {ids[n]} --> {ids[dep]}")
        if args.format == "dot":
            print("}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, sqlite3.Error, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
