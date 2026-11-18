#!/usr/bin/env python3
"""Generate scoped SemanTeX runtime data, never edit authored mathematics.

The context installation plan is a reviewable, hash-guarded proposal. Its UUIDs
must be persisted once and carried with documents when they move.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
import unicodedata


ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9:._/-]*\Z")
CONTEXT = re.compile(r"\\SemanTeXContext\s*\{([^{}]+)\}")
KINDS = {"thm": "Theorem", "lem": "Lemma", "prop": "Proposition",
         "cor": "Corollary", "def": "Definition", "prf": "Proof",
         "src": "Source application", "cex": "Counterexample", "conj": "Conjecture",
         "ex": "Example", "rem": "Remark", "sec": "Section", "eq": "Equation",
         "fig": "Figure", "tab": "Table"}


# The graph records the actual semantic environment independently of immutable
# historical label prefixes. Shared amsthm counters do not identify that kind.
LOCAL_KIND_NAMES = {
    "theorem": "Theorem", "lemma": "Lemma", "proposition": "Proposition",
    "corollary": "Corollary", "definition": "Definition",
    "convention": "Convention", "notation": "Notation", "conjecture": "Conjecture",
    "assumption": "Assumption", "hypothesis": "Hypothesis", "example": "Example",
    "counterexample": "Counterexample", "remark": "Remark", "construction": "Construction",
    "observation": "Observation", "warning": "Warning", "question": "Question",
    "blank": "Claim", "exercise": "Exercise", "openquestion": "Open question",
    "claim": "Claim", "conditionaltheorem": "Conditional theorem",
    "manuscriptinput": "Input", "obligation": "Open obligation", "principle": "Principle",
    "problem": "Unproved geometric statement", "proposal": "Proposed theorem",
    "scope": "Scope", "tool": "Tool",
}


def local_kind_name(node):
    """Use inspected graph environments; preserve native navigation fallbacks.

    Proof text is supplied by its explicit attachment, and clause/item anchors
    retain their native numbering conventions. Never derive a type from an ID.
    """
    from manuscript_graph import NAVIGATION
    if node.get("kind") in NAVIGATION:
        return None
    return LOCAL_KIND_NAMES.get((node.get("environment") or "").rstrip("*"))


def checked_id(value):
    # Native retained labels are not limited to the authored ID grammar. Never
    # interpolate them as TeX identifiers: machine keys below are ASCII hashes.
    if not isinstance(value, str) or not value.strip() or not value.isprintable():
        raise ValueError(f"invalid runtime identifier: {value!r}")
    return value


def runtime_key(value):
    """Match pdftexcmds' MD5 of TeX's detokenized UTF-8 input (not a trust hash)."""
    return hashlib.md5(checked_id(value).encode("utf-8")).hexdigest().upper()


def tex_identifier(value):
    """Literal native display text, with safe TeX escaping and break positions."""
    clusters = []
    for char in checked_id(value):
        if unicodedata.combining(char) and clusters:
            clusters[-1] += char
        else:
            clusters.append(char)
    result = []
    for cluster in clusters:
        literal = {" ": r"\ ", "'": r"\textquotesingle{}", "`": r"\textasciigrave{}"}.get(cluster)
        escaped = literal if literal is not None else tex_text(cluster)
        # Group UTF-8 sequences and escaped control sequences as one map item.
        # ASCII characters need no groups. Break tokens are emitted only when
        # displayed, keeping the global generated table compact in TeX memory.
        result.append("{" + escaped + "}" if escaped != cluster or not cluster.isascii() else escaped)
    return r"\SemanTeXLiteralID{" + "".join(result) + "}"


def tex_text(value):
    """Render data as text, never execute arbitrary metadata as TeX."""
    chars = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}",
             "%": r"\%", "#": r"\#", "&": r"\&", "_": r"\_",
             "$": r"\$", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(chars.get(c, c) for c in " ".join(str(value).split()))


def masked(text):
    # Reuse the graph's literal-source rules (comments, verbatim, conditionals).
    from manuscript_graph import masked as graph_masked
    return graph_masked(text)


def embedded_context(text):
    contexts = CONTEXT.findall(masked(text))
    if len(contexts) > 1:
        raise ValueError("document must have exactly one literal SemanTeXContext")
    return checked_id(contexts[0]) if contexts else None


def source_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"runtime source is absent or outside repository: {relative}")
    return path


def registry_contexts(registry):
    if registry.get("schema_version") != 1 or not isinstance(registry.get("contexts"), dict):
        raise ValueError("document-contexts.json must have schema_version 1 and contexts map")
    contexts = registry["contexts"]
    for identity, record in contexts.items():
        checked_id(identity)
        if not identity.startswith("ctx:") or not ID.fullmatch(identity):
            raise ValueError(f"context identity must begin with ctx: {identity}")
        if not isinstance(record, dict) or not isinstance(record.get("file"), str):
            raise ValueError(f"invalid context record: {identity}")
        for field in ("labels", "references"):
            if not isinstance(record.get(field), dict):
                raise ValueError(f"{identity}: missing {field} map")
            for original, target in record[field].items():
                checked_id(original)
                checked_id(target)
        if not isinstance(record.get("aliases", {}), dict):
            raise ValueError(f"{identity}: aliases must map native aliases to native primary IDs")
        for alias, primary in record.get("aliases", {}).items():
            checked_id(alias)
            checked_id(primary)
            if alias == primary or alias not in record["labels"] or primary not in record["labels"]:
                raise ValueError(f"{identity}: alias and primary must be distinct declared native IDs")
        for label in record["labels"].keys() & record["references"].keys():
            if record["labels"][label] != record["references"][label]:
                raise ValueError(f"{identity}: conflicting local and external binding for {label}")
    return contexts


def declarations_for_file(graph, path):
    declarations = getattr(graph, "declarations_by_file", None)
    if declarations is not None:
        return dict(declarations.get(path, {}))
    return {node.get("source_label", key): key for key, node in graph.nodes.items()
            if node["file"] == path and node.get("origin") == "authored"}


def locate_contexts(graph, registry):
    """Embedded identity is authoritative; registry file is moveable metadata."""
    contexts = registry_contexts(registry)
    found = {}
    for path, data in sorted(graph.files.items()):
        if not path.endswith(".tex"):
            continue
        identity = embedded_context(data.decode("utf-8"))
        if identity is None:
            raise ValueError(f"{path}: missing SemanTeXContext; install a reviewed context plan")
        if identity not in contexts:
            raise ValueError(f"{path}: unregistered context {identity}")
        if identity in found:
            raise ValueError(f"duplicate context {identity}: {found[identity]} and {path}")
        found[identity] = path
    missing = set(contexts) - set(found)
    if missing:
        raise ValueError("registered context sources missing: " + ", ".join(sorted(missing)))
    return found


def plan_contexts(graph, registry=None, *, only=None):
    """Return a proposed registry plus insert-only, byte-hash-guarded wrappers."""
    registry = registry or {"schema_version": 1, "contexts": {}}
    contexts = registry_contexts(registry)
    proposed, wrappers, seen = (dict(contexts) if only else {}), [], set()
    by_path = {record["file"]: key for key, record in contexts.items()}
    if len(by_path) != len(contexts):
        raise ValueError("context registry repeats a current file path")
    for path in ([only] if only else sorted(graph.files)):
        if not path.endswith(".tex"):
            continue
        data = graph.files[path]
        raw = data.decode("utf-8")
        embedded = embedded_context(raw)
        identity = embedded or by_path.get(path) or f"ctx:{uuid.uuid4().hex}"
        if embedded and embedded not in contexts:
            raise ValueError(f"{path}: embedded context is not registered: {embedded}")
        if identity in seen or getattr(graph, "context_files", {}).get(identity, path) != path:
            raise ValueError(f"duplicate embedded context: {identity}")
        seen.add(identity)
        record = dict(contexts.get(identity, {}))
        effective = getattr(graph, "document_contexts", {}).get(identity)
        references = (effective["references"] if effective is not None else
                      getattr(graph, "reference_bindings", {}).get(path, {}))
        declarations = declarations_for_file(graph, path)
        references = dict(references)
        # A retired declaration remains a native reference in this document.
        # Carry its original qualified identity across context installation and
        # moves; do not accidentally rebind it to an unqualified/global label.
        namespace = (effective.get("labels", {}) if effective is not None else
                     getattr(graph, "label_namespaces", {}).get(path, {}))
        for native, declared in namespace.items():
            if native not in declarations and declared in getattr(graph, "unit_redirects", {}):
                references[native] = declared
        record.update(file=path, labels=declarations, references=references)
        aliases = dict(getattr(graph, "native_aliases_by_file", {}).get(path, {}))
        if aliases or "aliases" in record:
            record["aliases"] = aliases
        proposed[identity] = record
        if embedded:
            continue
        begin = re.search(r"\\begin\s*\{document\}", masked(raw))
        if begin:
            edits = [{"offset": begin.end(), "text": f"\n\\SemanTeXContext{{{identity}}}"}]
        else:
            edits = [{"offset": 0, "text": f"\\begingroup\n\\SemanTeXContext{{{identity}}}\n"},
                     {"offset": len(raw), "text": "\n\\endgroup\n"}]
        updated = raw
        for edit in sorted(edits, key=lambda x: x["offset"], reverse=True):
            updated = updated[:edit["offset"]] + edit["text"] + updated[edit["offset"]:]
        wrappers.append({"file": path, "context": identity,
                         "before_sha256": hashlib.sha256(data).hexdigest(),
                         "after_sha256": hashlib.sha256(updated.encode()).hexdigest(),
                         "offset_unit": "Unicode code points", "insertions": edits})
    if not only and set(contexts) - seen:
        raise ValueError("registered contexts missing from graph; investigate before planning")
    result = {"schema_version": 1, "contexts": proposed}
    registry_contexts(result)
    return result, {"schema_version": 1, "operation": "insert-only",
                    "mathematical_acceptance": False, "files": wrappers}


def generate_runtime(graph, registry):
    if registry.get("diagnostic_status") == "incomplete-do-not-apply":
        raise ValueError("incomplete diagnostic context proposal; generate a fresh reviewed plan")
    if graph.errors:
        raise ValueError("graph has structural errors; runtime generation refused:\n" + "\n".join(graph.errors))
    current = locate_contexts(graph, registry)
    contexts = registry_contexts(registry)
    aliases = dict(getattr(graph, "aliases", {}))

    def canonical(identity):
        visited = set()
        while identity in aliases:
            if identity in visited:
                raise ValueError(f"runtime alias cycle at {identity}")
            visited.add(identity)
            identity = aliases[identity]
        if identity not in graph.nodes:
            raise ValueError(f"runtime alias or reference has no canonical node: {identity}")
        return identity

    aliases = {alias: canonical(alias) for alias in aliases}
    # Definitions still receive scoped label keys. External display metadata is
    # needed only for actual uses; emitting every unused retained/author unit
    # needlessly exhausts TeX's string/token pools on the full corpus.
    authored_files = set(graph.files)
    needed = {item["target"] for item in graph.occurrences if item["file"] in authored_files}
    needed.update(target for citation in graph.citations for target in citation["targets"])
    for record in contexts.values():
        needed.update(record["references"].values())
    needed = {canonical(identity) for identity in needed}
    # Include exact proof-target chains; never infer an attachment from titles.
    pending = list(needed)
    while pending:
        claim = graph.proofs.get(pending.pop())
        if claim:
            claim = canonical(claim)
        if claim and claim not in needed:
            needed.add(claim)
            pending.append(claim)
    if needed - graph.nodes.keys():
        raise ValueError("runtime requires missing graph targets: " + ", ".join(sorted(needed - graph.nodes.keys())))
    identities = set(needed)
    for record in contexts.values():
        identities.update(record["labels"])
        identities.update(record["references"])
        identities.update(record["labels"].values())
        identities.update(record["references"].values())
    identities.update(graph.proofs)
    identities.update(graph.proofs.values())
    identities.update(aliases)
    identities.update(aliases.values())
    by_key = {}
    for identity in sorted(identities):
        key = runtime_key(identity)
        if key in by_key and by_key[key] != identity:
            raise ValueError(f"runtime key collision: {identity!r} and {by_key[key]!r}")
        by_key[key] = identity
    lines = ["% Generated by scripts/semantex_runtime.py; do not edit.",
             "% Navigation data only; no mathematical acceptance is asserted."]
    for identity, record in sorted(contexts.items()):
        lines.append(r"\SemanTeXDeclareContext{" + identity + "}")
        # Compare every authored definition against the graph, rather than
        # trusting an obsolete registry after manual namespace edits.
        actual = declarations_for_file(graph, current[identity])
        if actual != record["labels"]:
            raise ValueError(f"{identity}: context labels disagree with current graph")
        expected_aliases = getattr(graph, "native_aliases_by_file", {}).get(current[identity], {})
        if record.get("aliases", {}) != expected_aliases:
            raise ValueError(f"{identity}: context aliases disagree with current graph")
        for field, command in (("labels", "Label"), ("references", "Reference")):
            for original, target in sorted(record[field].items()):
                if target not in graph.nodes and target not in aliases:
                    raise ValueError(f"{identity}: missing {field} target {target}")
                lines.append(f"\\SemanTeXDeclare{command}Key{{{identity}}}"
                             f"{{{runtime_key(original)}}}{{{runtime_key(target)}}}")
    for alias, primary in sorted(aliases.items()):
        lines.append(f"\\SemanTeXDeclareAliasKey{{{runtime_key(alias)}}}{{{runtime_key(primary)}}}")
    for identity in sorted(needed):
        node = graph.nodes[identity]
        key = runtime_key(identity)
        if node["kind"] == "gap":
            lines.append(f"\\SemanTeXDeclareGapKey{{{key}}}"
                         f"{{{tex_identifier(node['gap']['original_label'])}}}"
                         f"{{{tex_text(node['gap']['reason'])}}}")
            continue
        path = source_path(graph.root, node["file"])
        # Legacy citation nodes use page=True with the physical page in line;
        # registered locators carry the positive page number explicitly.
        page = node.get("page")
        if page:
            number = node["line"] if page is True else page
            if type(number) is not int or number < 1:
                raise ValueError(f"invalid physical PDF page for {identity}")
            lines.append(f"\\SemanTeXDeclarePDFPageKey{{{key}}}{{{number}}}")
        else:
            locator = f"L{node['line']}"
        url = path.as_uri() + ("" if page else "#" + locator)
        # URI percent/hash syntax is made TeX-safe, not turned into active data.
        url = url.replace("%", r"\%").replace("#", r"\#")
        title = node.get("metadata", {}).get("title", "")
        # A source title with math/macros is not safe plain prose. Keep its
        # immutable identifier as the visible fallback instead of guessing.
        if re.search(r"[\\${}]", title):
            title = ""
        local_kind = local_kind_name(node)
        if local_kind:
            lines.append(f"\\SemanTeXDeclareKindKey{{{key}}}{{{tex_text(local_kind)}}}")
        kind = ("Source locator" if node.get("environment") == "pdf-locator" else
                local_kind or KINDS.get(node["kind"], "Mathematical unit"))
        display = tex_identifier(identity)
        text = tex_text(kind) + ": " + (tex_text(title) + " (" + display + ")" if title else display)
        lines.append(f"\\SemanTeXDeclareExternalKey{{{key}}}{{{text}}}{{{url}}}")
    for proof, claim in sorted(graph.proofs.items()):
        checked_id(proof)
        checked_id(claim)
        if proof not in graph.nodes or claim not in graph.nodes:
            raise ValueError(f"invalid proof attachment {proof} -> {claim}")
        lines.append(f"\\SemanTeXDeclareProofTargetKey{{{runtime_key(proof)}}}{{{runtime_key(claim)}}}")
    return "\n".join(lines) + "\n"


def replace_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".runtime-", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(data)
            handle.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def write_runtime(graph, registry_bytes, output):
    """Only reuse bytes generated from the same validated inputs and tool."""
    checked_signature = getattr(graph, "cache_signature", None)
    receipt = output.with_suffix(output.suffix + ".cache.json")
    if checked_signature:
        key = [checked_signature, hashlib.sha256(registry_bytes).hexdigest(),
               hashlib.sha256(Path(__file__).read_bytes()).hexdigest()]
    try:
        existing = output.read_bytes()
    except FileNotFoundError:
        existing = None
    if checked_signature and existing is not None:
        try:
            if json.loads(receipt.read_bytes()) == [key, hashlib.sha256(existing).hexdigest()]:
                return
        except (ValueError, OSError):
            pass
    data = generate_runtime(graph, json.loads(registry_bytes)).encode()
    if existing != data:
        replace_bytes(output, data)
    if checked_signature:
        try:
            replace_bytes(receipt, json.dumps([key, hashlib.sha256(data).hexdigest()]).encode())
        except OSError:
            pass


def register_document(root, source):
    """Refresh the bindings for one authored document, preserving all other records."""
    from manuscript_graph import Graph
    from semantex_cache import load_graph

    root = root.resolve()
    path = root / source
    relative = path.resolve().relative_to(root).as_posix()
    parts = Path(relative).parts
    authored = parts[:1] in (("draft",), ("notes",)) or (len(parts) >= 4 and parts[0] == "references" and parts[2] == "audit")
    if not authored or path != path.resolve() or path.suffix != ".tex":
        raise ValueError("expected an authored TeX path without symlinks or parent traversal")
    lock_dir = root / "build/semantex"
    lock_dir.mkdir(parents=True, exist_ok=True)
    registry_path = root / "workflow/document-contexts.json"
    with (lock_dir / "contexts.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not registry_path.is_file():
            raise ValueError("initialize a full context plan before registering individual documents")
        before = registry_path.read_bytes()
        registry = json.loads(before)
        if registry.get("diagnostic_status") == "incomplete-do-not-apply":
            raise ValueError("incomplete diagnostic context proposal")
        graph = load_graph(Graph, root)
        if graph.errors:
            raise ValueError("\n".join(graph.errors))
        if relative not in graph.files:
            raise ValueError("expected an indexed authored TeX document")
        current = graph.files[relative]
        proposed, manifest = plan_contexts(graph, registry, only=relative)
        updated = current.decode("utf-8")
        for wrapper in manifest["files"]:
            for edit in reversed(wrapper["insertions"]):
                offset = edit["offset"]
                updated = updated[:offset] + edit["text"] + updated[offset:]
        if path.read_bytes() != current or registry_path.read_bytes() != before:
            raise ValueError("source or registry changed during registration; retry")
        # Register the identity first. After an interrupted insertion, retrying
        # recovers the same ID from the registered path.
        if proposed["contexts"] != registry["contexts"]:
            registry.update(contexts=proposed["contexts"])
            replace_document(registry_path, (json.dumps(registry, indent=2) + "\n").encode())
        if manifest["files"]:
            if path.read_bytes() != current:
                raise ValueError("source changed before context insertion; retry")
            replace_document(path, updated.encode())
        return relative


def replace_document(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temp:
        temporary = Path(temp.name)
        try:
            temp.write(data)
            temp.flush()
            temporary.chmod(path.stat().st_mode & 0o777)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "generate", "register"))
    parser.add_argument("source", nargs="?", help="Authored TeX path for register")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path, help="Required for plan; no files are modified")
    args = parser.parse_args()
    from manuscript_graph import Graph
    from semantex_cache import load_graph
    root = args.root.resolve()
    if args.command == "register":
        if not args.source or args.registry or args.output or args.manifest:
            parser.error("register requires one source path and uses the project's registry")
        try:
            print(register_document(root, args.source))
        except (ValueError, OSError) as exc:
            parser.exit(1, f"semantex runtime: {exc}\n")
        return
    if args.source or not args.output:
        parser.error("plan and generate require --output and take no source path")
    graph = load_graph(Graph, root)
    registry_path = args.registry or root / "workflow/document-contexts.json"
    registry_bytes = registry_path.read_bytes() if registry_path.exists() else None
    try:
        if args.command == "plan":
            if not args.manifest:
                parser.error("plan requires --manifest")
            # Planning is allowed before cleanup, but explicitly retains all
            # diagnostics. Generation, unlike this insert-only plan, is strict.
            result, manifest = plan_contexts(graph, json.loads(registry_bytes) if registry_bytes is not None else None)
            manifest["graph_errors_at_planning"] = graph.errors
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n")
        else:
            if registry_bytes is None:
                raise ValueError("missing context registry")
            write_runtime(graph, registry_bytes, args.output)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"semantex runtime: {exc}\n")


if __name__ == "__main__":
    main()
