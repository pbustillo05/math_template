#!/usr/bin/env python3
"""Acquire pinned papers, retain DOI evidence, and maintain real alpha.bst keys."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
from bibtex_utils import bibtex_transport, compute_alpha_labels, safe_alpha_key

ROOT = Path(__file__).resolve().parents[1]
ENTRY = re.compile(r'(@[A-Za-z]+\s*[{(])\s*([^,\s]+)(,)')
ARXIV = re.compile(r'(?:\d{4}\.\d{4,5}|[a-z][a-z.-]*(?:\.[A-Z]{2})?/\d{7})v[1-9]\d*\Z')
MAX_BYTES = 100 * 1024 * 1024
MAX_EXPANDED = 500 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def normalize_doi(doi):
    doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi.strip(), flags=re.I)
    doi = re.sub(r'^doi:\s*', '', doi, flags=re.I).lower()
    if not re.fullmatch(r'10\.\d{4,9}/\S+', doi) or any(c in doi for c in '{}<>'):
        raise ValueError('expected a DOI such as 10.1000/example')
    return doi


def download(url, accept=None):
    if urllib.parse.urlparse(url).scheme != 'https':
        raise ValueError('downloads require an HTTPS URL')
    headers = {'User-Agent': 'math-research-template/1.0 (single-paper acquisition)'}
    if accept:
        headers['Accept'] = accept
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        if urllib.parse.urlparse(response.geturl()).scheme != 'https':
            raise ValueError('download redirected away from HTTPS')
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('download exceeds 100 MiB limit')
        return data, {'requested_url': url, 'resolved_url': response.geturl(),
                      'content_type': response.headers.get('Content-Type', ''), 'sha256': sha(data)}


def canonical_bib(data, key):
    text = bibtex_transport(data.decode('utf-8').strip())
    matches = list(ENTRY.finditer(text))
    if len(matches) != 1 or not text.startswith('@'):
        raise ValueError('DOI response must contain exactly one BibTeX entry')
    if re.search(r'@(?:string|preamble|comment)\b', text, re.I):
        raise ValueError('DOI response is not a bibliographic entry')
    match = matches[0]
    text = text[:match.start(2)] + key + text[match.end(2):]
    # Quote provider month strings; standard BibTeX macros otherwise vary.
    text = re.sub(r'(\bmonth\s*=\s*)([A-Za-z]+)(\s*[,}])', r'\1{\2}\3', text)
    return text + '\n'


def doi_metadata(root, doi):
    cache = root / 'build/doi-metadata' / sha(doi.encode())
    payload, provenance = cache.with_suffix('.bib'), cache.with_suffix('.json')
    if payload.exists() or provenance.exists():
        data = payload.read_bytes()
        info = json.loads(provenance.read_text())
        if info['doi'] != doi or info['sha256'] != sha(data):
            raise ValueError('DOI metadata cache mismatch; inspect before removing it')
    else:
        url = 'https://doi.org/' + urllib.parse.quote(doi, safe='/')
        data, info = download(url, 'application/x-bibtex; charset=utf-8')
        canonical_bib(data, 'probe')
        info['doi'] = doi
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_bytes(data)
        write_json(provenance, info)
    return data, info


def extract_payload(data, destination):
    """Extract regular files only, rejecting traversal, links and archive bombs."""
    if data.lstrip().lower().startswith((b'<!doctype html', b'<html')):
        raise ValueError('received HTML instead of source')
    try:
        archive = tarfile.open(fileobj=io.BytesIO(data), mode='r:*')
    except tarfile.ReadError:
        archive = None
    if archive is not None:
        with archive:
            members = archive.getmembers()
            if len(members) > 20000 or sum(m.size for m in members) > MAX_EXPANDED:
                raise ValueError('expanded archive exceeds limits')
            names = set()
            for m in members:
                pure = PurePosixPath(m.name)
                if (pure.is_absolute() or '..' in pure.parts or '\\' in m.name or
                        not (m.isfile() or m.isdir()) or
                        (pure.parts and pure.parts[0] in {'audit', 'metadata'}) or
                        (m.isfile() and (pure.as_posix() in names or pure.as_posix() == '.'))):
                    raise ValueError(f'unsafe archive member: {m.name!r}')
                names.add(pure.as_posix())
            for m in members:
                target = destination / m.name
                if m.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.extractfile(m).read())
        return 'tar'
    if data.startswith(b'\x1f\x8b'):
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as compressed:
            data = compressed.read(MAX_EXPANDED + 1)
        if len(data) > MAX_EXPANDED:
            raise ValueError('expanded gzip exceeds limits')
    if data.startswith(b'%PDF'):
        (destination / 'original.pdf').write_bytes(data)
        return 'pdf'
    if b'\\' not in data or b'\x00' in data:
        raise ValueError('unrecognized arXiv source payload; retain and inspect manually')
    (destination / 'source.tex').write_bytes(data)
    return 'single-tex'


def acquire_arxiv(identifier, destination):
    if not ARXIV.fullmatch(identifier):
        raise ValueError('pin an arXiv version, e.g. 2301.01234v2 or math/0301234v1')
    url = 'https://arxiv.org/src/' + urllib.parse.quote(identifier, safe='/')
    data, info = download(url)
    kind = extract_payload(data, destination)
    if not any(destination.rglob('*.tex')) and not any(destination.rglob('*.pdf')):
        raise ValueError('arXiv payload contains neither TeX nor PDF; inspect manually')
    info.update(arxiv=identifier, format=kind)
    (destination / 'metadata').mkdir(exist_ok=True)
    (destination / 'metadata/source.archive').write_bytes(data)
    write_json(destination / 'metadata/source.json', info)
    return info


def manifest(directory):
    result = {}
    for p in sorted(directory.rglob('*')):
        if p.is_symlink():
            raise ValueError(f'symlink in retained payload: {p}')
        if p.is_file() and p.relative_to(directory).parts[0] != 'audit':
            result[p.relative_to(directory).as_posix()] = sha(p.read_bytes())
    return result


def bibliography(records, directory):
    temporary = {r['id']: canonical_bib((directory / r['key'] / 'metadata/doi-response.bib').read_bytes(), r['id'])
                 for r in records}
    labels = compute_alpha_labels(list(temporary.values())) if records else {}
    text = '\n'.join(canonical_bib((directory / r['key'] / 'metadata/doi-response.bib').read_bytes(), labels[r['id']]).rstrip()
                     for r in records)
    return labels, (text + '\n' if text else '% Add papers with scripts/references.py add.\n')


def verify(root, *, alpha=True):
    refs = root / 'references'
    catalog = json.loads((refs / 'catalog.json').read_text())
    lock = json.loads((refs / 'lock.json').read_text())
    if catalog.get('schema_version') != 1 or lock.get('schema_version') != 1:
        raise ValueError('unsupported reference schema')
    records = catalog['records']
    if len({r['id'] for r in records}) != len(records) or len({r['key'] for r in records}) != len(records):
        raise ValueError('duplicate reference ID or key')
    locked = {r['id']: r for r in lock['records']}
    if set(locked) != {r['id'] for r in records}:
        raise ValueError('catalog/lock mismatch')
    actual_dirs = {p.name for p in refs.iterdir() if p.is_dir()}
    if actual_dirs != {r['key'] for r in records}:
        raise ValueError('paper directories must match catalog keys exactly')
    for r in records:
        if not safe_alpha_key(r['key']) or r['id'] != 'r' + sha(r['doi'].encode())[:16]:
            raise ValueError('invalid paper identity/key')
        saved = locked[r['id']]
        if saved['record'] != r or saved['files'] != manifest(refs / r['key']):
            raise ValueError(f"retained source or catalog changed: {r['key']}; restore locked bytes, never bless edits")
        directory = refs / r['key']
        meta = json.loads((directory / 'metadata/doi.json').read_text())
        data = (directory / 'metadata/doi-response.bib').read_bytes()
        if meta['sha256'] != sha(data) or meta['doi'] != r['doi']:
            raise ValueError('DOI provenance mismatch')
        source = json.loads((directory / 'metadata/source.json').read_text())
        original = directory / ('metadata/source.archive' if r.get('arxiv') else 'original.pdf')
        if source['sha256'] != sha(original.read_bytes()):
            raise ValueError('source acquisition hash mismatch')
    if alpha:
        labels, text = bibliography(records, refs)
        if any(labels[r['id']] != r['key'] for r in records):
            raise ValueError('alpha keys changed; run sync to inspect migration')
        if (refs / 'references.bib').read_text() != text:
            raise ValueError('bibliography differs from retained DOI responses')
    return records


def rewrite_tokens(content, mapping):
    if not mapping:
        return content
    token = re.compile(r'(?<![\w+.-])(' + '|'.join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)) + r')(?=[:},]|/|$)')
    return token.sub(lambda m: mapping[m[1]], content)


def replacements(root, mapping):
    """Rewrite structured key/locator tokens simultaneously, including collision chains."""
    changes = {}
    if not mapping:
        return changes
    for base in ('draft', 'notes', 'agents', 'workflow', 'lean'):
        for p in (root / base).rglob('*'):
            if not p.is_file() or p.suffix not in {'.tex', '.md', '.json'} or p.is_symlink():
                continue
            old = p.read_text()
            new = rewrite_tokens(old, mapping)
            if new != old:
                changes[p] = (old, new)
    return changes


def synchronize(root, new=None, *, apply_rekeys=False):
    refs = root / 'references'
    records = verify(root, alpha=False)
    with tempfile.TemporaryDirectory(prefix='.references-', dir=root) as scratch:
        work = Path(scratch) / 'next'
        shutil.copytree(refs, work)
        if new:
            record, paper = new
            if any(r['doi'] == record['doi'] for r in records):
                raise ValueError('DOI already retained; version changes require a deliberate migration')
            records.append(record)
            shutil.copytree(paper, work / record['key'])
        records.sort(key=lambda r: r['doi'])
        labels, text = bibliography(records, work)
        existing = {r['key']: labels[r['id']] for r in records if r['key'] in {p.name for p in refs.iterdir() if p.is_dir()} and r['key'] != labels[r['id']]}
        if existing and not apply_rekeys:
            raise ValueError('alpha collision changes existing keys: ' + json.dumps(existing) +
                             '; rerun with --apply-rekeys to migrate tracked locators; inspect git diff afterwards')
        changes = replacements(root, existing)
        # Rename via stable IDs to handle swaps and chains without overwriting papers.
        holding = Path(scratch) / 'holding'
        holding.mkdir()
        for r in records:
            shutil.move(str(work / r['key']), holding / r['id'])
        for r in records:
            r['key'] = labels[r['id']]
            shutil.move(str(holding / r['id']), work / r['key'])
        # Migrate cross-paper audit links, preserving retained payload bytes.
        for paper in work.iterdir():
            if paper.is_dir():
                for p in (paper / 'audit').rglob('*'):
                    if p.is_file() and p.suffix in {'.md', '.tex', '.json'}:
                        content = p.read_text()
                        content = rewrite_tokens(content, existing)
                        p.write_text(content)
        (work / 'references.bib').write_text(text)
        write_json(work / 'catalog.json', {'schema_version': 1, 'records': records})
        write_json(work / 'lock.json', {'schema_version': 1, 'records': [
            {'id': r['id'], 'record': r, 'files': manifest(work / r['key'])} for r in records]})
        backup = Path(scratch) / 'previous'
        # Prepare everything first. Roll back both the corpus and locator edits on error.
        os.replace(refs, backup)
        try:
            os.replace(work, refs)
            for p, (_, content) in changes.items():
                p.write_text(content)
        except BaseException:
            if refs.exists():
                shutil.rmtree(refs)
            os.replace(backup, refs)
            for p, (old, _) in changes.items():
                p.write_text(old)
            raise
    print(json.dumps({'keys': {r['doi']: r['key'] for r in records}, 'migrated_keys': existing,
                      'updated_locators': [p.relative_to(root).as_posix() for p in changes]}, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    sub = parser.add_subparsers(dest='command', required=True)
    doi = sub.add_parser('doi', help='DOI-derived BibTeX; response is cached and hash checked')
    doi.add_argument('doi')
    doi.add_argument('--key', default='doi_record')
    alpha = sub.add_parser('alpha', help='compute actual alpha.bst labels for a BibTeX file')
    alpha.add_argument('bib', type=Path)
    arxiv = sub.add_parser('arxiv', help='download exact pinned arXiv source into a NEW directory')
    arxiv.add_argument('identifier')
    arxiv.add_argument('--dest', type=Path, required=True)
    add = sub.add_parser('add', help='retain one relevant paper and synchronize the corpus')
    add.add_argument('--doi')
    source = add.add_mutually_exclusive_group(required=True)
    source.add_argument('--arxiv')
    source.add_argument('--pdf', help='HTTPS PDF URL when TeX is unavailable')
    source.add_argument('--local-pdf', type=Path)
    add.add_argument('--reason', help='why no TeX is available (required for PDF fallback)')
    add.add_argument('--relevance', required=True)
    add.add_argument('--apply-rekeys', action='store_true')
    sync = sub.add_parser('sync', help='rebuild from retained evidence without network access')
    sync.add_argument('--apply-rekeys', action='store_true')
    sub.add_parser('verify', help='verify hashes, corpus coverage and deterministic bibliography')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.command == 'doi':
        if not safe_alpha_key(args.key):
            raise ValueError('unsafe BibTeX key')
        data, _ = doi_metadata(root, normalize_doi(args.doi))
        print(canonical_bib(data, args.key), end='')
    elif args.command == 'alpha':
        text = args.bib.read_text()
        entries = [text] if text.strip() else []
        # alpha.bst processes the whole file to resolve collisions globally.
        if entries:
            count = len(ENTRY.findall(text))
            # compute_alpha_labels expects one list element per bibliographic record.
            # Split at entry starts, retaining the exact provider contents.
            starts = [m.start() for m in ENTRY.finditer(text)] + [len(text)]
            entries = [text[a:b] for a, b in zip(starts, starts[1:])]
            if not count:
                raise ValueError('no BibTeX entries found')
        print(json.dumps(compute_alpha_labels(entries) if entries else {}, indent=2, ensure_ascii=False))
    elif args.command == 'arxiv':
        target = args.dest.resolve()
        if target.exists():
            raise ValueError('destination must not exist')
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as temp:
            staged = Path(temp) / 'source'
            staged.mkdir()
            info = acquire_arxiv(args.identifier, staged)
            os.replace(staged, target)
        print(json.dumps(info, indent=2))
    elif args.command == 'add':
        if args.arxiv and not ARXIV.fullmatch(args.arxiv):
            raise ValueError('arXiv identifier must include a pinned vN')
        doi = args.doi or ('10.48550/arxiv.' + re.sub(r'v\d+$', '', args.arxiv) if args.arxiv else '')
        doi = normalize_doi(doi)
        if not args.arxiv and not args.reason:
            raise ValueError('--reason is required for a PDF fallback')
        data, metadata = doi_metadata(root, doi)
        identity = 'r' + sha(doi.encode())[:16]
        with tempfile.TemporaryDirectory() as temp:
            paper = Path(temp)
            (paper / 'metadata').mkdir()
            (paper / 'metadata/doi-response.bib').write_bytes(data)
            write_json(paper / 'metadata/doi.json', metadata)
            if args.arxiv:
                info = acquire_arxiv(args.arxiv, paper)
            else:
                if args.local_pdf:
                    payload = args.local_pdf.read_bytes()
                    info = {'kind': 'local-pdf', 'sha256': sha(payload)}
                else:
                    payload, info = download(args.pdf)
                if not payload.startswith(b'%PDF'):
                    raise ValueError('PDF fallback is not a PDF')
                (paper / 'original.pdf').write_bytes(payload)
                write_json(paper / 'metadata/source.json', info)
            (paper / 'audit').mkdir()
            (paper / 'audit/README.md').write_text('# Source audit\n\nRelevance: ' + args.relevance + '\n\nStatus: acquired; not yet audited.\n\nRecord exact claims, version, locators, matched hypotheses, gaps and errata here.\n')
            record = {'id': identity, 'key': identity, 'doi': doi, 'relevance': args.relevance}
            if args.arxiv:
                record['arxiv'] = args.arxiv
            if args.reason:
                record['source_gap'] = args.reason
            if not any(paper.rglob('*.tex')) and not args.reason:
                raise ValueError('arXiv returned PDF-only; provide --reason documenting the TeX gap')
            synchronize(root, (record, paper), apply_rekeys=args.apply_rekeys)
    elif args.command == 'sync':
        synchronize(root, apply_rekeys=args.apply_rekeys)
    else:
        print(f'Verified {len(verify(root))} retained papers and their DOI-derived bibliography.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        print('error: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
