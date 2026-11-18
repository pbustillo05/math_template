"""Reusable, data-only snapshots of the checked SemanTeX graph."""
from collections.abc import Mapping
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
from stat import S_ISLNK, S_ISREG
import tempfile
from typing import NamedTuple
import zlib


SCRIPTS = ("manuscript_graph.py", "semantex_sources.py", "semantex_links.py", "semantex_cache.py")
SET_MAPS = {"direct_edges", "edges", "dependents", "source_audits"}
BUILD_STATE = {"_declarations", "_pending_aliases", "citations_by_owner", "overlays", "_fingerprints", "_reviewed_hashes", "_shared_review_paths",
               "file_hashes", "_decoded_files", "_citation_lines", "_paper_pdfs",
               "cache_signature", "cache_inputs", "_scan_store"}
RECORDS = {"nodes", "source_labels"}


def stamp(path, follow_symlinks=True):
    return stat_fields(os.stat(path, follow_symlinks=follow_symlinks))


def stat_fields(info):
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def external_inputs(root):
    """Include graph evidence whose paths are supplied by a registry."""
    result = set()
    for registry, field in (("unit-redirects.json", "redirects"), ("source-documents.json", "documents")):
        path = root / "workflow" / registry
        if not path.is_file():
            continue
        entries = json.loads(path.read_bytes())[field]
        for record in entries.values():
            files = (record["original"]["evidence_file"], record["review"]["report"]) if field == "redirects" else (record["file"],)
            for file in files:
                relative = Path(file)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("invalid evidence path")
                result.add(root / relative)
    return result


class GraphInputs(NamedTuple):
    full: str
    structure: str
    markdown: dict
    version: str
    retained: str


def signature(root):
    """Check file identity and change times without reading the corpus bodies."""
    def corpus_files(subtree, relative):
        with os.scandir(root / relative) as entries:
            for entry in entries:
                file = relative + "/" + entry.name
                relevant = subtree == "references" or entry.name.endswith((".tex", ".md"))
                if entry.is_symlink() and (relevant or entry.is_dir()):
                    # Explicit components of authored audit globs can be links.
                    raise ValueError("symlink in corpus")
                directory = entry.is_dir(follow_symlinks=False)
                if directory:
                    yield from corpus_files(subtree, file)
                if (relevant and not directory) or entry.name.endswith((".tex", ".md")) or entry.name == "semantex.json":
                    yield file, stat_fields(entry.stat(follow_symlinks=False))

    try:
        extra = external_inputs(root)
        if (root / "workflow").is_symlink() or any(path.resolve() != path for path in extra):
            return None
        paths = set((root / "workflow").glob("*.json"))
        paths.update(extra)
        values = {}
        for subtree in ("draft", "notes", "references"):
            base = root / subtree
            if base.is_symlink():
                return None
            if base.exists():
                values.update(corpus_files(subtree, subtree))
        for path in paths:
            info = stamp(path, follow_symlinks=False)
            if S_ISLNK(info[2]):
                return None
            values[path.relative_to(root).as_posix()] = info
        values = sorted(values.items())
        tools = [(name, stamp(Path(__file__).with_name(name))) for name in SCRIPTS]
        pdfinfo = shutil.which("pdfinfo")
        tools.append((pdfinfo, stamp(Path(pdfinfo)) if pdfinfo else None))
        version = digest(tools)
        retained = digest([value for value in values if value[0].startswith("references/")
                           and not {"audit", "metadata"} & set(value[0].split("/"))])
        # Only existing, ordinary authored Markdown can change navigation alone.
        # Source/audit evidence, registry inputs, and path-set changes need full checks.
        evidence = {path.relative_to(root).as_posix() for path in extra}
        markdown = {file: info for file, info in values
                    if file.endswith(".md") and file.startswith(("draft/", "notes/"))
                    and "/archived/" not in file and file not in evidence and S_ISREG(info[2])}
        structure = digest([str(root), version, [item for item in values if item[0] not in markdown],
                            list(markdown)])
        return GraphInputs(digest([structure, markdown]), structure, markdown, version, retained)
    except (OSError, ValueError, AttributeError, KeyError, TypeError):
        # Let the graph report malformed, missing, or unreadable inputs.
        return None


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


