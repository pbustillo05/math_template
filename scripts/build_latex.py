#!/usr/bin/env python3
"""Build authored entry points into ignored output; never compile in references/."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]


def build(root, bibliography=False):
    if not shutil.which('latexmk'):
        raise ValueError('latexmk is missing; install a TeX distribution')
    if bibliography:
        from references import verify
        records = verify(root)
        if not records:
            print('No retained papers yet; bibliography build skipped.')
            return
        source = root / 'references/cite-all.tex'
        # The compiler works on a scratch copy; retained evidence stays read-only.
        work = root / 'build/bibliography-source'
        work.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, work / source.name)
        shutil.copy2(root / 'references/references.bib', work / 'references.bib')
        sources = [(work / source.name, root / 'build/latex/references')]
    else:
        from manuscript_graph import Graph
        graph = Graph(root)
        if graph.errors:
            raise ValueError('\n'.join(graph.errors))
        from lean_status import check
        check(root)
        sources = []
        for p in sorted((root / 'draft').rglob('*.tex')):
            if '\\documentclass' in p.read_text():
                sources.append((p, root / 'build/latex' / p.relative_to(root).parent / p.stem))
    env = os.environ.copy()
    env['TEXINPUTS'] = str(root / 'preamble') + os.pathsep + str(root) + '//' + os.pathsep + env.get('TEXINPUTS', '')
    env['BIBINPUTS'] = str(root) + '//' + os.pathsep + env.get('BIBINPUTS', '')
    for source, output in sources:
        # main.pdf lives at build/latex/draft/main.pdf, sections at .../sections/example/.
        if source.name == 'main.tex':
            output = output.parent
        output.mkdir(parents=True, exist_ok=True)
        command = ['latexmk', '-pdf', '-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error',
                   '-file-line-error', '-synctex=1', '-outdir=' + str(output), source.name]
        result = subprocess.run(command, cwd=source.parent, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (output / 'build.log').write_text(result.stdout)
        if result.returncode:
            raise ValueError(f'LaTeX failed: {source.relative_to(root)}; see {output.relative_to(root)}/build.log\n' + result.stdout[-4000:])
        log = (output / (source.stem + '.log')).read_text(errors='replace')
        if 'There were undefined references' in log or 'There were undefined citations' in log:
            raise ValueError(f'unresolved references/citations in {source.relative_to(root)}')
        print((output / (source.stem + '.pdf')).relative_to(root))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bibliography', action='store_true')
    args = parser.parse_args()
    try:
        build(ROOT, args.bibliography)
    except (ValueError, OSError) as error:
        sys.exit('error: ' + str(error))
