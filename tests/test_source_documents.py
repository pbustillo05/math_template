"""Pinned background PDF locators: identity, strict validation, CLI and links."""
from pathlib import Path
import contextlib,copy,hashlib,io,json,os,pickle,re,shutil,subprocess,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from manuscript_graph import Graph,main
from semantex_runtime import generate_runtime,plan_contexts,runtime_key
from semantex_sources import registered_pdf_locators
PACKAGE=Path(__file__).resolve().parents[1]/'preamble/semantex.sty'


def pdf_bytes(pages=3):
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Count '+str(pages).encode()+b' /Kids ['+b' '.join(f'{n+3} 0 R'.encode() for n in range(pages))+b'] >>']
    objects += [b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << >> >>' for _ in range(pages)]
    out=bytearray(b'%PDF-1.4\n');offsets=[0]
    for n,body in enumerate(objects,1):offsets.append(len(out));out.extend(f'{n} 0 obj\n'.encode()+body+b'\nendobj\n')
    start=len(out);out.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:out.extend(f'{offset:010d} 00000 n \n'.encode())
    out.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode());return bytes(out)


@unittest.skipUnless(shutil.which('pdfinfo'),'Poppler required for physical-page validation')
class SourceDocumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='source-documents-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.file='migration/references-background/book.pdf';self.write(self.file,pdf_bytes())
        self.registry={'schema_version':1,'documents':{'doc:book-2017':{'title':'Test Background','edition':'2017 retained fixture','file':self.file,'sha256':hashlib.sha256(pdf_bytes()).hexdigest()}},'locators':{'loc:book:lemma':{'document':'doc:book-2017','page':2,'end_page':3,'printed_locator':'Lemma 1.2, printed pp. 1–2'}}};self.save()
        self.write('notes/use.tex',r'\begin{lemma}\label[A consumer.]{lem:consumer}\use{loc:book:lemma}\mention{loc:book:lemma}\end{lemma}')
    def write(self,path,text):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(text if isinstance(text,bytes) else text.encode())
    def save(self):self.write('workflow/source-documents.json',json.dumps(self.registry))
    def graph(self):
        g=Graph(self.root);self.assertEqual(g.errors,[]);return g
    def cli(self,*args):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):self.assertEqual(main(['--root',str(self.root),*args]),0)
        return json.loads(out.getvalue())
    def invalid(self,substring):
        g=Graph(self.root);self.assertTrue(any('source-documents.json:' in e and substring in e for e in g.errors),g.errors)
        self.assertNotIn('loc:book:lemma',g.source_labels)
    def test_valid_lookup_cli_dependency_context_and_no_fabricated_text(self):
        g=self.graph();n=g.nodes['loc:book:lemma'];self.assertEqual(n['origin'],'retained');self.assertEqual(n['page'],2);self.assertEqual(n['end_page'],3)
        self.assertNotIn('bib_key',n);self.assertNotIn('doc:book-2017',g.papers)
        self.assertEqual(g.status(n['id']),'source-unreviewed');self.assertEqual(g.source(n['id']),'');self.assertEqual(g.blocks(n['id']),[])
        self.assertEqual(g.edges['lem:consumer'],{n['id']});self.assertEqual(g.proofs,{})
        self.assertEqual(self.cli('get',n['id'],'--json')['blocks'],[])
        loc=self.cli('locate',n['id'],'--json');self.assertEqual(loc['source_document']['edition'],'2017 retained fixture');self.assertTrue(loc['url'].endswith('/book.pdf#page=2'))
        self.assertEqual(len(self.cli('backrefs',n['id'],'--json')),2)
        self.assertEqual(self.cli('refs','lem:consumer','--json')[0]['target_location']['page'],2)
        bundle=self.cli('context','lem:consumer','--depth','1','--json');self.assertIn(n['id'],json.dumps(bundle));self.assertNotIn('latex transcription',json.dumps(bundle));source_unit=next(x for x in bundle['units'] if x['id']==n['id']);self.assertEqual(source_unit['provenance']['page'],2);self.assertEqual(source_unit['provenance']['edition'],'2017 retained fixture')
        self.assertEqual(len(self.cli('fingerprint',n['id'],'--json')['fingerprint']),64)
        self.write('workflow/reviews.json',json.dumps({'schema_version':1,'records':{n['id']:{'status':'accepted'}}}));self.assertEqual(self.graph().status(n['id']),'source-unreviewed')
    def test_document_move_retains_id_and_hash_with_new_location(self):
        before=self.graph();old=before.locate('loc:book:lemma');new='migration/background-moved/book.pdf';(self.root/new).parent.mkdir(parents=True);(self.root/self.file).rename(self.root/new);self.registry['documents']['doc:book-2017']['file']=new;self.save();after=self.graph()
        self.assertEqual(before.edges,after.edges);self.assertEqual(before.nodes.keys(),after.nodes.keys());self.assertEqual(after.locate('loc:book:lemma')['source_document']['sha256'],old['source_document']['sha256']);self.assertEqual(after.locate('loc:book:lemma')['file'],new)
    def test_pin_missing_file_and_non_pdf_rejected(self):
        original=copy.deepcopy(self.registry);self.registry['documents']['doc:book-2017']['sha256']='0'*64;self.save();self.invalid('hash mismatch')
        self.registry=original;self.save();(self.root/self.file).unlink();self.invalid('missing')
        self.write(self.file,b'Not PDF');self.registry['documents']['doc:book-2017']['sha256']=hashlib.sha256(b'Not PDF').hexdigest();self.save();self.invalid('not a PDF')
    def test_absolute_traversal_and_symlink_paths_rejected(self):
        for path in ['/tmp/book.pdf','../book.pdf','migration/../book.pdf','migration//book.pdf']:
            with self.subTest(path=path):self.registry['documents']['doc:book-2017']['file']=path;self.save();self.invalid('path')
        with tempfile.TemporaryDirectory() as outside:
            target=Path(outside)/'book.pdf';target.write_bytes(pdf_bytes());(self.root/'migration/link.pdf').symlink_to(target);self.registry['documents']['doc:book-2017']['file']='migration/link.pdf';self.save();self.invalid('path')
    def test_physical_page_range_strictly_validated(self):
        for page,end in [(0,1),(-1,1),(True,2),('2',3),(2,1),(2,4),(4,4),(2,True)]:
            with self.subTest(page=page,end=end):self.registry['locators']['loc:book:lemma'].update(page=page,end_page=end);self.save();self.invalid('page range')
    def test_collision_and_schema_reject_whole_registry(self):
        self.write('notes/collision.tex',r'\begin{definition}\label[Collision.]{loc:book:lemma}Object.\end{definition}');self.invalid('collides');(self.root/'notes/collision.tex').unlink()
        self.registry['locators']['loc:bad']={'document':'doc:missing','page':1};self.save();self.invalid('unknown source document')
        del self.registry['locators']['loc:bad'];self.registry['locators']['loc:book:lemma']['proof']='invented';self.save();self.invalid('only end_page')
    def test_duplicate_json_keys_and_edition_requirement(self):
        self.write('workflow/source-documents.json','{"schema_version":1,"schema_version":1,"documents":{},"locators":{}}');self.invalid('duplicate registry key')
        self.registry['documents']['doc:book-2017']['edition']='';self.save();self.invalid('edition')
    def test_locator_metadata_and_payload_participate_in_consumer_fingerprint(self):
        before=self.graph().fingerprint('lem:consumer');self.registry['locators']['loc:book:lemma']['page']=1;self.save();self.assertNotEqual(before,self.graph().fingerprint('lem:consumer'))
        prior=self.graph().fingerprint('lem:consumer');self.registry['documents']['doc:book-2017']['edition']='Corrected fixture edition';self.save();self.assertNotEqual(prior,self.graph().fingerprint('lem:consumer'))
        prior=self.graph().fingerprint('lem:consumer');new=pdf_bytes(4);self.write(self.file,new);self.registry['documents']['doc:book-2017']['sha256']=hashlib.sha256(new).hexdigest();self.save();self.assertNotEqual(prior,self.graph().fingerprint('lem:consumer'))
    def test_no_registry_and_pickled_graph_remain_compatible(self):
        (self.root/'workflow/source-documents.json').unlink();self.write('notes/use.tex',r'\begin{definition}\label[Plain.]{def:x}Object.\end{definition}');g=self.graph();old=pickle.loads(pickle.dumps(g));self.assertEqual(old.describe('def:x'),g.describe('def:x'));self.assertEqual(registered_pdf_locators(self.root,g.pdf_page_count),{})

    @unittest.skipUnless(shutil.which('pdflatex') and shutil.which('pdftotext'),'TeX and Poppler required')
    def test_actual_runtime_links_registered_and_legacy_pdf_pages(self):
        self.write('references/TST/paper.pdf',pdf_bytes());(self.root/'notes/use.tex').unlink()
        self.registry['documents']['doc:book-2017']['title']=r'Background \input{DO-NOT-READ}';self.save()
        self.write('preamble/semantex.sty',PACKAGE.read_bytes())
        legacy='loc:TST:references/TST/paper.pdf:3'
        tex=r'''\documentclass{article}
\usepackage[T1]{fontenc}\usepackage{amsmath,amsthm,hyperref}
\usepackage{../preamble/semantex}\newtheorem{lemma}{Lemma}
\pdfcompresslevel=0 \pdfobjcompresslevel=0
\input{../runtime.tex}
\begin{document}
\begin{lemma}\label[Consumer.]{lem:consumer}\use{loc:book:lemma}\end{lemma}
\cite[text={fixture page},file={paper.pdf},page=3]{TST}
Legacy locator: \mention{'''+legacy+r'''}.
\begin{thebibliography}{1}\bibitem{TST}Synthetic test fixture.\end{thebibliography}
\end{document}'''
        self.write('draft/main.tex',tex);g=self.graph();self.assertIs(g.nodes[legacy]['page'],True)
        registry,manifest=plan_contexts(g)
        for edit in manifest['files']:
            path=self.root/edit['file'];text=path.read_text()
            for ins in sorted(edit['insertions'],key=lambda x:x['offset'],reverse=True):text=text[:ins['offset']]+ins['text']+text[ins['offset']:]
            path.write_text(text)
        self.write('workflow/document-contexts.json',json.dumps(registry));g=self.graph();runtime=generate_runtime(g,registry);self.assertNotIn('page=True',runtime);self.assertNotIn(r'\input{DO-NOT-READ}',runtime);self.assertIn('\\SemanTeXDeclarePDFPageKey{'+runtime_key('loc:book:lemma')+'}{2}',runtime);self.assertIn('\\SemanTeXDeclarePDFPageKey{'+runtime_key(legacy)+'}{3}',runtime);self.write('runtime.tex',runtime)
        for _ in range(2):
            proc=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=self.root/'draft',capture_output=True,text=True,timeout=40);self.assertEqual(proc.returncode,0,proc.stdout[-3000:])
        pdf=(self.root/'draft/main.pdf').read_bytes();self.assertTrue(re.search(rb'/Subtype\s*/Link',pdf));self.assertTrue(re.search(rb'book\.pdf\)/S/GoToR/D\[1/Fit\]',pdf));self.assertTrue(re.search(rb'paper\.pdf\)/S/GoToR/D\[2/Fit\]',pdf));self.assertFalse(re.search(rb'/D\(page=',pdf));self.assertNotIn(b'#page=True',pdf)
        log=(self.root/'draft/main.log').read_text();self.assertNotIn('Unresolved reference',log);self.assertNotIn('undefined references',log)

if __name__=='__main__':unittest.main()