class ScanStore:
    """Cache each file's parse independently of the finalized dependency graph."""
    def __init__(self, root, version, retained, refresh=False):
        self.root = root
        self.version = version
        self.retained = retained
        self.refresh = refresh
        self.pending = []
        self.path = root / "build/semantex/scans.sqlite3"

    def __enter__(self):
        self.db = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(self.path, timeout=0.2)
            self.db.execute("CREATE TABLE IF NOT EXISTS scans (kind TEXT, path TEXT, stamp TEXT, "
                            "data BLOB, PRIMARY KEY (kind, path))")
        except (OSError, sqlite3.Error):
            if self.db is not None:
                self.db.close()
            self.db = None
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self.db is None:
            return
        try:
            if exc_type is None and (self.pending or self.refresh):
                with self.db:
                    if self.refresh:
                        self.db.execute("DELETE FROM scans")
                    self.db.executemany("INSERT OR REPLACE INTO scans VALUES (?, ?, ?, ?)", self.pending)
        except sqlite3.Error:
            pass
        finally:
            self.db.close()
            self.db = None

    def key(self, path):
        return digest([self.version, stamp(path)])

    def get(self, kind, path, key):
        if self.db is not None and not self.refresh:
            try:
                row = self.db.execute("SELECT data FROM scans WHERE kind = ? AND path = ? AND stamp = ?",
                                      (kind, path, key)).fetchone()
                if row is not None:
                    return decode(row[0])
            except (sqlite3.Error, ValueError, zlib.error):
                pass
        return None

    def put(self, kind, path, key, value):
        if self.db is not None:
            try:
                if self.key(self.root / path) == key:
                    self.pending.append((kind, path, key, encode(value)))
            except OSError:
                pass


