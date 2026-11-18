#!/usr/bin/env python3
"""Generate topic navigation without mutable mathematical file/line locators."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]


def render(root=ROOT):
    notes = root / 'notes'
    marker = '<!-- generated topic table -->'
    destination = notes / 'INDEX.md'
    intro = '# Notes index'
    if destination.exists():
        previous = destination.read_text()
        if marker not in previous:
            raise ValueError(f'{destination}: insert {marker} before the generated topic table')
        intro = previous.split(marker, 1)[0].rstrip()
    lines = [intro, '', marker, '',
        '| Topic | Current TeX files | Historical TeX files | Markdown files |',
        '| --- | ---: | ---: | ---: |',
    ]
    for directory in sorted(notes.iterdir()):
        if not directory.is_dir():
            continue
        tex = list(directory.rglob('*.tex'))
        historical = sum('history' in path.relative_to(directory).parts for path in tex)
        markdown = list(directory.rglob('*.md'))
        destination = directory / 'README.md'
        if not destination.exists():
            destination = directory
        link = destination.relative_to(notes).as_posix()
        lines.append(f'| [{directory.name}]({link}) | {len(tex)-historical} | {historical} | {len(markdown)} |')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='report whether saved navigation is current')
    args = parser.parse_args()
    target = ROOT / 'notes/INDEX.md'
    expected = render()
    if args.check:
        if not target.exists() or target.read_text() != expected:
            parser.exit(1, 'notes/INDEX.md needs regeneration\n')
        print('notes/INDEX.md is current')
        return
    if not target.exists() or target.read_text() != expected:
        target.write_text(expected)
    print('notes/INDEX.md')


if __name__ == '__main__':
    main()
