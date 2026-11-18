#!/usr/bin/env python3
"""Index literal authored LaTeX, retrieve exact units, and navigate review dependencies.

No TeX expansion or mathematical dependency inference is performed. Source is the
single authority for the index, including organized research notes.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import defaultdict, deque
from functools import cache, cached_property
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
from semantex_cache import digest, load_graph
from semantex_links import RELATIONS, add_link, read_links, visible_links
from semantex_embeddings import DEFAULT, PROFILES, EmbeddingServer, model_setup
from semantex_rag import StaleIndex, VectorIndex, context_bundle, hits, hybrid_rank, lexical_rank

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r"[A-Za-z][A-Za-z0-9:._-]*\Z")
REFERENCE = {"mention": (False, True), "use": (True, True),
             "hiddenmention": (False, False), "hiddenuse": (True, False)}
RETIRED = {"xref", "dxref", "hxref", "hdxref", "ref", "eqref", "autoref", "cref", "Cref",
           "uses", "proves", "evidence", "sourceat", "sourcepage"}
TOKEN = re.compile(r"\\(" + "|".join(sorted(set(REFERENCE) | RETIRED)) +
                   r"|cite|begin|end|label|section|subsection|subsubsection|chapter|item)(?![A-Za-z@])")
SEMANTIC = {
    "definition", "convention", "notation", "conjecture", "assumption",
    "hypothesis", "example", "counterexample", "remark", "construction",
    "observation", "warning", "question", "theorem", "lemma", "proposition",
    "corollary", "blank", "exercise", "openquestion", "proof", "clause",
    "claim", "conditionaltheorem", "manuscriptinput", "obligation", "principle", "problem", "proposal", "scope", "tool",
}
NAVIGATION = {"goal", "sec", "eq", "fig", "tab", "chap", "part", "app", "item"}
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
             thm="thm", lem="lem", prop="prop", propn="prop", cor="cor")


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


LITERAL = re.compile(
    r"\\begin\{(verbatim\*?|Verbatim|lstlisting|minted)\}.*?\\end\{\1\}"
    r"|\\verb\*?(?P<delimiter>[^\w\s]).*?(?P=delimiter)", re.S)
COMMENT = re.compile("%")
NEWLINE = re.compile("\n")
BRACE_TOKEN = re.compile(r"\\[{}\\]|[{}]")
MARKDOWN_REFERENCE = re.compile(r"(?<!\\)\\(" + "|".join(REFERENCE) + r")(?![A-Za-z@])")


def literal_mask(text: str) -> str:
    return LITERAL.sub(lambda match: "\n".join(" " * len(line) for line in match[0].split("\n")), text)


def masked(text: str) -> str:
    """Mask comments/literal regions without changing character offsets."""
    return mask_comments(literal_mask(text))


def mask_comments(text):
    # A percent preceded by an odd number of backslashes is literal.
    parts, start = [], 0
    for match in COMMENT.finditer(text):
        offset = match.start()
        if offset < start:
            continue
        preceding = offset
        while preceding > 0 and text[preceding - 1] == "\\":
            preceding -= 1
        if (offset - preceding) % 2 == 0:
            end = text.find("\n", offset)
            end = len(text) if end == -1 else end
            parts.extend((text[start:offset], " " * (end - offset)))
            start = end
    return "".join((*parts, text[start:])) if parts else text


def argument(text: str, pos: int) -> tuple[str, int]:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos == len(text) or text[pos] != "{":
        raise ValueError("annotation requires a literal brace argument")
    start, depth = pos + 1, 1
    for match in BRACE_TOKEN.finditer(text, start):
        if match[0] == "{":
            depth += 1
        elif match[0] == "}":
            depth -= 1
            if depth == 0:
                return text[start:match.start()].strip(), match.end()
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
    def __getattr__(self, name):
        snapshot = self.__dict__.get("_snapshot")
        if snapshot is None or name not in snapshot.fields:
            raise AttributeError(name)
        value = snapshot.read(name)
        self.__dict__[name] = value
        return value

    def __init__(self, root: Path, overlays=None, *, scan_store=None):
        self.root = root
        self._scan_store = scan_store
        namespace_file = root / "workflow/label-namespaces.json"
        self.label_namespaces = json.loads(namespace_file.read_text()).get("files", {}) if namespace_file.exists() else {}
        binding_file = root / "workflow/reference-bindings.json"
        self.reference_bindings = json.loads(binding_file.read_text()).get("files", {}) if binding_file.exists() else {}
        self.overlays = overlays or {}
        self.nodes: dict[str, dict] = {}
        self.edges: dict[str, set[str]] = {}
        self.direct_edges: dict[str, set[str]] = {}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.declarations_by_file: dict[str, dict[str, str]] = {}
        self.native_aliases_by_file: dict[str, dict[str, str]] = {}
        self.aliases: dict[str, str] = {}
        self.alias_declarations: dict[str, dict] = {}
        self.unit_redirects: dict[str, dict] = {}
        self.redirect_evidence: set[str] = set()
        self._declarations: dict[str, dict] = {}
        self._pending_aliases: dict[str, tuple[str, str]] = {}
        self.label_aliases = {}
        alias_file = root / "workflow/label-aliases.json"
        if alias_file.exists():
            try:
                data = json.loads(alias_file.read_text())
                if data.get("schema_version") != 1 or not isinstance(data.get("files"), dict):
                    raise ValueError("expected schema version 1 with a files map")
                for file, mapping in data["files"].items():
                    path = Path(file)
                    if path.is_absolute() or ".." in path.parts or not file.endswith(".tex"):
                        raise ValueError(f"invalid alias source path {file}")
                    self.validate_alias_map(mapping)
                    self.label_aliases[file] = mapping
            except (ValueError, OSError, AttributeError, TypeError) as exc:
                self.errors.append(f"workflow/label-aliases.json: {exc}")
        self.occurrences: list[dict] = []
        self.description_spans: dict[str, list[tuple[int, int]]] = {}
        self.source_audits: dict[str, set[str]] = {}
        self.proofs: dict[str, str] = {}
        self.selected_proofs: dict[str, str] = {}
        self.records: dict[str, dict] = {}
        self.files: dict[str, bytes] = {}
        self.citations: list[dict] = []
        self.pdf_pages: dict[str, int] = {}
        self.reset_review_cache()
        self.document_contexts = {}
        self.context_files = {}
        context_file = root / "workflow/document-contexts.json"
        if context_file.exists():
            try:
                data = json.loads(context_file.read_text())
                if data.get("schema_version") != 1 or not isinstance(data.get("contexts"), dict):
                    raise ValueError("expected schema version 1 with a contexts map")
                for key, record in data["contexts"].items():
                    if not ID.fullmatch(key) or not key.startswith("ctx:") or not isinstance(record, dict):
                        raise ValueError(f"invalid document context {key}")
                    for field in ("labels", "references"):
                        mapping = record.get(field, {})
                        if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
                            raise ValueError(f"{key}: {field} must map original labels to graph identities")
                    self.validate_alias_map(record.get("aliases", {}))
                    self.document_contexts[key] = record
            except (ValueError, OSError, AttributeError, TypeError) as exc:
                self.errors.append(f"workflow/document-contexts.json: {exc}")
        from semantex_sources import index_sources
        self.source_spans = {}
        self.source_labels, self.papers = index_sources(root, masked, argument, self.source_spans, scan_store)
        for subtree in ("draft", "notes"):
            for path in sorted((root / subtree).rglob("*.tex")):
                if not is_archived_source(root, path):
                    self.scan_file(path)
        for path in audit_tex_files(root):
            self.scan_file(path)
        self.add_source_document_locators()
        self.markdown_start = len(self.occurrences)
        markdown_paths = set()
        for subtree in ("draft", "notes"):
            markdown_paths.update((root / subtree).rglob("*.md"))
        for directory in (root / "references").glob("*/audit"):
            markdown_paths.update(directory.rglob("*.md"))
        for path in sorted(markdown_paths):
            if not is_archived_source(root, path):
                self.scan_file(path, markdown=True)
        self.markdown_end = len(self.occurrences)
        self.finalize_aliases()
        authored_count = len(self.occurrences)
        self.add_retained_nodes()
        self.add_unresolved_nodes()
        self.read_unit_redirects()
        for index, occurrence in enumerate(self.occurrences):
            self.bind_occurrence(occurrence, authored=index < authored_count)
        canonical_proofs = {}
        for proof, claim in self.proofs.items():
            proof, claim = self.resolve_id(proof), self.resolve_id(claim)
            if proof in canonical_proofs and canonical_proofs[proof] != claim:
                self.errors.append(f"alias proof has conflicting attachments: {proof}")
            canonical_proofs[proof] = claim
        self.proofs = canonical_proofs
        for proof, claim in self.proofs.items():
            if proof not in self.nodes or not proof.startswith("prf:"):
                self.errors.append(f"invalid proof ID {proof}")
            if claim not in self.nodes or self.nodes[claim]["kind"] in NAVIGATION | {"prf", "gap"}:
                self.errors.append(f"invalid proof target {claim}")
        for claim in self.nodes:
            proofs = self.attachments.get(claim, ())
            chosen = self.nodes[claim]["metadata"].get("proof")
            if chosen:
                chosen = self.resolve_id(chosen)
                self.nodes[claim]["metadata"]["proof"] = chosen
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

    def bind_occurrence(self, occurrence, *, authored):
        requested = occurrence["target"]
        occurrence.setdefault("requested_target", requested)
        occurrence["target"] = self.resolve_id(requested)
        target, owner = occurrence["target"], occurrence["owner"]
        locator = f"{occurrence['file']}:{occurrence['line']}:{occurrence['column']}"
        if target not in self.nodes:
            if authored:
                external = self.source_labels.get(target, [])
                error = "ambiguous source label" if len(external) > 1 else "unresolved reference"
                self.errors.append(f"{locator}: {error} {target}")
            return
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

    @staticmethod
    def validate_alias_map(mapping):
        """An explicit native-label map authorizes scope validation, not merging."""
        if not isinstance(mapping, dict) or not all(
                isinstance(k, str) and isinstance(v, str) and ID.fullmatch(k) and ID.fullmatch(v)
                for k, v in mapping.items()):
            raise ValueError("aliases must map literal native labels to literal native labels")
        for alias in mapping:
            current, seen = alias, set()
            while current in mapping:
                if current in seen:
                    raise ValueError(f"alias cycle involving {alias}")
                seen.add(current)
                current = mapping[current]

    @cached_property
    def attachments(self):
        by_claim = defaultdict(list)
        for proof, claim in sorted(self.proofs.items()):
            by_claim[claim].append(proof)
        return dict(by_claim)

    @cached_property
    def citations_by_owner(self):
        by_owner = defaultdict(list)
        for citation in self.citations:
            by_owner[citation["owner"]].append(citation)
        return dict(by_owner)

    @cached_property
    def _decoded_files(self):
        return {}

    @cached_property
    def _citation_lines(self):
        return {}

    @cached_property
    def _paper_pdfs(self):
        return {}

    def decoded_file(self, file):
        if file not in self._decoded_files:
            self._decoded_files[file] = self.files[file].decode("utf-8")
        return self._decoded_files[file]

    def finalize_aliases(self):
        """Validate every listed declaration against the same actual semantic frame."""
        for file, mapping in self.native_aliases_by_file.items():
            declarations = self.declarations_by_file.get(file, {})
            for native, target in mapping.items():
                if native not in declarations:
                    self.errors.append(f"{file}: alias declaration not found: {native}")
                    continue
                alias = declarations[native]
                record = self._declarations.get(alias)
                if alias not in self._pending_aliases or record is None:
                    continue  # Registration already reported a collision or invalid label.
                while target in mapping:
                    target = mapping[target]
                if target not in declarations:
                    self.errors.append(f"{file}: alias target declaration not found: {target}")
                    continue
                canonical = declarations[target]
                primary = self._declarations.get(canonical)
                frame = record["frame"]
                if (record["kind"] in NAVIGATION or primary is None or
                        primary["kind"] in NAVIGATION):
                    self.errors.append(f"{file}:{record['line']}: aliases cannot merge navigation anchors")
                    continue
                if (frame is None or frame["environment"] not in SEMANTIC or
                        primary["frame"] is None or frame["start"] != primary["frame"]["start"] or
                        frame["owner"] != canonical or
                        canonical not in self.nodes):
                    self.errors.append(f"{file}:{record['line']}: alias {native} must name the same actual semantic frame as {target}")
                    continue
                self.aliases[alias] = canonical
                self.alias_declarations[alias] = {
                    k: v for k, v in record.items() if k != "frame"
                }
                self.alias_declarations[alias]["canonical_id"] = canonical
                self.alias_declarations[alias]["effective_description"] = (
                    record["description"] or self.nodes[canonical]["description"])
                self.alias_declarations[alias]["description_inherited"] = not bool(record["description"])
        # Values are terminal node IDs, never another alias; no graph edge is added.
        for alias, canonical in self.aliases.items():
            self.nodes[canonical].setdefault("aliases", []).append(alias)
        for node in self.nodes.values():
            if "aliases" in node:
                node["aliases"].sort()

    def unit_identity_hash(self, node, resolver=None):
        """Pin exact reviewed body and reference meaning, independent of file moves.

        Retrieval descriptions are excluded by the existing review convention.
        Reference commands, dependency roles, resolved targets, proof attachment
        and explicit proof selection remain part of this editorial identity.
        """
        resolve = resolver or self.resolve_id
        node = resolve(node)
        record = self.nodes[node]
        references = [(o["command"], resolve(o["target"]), o["dependency"], o["relation"])
                      for o in self.occurrences if o["owner"] == node]
        payload = {"schema": 1, "body": self.reviewed_source(node),
                   "kind": record["kind"], "references": references,
                   "proof_of": resolve(self.proofs[node]) if node in self.proofs else None,
                   "proof_choice": resolve(record["metadata"]["proof"])
                       if record["metadata"].get("proof") else None}
        return sha(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode())

    def read_unit_redirects(self):
        """Load reviewed editorial identities, never infer mathematical acceptance.

        The whole registry fails closed: invalid evidence, a stale canonical
        unit, or a bad chain installs no redirects. Evidence paths are immutable
        historical payloads, distinct from the possibly moved live source.
        """
        path = self.root / "workflow/unit-redirects.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            records = data.get("redirects")
            if data.get("schema_version") != 1 or not isinstance(records, dict):
                raise ValueError("expected schema version 1 with a redirects map")
            terminal, evidence = {}, set()

            def identity(value):
                if not isinstance(value, str) or not ID.fullmatch(value):
                    raise ValueError(f"invalid qualified identity {value!r}")
                return value

            def digest(value):
                if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                    raise ValueError("expected a lowercase SHA-256")
                return value

            def checked_file(file, expected):
                if not isinstance(file, str) or not file:
                    raise ValueError("missing evidence path")
                content = safe_path(self.root, file).read_bytes()
                if sha(content) != digest(expected):
                    raise ValueError(f"evidence hash mismatch: {file}")
                evidence.add(file)
                return content

            def resolve(value, seen=None):
                seen = set() if seen is None else seen
                while value in records:
                    if value in seen:
                        raise ValueError(f"redirect cycle at {value}")
                    seen.add(value)
                    record = records[value]
                    if not isinstance(record, dict):
                        raise ValueError(f"{value}: redirect must be a record")
                    value = identity(record.get("target"))
                return self.resolve_id(value)

            for retired, record in records.items():
                identity(retired)
                if retired in self.nodes or retired in self._declarations or retired in self.aliases or retired in self.source_labels:
                    raise ValueError(f"{retired}: redirect collides with a live declaration")
                target = resolve(retired)
                if target not in self.nodes or self.nodes[target]["origin"] != "authored":
                    raise ValueError(f"{retired}: canonical target must be a live authored unit")
                node = self.nodes[target]
                original, review = record.get("original"), record.get("review")
                if not isinstance(original, dict) or not isinstance(review, dict):
                    raise ValueError(f"{retired}: original and review records are required")
                if node["kind"] in NAVIGATION | {"gap"} or original.get("kind") != node["kind"]:
                    raise ValueError(f"{retired}: redirect must preserve mathematical kind")
                if self.unit_identity_hash(target, resolver=resolve) != digest(record.get("canonical_unit_sha256")):
                    raise ValueError(f"{retired}: canonical unit hash is stale")
                if review.get("status") != "reviewed-equivalent" or any(
                        not isinstance(review.get(k), str) or not review[k].strip()
                        for k in ("reviewer", "basis")):
                    raise ValueError(f"{retired}: explicit reviewed equivalence is required")
                if not checked_file(review.get("report"), review.get("report_sha256")).strip():
                    raise ValueError(f"{retired}: equivalence review report is empty")
                native = identity(original.get("source_label"))
                if not isinstance(original.get("context"), dict) or original["context"].get("labels", {}).get(native) != retired:
                    raise ValueError(f"{retired}: original context must preserve its native declaration")
                for key in ("historical_status", "review_status"):
                    if not isinstance(original.get(key), str) or not original[key].strip():
                        raise ValueError(f"{retired}: preserve original {key}")
                if not isinstance(original.get("file"), str) or not original["file"]:
                    raise ValueError(f"{retired}: original source path is required")
                historical_path = Path(original["file"])
                if historical_path.is_absolute() or ".." in historical_path.parts:
                    raise ValueError(f"{retired}: original path must be repository-relative")
                raw = checked_file(original.get("evidence_file"), original.get("source_sha256"))
                text = raw.decode("utf-8")
                start, end = original.get("start"), original.get("end")
                if (type(start) is not int or type(end) is not int or
                        not 0 <= start < end <= len(text)):
                    raise ValueError(f"{retired}: invalid original character span")
                for key in ("line", "end_line", "column"):
                    if type(original.get(key)) is not int or original[key] < 1:
                        raise ValueError(f"{retired}: invalid original {key}")
                if original["end_line"] < original["line"]:
                    raise ValueError(f"{retired}: reversed original lines")
                if original["end_line"] != text.count("\n", 0, end) + 1:
                    raise ValueError(f"{retired}: original end line disagrees with span")
                unit = text[start:end]
                if sha(unit.encode()) != digest(original.get("unit_sha256")):
                    raise ValueError(f"{retired}: original unit hash mismatch")
                # Check the literal native declaration, not a coincidental
                # reference or a label string hidden in a comment.
                found = False
                original_attachment = None
                declaration_offsets = []
                clean = masked(unit)
                opening = re.match(r"\s*\\begin\s*\{([^{}]+)\}", clean)
                if not opening or opening[1] not in SEMANTIC or ((original["kind"] == "prf") != (opening[1] == "proof")):
                    raise ValueError(f"{retired}: original span must contain its actual semantic unit")
                for match in TOKEN.finditer(clean):
                    if match[1] == "label":
                        _, pos = optional_argument(clean, match.end())
                        label, _ = argument(clean, pos)
                        if label == native:
                            found = True
                            declaration_offsets.append(start + match.start())
                    elif match[1] == "begin":
                        env, pos = argument(clean, match.end())
                        if env == "proof":
                            span, _ = optional_argument(clean, pos)
                            if span:
                                opts, _ = key_options(clean, span, {"label", "proves", "description", "heading"})
                                if match.start() == len(clean) - len(clean.lstrip()):
                                    original_attachment = opts.get("proves")
                                if opts.get("label") == native:
                                    found = True
                                    declaration_offsets.append(start + match.start())
                if not found:
                    raise ValueError(f"{retired}: native declaration is absent from the original unit")
                if not any(text.count("\n", 0, offset) + 1 == original["line"] and
                           offset - text.rfind("\n", 0, offset) == original["column"]
                           for offset in declaration_offsets):
                    raise ValueError(f"{retired}: original declaration location disagrees with evidence")
                if original["kind"] == "prf":
                    context = original["context"]
                    attached = context.get("labels", {}).get(original_attachment,
                               context.get("references", {}).get(original_attachment, original_attachment))
                    if attached != original.get("proof_of"):
                        raise ValueError(f"{retired}: original proof attachment disagrees with source evidence")
                terminal[retired] = target
            # A retired proof must prove the very claim of its canonical proof,
            # after resolving reviewed claim redirects (including chains).
            for retired, target in terminal.items():
                original = records[retired]["original"]
                if original["kind"] == "prf":
                    claim = resolve(identity(original.get("proof_of")))
                    actual = self.proofs.get(target)
                    if actual is None or claim != resolve(actual):
                        raise ValueError(f"{retired}: proof redirect changes the attached claim")
                elif original.get("proof_of") is not None:
                    raise ValueError(f"{retired}: non-proof redirect has a proof attachment")
            self.unit_redirects = records
            self.redirect_evidence = evidence
            for retired, target in terminal.items():
                self.aliases[retired] = target
                original = records[retired]["original"]
                self.alias_declarations[retired] = dict(
                    original, id=retired, canonical_id=target, origin="retired",
                    provenance={"id": retired, "file": original["evidence_file"],
                                "line": original["line"], "page": False,
                                "original_source": original["file"],
                                "redirect": records[retired]}, retired=True)
                self.nodes[target].setdefault("redirects", []).append(retired)
            for node in self.nodes.values():
                if "redirects" in node:
                    node["redirects"].sort()
        except (ValueError, OSError, AttributeError, TypeError, KeyError) as exc:
            self.errors.append(f"workflow/unit-redirects.json: {exc}")

    def resolve_id(self, node):
        """Resolve a declared qualified alias, preserving normal unknown-ID checks."""
        return self.aliases.get(node, node)

    resolve_alias = resolve_id

    def locate(self, node):
        """Keep an alias's own declaration position alongside its canonical unit."""
        canonical = self.resolve_id(node)
        record = self.alias_declarations.get(node, self.nodes.get(canonical))
        if record is None:
            raise ValueError(f"unknown node {node}")
        result = {k: record[k] for k in ("id", "file", "line", "column", "page", "end_page", "document_id", "source_document", "printed_locator", "source_registry", "provenance") if k in record}
        if node != canonical:
            result.update(requested_id=node, canonical_id=canonical,
                          canonical_location={k: self.nodes[canonical][k] for k in ("file", "line", "column")})
        if node in self.unit_redirects:
            result["redirect"] = self.unit_redirects[node]
            result["retired"] = True
        return result

    def add_unresolved_nodes(self):
        """Expose documented missing versions without manufacturing statements."""
        path = self.root / "workflow/unresolved.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            if data.get("schema_version") != 1 or not isinstance(data.get("records"), dict):
                raise ValueError("expected schema version 1 with a records map")
            for label, record in data["records"].items():
                try:
                    if not ID.fullmatch(label) or not label.startswith("gap:"):
                        raise ValueError("gap IDs must begin with gap:")
                    if label in self.nodes or label in self.source_labels or label in self.aliases:
                        raise ValueError("gap collides with an existing mathematical unit")
                    if not isinstance(record, dict):
                        raise ValueError("expected a gap record")
                    for field in ("original_label", "source_document", "source_sha256", "reason"):
                        if not isinstance(record.get(field), str) or not record[field].strip():
                            raise ValueError(f"missing {field}")
                    if not re.fullmatch(r"[0-9a-f]{64}", record["source_sha256"]):
                        raise ValueError("source_sha256 must identify the captured source bytes")
                    if record.get("status") != "unresolved" or record.get("mathematical_statement", False) is not None:
                        raise ValueError("a gap must remain unresolved with no mathematical statement")
                    if not isinstance(record.get("candidates"), list):
                        raise ValueError("candidates must be an explicit list (possibly empty)")
                    self.nodes[label] = dict(
                        id=label, source_label=record["original_label"], kind="gap",
                        scope="notes", origin="unresolved", environment="unresolved",
                        file="workflow/unresolved.json", line=1, column=1,
                        description=record["reason"], metadata={}, gap=record.copy())
                    self.direct_edges[label] = set()
                    self.warnings.append(f"{label}: unresolved dependency: {record['reason']}")
                except (ValueError, TypeError) as exc:
                    self.errors.append(f"workflow/unresolved.json: {label}: {exc}")
        except (ValueError, OSError, AttributeError, TypeError) as exc:
            self.errors.append(f"workflow/unresolved.json: {exc}")

    def add_source_document_locators(self):
        """Load explicit background PDF identities independently of DOI papers."""
        from semantex_sources import registered_pdf_locators
        try:
            occupied = set(self.nodes) | set(self.source_labels) | set(self._declarations)
            records = registered_pdf_locators(self.root, self.pdf_page_count, occupied)
            self.source_labels.update({key: [record] for key, record in records.items()})
        except (ValueError, OSError, TypeError, subprocess.TimeoutExpired) as exc:
            self.errors.append(f"workflow/source-documents.json: {exc}")

    def add_retained_nodes(self):
        occurrences = set()
        for label, matches in self.source_labels.items():
            if len(matches) != 1:
                continue
            original = matches[0]
            self.nodes[label] = {k: v for k, v in original.items() if k not in {"latex", "proof", "mentions"}}
            self.nodes[label].update(scope="references", origin="retained", description=original.get("description", ""), metadata=original.get("metadata", {}),
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
            if key not in self._paper_pdfs:
                base = self.root / "references" / key
                self._paper_pdfs[key] = [p.relative_to(base).as_posix() for p in base.rglob("*.pdf")
                                         if citation_source_is_retained(self.root, key, p.relative_to(self.root).as_posix())]
            pdfs = self._paper_pdfs[key]
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
        if locator == "line":
            if file not in self._citation_lines:
                self._citation_lines[file] = len(source.read_bytes().splitlines())
            if number > self._citation_lines[file]:
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
            store = self._scan_store
            key = store.key(self.root / file) if store else None
            pages = store.get("pdf", file, key) if store else None
            if type(pages) is int:
                self.pdf_pages[file] = pages
                return pages
            executable = shutil.which("pdfinfo")
            if not executable:
                raise ValueError("pdfinfo (Poppler) is required to validate physical PDF locators")
            result = subprocess.run([executable, str(self.root / file)], capture_output=True, text=True,
                                    env=dict(os.environ, LC_ALL="C"), timeout=30)
            pages = re.search(r"(?m)^Pages:\s+([0-9]+)$", result.stdout)
            if result.returncode or not pages:
                raise ValueError(f"could not read physical page count of {file}")
            self.pdf_pages[file] = int(pages[1])
            if store:
                store.put("pdf", file, key, self.pdf_pages[file])
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
                if node not in self.nodes and node not in self.unit_redirects:
                    self.errors.append(f"review for unknown node {node}")
                if node in self.unit_redirects and isinstance(record, dict):
                    if record.get("status") != self.unit_redirects[node]["original"]["review_status"]:
                        self.errors.append(f"{node}: historical review status disagrees with redirect provenance")
                if not isinstance(record, dict) or record.get("status") not in STATES:
                    self.errors.append(f"invalid review state for {node}")
        except (ValueError, AttributeError) as exc:
            self.errors.append(f"invalid reviews.json: {exc}")

    def scan_file(self, path, markdown=False):
        scan = self.scan_markdown if markdown else self.scan
        relative = path.relative_to(self.root).as_posix()
        store = self._scan_store
        if store is None or relative in self.overlays or not path.is_file():
            scan(path)
            return
        key = store.key(path)

        def bindings(context):
            return digest([self.label_namespaces.get(relative), self.reference_bindings.get(relative),
                           self.label_aliases.get(relative), self.document_contexts.get(context)])

        fragment = store.get("authored", relative, key)
        if fragment is not None and self.reuse_scan(path, relative, fragment, bindings):
            return
        errors, occurrence_start, citation_start = len(self.errors), len(self.occurrences), len(self.citations)
        context = scan(path)
        if len(self.errors) != errors:
            return
        declared = self.declarations_by_file.get(relative, {})
        declarations = {}
        for label in declared.values():
            record = dict(self._declarations[label])
            if record["frame"] is not None:
                record["frame"] = {key: record["frame"][key] for key in ("start", "owner", "environment")}
            declarations[label] = record
        occurrences = self.occurrences[occurrence_start:]
        citations = self.citations[citation_start:]
        locators = {target: self.source_labels[target] for cite in citations for target in cite["targets"]
                    if target.startswith("loc:")}
        store.put("authored", relative, key, {
            "context": context, "bindings": bindings(context), "retained": store.retained if citations else None,
            "declared": declared, "declarations": declarations,
            "nodes": {label: self.nodes[label] for label in declared.values() if label in self.nodes},
            "proofs": {label: self.proofs[label] for label in declared.values() if label in self.proofs},
            "aliases": self.native_aliases_by_file.get(relative, {}),
            "pending_aliases": {label: self._pending_aliases[label] for label in declared.values()
                                if label in self._pending_aliases},
            "descriptions": self.description_spans.get(relative, []),
            "occurrences": occurrences, "citations": citations, "locators": locators,
            "source_ids": sorted({ref["target"] for ref in occurrences
                                  if ref["relation"] != "citation" and not ID.fullmatch(ref["target"])}),
        })

    def reuse_scan(self, path, relative, fragment, bindings):
        context = fragment["context"]
        declarations = fragment["declarations"]
        if (fragment["bindings"] != bindings(context) or context in self.context_files
                or (fragment["citations"] and fragment["retained"] != self._scan_store.retained)
                or any(label in self._declarations or label in self.source_labels for label in declarations)
                or any(label not in self.source_labels for label in fragment["source_ids"])):
            return False
        self.files[relative] = path.read_bytes()
        if relative.endswith(".tex"):
            self.declarations_by_file[relative] = fragment["declared"]
            self.native_aliases_by_file[relative] = fragment["aliases"]
        if context is not None:
            self.context_files[context] = relative
        self._declarations.update(declarations)
        self._pending_aliases.update(fragment["pending_aliases"])
        self.nodes.update(fragment["nodes"])
        self.direct_edges.update((label, set()) for label in fragment["nodes"])
        self.proofs.update(fragment["proofs"])
        if fragment["descriptions"]:
            self.description_spans[relative] = fragment["descriptions"]
        self.occurrences.extend(fragment["occurrences"])
        self.citations.extend(fragment["citations"])
        self.source_labels.update(fragment["locators"])
        return True

    def refresh_markdown(self, changed):
        """Replace the navigation occurrences of edited Markdown in source order."""
        updated = []
        for file in sorted(changed, key=Path):
            self._decoded_files.pop(file, None)
            self.scan_markdown(self.root / file, updated)
        for occurrence in updated:
            self.bind_occurrence(occurrence, authored=True)

        old = self.occurrences[self.markdown_start:self.markdown_end]
        kept = [occurrence for occurrence in old if occurrence["file"] not in changed]
        # The full scan orders pathlib paths first, then occurrences within each file.
        merged = sorted(kept + updated, key=lambda occurrence: Path(occurrence["file"]).parts)
        self.occurrences[self.markdown_start:self.markdown_end] = merged
        self.markdown_end = self.markdown_start + len(merged)

    def scan_markdown(self, path: Path, occurrences=None) -> None:
        """Index literal semantic links; Markdown cannot supply mathematical owners."""
        relative = path.relative_to(self.root).as_posix()
        if not path.resolve().is_relative_to(self.root.resolve()):
            self.errors.append(f"source path escapes repository: {relative}")
            return
        data = self.overlays[relative] if relative in self.overlays else path.read_bytes()
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.files[relative] = data
        raw = data.decode("utf-8")
        if not MARKDOWN_REFERENCE.search(raw):
            return
        chars = list(raw)
        def hide(start, end):
            for i in range(start, end):
                if chars[i] != "\n":
                    chars[i] = " "
        for comment in re.finditer(r"<!--.*?(?:-->|\Z)", raw, re.S):
            hide(comment.start(), comment.end())
        text = "".join(chars)
        fence, offset = None, 0
        for line in text.splitlines(keepends=True):
            marker = re.match(r" {0,3}(`{3,}|~{3,})(.*)", line)
            if fence:
                hide(offset, offset + len(line))
                if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                    fence = None
            elif marker:
                fence = marker[1]
                hide(offset, offset + len(line))
            elif line.startswith(("    ", "\t")):
                hide(offset, offset + len(line))
            offset += len(line)
        text = "".join(chars)
        # Inline code is the prescribed notation for links. Other code is literal.
        command = r"\\(?:mention|hiddenmention|use|hiddenuse)\s*\{[^{}]*\}"
        for code in re.finditer(r"(?<!`)(`+)(?!`)(.*?)(?<!`)\1(?!`)", text, re.S):
            if not re.fullmatch(r"\s*(?:" + command + r"\s*)+", code[2]):
                hide(code.start(), code.end())
        text = "".join(chars)
        if occurrences is None:
            occurrences = self.occurrences
        bindings = self.reference_bindings.get(relative, {})
        for match in MARKDOWN_REFERENCE.finditer(text):
            offset = match.start()
            location = dict(file=relative, line=raw.count("\n", 0, offset) + 1,
                            column=offset - raw.rfind("\n", 0, offset))
            try:
                original, _ = argument(text, match.end())
                target = bindings.get(original, original)
                if not ID.fullmatch(target) and target not in self.source_labels:
                    raise ValueError("reference requires one literal label")
                dependency, visible = REFERENCE[match[1]]
                occurrences.append(dict(location, target=target, original_target=original, owner=None,
                    dependency=dependency, visible=visible, command=match[1],
                    offset=offset, relation="reference", format="markdown"))
            except ValueError as exc:
                self.errors.append(f"{relative}:{location['line']}:{location['column']}: {exc}")

    def scan(self, path: Path) -> str | None:
        relative = path.relative_to(self.root).as_posix()
        namespace = self.label_namespaces.get(relative, {})
        bindings = self.reference_bindings.get(relative, {})
        native_aliases = self.label_aliases.get(relative, {})
        context_id = None
        def qualified(label):
            return namespace.get(label, label)
        def reference_target(label):
            return namespace.get(label, bindings.get(label, label))
        def label_kind(label):
            parts = label.split(":")
            if parts[0] in NAVIGATION:
                return parts[0]
            # The supplied historical dossier uses current-eq: for equation
            # anchors. Keep its native spelling; it is not a second claim.
            if parts[0] == "current-eq":
                return "eq"
            for part in parts[1:]:
                match = re.match(r"(eq|sec|fig|tab)(?:-|$)", part)
                if match:
                    return match[1]
            return parts[0]
        if not path.resolve().is_relative_to(self.root.resolve()):
            self.errors.append(f"source path escapes repository: {relative}")
            return
        data = self.overlays[relative] if relative in self.overlays else path.read_bytes()
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.files[relative] = data
        raw = data.decode("utf-8")
        literal = literal_mask(raw)
        text = mask_comments(literal)
        newlines = [match.start() for match in NEWLINE.finditer(raw)]
        contexts = re.findall(r"\\SemanTeXContext\s*\{([^{}]+)\}", text)
        if len(contexts) > 1:
            self.errors.append(f"{relative}: exactly one document context declaration is allowed")
        if contexts:
            context_id = contexts[0]
            if context_id not in self.document_contexts:
                self.errors.append(f"{relative}: unknown document context {context_id}")
            else:
                context = self.document_contexts[context_id]
                namespace = context.get("labels", {})
                bindings = context.get("references", {})
                native_aliases = context.get("aliases", {})
                if context_id in self.context_files and self.context_files[context_id] != relative:
                    self.errors.append(f"{relative}: document context {context_id} also belongs to {self.context_files[context_id]}")
                self.context_files[context_id] = relative
        self.declarations_by_file[relative] = {}
        self.native_aliases_by_file[relative] = dict(native_aliases)
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
            return {"file": relative, "line": bisect_right(newlines, offset - 1) + 1,
                    "column": offset - raw.rfind("\n", 0, offset)}

        def context():
            for frame in reversed(stack):
                if frame["environment"] in SEMANTIC:
                    return frame
            if item:
                return item
            return heading

        original_labels = {}
        for original, identity in namespace.items():
            original_labels.setdefault(identity, original)

        def register_label(label, description, frame, offset, end):
            native_label = label
            source_label = original_labels.get(label, label)
            label = qualified(label)
            if not ID.fullmatch(label):
                raise ValueError(f"invalid literal node ID {label!r}")
            if label in self.nodes or label in self.source_labels or label in self._declarations:
                raise ValueError(f"duplicate node ID {label}")
            kind = label_kind(source_label)
            if kind not in NAVIGATION and not description.strip() and native_label not in native_aliases:
                raise ValueError(f"{label}: add a description to the mathematical label")
            declaration = dict(location(offset), id=label, source_label=native_label,
                               context_id=context_id, kind=kind, frame=frame, offset=offset,
                               end_offset=end, description=" ".join(description.split()),
                               environment=frame["environment"] if frame else "anchor")
            self.declarations_by_file[relative][native_label] = label
            self._declarations[label] = declaration
            if native_label in native_aliases:
                self._pending_aliases[label] = (relative, native_label)
                return
            if frame and frame["environment"] in SEMANTIC and kind not in NAVIGATION:
                if frame["owner"]:
                    raise ValueError(f"multiple principal labels in {frame['environment']}")
                frame["owner"] = label
            elif frame and frame["environment"] in set(HEADINGS) | {"item"} and not frame["owner"]:
                frame["owner"] = label
            node = dict(location(offset), id=label, source_label=source_label, context_id=context_id, kind=kind, metadata={}, offset=offset, origin="authored",
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
                    raise ValueError(f"retired authored command \\{command}; see workflow/SEMANTEX.md")
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
                elif command in HEADINGS:
                    _, star = optional_argument(text, star)
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
                        proof, claim = qualified(options.get("label", "")), reference_target(options.get("proves", ""))
                        if not proof.startswith("prf:") or not ID.fullmatch(claim):
                            raise ValueError("proof requires label=prf:ID and proves=RESULT")
                        register_label(options.get("label", ""), options.get("description", ""), frame, offset, pos)
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
                    original_target = first
                    first = reference_target(first)
                    dependency, visible = REFERENCE[command]
                    if not ID.fullmatch(first) and first not in self.source_labels:
                        raise ValueError("reference requires one literal label")
                    references.append(dict(loc, target=first, original_target=original_target, dependency=dependency,
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
            node.update(start=start, end=end, start_line=bisect_right(newlines, start - 1) + 1,
                        end_line=bisect_right(newlines, max(start, end - 1) - 1) + 1)
        for ref in references:
            frame = ref.pop("frame")
            ref["owner"] = frame.get("owner") if frame else None
            self.occurrences.append(ref)
        for citation in citations:
            frame = citation.pop('frame')
            citation['owner'] = frame.get('owner') if frame else None
            self.citations.append(citation)
        # Metadata is a contiguous comment block immediately preceding a unit or its label.
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
            if key == "proof":
                value = reference_target(value)
            old = node["metadata"].get(key)
            if key in {"related", "supersedes", "tags"}:
                values = [v.strip() for v in value.split(",") if v.strip()]
                if key in {"related", "supersedes"}:
                    values = [reference_target(v) for v in values]
                node["metadata"][key] = (old or []) + values
            elif old and key != "title":
                node["metadata"][key] = old + "\n" + value
            else:
                node["metadata"][key] = value
            node["start"] = min(node["start"], meta.start())
            node["start_line"] = bisect_right(newlines, node["start"] - 1) + 1
            if key in {"related", "supersedes"}:
                for label in node["metadata"][key] if not old else values:
                    if not ID.fullmatch(label) and label not in self.source_labels:
                        self.errors.append(f"{relative}:{location(meta.start())['line']}: invalid metadata label {label}")
                    else:
                        self.occurrences.append(dict(location(meta.start()), owner=node["id"], target=label,
                                                     dependency=False, visible=False, command="metadata",
                                                     relation=key, offset=meta.start()))
        return context_id

    def adjacency(self, reverse=False, support=False, mentions=False, within=None):
        if within is not None:
            within = {self.resolve_id(node) for node in within}
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
        node = self.resolve_id(node)
        if node not in self.nodes:
            raise ValueError(f"unknown node {node}")
        # Forward walks need only the visited adjacency lists.  Keep the general
        # builder for reversed, mention-inclusive, and scope-restricted walks.
        direct = not reverse and not mentions and within is None
        edges = self.edges if direct else self.adjacency(reverse, support, mentions, within)
        if node not in edges:
            raise ValueError(f"{node} is outside the requested scope")
        distances = {node: 0}
        queue = deque([node])
        while queue:
            current = queue.popleft()
            if depth is not None and distances[current] >= depth:
                continue
            targets = edges[current]
            if direct and support:
                proof = self.selected_proofs.get(current)
                if proof in edges:
                    targets = targets | {proof}
            for target in sorted(targets):
                if target not in distances:
                    distances[target] = distances[current] + 1
                    queue.append(target)
        return distances

    def closure(self, node, reverse=False, support=True):
        return set(self.distances(node, reverse=reverse, support=support))

    def focused_paths(self, root, distances, focused, reverse=False, mentions=False):
        root = self.resolve_id(root)
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
        if subset is not None:
            subset = {self.resolve_id(node) for node in subset}
        edges = self.edges
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
                    targets = edges[node]
                    if support and node in self.selected_proofs:
                        proof = self.selected_proofs[node]
                        if proof in edges:
                            targets = targets | {proof}
                    stack.extend((dep, False) for dep in sorted(targets, reverse=True))
        return output

    def source(self, node):
        node = self.resolve_id(node)
        record = self.nodes[node]
        if record["origin"] == "unresolved":
            return ""
        if record["origin"] == "retained":
            original = self.source_labels[node][0]
            if "latex" in original:
                return original["latex"]
            if record.get("page"):
                return ""
            from semantex_sources import source_text
            text, _ = source_text(self.root / record["file"])
            return text.splitlines()[record["line"] - 1]
        return self.decoded_file(record["file"])[record["start"]:record["end"]]

    def blocks(self, node, proof=None):
        node = self.resolve_id(node)
        if node not in self.nodes:
            raise ValueError(f"unknown node {node}")
        if proof and proof != "all":
            proof = self.resolve_id(proof)
        record = self.nodes[node]
        if record["origin"] == "unresolved":
            return []
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
        attached = self.attachments.get(node, ())
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
                           "end_line": record["end_line"], "start_column": record["start"] - self.decoded_file(record["file"]).rfind("\n", 0, record["start"]),
                           "latex": self.source(key)})
        return result

    def reviewed_source(self, node):
        """Hash the argument independently of its retrieval descriptions."""
        node = self.resolve_id(node)
        record = self.nodes[node]
        if record["origin"] == "unresolved":
            return json.dumps(record["gap"], sort_keys=True)
        text = self.source(node)
        if record["origin"] == "retained":
            return text
        for start, end in reversed(self.description_spans.get(record["file"], [])):
            if record["start"] <= start < end <= record["end"]:
                left, right = start - record["start"], end - record["start"]
                text = text[:left] + text[right:]
        return text

    def editor_blocks(self, label, limit=16000):
        """Send preview positions so the editor only reads the hovered source."""
        record = self.nodes[label]
        if record["origin"] == "unresolved" or record.get("page"):
            return []
        if record["origin"] == "retained":
            original = self.source_labels[label][0]
            if label not in self.source_spans:
                return [dict(file=record["file"], start_line=record["line"], end_line=record["line"])]
            blocks = zip((original, original.get("proof")), self.source_spans[label])
        else:
            proof = self.selected_proofs.get(label)
            records = (record, self.nodes[proof]) if proof else (record,)
            blocks = ((item, (item["start"], item["end"])) for item in records)
        return [dict(file=item["file"], start_line=item.get("start_line", item.get("line")),
                     end_line=item.get("end_line", item.get("line")), start=start,
                     end=min(end, start + limit), truncated=end - start > limit)
                for item, (start, end) in blocks]

    def source_support(self, node):
        node = self.resolve_id(node)
        files = {self.source_labels[target][0]["file"]
                for citation in self.citations_by_owner.get(node, [])
                for target in citation["targets"]}
        if self.nodes[node]["origin"] == "retained":
            files.add(self.nodes[node]["file"])
            if self.nodes[node].get("source_registry"):
                files.add(self.nodes[node]["source_registry"])
        return files

    def hash_file(self, path):
        if path not in self.file_hashes:
            self.file_hashes[path] = sha(safe_path(self.root, path).read_bytes())
        return self.file_hashes[path]

    def reset_review_cache(self):
        self.file_hashes = {}
        self._fingerprints = {}
        self._reviewed_hashes = {}
        self._shared_review_paths = None

    def shared_review_paths(self):
        paths = set(path.relative_to(self.root).as_posix() for path in (self.root / "preamble").rglob("*")
                     if path.is_file() and path.suffix in {".sty", ".tex"})
        paths.update(p for p in ("AGENTS.md", "writing-style.md", "workflow/SEMANTEX.md", "references/README.md", "references/lock.json", "workflow/label-namespaces.json", "workflow/reference-bindings.json", "workflow/unresolved.json", "workflow/document-contexts.json", "workflow/label-aliases.json", "workflow/unit-redirects.json") if (self.root / p).is_file())
        paths.update(path.relative_to(self.root).as_posix()
                     for path in (self.root / ".agents" / "skills").rglob("*")
                     if path.is_file() and path.suffix in {".md", ".yaml", ".yml"})
        paths.update(self.redirect_evidence)
        return paths

    def reviewed_hash(self, node):
        if node not in self._reviewed_hashes:
            self._reviewed_hashes[node] = sha(self.reviewed_source(node).encode())
        return self._reviewed_hashes[node]

    def fingerprint(self, node):
        node = self.resolve_id(node)
        if node in self._fingerprints:
            return self._fingerprints[node]
        closure = self.closure(node)
        paths = set().union(*(self.source_support(key) | self.source_audits.get(key, set()) for key in closure))
        if self._shared_review_paths is None:
            self._shared_review_paths = self.shared_review_paths()
        paths.update(self._shared_review_paths)
        payload = {"schema": 3, "target": node,
                   "units": [(key, self.nodes[key]["file"], self.reviewed_hash(key),
                              sorted(self.edges[key]), self.selected_proofs.get(key)) for key in sorted(closure)],
                   "evidence": [(p, self.hash_file(p)) for p in sorted(paths)]}
        value = sha(json.dumps(payload, sort_keys=True).encode())
        self._fingerprints[node] = value
        return value

    def status(self, node, cache=None):
        if node in self.unit_redirects:
            return "redirected"
        node = self.resolve_id(node)
        cache = {} if cache is None else cache
        if self.nodes[node]["origin"] == "unresolved":
            return "unresolved"
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
        if self.nodes[node]["origin"] == "unresolved":
            return "unresolved"
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
        deps = self.edges[node]
        proof = self.selected_proofs.get(node)
        if proof in self.edges:
            deps = deps | {proof}
        if any(cache[dep] != "accepted" for dep in deps):
            valid = False
        cache[node] = "accepted" if valid else "stale"
        return cache[node]

    def occurrence(self, occurrence):
        result = dict(occurrence)
        if occurrence["target"] in self.nodes:
            target = self.nodes[occurrence["target"]]
            result["target_location"] = {k: target[k] for k in ("file", "line", "page", "end_page", "document_id") if k in target}
            requested = occurrence.get("requested_target", occurrence["target"])
            if requested in self.alias_declarations:
                result["alias_location"] = {k: self.alias_declarations[requested][k] for k in ("file", "line", "column")}
                if requested in self.unit_redirects:
                    result["redirect"] = self.unit_redirects[requested]
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
        target = self.resolve_id(target)
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
            if occurrence["target"] not in self.nodes:
                errors.append(f"{occurrence['file']}:{occurrence['line']}: unresolved reference {occurrence['target']}")
                continue
            destination = self.nodes[occurrence["target"]]
            if destination["file"] not in assembled:
                errors.append(f"{occurrence['file']}:{occurrence['line']}: visible reference "
                              f"{occurrence['target']} is outside the assembled manuscript")
        return errors

    def describe(self, node, cache=None):
        requested = node
        node = self.resolve_id(node)
        data = {k: v for k, v in self.nodes[node].items() if k not in {"offset", "start", "end"}}
        data.update(dependencies=sorted(self.edges[node]), direct_dependencies=sorted(self.direct_edges[node]),
                    dependents=sorted(self.dependents[node]),
                    proofs=list(self.attachments.get(node, ())),
                    selected_proof=self.selected_proofs.get(node), proof_of=self.proofs.get(node),
                    status=self.status(node, cache), fingerprint=self.fingerprint(node),
                    source_audits=sorted(self.source_audits.get(node, ())))
        owners = [node]
        if node in self.selected_proofs:
            owners.append(self.selected_proofs[node])
        data["citations"] = [dict(c) for owner in owners for c in self.citations_by_owner.get(owner, [])]
        if requested != node:
            data.update(requested_id=requested, canonical_id=node,
                        alias_declaration=dict(self.alias_declarations[requested]))
        if requested in self.unit_redirects:
            data.update(redirect=self.unit_redirects[requested],
                        historical_status=self.unit_redirects[requested]["original"]["historical_status"],
                        historical_review_status=self.unit_redirects[requested]["original"]["review_status"],
                        canonical_status=data["status"], status="redirected")
        return data

    def export(self, focused=None):
        cache = {}
        focused = self.nodes.keys() if focused is None else {self.resolve_id(node) for node in focused}
        return {"schema_version": 3, "edge_direction": "owner-uses-prerequisite",
                "nodes": [self.describe(node, cache) for node in sorted(focused)],
                "references": [self.occurrence(o) for o in self.occurrences
                               if o["owner"] in focused or o["target"] in focused],
                "links": [link for link in visible_links(self)
                          if link["from"] in focused or link["to"] in focused],
                "proof_attachments": self.proofs,
                "aliases": {a: n for a, n in self.aliases.items() if n in focused},
                "alias_declarations": {a: d for a, d in self.alias_declarations.items() if self.aliases[a] in focused},
                "unit_redirects": {a: r for a, r in self.unit_redirects.items() if self.aliases[a] in focused},
                "name": "SemanTeX",
                "citations": [dict(c, targets_resolved=[{k: v for k, v in self.source_labels[t][0].items() if k not in {'latex', 'proof'}} for t in c['targets'] if len(self.source_labels.get(t, [])) == 1]) for c in self.citations],
                "warnings": self.warnings}

    def references(self, node, reverse=False):
        node = self.resolve_id(node)
        if node not in self.nodes and not (reverse and node in self.source_labels):
            raise ValueError(f"unknown node {node}")
        owners = {node}
        if node in self.selected_proofs:
            owners.add(self.selected_proofs[node])
        return [self.occurrence(o) for o in self.occurrences if
                (o["target"] == node if reverse else o["owner"] in owners)]

    def why(self, start, target, within=None):
        start, target = self.resolve_id(start), self.resolve_id(target)
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


@cache
def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--overlays", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--rebuild", action="store_true", help="refresh the graph cache from source")
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
    sub.choices["backrefs"].add_argument("--markdown", action="store_true",
        help="list Markdown files mentioning this label; JSON includes each occurrence")
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
    for action in ("setup", "build", "status", "profiles", "stop"):
        child = actions.add_parser(action)
        if action not in {"profiles", "stop"}:
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
    editor = sub.add_parser("editor-index", help=argparse.SUPPRESS)
    editor.add_argument("--source-ranges", action="store_true")
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
    return parser


def main(argv=None, *, worker=None):
    args = argument_parser().parse_args(argv)
    if args.command == "rag":
        if args.action == "stop":
            print("No SemanTeX worker is running.")
            return 0
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
    root = args.root.resolve()
    if args.command == "reference-view":
        from reference_views import build_view
        build_view(root, args.key, args.main)
        return 0
    graph = worker.graph(Graph, root) if worker else load_graph(Graph, root, overlays, rebuild=args.rebuild)
    if args.command in {"paper-graph", "source-labels"}:
        from reference_views import paper_graph, render_graph
        data = paper_graph(graph, args.key)
        dump(data['nodes']) if args.command == "source-labels" else print(render_graph(data, args.format))
        return 0
    if args.command == "editor-index":
        if graph.errors:
            dump({"errors": graph.errors, "nodes": [], "references": []})
            return 0
        # The editor needs navigation and bounded hover previews. A full export
        # also computes every review fingerprint and includes unused provenance.
        statuses = {}
        nodes = []
        for label, record in graph.nodes.items():
            node = {key: record[key] for key in ("id", "kind", "file", "line", "column",
                                                  "description", "page", "virtual") if key in record}
            node.update(status=graph.status(label, statuses), dependencies=sorted(graph.edges[label]))
            node["blocks"] = graph.editor_blocks(label) if args.source_ranges else graph.blocks(label)
            nodes.append(node)
        ids = {node["id"] for node in nodes}
        references = [{key: record[key] for key in ("relation", "target", "file", "line", "column",
                                                      "offset", "end_offset") if key in record}
                      for record in graph.occurrences
                      if record["owner"] in ids or record["target"] in ids]
        print(json.dumps({"errors": [], "nodes": nodes, "references": references},
                         separators=(",", ":"), ensure_ascii=False))
        return 0
    if graph.errors:
        raise ValueError("\n".join(graph.errors))
    command = args.command
    requested_ids = {}
    for field in ("node", "target", "other"):
        value = getattr(args, field, None)
        if value:
            requested_ids[field] = value
            setattr(args, field, graph.resolve_id(value))
    if hasattr(args, "seeds"):
        args.seeds = [graph.resolve_id(seed) for seed in args.seeds]
    if hasattr(args, "proof") and args.proof and args.proof != "all":
        args.proof = graph.resolve_id(args.proof)
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
    markdown_backrefs = command == "backrefs" and args.markdown
    focused = ({n for n, record in graph.nodes.items()
                if record["scope"] in scopes and (not paper or record.get("bib_key") == paper)}
               if (scope or paper) and not markdown_backrefs else graph.nodes.keys())
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
                  if node not in graph.unit_redirects and record["status"] == "accepted" and graph.status(node) != "accepted"]
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
        record = graph.nodes[args.node]
        blocks = graph.blocks(args.node, args.proof)
        if args.show == "description":
            if args.json:
                dump(dict(id=args.node, requested_id=requested_ids.get("node", args.node), description=record["description"]))
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
            dump({"node": graph.describe(requested_ids.get("node", args.node)), "blocks": blocks})
        elif args.latex:
            sys.stdout.write("\n".join(b["latex"] for b in blocks))
            if blocks and not blocks[-1]["latex"].endswith("\n"):
                print()
        else:
            record = graph.describe(requested_ids.get("node", args.node))
            requested = requested_ids.get("node", args.node)
            identity = args.node if requested == args.node else f"{requested} -> {args.node}"
            print(f"{identity} [{record['status']}] {record['file']}:{record['line']}")
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
        ranked = sorted(((n, d) for n, d in distances.items() if n != args.node and n in selected),
                        key=lambda p: (p[1], p[0]))
        if args.json:
            statuses = {}
            nodes = [dict(graph.describe(n, statuses), distance=d, in_scope=n in focused) for n, d in ranked]
            requested = requested_ids.get("node", args.node)
            if requested != args.node:
                nodes = [dict(node, requested_root=requested, canonical_root=args.node) for node in nodes]
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
            statuses = {}
            for label, distance in ranked:
                node = graph.nodes[label]
                suffix = "" if label in focused else "\t[outside scope]"
                print(f"{distance}\t{label}\t{graph.status(label, statuses)}\t{node['file']}:{node['line']}{suffix}")
    elif command in {"refs", "backrefs"}:
        reverse = command == "backrefs"
        refs = graph.references(args.node, reverse)
        if markdown_backrefs:
            refs = [ref for ref in refs if ref.get("format") == "markdown"
                    and ref["file"].split("/", 1)[0] in scopes
                    and (not paper or ref["file"].startswith(f"references/{paper}/"))]
        elif scope or paper:
            endpoint = "owner" if reverse else "target"
            refs = [ref for ref in refs if ref[endpoint] in focused]
        if args.json:
            dump(refs)
        elif markdown_backrefs:
            files = {}
            for ref in refs:
                files.setdefault(ref["file"], ref["line"])
            for file, line in files.items():
                print(f"{file}:{line}")
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
        unresolved = [dict(graph.describe(n), reasons=[graph.nodes[n]["gap"]["reason"] if graph.nodes[n]["origin"] == "unresolved"
                                                       else "current review missing, disputed, or stale"])
                      for n in sorted(nodes) if n in focused and graph.status(n) != "accepted"]
        if args.json:
            dump({"units": unresolved})
        else:
            for node in unresolved:
                print(f"{node['id']}\t{node['status']}\t{node['file']}:{node['line']}")
    elif command == "fingerprint":
        dump({"id": args.node, "requested_id": requested_ids.get("node", args.node), "fingerprint": graph.fingerprint(args.node)}) if args.json else print(graph.fingerprint(args.node))
    elif command == 'locate':
        from semantex_sources import source_url
        record = graph.locate(requested_ids.get("node", args.node))
        if args.node not in focused:
            raise ValueError(f"{args.node} is outside the requested scope")
        result = dict(record)
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
        index = (worker.index(args.profile, model["dimensions"]) if worker else
                 VectorIndex(graph.root, args.profile, model["dimensions"]))
        if args.action == "build":
            backend = worker.embedder(args.profile) if worker else EmbeddingServer(graph.root, args.profile)
            result = index.build(graph, backend, rebuild=args.rebuild)
        else:
            result = index.status(graph, focused, scopes, paper)
            if worker:
                result["resident_model"] = worker.model_status()
        dump(dict(result, profile=args.profile))
    elif command in {"search", "neighbors"}:
        candidates = {n for n in focused if (not args.kind or graph.nodes[n]["kind"] == args.kind)
                      and (not args.status or graph.status(n) == args.status)}
        dimensions = PROFILES[args.profile]["dimensions"]
        index = worker.index(args.profile, dimensions) if worker else VectorIndex(graph.root, args.profile, dimensions)
        lexical_cache = worker.lexical_text if worker else None
        if command == "search" and args.mode == "lexical":
            ranking = lexical_rank(graph, args.query, candidates, lexical_cache)
        else:
            query = args.query if command == "search" else None
            if query is not None and not query.strip():
                raise ValueError("semantic and hybrid search require a query")
            def embedder():
                return worker.embedder(args.profile) if worker else EmbeddingServer(graph.root, args.profile)

            backend = embedder() if query is not None else None
            options = {"query": query, "label": getattr(args, "node", None), "backend": backend,
                       "all_versions": getattr(args, "all_versions", False) if query is None else False}
            try:
                ranking = index.rank(graph, candidates, **options)
            except StaleIndex:
                if backend is None:
                    backend = embedder()
                index.build(graph, backend, require_current_model=True)
                ranking = index.rank(graph, candidates, **options)
            if query is not None and args.mode == "hybrid":
                ranking = hybrid_rank(lexical_rank(graph, args.query, candidates, lexical_cache), ranking)
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
