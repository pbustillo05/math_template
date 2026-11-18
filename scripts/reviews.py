#!/usr/bin/env python3
"""Record real independent reports and accept only fresh, complete support."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from manuscript_graph import Graph, ROLES, safe_path
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    author = sub.add_parser('author', help='record the actual author; does not imply acceptance')
    author.add_argument('label')
    author.add_argument('identity')
    record = sub.add_parser('record', help='attach a report actually produced by the named reviewer')
    record.add_argument('label')
    record.add_argument('--role', choices=sorted(ROLES), required=True)
    record.add_argument('--reviewer', required=True)
    record.add_argument('--verdict', choices=['pass', 'needs-repair', 'unresolved', 'clear-for-review', 'found'], required=True)
    record.add_argument('--report', required=True)
    record.add_argument('--fingerprint', required=True, help='fingerprint reviewed, copied from the report; never silently renewed')
    accept = sub.add_parser('accept', help='after reading all reports, attempt acceptance of a single unit')
    accept.add_argument('label')
    args = parser.parse_args()
    update_review(ROOT, args)


def update_review(root, args):
    directory = root / 'build/semantex'
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'reviews.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return update_locked(root, args)


def update_locked(root, args):
    from semantex_cache import load_graph
    graph = load_graph(Graph, root)
    if graph.errors:
        raise ValueError('\n'.join(graph.errors))
    if args.label not in graph.nodes:
        raise ValueError('unknown mathematical label')
    path = root / 'workflow/reviews.json'
    data = json.loads(path.read_text())
    entry = data['records'].setdefault(args.label, {'status': 'unreviewed', 'reviews': []})
    if args.command == 'author':
        entry['author'] = args.identity
        entry['status'] = 'unreviewed'
    elif args.command == 'record':
        report = safe_path(root, args.report)
        if args.fingerprint != graph.fingerprint(args.label):
            raise ValueError('report fingerprint is stale; review the changed support rather than updating a hash')
        if args.role == 'proof-verifier' and args.reviewer == entry.get('author'):
            raise ValueError('the author cannot be the independent proof verifier')
        report_bytes = report.read_bytes()
        if args.fingerprint not in report_bytes.decode('utf-8'):
            raise ValueError('the report must state the exact reviewed fingerprint')
        entry['reviews'] = [r for r in entry['reviews'] if r['role'] != args.role]
        entry['reviews'].append({'role': args.role, 'reviewer': args.reviewer, 'verdict': args.verdict,
                                 'fingerprint': args.fingerprint, 'report': args.report,
                                 'report_sha256': hashlib.sha256(report_bytes).hexdigest()})
        entry['status'] = 'unreviewed'
    else:
        entry['status'] = 'accepted'
        graph.records = data['records']
        if graph.status(args.label) != 'accepted':
            raise ValueError('acceptance failed: missing author, independent roles, fresh reports, evidence, attached proof or accepted prerequisites')
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            json.dump(data, output, indent=2)
            output.write('\n')
            output.flush()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    print(args.label + ': ' + entry['status'])


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        sys.exit('error: ' + str(error))