class Records(Mapping):
    def __init__(self, db, table, decode):
        self.db = db
        self.table = table
        self.decode = decode
        self.loaded = {}

    def __getitem__(self, key):
        if key in self.loaded:
            return self.loaded[key]
        row = self.db.execute(f"SELECT value FROM {self.table} WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        value = self.decode(row[0])
        self.loaded[key] = value
        return value

    def __setitem__(self, key, value):
        # A refreshed Markdown file shadows its original bytes in this reader only.
        self.loaded[key] = value

    def __iter__(self):
        return (row[0] for row in self.db.execute(f"SELECT key FROM {self.table} ORDER BY rowid"))

    def __len__(self):
        return self.db.execute(f"SELECT count(*) FROM {self.table}").fetchone()[0]

    def items(self):
        for key, value in self.db.execute(f"SELECT key, value FROM {self.table} ORDER BY rowid"):
            if key not in self.loaded:
                self.loaded[key] = self.decode(value)
            yield key, self.loaded[key]


def encode(value):
    return zlib.compress(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode(), level=1)


def unpack_file(payload):
    try:
        return zlib.decompress(payload)
    except zlib.error as exc:
        raise ValueError("invalid cached data; run scripts/semantex --rebuild check") from exc


def decode(payload):
    return json.loads(unpack_file(payload))


class Snapshot:
    def __init__(self, db, fields):
        self.db = db
        self.fields = frozenset(fields)

    def read(self, name):
        value = decode(self.db.execute("SELECT value FROM graph WHERE name = ?", (name,)).fetchone()[0])
        if name in SET_MAPS:
            return {key: set(items) for key, items in value.items()}
        if name == "redirect_evidence":
            return set(value)
        return value


def refresh_markdown(graph, previous, inputs):
    changed = {file for file, info in inputs.markdown.items() if tuple(previous[file]) != info}
    graph.refresh_markdown(changed)
    return all(stamp(graph.root / file) == inputs.markdown[file] for file in changed)


def read_snapshot(path, graph_type, root, inputs):
    if not path.is_file():
        return None
    db = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        stored, structure, fields = db.execute("SELECT stamp, structure, fields FROM manifest").fetchone()
        if structure == inputs.structure:
            graph = graph_type.__new__(graph_type)
            graph.__dict__.update(root=root, overlays={}, errors=[], _snapshot=Snapshot(db, json.loads(fields)))
            graph.reset_review_cache()
            graph.files = Records(db, "files", unpack_file)
            for name in RECORDS:
                graph.__dict__[name] = Records(db, name, decode)
            if stored == inputs.full or refresh_markdown(
                    graph, decode(db.execute("SELECT markdown FROM manifest").fetchone()[0]), inputs):
                graph.cache_signature = None if graph.errors else inputs.full
                graph.cache_inputs = inputs
                return graph
    except (ValueError, TypeError, KeyError, sqlite3.Error, zlib.error):
        pass
    db.close()
    return None


def write_snapshot(path, graph, inputs):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".graph-", suffix=".sqlite3")
    os.close(fd)
    db = sqlite3.connect(temporary)
    try:
        db.execute("PRAGMA journal_mode = OFF")
        db.execute("PRAGMA synchronous = OFF")
        db.execute("CREATE TABLE graph (name TEXT PRIMARY KEY, value BLOB NOT NULL)")
        db.execute("CREATE TABLE manifest (stamp TEXT, structure TEXT, markdown BLOB, fields TEXT)")
        fields = vars(graph).keys() - BUILD_STATE - RECORDS - {"root", "files", "errors"}
        for name in sorted(fields):
            value = getattr(graph, name)
            if name in SET_MAPS:
                value = {key: sorted(items) for key, items in value.items()}
            elif name == "redirect_evidence":
                value = sorted(value)
            db.execute("INSERT INTO graph VALUES (?, ?)", (name, encode(value)))
        for name in sorted(RECORDS | {"files"}):
            pack = (lambda value: zlib.compress(value, level=1)) if name == "files" else encode
            db.execute(f"CREATE TABLE {name} (key TEXT PRIMARY KEY, value BLOB NOT NULL)")
            db.executemany(f"INSERT INTO {name} VALUES (?, ?)",
                           ((key, pack(value)) for key, value in getattr(graph, name).items()))
        db.execute("INSERT INTO manifest VALUES (?, ?, ?, ?)",
                   (inputs.full, inputs.structure, encode(inputs.markdown), json.dumps(sorted(fields))))
        db.commit()
        db.close()
        os.replace(temporary, path)
    finally:
        db.close()
        Path(temporary).unlink(missing_ok=True)


def load_graph(graph_type, root, overlays=None, *, rebuild=False, inputs=..., save_snapshot=True, previous=None):
    path = root / "build/semantex/graph.sqlite3"
    before = signature(root) if inputs is ... else inputs
    if before is None:
        return graph_type(root, overlays) if overlays else graph_type(root)
    if not (overlays or rebuild):
        try:
            if (previous is not None and previous.cache_signature and not previous.errors
                    and previous.cache_inputs.structure == before.structure):
                previous.cache_signature = None
                previous.reset_review_cache()
                if refresh_markdown(previous, previous.cache_inputs.markdown, before):
                    previous.cache_signature = None if previous.errors else before.full
                    previous.cache_inputs = before
                    return previous
            cached = read_snapshot(path, graph_type, root, before)
            if cached is not None:
                return cached
        except (OSError, sqlite3.Error):
            pass
    with ScanStore(root, before.version, before.retained, refresh=rebuild) as store:
        graph = graph_type(root, overlays, scan_store=store)
    if not overlays and not graph.errors and signature(root) == before:
        graph.cache_signature = before.full
        graph.cache_inputs = before
        if save_snapshot:
            try:
                write_snapshot(path, graph, before)
            except (OSError, sqlite3.Error):
                pass  # Read-only checkouts can still use the graph.
    return graph
