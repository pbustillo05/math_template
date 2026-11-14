#!/usr/bin/env python3
"""Conservative, non-executing reference views inspired by texphage's unfold stage."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from manuscript_graph import Graph, argument, masked
from semantex_sources import scan_source, source_text
ROOT = Path(__file__).resolve().parents[1]


def paper_graph(graph, key):
    nodes = [records[0] for label, records in sorted(graph.source_labels.items())
             if label.startswith(key + ':') and len(records) == 1]
    if key not in graph.papers:
        raise ValueError('unknown or unavailable paper: ' + key)
    ids = {n['id'] for n in nodes}
    edges = [dict(e, resolved=e['target'] in ids) for n in nodes for e in n.get('mentions', [])]
    # Alias labels can share an environment; deduplicate exact use sites.
    edges = [dict(item) for item in {json.dumps(e, sort_keys=True): e for e in edges}.values()]
    return {'schema_version': 1, 'paper': key, 'edge_direction': 'owner-mentions-target',
            'logical_inference': False, 'diagnostics': graph.papers[key].get('diagnostics', []),
            'nodes': [{k: v for k, v in n.items() if k not in {'latex', 'proof', 'mentions'}} for n in nodes],
            'edges': edges,
            'limitations': ['Literal source only; no macro expansion or conditional evaluation.',
                            'Ordinary references are mentions, not proof dependencies.',
                            'Cross-file split environments are not indexed as complete units.']}


def flatten(root, key, main):
    root = root.resolve()
    base = (root / 'references' / key).resolve()
    output, mapping, diagnostics = [], [], []
    total = [0]

    def emit(text, file=None, start=0):
        output.append(text)
        mapping.append({'start': total[0], 'end': total[0] + len(text), 'file': file, 'source_start': start})
        total[0] += len(text)
        if total[0] > 30_000_000:
            raise ValueError('flattened view exceeds 30 million characters')

    def visit(path, stack):
        path = path.resolve()
        if not path.is_relative_to(base) or not path.is_file() or {'audit', 'metadata'} & set(path.relative_to(base).parts):
            raise ValueError('include escapes retained paper or enters metadata/audit')
        if path in stack:
            diagnostics.append('include cycle: ' + path.relative_to(root).as_posix())
            emit('% [SemanTeX: cyclic include omitted from navigation view]\n')
            return
        if len(stack) > 100:
            raise ValueError('include depth exceeds 100')
        raw, _ = source_text(path)
        active = masked(raw)
        relative = path.relative_to(root).as_posix()
        records, warnings = scan_source(path, root, key, masked, argument)
        diagnostics.extend(warnings)
        # Virtual IDs are comments, never inserted executable labels in upstream TeX.
        events = {}
        for record in records:
            if record['virtual']:
                offset = sum(len(line) for line in raw.splitlines(keepends=True)[:record['start_line'] - 1])
                events.setdefault(offset, []).append(record['id'])
        includes = []
        for m in re.finditer(r'\\(input|include)\b', active):
            try:
                name, end = argument(active, m.end())
            except ValueError:
                diagnostics.append(f'{relative}: non-braced include left unchanged')
                continue
            if not re.fullmatch(r'[A-Za-z0-9_./ -]+', name) or '..' in Path(name).parts or Path(name).is_absolute():
                diagnostics.append(f'{relative}: dynamic/unsafe include left unchanged: {name}')
                continue
            candidate = path.parent / name
            if not candidate.suffix:
                candidate = candidate.with_suffix('.tex')
            if not candidate.is_file():
                candidate = base / name
                if not candidate.suffix:
                    candidate = candidate.with_suffix('.tex')
            if not candidate.is_file():
                diagnostics.append(f'{relative}: missing include left unchanged: {name}')
                continue
            includes.append((m.start(), end, candidate))
        # Insert virtual-label comments and inline supported includes in source order.
        cursor = 0
        for start, end, candidate in includes + [(len(raw), len(raw), None)]:
            for offset in sorted(o for o in events if cursor <= o < start):
                emit(raw[cursor:offset], relative, cursor)
                emit('\n% [SemanTeX virtual: ' + ', '.join(events[offset]) + ']\n')
                cursor = offset
            emit(raw[cursor:start], relative, cursor)
            if candidate:
                emit('\n% [SemanTeX begin include: ' + candidate.name + ']\n')
                visit(candidate, stack + [path])
                emit('\n% [SemanTeX end include]\n')
            cursor = end
        unsupported = re.findall(r'\\(?:import|subimport|subfile|InputIfFileExists|includeonly)\b', active)
        if unsupported:
            diagnostics.append(f'{relative}: unsupported inclusion/conditional controls left verbatim: ' + ', '.join(sorted(set(unsupported))))

    entry = (base / main).resolve()
    visit(entry, [])
    # Hash every retained TeX input so source/view divergence is explicit.
    hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(base.rglob('*.tex')) if p.is_file() and p.resolve().is_relative_to(base)
              and not {'audit', 'metadata'} & set(p.relative_to(base).parts)}
    return ''.join(output), {'schema_version': 1, 'paper': key, 'entry': entry.relative_to(root).as_posix(),
                             'input_sha256': hashes, 'segments': mapping, 'diagnostics': diagnostics,
                             'compile_equivalence_claimed': False}


def build_view(root, key, main):
    graph = Graph(root)
    data = paper_graph(graph, key)
    text, mapping = flatten(root, key, main)
    output = root / 'build/reference-views' / key
    output.mkdir(parents=True, exist_ok=True)
    (output / 'flattened.tex').write_text(text)
    (output / 'source-map.json').write_text(json.dumps(mapping, indent=2) + '\n')
    (output / 'graph.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'output': output.relative_to(root).as_posix(), 'environments': len(data['nodes']),
                      'diagnostics': mapping['diagnostics']}, indent=2))


def render_graph(data, format):
    if format == 'json':
        return json.dumps(data, indent=2)
    ids = {n['id']: 'n' + str(i) for i, n in enumerate(data['nodes'])}
    lines = ['digraph references {' if format == 'dot' else 'flowchart TD']
    for label, identifier in ids.items():
        escaped = label.replace('"', "'").replace('[', '(').replace(']', ')')
        lines.append(f'  {identifier} [label="{escaped}"];' if format == 'dot' else f'  {identifier}["{escaped}"]')
    for edge in data['edges']:
        if edge['resolved']:
            if format == 'dot':
                lines.append(f'  {ids[edge["owner"]]} -> {ids[edge["target"]]} [style={"solid" if edge["dependency"] else "dashed"}];')
            else:
                lines.append(f'  {ids[edge["owner"]]} {"-->" if edge["dependency"] else "-.->"} {ids[edge["target"]]}')
    if format == 'dot':
        lines.append('}')
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('key')
    parser.add_argument('--main', required=True, help='entry .tex file relative to paper directory; never guessed')
    args = parser.parse_args()
    try:
        build_view(ROOT, args.key, args.main)
    except (ValueError, OSError) as error:
        sys.exit('error: ' + str(error))
