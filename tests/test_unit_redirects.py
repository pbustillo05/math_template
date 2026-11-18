"""Hash-pinned editorial redirects retain provenance without granting acceptance."""
from pathlib import Path
import contextlib,copy,hashlib,io,json,shutil,subprocess,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from manuscript_graph import Graph,main
from semantex_runtime import generate_runtime,runtime_key
sha=lambda b:hashlib.sha256(b).hexdigest()
PACKAGE=Path(__file__).resolve().parents[1]/'preamble/semantex.sty'

class RedirectTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.old=r'''\begin{definition}\label[An object.]{def:old}Object.\end{definition}
\begin{lemma}\label[A claim.]{lem:old}Claim.\end{lemma}
\begin{proof}[label={prf:old},proves={lem:old},description={Uses object.}]\use{def:old}\end{proof}'''
  self.write('notes/old.tex',self.old);old=Graph(self.root);self.assertEqual(old.errors,[])
  self.write('workflow/history/old.tex',self.old);(self.root/'notes/old.tex').unlink()
  self.new=self.old.replace(':old',':new')
  self.write('notes/new.tex',self.new);self.write('migration/equivalence.md','Editorial equivalence inspected; no mathematical acceptance.\n')
  new=Graph(self.root);self.assertEqual(new.errors,[]);self.records={}
  for k in ['def:old','lem:old','prf:old']:
   n=old.nodes[k];target=k.replace(':old',':new')
   self.records[k]={'target':target,'canonical_unit_sha256':new.unit_identity_hash(target),'original':{
    'source_label':k,'kind':n['kind'],'file':'notes/old.tex','evidence_file':'workflow/history/old.tex',
    'source_sha256':sha(self.old.encode()),'unit_sha256':sha(old.source(k).encode()),
    'start':n['start'],'end':n['end'],'line':n['line'],'end_line':n['end_line'],'column':n['column'],
    'context':{'labels':{k:k}},'historical_status':'Provisional historical deduction','review_status':'unreviewed',
    **({'proof_of':'lem:old'} if k=='prf:old' else {})},
    'review':{'status':'reviewed-equivalent','reviewer':'test-reviewer','report':'migration/equivalence.md',
              'report_sha256':sha((self.root/'migration/equivalence.md').read_bytes()),'basis':'Inspected identical claim and proof modulo preserved version identities.'}}
  self.save()
 def write(self,f,t):
  p=self.root/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t)
 def save(self):self.write('workflow/unit-redirects.json',json.dumps({'schema_version':1,'redirects':self.records}))
 def graph(self):
  g=Graph(self.root);self.assertEqual(g.errors,[]);return g
 def cli(self,*args):
  out=io.StringIO()
  with contextlib.redirect_stdout(out):self.assertEqual(main(['--root',str(self.root),*args]),0)
  return json.loads(out.getvalue())
 def test_cli_and_graph_keep_canonical_content_original_identity_and_status(self):
  self.write('notes/use.tex',r'\begin{lemma}\label[Uses old.]{lem:consumer}\use{lem:old}\mention{prf:old}\end{lemma}')
  g=self.graph();self.assertEqual(g.edges['lem:consumer'],{'lem:new'})
  self.assertEqual(g.proofs,{'prf:new':'lem:new'});self.assertEqual(g.selected_proofs['lem:new'],'prf:new')
  self.assertEqual(g.status('lem:old'),'redirected');self.assertEqual(g.status('lem:new'),'unreviewed')
  self.assertEqual(g.source('lem:old'),g.source('lem:new'));self.assertEqual(g.fingerprint('lem:old'),g.fingerprint('lem:new'))
  get=self.cli('get','lem:old','--json')['node'];self.assertEqual(get['requested_id'],'lem:old');self.assertEqual(get['status'],'redirected');self.assertEqual(get['historical_review_status'],'unreviewed')
  loc=self.cli('locate','lem:old','--json');self.assertEqual(loc['file'],'notes/old.tex');self.assertEqual(loc['canonical_location']['file'],'notes/new.tex');self.assertTrue(loc['retired'])
  self.assertEqual([x['id'] for x in self.cli('deps','lem:old','--json')],['def:new'])
  self.assertIn('lem:consumer',[x['id'] for x in self.cli('rdeps','lem:old','--json')])
  self.assertEqual(self.cli('refs','prf:old','--json')[0]['target'],'def:new')
  back=self.cli('backrefs','lem:old','--json');self.assertEqual(back[0]['requested_target'],'lem:old')
  self.assertEqual(self.cli('fingerprint','lem:old','--json')['requested_id'],'lem:old')
  self.assertEqual(g.blocks('lem:old','prf:old'),g.blocks('lem:new','prf:new'))
  self.assertTrue(g.export()['unit_redirects'])
 def test_file_move_and_description_edit_do_not_stale_identity(self):
  before=self.graph();fp=before.fingerprint('lem:old')
  self.write('notes/new.tex',self.new.replace('A claim.','An improved retrieval description.').replace('Uses object.','Description improved.'))
  after=self.graph();self.assertEqual(after.fingerprint('lem:old'),fp)
  (self.root/'notes/new.tex').rename(self.root/'notes/moved.tex');g=self.graph()
  self.assertEqual(g.locate('lem:old')['canonical_location']['file'],'notes/moved.tex')
 def test_body_or_binding_change_rejects_registry_atomically(self):
  self.write('notes/new.tex',self.new.replace('Claim.','Different conclusion.'))
  g=Graph(self.root);self.assertTrue(any('hash is stale' in e for e in g.errors));self.assertEqual(g.unit_redirects,{})
  self.write('notes/new.tex',self.new+r'\begin{definition}\label[Other.]{def:other}Other.\end{definition}')
  self.write('workflow/reference-bindings.json',json.dumps({'files':{'notes/new.tex':{'def:new':'def:other'}}}))
  g=Graph(self.root);self.assertTrue(any('hash is stale' in e for e in g.errors))
 def test_chains_cycles_missing_targets_and_live_collisions(self):
  self.records['def:old']['target']='def:middle';self.records['def:middle']=copy.deepcopy(self.records['def:old']);self.records['def:middle']['target']='def:new'
  mid=self.records['def:middle'];text=self.old.replace('def:old','def:middle');self.write('workflow/history/mid.tex',text)
  # A separate retired source identity has its own exact evidence, not invented alias provenance.
  self.write('notes/mid.tex',text.replace('lem:old','lem:middle').replace('prf:old','prf:middle'));g=Graph(self.root)
  # It is not yet in the registry saved on disk, so the old source can be captured independently.
  n=g.nodes['def:middle'];mid['original'].update(source_label='def:middle',file='notes/mid.tex',evidence_file='workflow/history/mid.tex',source_sha256=sha(text.encode()),start=n['start'],end=n['end'],line=n['line'],end_line=n['end_line'],column=n['column'],unit_sha256=sha(g.source('def:middle').encode()),context={'labels':{'def:middle':'def:middle'}})
  (self.root/'notes/mid.tex').unlink();self.save();self.assertEqual(self.graph().aliases['def:old'],'def:new')
  self.records['def:middle']['target']='def:old';self.save();g=Graph(self.root);self.assertTrue(any('redirect cycle' in e for e in g.errors));self.assertNotIn('def:old',g.aliases)
  self.records['def:middle']['target']='def:missing';self.save();self.assertTrue(any('canonical target' in e for e in Graph(self.root).errors))
  self.records['def:middle']['target']='def:new';self.save();self.write('notes/collision.tex',r'\begin{definition}\label[Live.]{def:old}Live.\end{definition}')
  self.assertTrue(any('collides' in e for e in Graph(self.root).errors))
 def test_invalid_record_evidence_kind_review_and_span_rejected(self):
  baseline=copy.deepcopy(self.records)
  mutations=[('review','status','unreviewed'),('original','source_sha256','0'*64),('original','unit_sha256','0'*64),('original','kind','thm'),('original','column',99),('original','source_label','def:not-there'),('original','evidence_file','../outside.tex')]
  for group,key,value in mutations:
   with self.subTest(key=key,value=value):
    self.records=copy.deepcopy(baseline);self.records['def:old'][group][key]=value;self.save();g=Graph(self.root)
    self.assertTrue(any('unit-redirects.json' in e for e in g.errors));self.assertEqual(g.unit_redirects,{})
 def test_proof_redirect_must_preserve_attachment_and_selection(self):
  self.records['prf:old']['original']['proof_of']='def:old';self.save()
  self.assertTrue(any('attachment' in e or 'attached claim' in e for e in Graph(self.root).errors))
  self.records['prf:old']['original']['proof_of']='lem:old'
  self.write('notes/new.tex',self.new.replace(r'\begin{lemma}','% @proof: prf:old\n'+r'\begin{lemma}'))
  # Derive the pin using the reviewed resolution, before installing the revised registry.
  (self.root/'workflow/unit-redirects.json').unlink();g=Graph(self.root)
  self.records['lem:old']['canonical_unit_sha256']=g.unit_identity_hash('lem:new',resolver=lambda k:k.replace(':old',':new'))
  self.save();self.assertEqual(self.graph().selected_proofs['lem:new'],'prf:new')
 def test_historical_acceptance_not_transferred_and_release_still_fails(self):
  self.records['lem:old']['original']['review_status']='accepted';self.save()
  self.write('workflow/reviews.json',json.dumps({'schema_version':1,'records':{'lem:old':{'status':'accepted'}}}))
  g=self.graph();self.assertEqual(g.describe('lem:old')['historical_review_status'],'accepted');self.assertEqual(g.status('lem:new'),'unreviewed')
  (self.root/'draft').mkdir();(self.root/'notes/new.tex').rename(self.root/'draft/main.tex')
  g=self.graph();self.assertIn('lem:new: release requires current acceptance',g.release_errors('lem:old'))
  with contextlib.redirect_stdout(io.StringIO()):
   self.assertEqual(main(['--root',str(self.root),'check']),0)
  with self.assertRaisesRegex(ValueError,'current acceptance'):
   main(['--root',str(self.root),'check','--release','--target','lem:old'])
 def test_redirect_through_existing_same_frame_alias_and_collision(self):
  self.write('notes/new.tex',self.new.replace(r'\label[An object.]{def:new}',r'\label[An object.]{def:new}\label{def:live-alias}'))
  self.write('workflow/label-aliases.json',json.dumps({'schema_version':1,'files':{'notes/new.tex':{'def:live-alias':'def:new'}}}))
  (self.root/'workflow/unit-redirects.json').unlink();g=Graph(self.root);self.assertEqual(g.errors,[])
  self.records['def:old']['target']='def:live-alias';self.records['def:old']['canonical_unit_sha256']=g.unit_identity_hash('def:new');self.save()
  self.assertEqual(self.graph().aliases['def:old'],'def:new')
  self.records['def:live-alias']=copy.deepcopy(self.records['def:old']);self.records['def:live-alias']['target']='def:new';self.save()
  self.assertTrue(any('collides' in e for e in Graph(self.root).errors))
 def test_review_artifact_must_be_nonempty_and_hash_pinned(self):
  self.write('migration/equivalence.md','Changed editorial conclusion.')
  self.assertTrue(any('evidence hash mismatch' in e for e in Graph(self.root).errors))
  self.write('migration/equivalence.md','')
  for record in self.records.values():record['review']['report_sha256']=sha(b'')
  self.save();self.assertTrue(any('review report is empty' in e for e in Graph(self.root).errors))
 def test_runtime_retired_statement_and_proof_have_only_canonical_anchors(self):
  ctx={'schema_version':1,'contexts':{'ctx:main':{'file':'draft/main.tex','labels':{'def:new':'def:new','lem:new':'lem:new','prf:new':'prf:new'},'references':{'lem:local-old':'lem:old','prf:local-old':'prf:old'}}}}
  pre=r'''\documentclass{article}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amsthm,hyperref}
\usepackage{../preamble/semantex}
\newtheorem{lemma}{Lemma}\newtheorem{definition}{Definition}
\providecommand{\lemmaautorefname}{Lemma}\providecommand{\definitionautorefname}{Definition}
\input{../runtime.tex}
\begin{document}\SemanTeXContext{ctx:main}
'''
  (self.root/'notes/new.tex').unlink();self.write('draft/main.tex',pre+self.new+r' References: \mention{lem:local-old}; \mention{prf:local-old}; \mention{lem:old}; \mention{prf:old}.\end{document}')
  self.write('workflow/document-contexts.json',json.dumps(ctx));self.write('preamble/semantex.sty',PACKAGE.read_text())
  g=self.graph();runtime=generate_runtime(g,ctx);self.write('runtime.tex',runtime)
  self.assertIn('\\SemanTeXDeclareAliasKey{'+runtime_key('prf:old')+'}{'+runtime_key('prf:new')+'}',runtime)
  self.assertNotIn('\\SemanTeXDeclareExternalKey{'+runtime_key('lem:old')+'}',runtime)
  self.assertIn('\\SemanTeXDeclareExternalKey{'+runtime_key('lem:new')+'}',runtime)
  self.assertIn((self.root/'draft/main.tex').resolve().as_uri(),runtime)
  if not shutil.which('pdflatex') or not shutil.which('pdftotext'):self.skipTest('PDF tools unavailable')
  for _ in range(2):
   x=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=self.root/'draft',capture_output=True,timeout=40)
   self.assertEqual(x.returncode,0,x.stdout.decode(errors='replace')[-4000:])
  aux=(self.root/'draft/main.aux').read_text();log=(self.root/'draft/main.log').read_text()
  self.assertNotIn('multiply defined',log);self.assertNotIn('Unresolved reference',log)
  self.assertNotIn('There were undefined references',log)
  for identity in ['def:new','lem:new','prf:new']:
   self.assertEqual(aux.count('\\newlabel{semantex@'+runtime_key(identity)+'}'),1)
  self.assertNotIn(runtime_key('lem:old'),aux);self.assertNotIn(runtime_key('prf:old'),aux)
  text=subprocess.check_output(['pdftotext',str(self.root/'draft/main.pdf'),'-']).decode()
  self.assertIn('Proof of Lemma',text);self.assertNotIn('Unresolved',text)

if __name__=='__main__':unittest.main()
