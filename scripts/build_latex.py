#!/usr/bin/env python3
"""Build authored entry points into ignored output; exclude retained reference payloads."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def authored_source(root, source):
    path = Path(source)
    path = (path if path.is_absolute() else root / path).resolve()
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise ValueError('source must be inside the project root') from None
    parts = relative.parts
    authored = bool(parts) and parts[0] in {'draft', 'notes'}
    audit = len(parts) >= 4 and parts[0] == 'references' and parts[2] == 'audit'
    if not (authored or audit):
        raise ValueError('source must be an authored entry point under draft/, notes/, or references/<KEY>/audit/')
    if path.suffix != '.tex' or not path.is_file() or '\\documentclass' not in path.read_text():
        raise ValueError('source must be an existing .tex documentclass entry point')
    return path


def publish_main(pdf, destination):
    # Keep the last successful manuscript across failed builds and make clean.
    # A temporary sibling plus replace never exposes a partially copied PDF.
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.main-', suffix='.pdf', delete=False) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copyfile(pdf, temporary)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def build(root, bibliography=False, source=None):
    root = Path(root).resolve()
    if bibliography and source is not None:
        raise ValueError('--source and --bibliography cannot be combined')
    selected = authored_source(root, source) if source is not None else None
    if not shutil.which('latexmk'):
        raise ValueError('latexmk is missing; install a TeX distribution')
    runtime_dir = root / 'build/semantex'
    runtime_path = runtime_dir / 'semantex-runtime.tex'
    runtime_generated = False
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
        registry_path = root / 'workflow/document-contexts.json'
        registry_bytes = registry_path.read_bytes() if registry_path.exists() else None
        if registry_bytes is None and runtime_path.exists():
            raise ValueError('document-contexts registry is absent but a generated runtime remains; restore the registry or remove build/semantex/semantex-runtime.tex before a legacy build')
        from manuscript_graph import Graph
        from semantex_cache import load_graph
        graph = load_graph(Graph, root)
        if graph.errors:
            raise ValueError('\n'.join(graph.errors))
        # The generator must see the registry used for the checked graph.
        current_registry = registry_path.read_bytes() if registry_path.exists() else None
        if current_registry != registry_bytes:
            raise ValueError('document-contexts registry changed during graph validation; retry the build')
        if registry_bytes is not None:
            from semantex_runtime import write_runtime
            write_runtime(graph, registry_bytes, runtime_path)
            runtime_generated = True
        sources = []
        candidates = [selected] if selected is not None else sorted(
            (root / 'draft').rglob('*.tex'),
            key=lambda p: (p != root / 'draft/main.tex', str(p)))
        for p in candidates:
            if '\\documentclass' in p.read_text():
                p = authored_source(root, p)
                sources.append((p, root / 'build/latex' / p.relative_to(root).parent))
    env = os.environ.copy()
    tex_paths = ([str(runtime_dir)] if runtime_generated else []) + [str(root / 'preamble'), str(root)]
    env['TEXINPUTS'] = os.pathsep.join(tex_paths) + os.pathsep + env.get('TEXINPUTS', '')
    env['BIBINPUTS'] = str(root / 'references') + os.pathsep + str(root) + os.pathsep + env.get('BIBINPUTS', '')
    for source, output in sources:
        # Mirror source directories so editors can locate each resulting PDF.
        # TeX searches the working directory before TEXINPUTS. Do not permit a
        # local same-named file to shadow the freshly checked generated runtime.
        if runtime_generated and (source.parent / 'semantex-runtime.tex').exists():
            raise ValueError(f'{source.parent}: local semantex-runtime.tex would shadow the generated runtime')
        output.mkdir(parents=True, exist_ok=True)
        command = ['latexmk', '-pdf', '-nobibtexfudge', '-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error',
                   '-file-line-error', '-synctex=1', '-outdir=' + str(output), source.name]
        result = subprocess.run(command, cwd=source.parent, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        (output / 'build.log').write_text(result.stdout)
        (output / (source.stem + '.build.log')).write_text(result.stdout)
        if result.returncode:
            raise ValueError(f'LaTeX failed: {source.relative_to(root)}; see {output.relative_to(root)}/build.log\n' + result.stdout[-4000:])
        log = (output / (source.stem + '.log')).read_text(errors='replace')
        if 'There were undefined references' in log or 'There were undefined citations' in log:
            raise ValueError(f'unresolved references/citations in {source.relative_to(root)}')
        pdf = output / (source.stem + '.pdf')
        if not pdf.is_file() or pdf.stat().st_size == 0:
            raise ValueError(f'compiler produced no PDF for {source.relative_to(root)}')
        if source == root / 'draft/main.tex':
            publish_main(pdf, root / 'draft/main.pdf')
        print(pdf.relative_to(root))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bibliography', action='store_true')
    parser.add_argument('--source', help='build one authored draft/, notes/, or references/<KEY>/audit/ .tex entry point (relative to project root)')
    args = parser.parse_args()
    try:
        build(ROOT, args.bibliography, args.source)
    except (ValueError, OSError) as error:
        sys.exit('error: ' + str(error))
