"""Build entry point generates and loads checked context bindings without authored inputs."""
from pathlib import Path
import importlib.util,json,os,re,shutil,subprocess,sys,tempfile,unittest
from unittest.mock import patch
HERE=Path(__file__).resolve();ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('runtime_build_under_test',HERE.parents[1]/'build_latex.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
import test_semantex_runtime as runtime_fixture
from semantex_runtime import runtime_key

@unittest.skipUnless(all(shutil.which(x) for x in ('latexmk','pdflatex','pdftotext','bibtex')), 'TeX and Poppler required')
class RuntimeBuildIntegrationTests(unittest.TestCase):
 def setUp(self):
  fixture=runtime_fixture.RuntimeTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
  self.fixture=fixture;self.root=fixture.root;self.registry=fixture.registry
  fixture.install_alias_fixture()
  shutil.copyfile(ROOT/'preamble/semantex.sty',self.root/'preamble/semantex.sty')
  main=self.root/'draft/main.tex';main.write_text(main.read_text().replace(r'\input{../runtime.tex}',''))
  self.runtime=self.root/'build/semantex/semantex-runtime.tex'
  self.pdf=self.root/'build/latex/draft/main.pdf'
  self.log=self.root/'build/latex/draft/main.log'
 def compile(self):
  builder.build(self.root)
  self.assertTrue(self.runtime.exists())
  self.assertFalse((self.root/'runtime.tex').exists())
  log=self.log.read_text()
  for bad in ['multiply defined','undefined references','Unresolved reference']:
   self.assertNotIn(bad,log)
  text=subprocess.check_output(['pdftotext','-layout',str(self.pdf),'-'],text=True)
  text=re.sub(r'([a-z])-\s*\n\s*([a-z])',r'\1\2',text)
  return ' '.join(text.split())
 def test_autoload_nested_versions_alias_proofs_context_restoration_and_regeneration(self):
  authored={p:p.read_bytes() for folder in ['draft','notes'] for p in (self.root/folder).rglob('*.tex')}
  first=self.compile()
  for expected in ['Local a: Lemma 1. Proof: Proof of Lemma 1.','Local child: Lemma 2. Proof: Proof of Lemma 2.','Local b: Lemma 3. Proof: Proof of Lemma 3.','Context restored: Lemma 1.','Host restored: Definition 1.','New version: Lemma 3. New proof: Proof of Lemma 3.','Alias a: Lemma 1. Alias proof: Proof of Lemma 1.']:
   self.assertIn(expected,first)
  aux=(self.pdf.with_suffix('.aux')).read_text()
  for n in ['a','b','child']:
   for native in ['lem:'+n+':x','lem:'+n+':old','prf:'+n+':x','current-prf:'+n+':x']:
    self.assertEqual(aux.count('\\newlabel{semantex@'+runtime_key(native)+'}'),1)
  old=self.runtime.read_bytes()
  self.registry['contexts']['ctx:a']['references'].update({'lem:new':'lem:child:x','prf:new':'prf:child:x'})
  (self.root/'workflow/document-contexts.json').write_text(json.dumps(self.registry))
  second=self.compile()
  self.assertNotEqual(old,self.runtime.read_bytes())
  self.assertIn('New version: Lemma 2. New proof: Proof of Lemma 2.',second)
  self.assertIn('Context restored: Lemma 1.',second)
  for p,b in authored.items():self.assertEqual(p.read_bytes(),b)
 def assert_refuses_without_compiler(self,pattern):
  old=self.runtime.read_bytes()
  # Graph construction is real. A compiler subprocess would prove stale data escaped the gate.
  with patch.object(builder.subprocess,'run',side_effect=AssertionError('compiler must not run')):
   with self.assertRaisesRegex(ValueError,pattern):builder.build(self.root)
  self.assertEqual(self.runtime.read_bytes(),old)
 def test_structural_error_refuses_even_when_previous_runtime_exists(self):
  self.compile();p=self.root/'notes/b.tex';p.write_text(p.read_text().replace(r'Claim.',r'Claim.\use{lem:missing}'))
  self.assert_refuses_without_compiler('unresolved reference')
 def test_stale_and_incomplete_context_registry_refuse_old_runtime(self):
  self.compile()
  registry=self.root/'workflow/document-contexts.json'
  self.registry['contexts']['ctx:b']['labels']['lem:never-declared']='lem:phantom'
  registry.write_text(json.dumps(self.registry))
  self.assert_refuses_without_compiler('disagree|declared|declaration')
  del self.registry['contexts']['ctx:b']['labels']['lem:never-declared']
  self.registry['diagnostic_status']='incomplete-do-not-apply';registry.write_text(json.dumps(self.registry))
  self.assert_refuses_without_compiler('incomplete diagnostic')
 def test_registry_change_during_graph_validation_refuses_unchecked_bindings(self):
  self.compile()
  from semantex_cache import load_graph
  def racing_graph(graph_type, root):
   graph=load_graph(graph_type, root)
   self.registry['contexts']['ctx:a']['references']['lem:new']='lem:child:x'
   (self.root/'workflow/document-contexts.json').write_text(json.dumps(self.registry))
   return graph
  with patch('semantex_cache.load_graph',side_effect=racing_graph):
   self.assert_refuses_without_compiler('registry changed during graph validation')
 def test_missing_registry_refuses_leftover_runtime(self):
  self.compile();(self.root/'workflow/document-contexts.json').unlink()
  self.assert_refuses_without_compiler('registry is absent.*generated runtime remains')
 def test_working_directory_runtime_shadow_is_rejected(self):
  self.compile();(self.root/'draft/semantex-runtime.tex').write_text(r'\begingroup\SemanTeXContext{ctx:shadow}\endgroup')
  self.registry['contexts']['ctx:shadow']={'file':'draft/semantex-runtime.tex','labels':{},'references':{}}
  (self.root/'workflow/document-contexts.json').write_text(json.dumps(self.registry))
  with patch.object(builder.subprocess,'run',side_effect=AssertionError('compiler must not run')):
   with self.assertRaisesRegex(ValueError,'shadow'):builder.build(self.root)
 def test_legacy_no_registry_build_has_no_runtime_requirement(self):
  with tempfile.TemporaryDirectory(prefix='legacy-build-') as directory:
   root=Path(directory);(root/'draft').mkdir();(root/'preamble').mkdir()
   shutil.copyfile(ROOT/'preamble/semantex.sty',root/'preamble/semantex.sty')
   (root/'draft/main.tex').write_text(r'''\documentclass{article}
\usepackage{amsmath,amsthm,hyperref,semantex}
\newtheorem{lemma}{Lemma}\providecommand{\lemmaautorefname}{Lemma}
\begin{document}\begin{lemma}\label[Legacy claim.]{lem:old}Claim.\end{lemma}
Legacy: \mention{lem:old}.\end{document}''')
   builder.build(root);self.assertFalse((root/'build/semantex/semantex-runtime.tex').exists())
   text=subprocess.check_output(['pdftotext',str(root/'build/latex/draft/main.pdf'),'-'],text=True)
   self.assertIn('Legacy: Lemma 1.',text)
 def test_bibliography_build_ignores_authored_registry_and_runtime(self):
  self.runtime.parent.mkdir(parents=True);self.runtime.write_text(r'\errmessage{STALE RUNTIME MUST NOT LOAD}')
  # The source verifier is a separate precondition: this fixture isolates bibliography build mechanics.
  refs=self.root/'references';refs.mkdir()
  (refs/'cite-all.tex').write_text(r'''\documentclass{article}
\begin{document}\nocite{*}\bibliographystyle{alpha}\bibliography{references}\end{document}''')
  (refs/'references.bib').write_text('@book{Fixture,author={Example, A.},title={Synthetic test fixture},year={2000}}\n')
  original={p:p.read_bytes() for p in refs.iterdir()}
  original_run=subprocess.run
  with patch('references.verify',return_value=[{'fixture':True}]), patch.object(builder.subprocess,'run',wraps=original_run) as calls:
   builder.build(self.root,bibliography=True)
  self.assertEqual(calls.call_count,1)
  self.assertNotIn(str(self.runtime.parent),calls.call_args.kwargs['env']['TEXINPUTS'].split(os.pathsep))
  self.assertTrue((self.root/'build/latex/references/cite-all.pdf').exists())
  self.assertEqual(self.runtime.read_text(),r'\errmessage{STALE RUNTIME MUST NOT LOAD}')
  for p,data in original.items():self.assertEqual(p.read_bytes(),data)

if __name__=='__main__':unittest.main()
