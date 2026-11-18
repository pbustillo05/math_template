"""Read-only native/virtual environment labels for pinned reference sources."""
from __future__ import annotations
from bisect import bisect_left, bisect_right
from collections import defaultdict
import hashlib
from pathlib import Path
import re
from urllib.parse import quote

NON_SPACE = re.compile(r'\S')


def source_text(path):
    data = path.read_bytes()
    try:
        return data.decode('utf-8'), 'utf-8'
    except UnicodeDecodeError:
        return data.decode('latin-1'), 'latin-1'


def citation_source_is_retained(root, key, file):
    relative = Path(file)
    if relative.is_absolute() or '..' in relative.parts:
        return False
    base = root / 'references' / key
    target = (root / relative).resolve()
    return (target.is_relative_to(base.resolve()) and
            not {'audit', 'metadata'} & set(relative.parts) and target.is_file())


def scan_source(path, root, key, mask, arg, spans=None):
    raw, encoding = source_text(path)
    text = mask(raw)
    relative = path.relative_to(root).as_posix()
    local_path = path.relative_to(root / 'references' / key).as_posix()
    path_id = hashlib.sha256(local_path.encode()).hexdigest()[:12]
    stack, frames, warnings = [], [], []
    counts = {}
    for token in re.finditer(r'\\(begin|end)\b', text):
        try:
            name, end = arg(text, token.end())
        except ValueError:
            continue
        if token[1] == 'begin':
            counts[name] = counts.get(name, 0) + 1
            frame = {'environment': name, 'start': token.start(), 'end': None,
                     'ordinal': counts[name], 'labels': []}
            stack.append(frame)
            frames.append(frame)
        elif stack and stack[-1]['environment'] == name:
            stack.pop()['end'] = end
        else:
            warnings.append(f'{relative}: unmatched end of {name}')
    for frame in stack:
        warnings.append(f'{relative}: unclosed environment {frame["environment"]}')
    complete = [f for f in frames if f['end'] is not None and f['environment'] != 'document']

    def with_owner(matches):
        index, active = 0, []
        for match in matches:
            offset = match.start()
            while index < len(complete) and complete[index]['start'] <= offset:
                frame = complete[index]
                while active and active[-1]['end'] <= frame['start']:
                    active.pop()
                active.append(frame)
                index += 1
            while active and active[-1]['end'] <= offset:
                active.pop()
            yield match, active[-1] if active else None

    newlines = [match.start() for match in re.finditer('\n', raw)]

    def line(offset):
        return bisect_right(newlines, offset - 1) + 1

    labels = []
    for m, frame in with_owner(re.finditer(r'\\label\s*\{([^{}]+)\}', text)):
        label = m[1].strip()
        if frame is not None:
            frame['labels'].append(label)
        labels.append((label, m.start(), frame, False))
    for frame in complete:
        if not frame['labels']:
            env = re.sub(r'[^A-Za-z0-9_-]', '-', frame['environment'])
            label = f'auto:{path_id}:{env}:{frame["ordinal"]}'
            frame['labels'].append(label)
            labels.append((label, frame['start'], frame, True))
    references = defaultdict(list)
    matches = re.finditer(r'\\(ref|eqref|autoref|cref|Cref|xref|dxref|hxref|hdxref|mention|hiddenmention|use|hiddenuse)\*?\s*\{([^{}]+)\}', text)
    for m, frame in with_owner(matches):
        if not frame:
            continue
        for target in m[2].split(','):
            command = m[1]
            owner = key + ':' + frame['labels'][0]
            references[owner].append({'owner': owner, 'target': key + ':' + target.strip(),
                               'dependency': command in {'dxref', 'hdxref', 'use', 'hiddenuse'}, 'file': relative,
                               'command': command, 'relation': 'reference',
                               'visible': command not in {'hxref', 'hdxref', 'hiddenmention', 'hiddenuse'},
                               'line': line(m.start()),
                               'column': m.start() - raw.rfind('\n', 0, m.start())})
    records = []
    proofs = [frame for frame in complete if frame['environment'] == 'proof']
    proof_starts = [frame['start'] for frame in proofs]
    for label, offset, frame, virtual in labels:
        start, end = (frame['start'], frame['end']) if frame else (offset, text.find('}', offset) + 1)
        record = {'id': key + ':' + label, 'bib_key': key, 'source_label': label,
                  'file': relative, 'line': line(offset),
                  'column': offset - raw.rfind('\n', 0, offset),
                  'start_line': line(start),
                  'end_line': line(max(start, end - 1)),
                  'latex': raw[start:end], 'encoding': encoding, 'kind': 'external',
                  'status': 'source-unreviewed', 'virtual': virtual,
                  'environment': frame['environment'] if frame else None,
                  'mentions': list(references.get(key + ':' + frame['labels'][0], ())) if frame else []}
        excerpt_spans = [(start, end)] if spans is not None else None
        if frame:
            index = bisect_left(proof_starts, end)
            if index < len(proofs) and NON_SPACE.search(text, end, proof_starts[index]) is None:
                following = proofs[index]
                record['proof'] = {'id': key + ':' + following['labels'][0],
                                   'file': relative, 'start_line': line(following['start']),
                                   'end_line': line(following['end'] - 1),
                                   'latex': raw[following['start']:following['end']]}
                if excerpt_spans is not None:
                    excerpt_spans.append((following['start'], following['end']))
        if spans is not None:
            spans[record['id']] = excerpt_spans
        records.append(record)
    return records, warnings


