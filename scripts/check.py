#!/usr/bin/env python3
"""Portable project structure and literal LaTeX hygiene checks."""
from pathlib import Path
import re
import sys
from manuscript_graph import Graph, masked
from references import verify
ROOT = Path(__file__).resolve().parents[1]


def check():
    graph = Graph(ROOT)
    errors = list(graph.errors)
    declaration = re.compile(r'\\(?:newcommand|renewcommand|providecommand|DeclareMathOperator|newtheorem|usepackage|RequirePackage|def)\b')
    for base in ('draft',):
        for path in (ROOT / base).rglob('*.tex'):
            text = masked(path.read_text())
            # Main entry points may load the shared preamble and subfiles only.
            if path == ROOT / 'draft/main.tex':
                text = re.sub(r'\\usepackage\{(?:research|subfiles)\}', '', text)
            if declaration.search(text):
                errors.append(f'{path.relative_to(ROOT)}: put declarations/packages in preamble/')
    for label, record in graph.records.items():
        if record.get('status') == 'accepted' and graph.status(label) != 'accepted':
            errors.append(f'{label}: accepted review is stale')
    try:
        verify(ROOT)
    except (ValueError, OSError, KeyError) as error:
        errors.append(str(error))
    if errors:
        raise ValueError('\n'.join(errors))
    print(f'Checked {len(graph.nodes)} anchors, reference integrity and source structure.')


if __name__ == '__main__':
    try:
        check()
    except (ValueError, OSError) as error:
        sys.exit('error: ' + str(error))
