"""Acquisition boundaries, exact evidence, replay, real alpha collisions and migration."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import references as refs
from bibtex_utils import compute_alpha_labels


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'references').mkdir()
        for name in ('catalog', 'lock'):
            refs.write_json(self.root / 'references' / (name + '.json'), {'schema_version': 1, 'records': []})
        (self.root / 'references/references.bib').write_text('% Add papers with scripts/references.py add.\n')

    def paper(self, doi, title):
        identity = 'r' + refs.sha(doi.encode())[:16]
        paper = self.root / 'incoming' / identity
        (paper / 'metadata').mkdir(parents=True)
        data = ('@article{provider, author={Ada Alpha}, title={' + title + '}, year={2024}, doi={' + doi + '}}').encode()
        (paper / 'metadata/doi-response.bib').write_bytes(data)
        refs.write_json(paper / 'metadata/doi.json', {'doi': doi, 'sha256': refs.sha(data)})
        payload = b'%PDF-1.5\nsynthetic fixture'
        (paper / 'original.pdf').write_bytes(payload)
        refs.write_json(paper / 'metadata/source.json', {'sha256': refs.sha(payload)})
        (paper / 'audit').mkdir()
        (paper / 'audit/README.md').write_text('Unreviewed.')
        return {'id': identity, 'key': identity, 'doi': doi, 'relevance': title, 'source_gap': 'fixture'}, paper

    def tar(self, name, *, link=False, content=b'\\begin{lemma}Fixture\\end{lemma}'):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            info = tarfile.TarInfo(name)
            if link:
                info.type = tarfile.SYMTYPE
                info.linkname = '/tmp/outside'
                archive.addfile(info)
            else:
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
        return stream.getvalue()

    def test_archive_rejects_traversal_links_reserved_metadata_and_html(self):
        for data in [self.tar('../escape.tex'), self.tar('/absolute.tex'), self.tar('link', link=True),
                     self.tar('metadata/source.json'), b'<!doctype html><html>rate limited</html>']:
            with self.subTest(data=data[:25]), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    refs.extract_payload(data, Path(tmp))

    def test_safe_archive_preserves_exact_payload_bytes(self):
        data = self.tar('section/lemma.tex')
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            self.assertEqual(refs.extract_payload(data, dest), 'tar')
            self.assertEqual((dest / 'section/lemma.tex').read_bytes(), b'\\begin{lemma}Fixture\\end{lemma}')

    def test_unversioned_arxiv_is_rejected_before_network(self):
        with mock.patch.object(refs, 'download') as fetch:
            with self.assertRaisesRegex(ValueError, 'pin an arXiv version'):
                refs.acquire_arxiv('2301.12345', self.root)
            fetch.assert_not_called()

    def test_doi_replay_uses_exact_response_and_rejects_cache_tampering(self):
        data = b'@article{remote, author={Ada Alpha}, title={Example}, year={2024}}'
        with mock.patch.object(refs, 'download', return_value=(data, {'sha256': refs.sha(data)})) as fetch:
            one, info = refs.doi_metadata(self.root, '10.1234/demo')
            two, _ = refs.doi_metadata(self.root, '10.1234/demo')
            self.assertEqual(one, two)
            self.assertEqual(fetch.call_count, 1)
        payload = next((self.root / 'build/doi-metadata').glob('*.bib'))
        payload.write_bytes(data + b'\n')
        with self.assertRaisesRegex(ValueError, 'cache mismatch'):
            refs.doi_metadata(self.root, '10.1234/demo')
        self.assertEqual(refs.normalize_doi('https://doi.org/10.1234/DeMo'), '10.1234/demo')

    @unittest.skipUnless(shutil.which('pdflatex') and shutil.which('bibtex'), 'real alpha.bst needs TeX')
    def test_global_collision_migrates_payload_audit_and_authored_locators_without_network(self):
        with contextlib.redirect_stdout(io.StringIO()):
            refs.synchronize(self.root, self.paper('10.1234/one', 'A first paper'))
        first = refs.verify(self.root)[0]
        key = first['key']
        (self.root / 'draft').mkdir()
        authored = self.root / 'draft/claim.tex'
        authored.write_text(r'\cite[text={A result}, page=1]{' + key + '}\n' +
                            r'\hiddenuse{ref:' + key + ':main}')
        audit = self.root / 'references' / key / 'audit'
        (audit / 'README.md').write_text('See references/' + key + '/original.pdf')
        locator = f'loc:{key}:references/{key}/original.pdf:1'
        (audit / 'semantex.json').write_text(json.dumps(
            {'schema_version': 1, 'units': {f'ref:{key}:main': {'source': locator}}}))
        before = (self.root / 'references' / key / 'original.pdf').read_bytes()
        incoming = self.paper('10.1234/two', 'Z second paper')
        with self.assertRaisesRegex(ValueError, 'collision'):
            refs.synchronize(self.root, incoming)
        self.assertEqual(len(refs.verify(self.root)), 1)
        with mock.patch.object(refs, 'download', side_effect=AssertionError('network')), contextlib.redirect_stdout(io.StringIO()):
            refs.synchronize(self.root, incoming, apply_rekeys=True)
            refs.synchronize(self.root)
        records = refs.verify(self.root)
        self.assertEqual({r['key'] for r in records}, {'Alp24a', 'Alp24b'})
        migrated = next(r for r in records if r['doi'] == first['doi'])['key']
        self.assertIn(r'\cite[text={A result}, page=1]{' + migrated + '}', authored.read_text())
        self.assertIn('ref:' + migrated + ':main', authored.read_text())
        self.assertEqual((self.root / 'references' / migrated / 'original.pdf').read_bytes(), before)
        self.assertIn('references/' + migrated + '/', (self.root / 'references' / migrated / 'audit/README.md').read_text())
        manifest = json.loads((self.root / 'references' / migrated / 'audit/semantex.json').read_text())
        self.assertEqual(manifest['units'][f'ref:{migrated}:main']['source'],
                         f'loc:{migrated}:references/{migrated}/original.pdf:1')
        (self.root / 'references' / migrated / 'original.pdf').write_bytes(b'%PDF changed')
        with self.assertRaisesRegex(ValueError, 'retained source'):
            refs.verify(self.root)
        with self.assertRaisesRegex(ValueError, 'retained source'):
            refs.synchronize(self.root)

    @unittest.skipUnless(shutil.which('pdflatex') and shutil.which('bibtex'), 'real alpha.bst needs TeX')
    def test_real_alpha_handles_authors_accents_and_collision_suffixes(self):
        entries = [refs.canonical_bib(('@article{z, author={' + author + '}, title={' + title + '}, year={2024}}').encode(), key)
                   for key, author, title in [('one', 'Ada Alpha', 'A'), ('two', 'Ada Alpha', 'Z'),
                                              ('three', 'Émile Bêta and Ada Alpha', 'C')]]
        labels = compute_alpha_labels(entries)
        self.assertEqual(labels['one'], 'Alp24a')
        self.assertEqual(labels['two'], 'Alp24b')
        self.assertEqual(labels['three'], 'BA24')

    def test_collision_chain_rewrites_are_simultaneous(self):
        content = r'\cite{AB24a} AB24a:lemma references/AB24b/source.tex'
        self.assertEqual(refs.rewrite_tokens(content, {'AB24a': 'AB24b', 'AB24b': 'AB24c'}),
                         r'\cite{AB24b} AB24b:lemma references/AB24c/source.tex')

    def test_multi_entry_or_html_metadata_is_rejected(self):
        for data in [b'<html>error</html>', b'@article{a,title={a}}\n@book{b,title={b}}']:
            with self.assertRaises(ValueError):
                refs.canonical_bib(data, 'key')


if __name__ == '__main__':
    unittest.main()