def index_sources(root, mask, arg, spans=None, store=None):
    labels, papers = {}, {}
    references = root / 'references'
    if not references.exists():
        return labels, papers
    for directory in sorted(p for p in references.iterdir() if p.is_dir() and not p.is_symlink()):
        key = directory.name
        files = [p for p in sorted(directory.rglob('*')) if p.is_file() and
                 not p.is_symlink() and p.resolve().is_relative_to(directory.resolve()) and
                 not {'audit', 'metadata'} & set(p.relative_to(directory).parts)]
        tex = [p for p in files if p.suffix == '.tex']
        candidates = []
        diagnostics = []
        for path in tex:
            relative = path.relative_to(root).as_posix()
            stamp = store.key(path) if store else None
            saved = store.get("retained", relative, stamp) if store else None
            if saved is None:
                offsets = {}
                records, warnings = scan_source(path, root, key, mask, arg, offsets)
                if store:
                    store.put("retained", relative, stamp, [records, warnings, offsets])
            else:
                records, warnings, offsets = saved
            if spans is not None:
                spans.update(offsets)
            diagnostics.extend(warnings)
            for record in records:
                labels.setdefault(record['id'], []).append(record)
            candidates.append((len(records), path.stat().st_size, relative))
        if candidates:
            papers[key] = {'file': max(candidates)[2], 'line': 1, 'has_tex': True, 'diagnostics': diagnostics}
        else:
            pdfs = [p for p in files if p.suffix.lower() == '.pdf']
            transcripts = [p for p in files if p.suffix in {'.txt', '.md'}]
            if pdfs or transcripts:
                path = (pdfs or transcripts)[0]
                papers[key] = {'file': path.relative_to(root).as_posix(), 'line': 1, 'has_tex': False}
    return labels, papers


def source_url(root, file, line=1, page=False):
    if page:
        return (root / file).resolve().as_uri() + '#page=' + str(line)
    return 'vscode://file/' + quote(str((root / file).resolve()).lstrip('/'), safe='/') + ':' + str(line)


