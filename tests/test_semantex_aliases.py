"""Explicit same-frame aliases preserve native navigation and logical ownership."""
from pathlib import Path
import contextlib
import io
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from manuscript_graph import Graph, main


class AliasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'notes').mkdir()
        (self.root / 'workflow').mkdir()

    def write(self, path, text):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)

    def registry(self, maps, file='notes/source.tex'):
        self.write('workflow/label-aliases.json', json.dumps({
            'schema_version': 1, 'files': {file: maps}}))

    def fixture(self):
        self.write('notes/source.tex', r'''\begin{definition}
\label[A first definition.]{def:primary}
\label[A historical description of that definition.]{def:alias}
An object.
\end{definition}
% @proof: current-prf:alias
\begin{lemma}\label[A claim.]{lem:primary}
\label[The same claim.]{lem:alias}
The claim.
\end{lemma}
\begin{proof}[label={prf:primary},proves={lem:alias},description={Uses the defined object.}]
\phantomsection\label[A native proof label.]{current-prf:alias}
\use{def:alias}\mention{lem:alias}
\end{proof}
''')
        self.registry({'def:alias': 'def:primary', 'lem:alias': 'lem:primary',
                       'current-prf:alias': 'prf:primary'})

    def graph(self):
        graph = Graph(self.root)
        self.assertEqual(graph.errors, [])
        return graph

    def cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(['--root', str(self.root), *args]), 0)
        return json.loads(out.getvalue())

    def test_proof_alias_keeps_one_attachment_and_every_declared_id(self):
        self.fixture()
        graph = self.graph()
        self.assertEqual(len(graph.nodes), 3)
        self.assertEqual(graph.proofs, {'prf:primary': 'lem:primary'})
        self.assertEqual(graph.selected_proofs, {'lem:primary': 'prf:primary'})
        self.assertEqual(graph.aliases['current-prf:alias'], 'prf:primary')
        self.assertEqual(graph.declarations_by_file['notes/source.tex']['current-prf:alias'], 'current-prf:alias')
        self.assertEqual(graph.native_aliases_by_file['notes/source.tex']['current-prf:alias'], 'prf:primary')
        self.assertEqual(graph.edges['lem:primary'], {'def:primary'})
        self.assertEqual(graph.blocks('lem:alias'), graph.blocks('lem:primary'))
        self.assertEqual(graph.blocks('lem:alias', 'current-prf:alias'), graph.blocks('lem:primary'))
        self.assertEqual(graph.blocks('current-prf:alias'), graph.blocks('prf:primary'))
        self.assertEqual(graph.fingerprint('lem:alias'), graph.fingerprint('lem:primary'))
        occurrence = next(o for o in graph.occurrences if o['command'] == 'use')
        self.assertEqual(occurrence['original_target'], 'def:alias')
        self.assertEqual(occurrence['requested_target'], 'def:alias')
        self.assertEqual(occurrence['target'], 'def:primary')
        self.assertTrue(occurrence['dependency'])
        self.assertEqual(graph.references('def:alias', reverse=True)[0]['alias_location']['line'], 3)

    def test_public_cli_resolves_aliases_and_locate_keeps_alias_position(self):
        self.fixture()
        data = self.cli('get', 'lem:alias', '--json')
        self.assertEqual(data['node']['id'], 'lem:primary')
        self.assertEqual(data['node']['requested_id'], 'lem:alias')
        proof = self.cli('get', 'current-prf:alias', '--json')
        self.assertEqual(proof['node']['proof_of'], 'lem:primary')
        located = self.cli('locate', 'def:alias', '--json')
        self.assertEqual(located['id'], 'def:alias')
        self.assertEqual(located['canonical_id'], 'def:primary')
        self.assertEqual(located['line'], 3)
        self.assertEqual(located['canonical_location']['line'], 2)
        deps = self.cli('deps', 'lem:alias', '--json')
        self.assertEqual([x['id'] for x in deps], ['def:primary'])
        self.assertEqual(self.cli('fingerprint', 'lem:alias', '--json')['requested_id'], 'lem:alias')
        self.assertTrue(self.cli('backrefs', 'def:alias', '--json')[0]['dependency'])
        self.assertEqual(self.cli('why', 'lem:alias', 'def:alias', '--json')['path'], ['lem:primary', 'def:primary'])
        self.assertEqual(self.cli('refs', 'current-prf:alias', '--json')[0]['requested_target'], 'def:alias')

    def test_namespace_and_document_context_survive_moves(self):
        self.fixture()
        mapping = {'def:primary':'def:v1:primary','def:alias':'def:v1:alias',
                   'lem:primary':'lem:v1:primary','lem:alias':'lem:v1:alias',
                   'prf:primary':'prf:v1:primary','current-prf:alias':'prf:v1:alias'}
        self.write('workflow/label-namespaces.json', json.dumps({'files':{'notes/source.tex':mapping}}))
        legacy = self.graph()
        self.assertEqual(legacy.aliases['prf:v1:alias'], 'prf:v1:primary')
        aliases = legacy.native_aliases_by_file['notes/source.tex']
        record = {'file':'notes/source.tex','labels':mapping,'aliases':aliases,'references':{}}
        self.write('workflow/document-contexts.json', json.dumps({'schema_version':1,'contexts':{'ctx:version':record}}))
        path = self.root / 'notes/source.tex'
        path.write_text(r'\SemanTeXContext{ctx:version}' + '\n' + path.read_text())
        before = self.graph()
        (self.root/'notes/moved').mkdir()
        path.rename(self.root/'notes/moved/version.tex')
        after = self.graph()
        self.assertEqual(after.aliases, before.aliases)
        self.assertEqual(after.proofs, before.proofs)
        self.assertEqual(after.edges, before.edges)
        self.assertEqual(after.declarations_by_file['notes/moved/version.tex']['current-prf:alias'], 'prf:v1:alias')
        self.assertEqual(after.native_aliases_by_file['notes/moved/version.tex'], aliases)
        self.assertEqual(after.locate('prf:v1:alias')['file'], 'notes/moved/version.tex')

    def test_embedded_empty_alias_map_does_not_inherit_stale_path_map(self):
        self.fixture()
        self.write('workflow/document-contexts.json', json.dumps({'schema_version':1,'contexts':{'ctx:version':{'labels':{},'aliases':{},'references':{}}}}))
        path=self.root/'notes/source.tex';path.write_text(r'\SemanTeXContext{ctx:version}'+'\n'+path.read_text())
        graph=Graph(self.root)
        self.assertEqual(graph.native_aliases_by_file['notes/source.tex'], {})
        self.assertTrue(any('multiple principal' in e for e in graph.errors))

    def test_explicit_chain_flattens_without_adding_edges(self):
        self.write('notes/source.tex',r'\begin{theorem}\label[Primary.]{thm:p}\label[Alias one.]{cor:a}\label[Alias two.]{lem:b}Claim.\end{theorem}')
        self.registry({'cor:a':'thm:p','lem:b':'cor:a'})
        graph=self.graph()
        self.assertEqual(graph.aliases,{'cor:a':'thm:p','lem:b':'thm:p'})
        self.assertEqual(graph.edges,{'thm:p':set()})
        self.assertEqual(graph.describe('cor:a')['environment'],'theorem')

    def test_alias_description_does_not_change_mathematical_fingerprint(self):
        self.fixture();before=self.graph().fingerprint('lem:alias')
        path=self.root/'notes/source.tex';path.write_text(path.read_text().replace('A historical description of that definition.','A revised retrieval description.'))
        self.assertEqual(self.graph().fingerprint('lem:alias'),before)

    def test_descriptionless_alias_inherits_without_weakening_principal_rule(self):
        self.fixture()
        path=self.root/'notes/source.tex'
        path.write_text(path.read_text().replace(r'\label[A native proof label.]{current-prf:alias}',
                                                r'\label{current-prf:alias}').replace(
                                                r'\label[The same claim.]{lem:alias}',r'\label{lem:alias}'))
        graph=self.graph()
        self.assertEqual(graph.describe('lem:alias')['description'],'A claim.')
        self.assertTrue(graph.alias_declarations['lem:alias']['description_inherited'])
        self.assertEqual(graph.alias_declarations['lem:alias']['description'],'')
        self.assertEqual(graph.declarations_by_file['notes/source.tex']['current-prf:alias'],'current-prf:alias')
        path.write_text(path.read_text().replace(r'\label[A claim.]{lem:primary}',r'\label{lem:primary}'))
        self.assertTrue(any('add a description' in e for e in Graph(self.root).errors))

    def test_unregistered_secondary_label_still_fails(self):
        self.fixture();(self.root/'workflow/label-aliases.json').unlink()
        self.assertTrue(any('multiple principal' in e for e in Graph(self.root).errors))

    def test_cross_unit_alias_rejected(self):
        self.write('notes/source.tex',r'\begin{lemma}\label[First.]{lem:p}First.\end{lemma}\begin{lemma}\label[Second.]{lem:a}Second.\end{lemma}')
        self.registry({'lem:a':'lem:p'})
        graph=Graph(self.root)
        self.assertTrue(any('same actual semantic frame' in e for e in graph.errors))
        self.assertNotIn('lem:a',graph.aliases)

    def test_navigation_alias_rejected_and_equation_use_stays_error(self):
        self.write('notes/source.tex',r'\begin{lemma}\label[Claim.]{lem:p}\begin{equation}\label{current-eq:one}1=1\end{equation}\use{current-eq:one}\end{lemma}')
        graph=Graph(self.root)
        self.assertEqual(graph.nodes['current-eq:one']['kind'],'eq')
        self.assertTrue(any('only a navigation anchor' in e for e in graph.errors))
        self.registry({'current-eq:one':'lem:p'})
        self.assertTrue(any('cannot merge navigation' in e for e in Graph(self.root).errors))

    def test_cycle_and_missing_declarations_rejected(self):
        self.fixture();self.registry({'lem:alias':'lem:primary','lem:primary':'lem:alias'})
        self.assertTrue(any('alias cycle' in e for e in Graph(self.root).errors))
        self.registry({'def:absent':'def:primary'})
        self.assertTrue(any('alias declaration not found' in e for e in Graph(self.root).errors))
        self.registry({'def:alias':'def:absent'})
        self.assertTrue(any('alias target declaration not found' in e for e in Graph(self.root).errors))

    def test_declared_alias_collision_is_not_silently_merged(self):
        self.fixture()
        self.write('notes/z.tex',r'\begin{definition}\label[Different declaration.]{def:alias}Different.\end{definition}')
        self.assertTrue(any('duplicate node ID def:alias' in e for e in Graph(self.root).errors))
        (self.root/'notes/z.tex').unlink()
        self.write('workflow/label-namespaces.json',json.dumps({'files':{'notes/source.tex':{'def:primary':'def:same','def:alias':'def:same'}}}))
        self.assertTrue(any('duplicate node ID def:same' in e for e in Graph(self.root).errors))

    def test_markdown_links_resolve_alias_without_becoming_premises(self):
        self.fixture();self.write('notes/ledger.md',r'`\mention{lem:alias}`')
        graph=self.graph();links=[o for o in graph.occurrences if o.get('format')=='markdown']
        self.assertEqual(links[0]['target'],'lem:primary');self.assertFalse(links[0]['dependency'])
        self.write('notes/ledger.md',r'`\use{lem:alias}`')
        self.assertTrue(any('no mathematical owner' in e for e in Graph(self.root).errors))

    def test_optional_heading_titles_preserve_native_labels(self):
        self.write('notes/source.tex',r'''\chapter[Short chapter]{Long chapter}\label{chap:original}
\section[Short {section}]{Long section}\label{sec:original}
\subsection[Short subsection]{Long subsection}
\begin{lemma}[Optional theorem title]\label[Claim.]{lem:p}Claim.\end{lemma}''')
        graph=self.graph()
        self.assertEqual(graph.nodes['chap:original']['metadata']['title'],'Long chapter')
        self.assertEqual(graph.nodes['sec:original']['metadata']['title'],'Long section')
        self.assertEqual(graph.declarations_by_file['notes/source.tex']['lem:p'],'lem:p')


if __name__=='__main__':
    unittest.main()
