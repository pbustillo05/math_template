"""Correspondence status must stale when either formal or informal support changes."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lean_status as lean


class LeanStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        for base in ('draft', 'lean', 'preamble'):
            (self.root / base).mkdir()
        self.tex = self.root / 'draft/unit.tex'
        self.tex.write_text(r'\begin{definition}\label{def:x}\leanref{def:x}{Project.x}{unchecked}A convention.\end{definition}')
        (self.root / 'lean/Claim.lean').write_text('def x := 1\n')
        (self.root / 'lean/correspondence.md').write_text('Exact statement matching evidence fixture.')
        self.record = {'entity': 'Project.x', 'file': 'lean/Claim.lean', 'status': 'unchecked',
                       'coverage': 'whole', 'correspondence': 'lean/correspondence.md'}
        self.save()

    def save(self):
        (self.root / 'lean/ledger.json').write_text(json.dumps({'schema_version': 1, 'records': {'def:x': self.record}}))

    def receipt(self):
        (self.root / 'lean/receipt.txt').write_text('synthetic receipt for freshness test')
        self.record['status'] = 'checked'
        self.record['receipt'] = {'entity': 'Project.x', 'file': 'lean/Claim.lean',
                                  'inputs_sha256': lean.snapshot(self.root, self.record, 'def:x'),
                                  'log': 'lean/receipt.txt',
                                  'log_sha256': lean.digest((self.root / 'lean/receipt.txt').read_bytes())}
        self.tex.write_text(self.tex.read_text().replace('{unchecked}', '{checked}'))
        self.save()

    def test_unchecked_mapping_is_optional_and_checked_mapping_is_pinned(self):
        self.assertEqual(lean.check(self.root), 1)
        self.receipt()
        self.assertEqual(lean.check(self.root), 1)
        (self.root / 'lean/Claim.lean').write_text('def x := 2\n')
        with self.assertRaisesRegex(ValueError, 'stale'):
            lean.check(self.root)

    def test_latex_statement_or_correspondence_edit_stales_receipt(self):
        self.receipt()
        self.tex.write_text(self.tex.read_text().replace('A convention.', 'A different convention.'))
        with self.assertRaisesRegex(ValueError, 'stale'):
            lean.check(self.root)
        self.tex.write_text(self.tex.read_text().replace('A different convention.', 'A convention.'))
        (self.root / 'lean/correspondence.md').write_text('Changed matching evidence')
        with self.assertRaisesRegex(ValueError, 'stale'):
            lean.check(self.root)

    def test_marker_must_be_attached_and_match_the_entity(self):
        self.tex.write_text(self.tex.read_text().replace('\\leanref', 'Some text.\\leanref'))
        with self.assertRaisesRegex(ValueError, 'follow'):
            lean.check(self.root)

    def test_partial_coverage_cannot_claim_checked(self):
        self.receipt()
        self.record['coverage'] = 'partial'
        self.save()
        with self.assertRaisesRegex(ValueError, 'stale'):
            lean.check(self.root)


if __name__ == '__main__':
    unittest.main()