def registered_pdf_locators(root, page_count, occupied=()):
    """Validate explicit, hash-pinned PDF identities without bibliography entries.

    The entire registry is validated before returning any records. Its text is
    data, not a mathematical transcription or an acceptance/review record.
    """
    import json
    registry = root / 'workflow/source-documents.json'
    if not registry.exists():
        return {}
    if registry.is_symlink() or not registry.resolve().is_relative_to(root.resolve()):
        raise ValueError('source-document registry must be a local regular file')

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'duplicate registry key {key}')
            result[key] = value
        return result

    data = json.loads(registry.read_text(), object_pairs_hook=unique_pairs)
    if not isinstance(data, dict) or set(data) != {'schema_version', 'documents', 'locators'} or type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('expected schema version 1 with documents and locators maps')
    if not isinstance(data['documents'], dict) or not isinstance(data['locators'], dict):
        raise ValueError('documents and locators must be maps')

    def identity(value, prefix):
        if not isinstance(value, str) or not re.fullmatch(prefix + r':[A-Za-z0-9][A-Za-z0-9:._-]*', value):
            raise ValueError(f'expected a stable {prefix}: identifier')

    def text(value, field):
        if not isinstance(value, str) or not value.strip() or not value.isprintable():
            raise ValueError(f'{field} must be nonempty printable text')
        return value

    documents = {}
    for identifier, record in data['documents'].items():
        identity(identifier, 'doc')
        if not isinstance(record, dict) or set(record) != {'title', 'edition', 'file', 'sha256'}:
            raise ValueError(f'{identifier}: document requires exactly title, edition, file and sha256')
        title, edition = text(record['title'], 'title'), text(record['edition'], 'edition')
        file = text(record['file'], 'file')
        relative = Path(file)
        if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != file or relative.suffix.lower() != '.pdf':
            raise ValueError(f'{identifier}: PDF path must be normalized and repository-relative')
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()) or any((root / Path(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)):
            raise ValueError(f'{identifier}: PDF path must stay inside the repository without symlinks')
        if not path.is_file():
            raise ValueError(f'{identifier}: retained PDF is missing: {file}')
        pin = record['sha256']
        if not isinstance(pin, str) or not re.fullmatch(r'[0-9a-f]{64}', pin):
            raise ValueError(f'{identifier}: sha256 must be a lowercase SHA-256 digest')
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != pin:
            raise ValueError(f'{identifier}: retained PDF hash mismatch')
        if not payload.startswith(b'%PDF-'):
            raise ValueError(f'{identifier}: retained source is not a PDF')
        count = page_count(file)
        if type(count) is not int or count < 1:
            raise ValueError(f'{identifier}: invalid physical PDF page count')
        if hashlib.sha256(path.read_bytes()).hexdigest() != pin:
            raise ValueError(f'{identifier}: PDF changed during page validation')
        documents[identifier] = dict(record, id=identifier, physical_page_count=count)

    records = {}
    for identifier, record in data['locators'].items():
        identity(identifier, 'loc')
        if identifier in occupied:
            raise ValueError(f'{identifier}: locator collides with an existing declaration or source identity')
        required, optional = {'document', 'page'}, {'end_page', 'printed_locator', 'title'}
        if not isinstance(record, dict) or not required <= record.keys() or record.keys() - required - optional:
            raise ValueError(f'{identifier}: locator requires document and page; only end_page, printed_locator and title are optional')
        document = record['document']
        if not isinstance(document, str) or document not in documents:
            raise ValueError(f'{identifier}: unknown source document')
        doc = documents[document]
        page, end = record['page'], record.get('end_page', record['page'])
        if type(page) is not int or type(end) is not int or not 1 <= page <= end <= doc['physical_page_count']:
            raise ValueError(f'{identifier}: physical page range must be positive, ordered and within the PDF')
        for field in optional & record.keys():
            if field != 'end_page':
                text(record[field], field)
        locator = record.get('printed_locator', f'physical page {page}' + (f'–{end}' if end != page else ''))
        title = record.get('title', f"{doc['title']} ({doc['edition']}), {locator}")
        records[identifier] = dict(
            id=identifier, source_label=None, file=doc['file'], line=page, column=1,
            page=page, end_page=end, kind='external', environment='pdf-locator',
            provenance=dict(id=document, file=doc['file'], line=page, page=page, end_page=end,
                            source_sha256=doc['sha256'], edition=doc['edition']),
            status='source-unreviewed', document_id=document, source_document=doc,
            printed_locator=record.get('printed_locator'), source_registry='workflow/source-documents.json',
            metadata={'title': title}, description=f'Retained PDF locator: {title}. No mathematical transcription or acceptance is supplied.')
    return records
