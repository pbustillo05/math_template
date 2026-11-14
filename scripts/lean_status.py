#!/usr/bin/env python3
"""Check invisible Lean correspondence; issue receipts for optional local Lean builds."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from manuscript_graph import Graph, argument, masked, safe_path
ROOT = Path(__file__).resolve().parents[1]
STATES = {'unchecked', 'partial', 'checked', 'stale'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(root, record, label):
    paths = [p for p in (root / 'lean').rglob('*.lean') if '.lake' not in p.parts]
    paths += [p for name in ('lean-toolchain', 'lakefile.toml', 'lakefile.lean', 'lake-manifest.json')
              if (p := root / 'lean' / name).is_file()]
    paths.append(safe_path(root, record['correspondence']))
    files = {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in sorted(set(paths))}
    graph = Graph(root)
    if graph.errors or label not in graph.nodes:
        raise ValueError('invalid LaTeX correspondence target')
    # Include the exact informal support, ignoring only invisible marker statuses.
    for node in sorted(graph.closure(label)):
        text = re.sub(r'\\leanref\s*\{[^{}]*\}\s*\{[^{}]*\}\s*\{[^{}]*\}', '', graph.source(node))
        files['unit:' + node] = digest(text.encode())
    for p in sorted((root / 'preamble').rglob('*')):
        if p.is_file() and p.suffix in {'.tex', '.sty'}:
            files[p.relative_to(root).as_posix()] = digest(p.read_bytes())
    lock = root / 'references/lock.json'
    if lock.is_file():
        files['references/lock.json'] = digest(lock.read_bytes())
    return digest(json.dumps(files, sort_keys=True).encode())


def markers(root):
    result = {}
    for base in ('draft', 'notes'):
        for path in (root / base).rglob('*.tex'):
            text = masked(path.read_text())
            for m in re.finditer(r'\\leanref\b', text):
                label, end = argument(text, m.end())
                entity, end = argument(text, end)
                status, end = argument(text, end)
                if label in result:
                    raise ValueError(f'duplicate Lean marker: {label}')
                # Immediate attachment, rather than a marker elsewhere in a proof.
                before = text[:m.start()].rstrip()
                if not before.endswith('\\label{' + label + '}'):
                    raise ValueError(f'Lean marker must follow its principal label: {label}')
                if status not in STATES or not re.fullmatch(r'[A-Za-z_][\w.\u0080-\uffff]*', entity):
                    raise ValueError(f'invalid Lean entity/status: {label}')
                result[label] = (entity, status)
    return result


def expected(root, record, label):
    status = record.get('status', 'unchecked')
    if status != 'checked':
        return status
    receipt = record.get('receipt', {})
    try:
        if (record.get('coverage') != 'whole' or not record.get('correspondence') or
                receipt.get('inputs_sha256') != snapshot(root, record, label) or
                receipt.get('entity') != record['entity'] or receipt.get('file') != record['file'] or
                receipt.get('log_sha256') != digest(safe_path(root, receipt['log']).read_bytes())):
            return 'stale'
    except (KeyError, OSError, ValueError):
        return 'stale'
    return 'checked'


def check(root):
    ledger = json.loads((root / 'lean/ledger.json').read_text())
    if ledger.get('schema_version') != 1:
        raise ValueError('unsupported Lean ledger schema')
    records = ledger['records']
    found = markers(root)
    graph = Graph(root)
    if graph.errors:
        raise ValueError('\n'.join(graph.errors))
    if set(found) != set(records):
        raise ValueError('Lean markers and ledger labels differ')
    for label, (entity, status) in found.items():
        node = graph.nodes.get(label)
        if not node or node['kind'] in {'prf', 'eq', 'sec', 'fig', 'tab', 'goal', 'obl'}:
            raise ValueError(f'Lean marker needs a principal mathematical label: {label}')
        record = records[label]
        source = safe_path(root, record['file'])
        if not source.is_relative_to((root / 'lean').resolve()) or source.suffix != '.lean':
            raise ValueError('Lean file must be under lean/')
        if record.get('status') not in STATES or record.get('coverage') not in {'whole', 'partial'}:
            raise ValueError('invalid Lean ledger status/coverage')
        if entity != record['entity'] or status != expected(root, record, label):
            raise ValueError(f'Lean correspondence mismatched or stale: {label}; update marker/ledger honestly')
    return len(found)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check')
    verify = sub.add_parser('verify', help='compile a whole correspondence and record a source-pinned receipt')
    verify.add_argument('label')
    verify.add_argument('--confirm-correspondence', action='store_true', required=True,
                        help='confirm that the documented LaTeX/Lean statement match was actually inspected')
    args = parser.parse_args()
    if args.command == 'check':
        print(f'Checked {check(ROOT)} optional Lean correspondences.')
        return
    ledger_path = ROOT / 'lean/ledger.json'
    ledger = json.loads(ledger_path.read_text())
    record = ledger['records'][args.label]
    if record['coverage'] != 'whole':
        raise ValueError('partial correspondence cannot be marked checked')
    source = safe_path(ROOT, record['file'])
    if not source.is_relative_to(ROOT / 'lean') or source.suffix != '.lean':
        raise ValueError('Lean source must be under lean/')
    entity = record['entity']
    if not re.fullmatch(r'[A-Za-z_][\w.\u0080-\uffff]*', entity):
        raise ValueError('invalid Lean entity')
    if not (ROOT / 'lean/lean-toolchain').is_file():
        raise ValueError('pin lean/lean-toolchain before verification')
    before = snapshot(ROOT, record, args.label)
    version = subprocess.check_output(['lake', 'env', 'lean', '--version'], cwd=ROOT / 'lean', text=True).strip()
    text = source.read_text() + '\n#check ' + entity + '\n#print axioms ' + entity + '\n#eval IO.println \"SEMANTEX_RECEIPT_END\"\n'
    run = subprocess.run(['lake', 'env', 'lean', '--stdin'], input=text, cwd=ROOT / 'lean',
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if run.returncode or 'SEMANTEX_RECEIPT_END' not in run.stdout or 'sorryAx' in run.stdout or 'declaration uses' in run.stdout and 'sorry' in run.stdout:
        raise ValueError('Lean failed or used sorry; no receipt issued:\n' + run.stdout)
    if before != snapshot(ROOT, record, args.label):
        raise ValueError('Lean sources changed while compiling; rerun on a stable snapshot')
    # A receipt is evidence, not a signature: reviewers must inspect the axiom list.
    path = ROOT / 'lean/receipts' / (args.label.replace(':', '-') + '.txt')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(version + '\n' + run.stdout)
    record['status'] = 'checked'
    record['receipt'] = {'inputs_sha256': before, 'entity': entity, 'file': record['file'], 'lean_version': version,
                         'log': path.relative_to(ROOT).as_posix(), 'log_sha256': digest(path.read_bytes())}
    ledger_path.write_text(json.dumps(ledger, indent=2) + '\n')
    print('Receipt recorded. Set the corresponding LaTeX marker to checked, then run make check. Inspect all listed axioms.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit('error: ' + str(error))
