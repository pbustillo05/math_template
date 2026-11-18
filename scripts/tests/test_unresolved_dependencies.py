"""Missing historical versions stay traversable, explicit and release-blocking."""
from pathlib import Path
import json, sys, tempfile, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from manuscript_graph import Graph

class UnresolvedTests(unittest.TestCase):
    def fixture(self, root):
        (root/'draft').mkdir(); (root/'workflow').mkdir()
        (root/'draft/main.tex').write_text(r'''\begin{lemma}\label[An inherited conditional claim.]{lem:claim}Claim.\end{lemma}
\begin{proof}[label={prf:claim},proves={lem:claim},description={Uses a missing historical version.}]\use{lem:old}.\mention{lem:unregistered}.\end{proof}''')
        record = dict(original_label='lem:old', source_document='archived/version/note.tex',
                      source_sha256='a'*64, reason='The captured version does not identify this premise.',
                      candidates=[], status='unresolved', mathematical_statement=None)
        registry = {'schema_version':1, 'records':{'gap:version-test':record}}
        (root/'workflow/unresolved.json').write_text(json.dumps(registry))
        (root/'workflow/reference-bindings.json').write_text(json.dumps({
            'schema_version':1, 'files':{'draft/main.tex':{'lem:old':'gap:version-test'}}}))
        return registry

    def test_gap_is_a_dependency_but_has_no_mathematical_statement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root); graph=Graph(root)
            self.assertEqual(graph.edges['lem:claim'], {'gap:version-test'})
            self.assertEqual(graph.why('lem:claim','gap:version-test')['path'], ['lem:claim','gap:version-test'])
            self.assertEqual(graph.source('gap:version-test'), '')
            self.assertEqual(graph.blocks('gap:version-test'), [])
            self.assertEqual(graph.status('gap:version-test'), 'unresolved')
            self.assertTrue(any('unresolved reference lem:unregistered' in e for e in graph.errors))
            self.assertEqual(graph.describe('gap:version-test')['gap']['mathematical_statement'], None)
            self.assertTrue(any('gap:version-test: release requires current acceptance' in e
                                for e in graph.release_errors('lem:claim')))
            graph.records['gap:version-test']={'status':'accepted'}
            self.assertEqual(graph.status('gap:version-test'), 'unresolved')
            self.assertEqual(graph._status_one('gap:version-test',{}), 'unresolved')

    def test_gap_edits_invalidate_dependent_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); registry=self.fixture(root)
            before=Graph(root).fingerprint('lem:claim')
            registry['records']['gap:version-test']['reason']='A newly inspected edition is still missing.'
            (root/'workflow/unresolved.json').write_text(json.dumps(registry))
            self.assertNotEqual(before,Graph(root).fingerprint('lem:claim'))

    def test_registry_cannot_hide_a_real_statement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); registry=self.fixture(root)
            registry['records']['gap:version-test']['mathematical_statement']='Fabricated theorem.'
            (root/'workflow/unresolved.json').write_text(json.dumps(registry))
            graph=Graph(root)
            self.assertNotIn('gap:version-test',graph.nodes)
            self.assertTrue(any('no mathematical statement' in e for e in graph.errors))

    def test_gap_cannot_receive_a_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fixture(root)
            path=root/'draft/main.tex'
            path.write_text(path.read_text().replace('proves={lem:claim}', 'proves={gap:version-test}'))
            graph=Graph(root)
            self.assertTrue(any('invalid proof target gap:version-test' in e for e in graph.errors))

if __name__=='__main__': unittest.main()
