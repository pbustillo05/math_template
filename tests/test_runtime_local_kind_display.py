"""Actual semantic kinds survive shared theorem counters and historical identities."""
from pathlib import Path
import json,re,shutil,subprocess,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_unit_redirects as redirect_fixture
from manuscript_graph import Graph,SEMANTIC
from semantex_runtime import LOCAL_KIND_NAMES,local_kind_name,plan_contexts,generate_runtime,runtime_key
PACKAGE=Path(__file__).resolve().parents[1]/'preamble/semantex.sty'

class LocalKindDisplayTests(unittest.TestCase):
 def test_environment_authority_and_navigation_fallback(self):
  self.assertEqual(set(LOCAL_KIND_NAMES),SEMANTIC-{'proof','clause'})
  self.assertEqual(local_kind_name({'id':'thm:misleading','kind':'thm','environment':'definition'}),'Definition')
  self.assertEqual(local_kind_name({'id':'conj:historical','kind':'conj','environment':'theorem'}),'Theorem')
  for kind,environment in [('eq','lemma'),('sec','section'),('item','clause'),('prf','proof'),('def','anchor'),('unknown','unknown')]:
   self.assertIsNone(local_kind_name({'kind':kind,'environment':environment}))
  self.assertEqual(local_kind_name({'kind':'not','environment':'notation'}),'Notation')
  self.assertEqual(local_kind_name({'kind':'conv','environment':'convention'}),'Convention')


 @unittest.skipUnless(shutil.which('pdflatex') and shutil.which('pdftotext'),'TeX and Poppler required')
 def test_no_runtime_preserves_native_autoref_and_aux_proof_fallback(self):
  import tempfile
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);shutil.copy(PACKAGE,root/'semantex.sty')
   (root/'main.tex').write_text(r"""\documentclass{article}
\usepackage{amsmath,amsthm,hyperref,semantex}
\newtheorem{theorem}{Theorem}\newtheorem{definition}[theorem]{Definition}
\begin{document}
\begin{definition}\label[Object.]{def:x}Object.\end{definition}
\begin{proof}[label={prf:x},proves={def:x},description={Argument.}]Immediate.\end{proof}
\section{Heading}\label{sec:x}
\begin{equation}\label{eq:x}1=1\end{equation}
References: \mention{def:x}; \mention{prf:x}; \mention{sec:x}; \mention{eq:x}.
\end{document}
""")
   for _ in range(2):
    run=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=root,capture_output=True,text=True,timeout=40)
    self.assertEqual(run.returncode,0,run.stdout[-2000:])
   text=' '.join(subprocess.check_output(['pdftotext',str(root/'main.pdf'),'-'],text=True).split())
   self.assertIn('References: Theorem 1; Proof of Theorem 1; section 1; Equation 1.',text)

 @unittest.skipUnless(shutil.which('pdflatex') and shutil.which('pdftotext'),'TeX and Poppler required')
 def test_two_pass_shared_counters_aliases_redirects_and_fallback_keep_anchors(self):
  fixture=redirect_fixture.RedirectTests();fixture.setUp();self.addCleanup(fixture.doCleanups);root=fixture.root
  pre=r'''\documentclass{article}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amsthm,hyperref}
\usepackage{../preamble/semantex}
\newtheorem{theorem}{Theorem}
\newtheorem{definition}[theorem]{Definition}
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{proposition}[theorem]{Proposition}
\newtheorem{convention}[theorem]{Convention}
\newtheorem{notation}[theorem]{Notation}
\pdfcompresslevel=0 \pdfobjcompresslevel=0
\input{../runtime.tex}
\begin{document}
\section{Heading}\label{sec:heading}
'''
  content=fixture.new.replace('Uses object.}]','Uses object.}]'+r'\phantomsection\label{prf:alias}')+r'''
\begin{proposition}\label[A proposition.]{prop:p}Claim.\end{proposition}
\begin{convention}\label[A convention.]{conv:c}Convention.\end{convention}
\begin{notation}\label[A notation.]{not:n}Notation.\end{notation}
\begin{definition}\label[Prefix is not semantic type.]{thm:misleading}Object.\end{definition}
\begin{equation}\label{eq:e}1=1\end{equation}
\par Definition: \mention{def:old}.
\par Lemma: \mention{lem:old}.
\par Proposition: \mention{prop:p}.
\par Convention: \mention{conv:c}.
\par Notation: \mention{not:n}.
\par Misleading prefix: \mention{thm:misleading}.
\par Proof redirect: \mention{prf:old}. Proof alias: \mention{prf:alias}.
\par Heading: \mention{sec:heading}. Equation: \mention{eq:e}.
\end{document}
'''
  (root/'notes/new.tex').unlink();fixture.write('draft/main.tex',pre+content)
  fixture.write('preamble/semantex.sty',PACKAGE.read_text())
  fixture.write('workflow/label-aliases.json',json.dumps({'schema_version':1,'files':{'draft/main.tex':{'prf:alias':'prf:new'}}}))
  (root/'workflow/unit-redirects.json').unlink()
  full=(root/'draft/main.tex').read_text();fixture.write('draft/main.tex',full.replace('\\mention{def:old}', '\\mention{def:new}').replace('\\mention{lem:old}', '\\mention{lem:new}').replace('\\mention{prf:old}', '\\mention{prf:new}'))
  g=Graph(root);self.assertEqual(g.errors,[])
  for k,record in fixture.records.items():record['canonical_unit_sha256']=g.unit_identity_hash(record['target'])
  fixture.write('draft/main.tex',full);fixture.save();g=fixture.graph();registry,manifest=plan_contexts(g)
  for edit in manifest['files']:
   path=root/edit['file'];text=path.read_text()
   for ins in sorted(edit['insertions'],key=lambda x:x['offset'],reverse=True):text=text[:ins['offset']]+ins['text']+text[ins['offset']:]
   path.write_text(text)
  fixture.write('workflow/document-contexts.json',json.dumps(registry));g=fixture.graph();runtime=generate_runtime(g,registry)
  self.assertEqual(g.aliases['prf:alias'],'prf:new');self.assertEqual(g.aliases['prf:old'],'prf:new');self.assertEqual(g.selected_proofs['lem:new'],'prf:new')
  for native in ['eq:e','sec:heading']:
   self.assertNotIn('\\SemanTeXDeclareKindKey{'+runtime_key(native)+'}',runtime)
  self.assertIn('\\SemanTeXDeclareKindKey{'+runtime_key('thm:misleading')+'}{Definition}',runtime)
  def compile(text):
   fixture.write('runtime.tex',text)
   for _ in range(2):
    proc=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=root/'draft',capture_output=True,text=True,timeout=40)
    self.assertEqual(proc.returncode,0,proc.stdout[-5000:])
   log=(root/'draft/main.log').read_text();self.assertNotIn('multiply defined',log);self.assertNotIn('undefined references',log);self.assertNotIn('Unresolved reference',log)
   pdf=(root/'draft/main.pdf').read_bytes();self.assertTrue(re.search(rb'/Subtype\s*/Link',pdf))
   txt=subprocess.check_output(['pdftotext','-layout',str(root/'draft/main.pdf'),'-'],text=True)
   labels=[x for x in (root/'draft/main.aux').read_text().splitlines() if x.startswith('\\newlabel')]
   return ' '.join(txt.split()),labels,pdf
  fallback,old_labels,_=compile('\n'.join(x for x in runtime.splitlines() if not x.startswith('\\SemanTeXDeclareKindKey')))
  self.assertIn('Definition: Theorem 1.',fallback)
  fixed,labels,pdf=compile(runtime)
  for expected in ['Definition: Definition 1.','Lemma: Lemma 2.','Proposition: Proposition 3.','Convention: Convention 4.','Notation: Notation 5.','Misleading prefix: Definition 6.','Proof redirect: Proof of Lemma 2. Proof alias: Proof of Lemma 2.','Heading: section 1. Equation: Equation 1.']:
   self.assertIn(expected,fixed)
  self.assertEqual(old_labels,labels,'Runtime kind metadata must not change any saved number or anchor.')
  self.assertNotIn(runtime_key('prf:old'),'\n'.join(labels))
  self.assertEqual(sum(runtime_key('prf:alias') in l for l in labels),1)
  for anchor in ['theorem.1','theorem.2','theorem.3']:
   self.assertIn(anchor.encode(),pdf)

if __name__=='__main__':unittest.main()
