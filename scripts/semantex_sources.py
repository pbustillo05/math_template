"""Read-only native/virtual environment labels for pinned reference sources."""
from __future__ import annotations
import hashlib
from pathlib import Path
import re
from urllib.parse import quote


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


def scan_source(path, root, key, mask, arg):
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

    def owner(offset):
        return next((f for f in reversed(complete) if f['start'] <= offset < f['end']), None)

    labels = []
    for m in re.finditer(r'\\label\s*\{([^{}]+)\}', text):
        label = m[1].strip()
        frame = owner(m.start())
        if frame is not None:
            frame['labels'].append(label)
        labels.append((label, m.start(), frame, False))
    for frame in complete:
        if not frame['labels']:
            env = re.sub(r'[^A-Za-z0-9_-]', '-', frame['environment'])
            label = f'auto:{path_id}:{env}:{frame["ordinal"]}'
            frame['labels'].append(label)
            labels.append((label, frame['start'], frame, True))
    references = []
    for m in re.finditer(r'\\(ref|eqref|autoref|cref|Cref|xref|dxref|hxref|hdxref)\*?\s*\{([^{}]+)\}', text):
        frame = owner(m.start())
        if not frame:
            continue
        for target in m[2].split(','):
            references.append({'owner': key + ':' + frame['labels'][0], 'target': key + ':' + target.strip(),
                               'dependency': m[1] in {'dxref', 'hdxref'}, 'file': relative,
                               'line': raw.count('\n', 0, m.start()) + 1})
    records = []
    for label, offset, frame, virtual in labels:
        start, end = (frame['start'], frame['end']) if frame else (offset, text.find('}', offset) + 1)
        record = {'id': key + ':' + label, 'bib_key': key, 'source_label': label,
                  'file': relative, 'line': raw.count('\n', 0, offset) + 1,
                  'column': offset - raw.rfind('\n', 0, offset),
                  'start_line': raw.count('\n', 0, start) + 1,
                  'end_line': raw.count('\n', 0, max(start, end - 1)) + 1,
                  'latex': raw[start:end], 'encoding': encoding, 'kind': 'external',
                  'status': 'source-unreviewed', 'virtual': virtual,
                  'environment': frame['environment'] if frame else None,
                  'mentions': [r for r in references if frame and r['owner'] == key + ':' + frame['labels'][0]]}
        if frame:
            following = next((f for f in complete if f['environment'] == 'proof' and f['start'] >= end and
                              not text[end:f['start']].strip()), None)
            if following:
                record['proof'] = {'file': relative, 'start_line': raw.count('\n', 0, following['start']) + 1,
                                   'end_line': raw.count('\n', 0, following['end'] - 1) + 1,
                                   'latex': raw[following['start']:following['end']]}
        records.append(record)
    return records, warnings


def index_sources(root, mask, arg):
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
            records, warnings = scan_source(path, root, key, mask, arg)
            diagnostics.extend(warnings)
            for record in records:
                labels.setdefault(record['id'], []).append(record)
            candidates.append((len(records), path.stat().st_size, path.relative_to(root).as_posix()))
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
