import json,time,sys
from pathlib import Path
pkg=Path(__file__).resolve().parents[1];sys.path.insert(0,str(pkg))
from dotenv import load_dotenv
load_dotenv(pkg/'.env')
from verifier.online import verify
from verifier.citations import check_reference
from verifier.claims import source_for
from verifier.legal import check_legal_reference
cases=[json.loads(s) for s in (pkg/'demo/reference_cases.jsonl').read_text().splitlines()]
selected=[c for c in cases if c['id'] in ('puppet-1','puppet-2','puppet-3','valid-rr','retracted-lancet') or c['category'] in ('ngo-valid','legal-fake')]
results=[]
for case in selected:
 start=time.monotonic()
 r=check_legal_reference(case['reference'],case['metadata']) if case.get('domain')=='legal' else check_reference(case['reference'],case['metadata'])
 if r['status']=='VERIFIED' and r.get('doi'):
  source=source_for(r['doi']);r['source_scope']=source.get('scope');r['retraction']=source.get('retraction')
  if source.get('retraction')=='retracted':r['status']='RETRACTED'
 results.append({'id':case['id'],'category':case['category'],'expected':case['expected'],'result':r,'seconds':round(time.monotonic()-start,3)})
 (pkg/'demo/hybrid_reference_validation.json').write_text(json.dumps({'results':results,'method':'Current live resolver with independently prepared metadata; not an end-to-end extraction benchmark.'},indent=2))
 print(case['id'],r['status'],flush=True)
# One real LLM bibliography-linking smoke test, independent of the resolver's supplied metadata.
subset=[c for c in selected if c['id'] in ('puppet-1','puppet-2','puppet-3')]
text='References\n'+'\n\n'.join(c['reference'] for c in subset)
out=verify(text,domain='academic')
(pkg/'demo/hybrid_extraction_validation.json').write_text(json.dumps({'input':text,'case_ids':[c['id'] for c in subset],'results':out,'method':'Live OpenAI extraction plus publication lookup of three exact original-v1 entries; bibliography only.'},indent=2))
print('OpenAI original-v1 extraction',[(r['citation_status'],r['status']) for r in out],flush=True)
