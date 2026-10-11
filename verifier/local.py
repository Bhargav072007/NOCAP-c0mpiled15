"""Evidence assessment without network calls or generative APIs."""
import re,json,hashlib,time
from pathlib import Path
from datetime import datetime,timezone
from .parser import parse_document,split_bibliography
from .provenance import verify_captures,sha256_file
from .data import data_checks
from .quantum import prioritize

class InputError(ValueError):pass

def normalize(text):return ' '.join(re.findall(r'\w+',text.casefold()))

def finding(check,status,reason,**extra):
    return {'check':check,'status':status,'reason':reason,'needs_human_review':status!='VERIFIED',**extra}

def references_in(text):
    _,bib=split_bibliography(text)
    if not bib:return []
    bib=bib.lstrip()
    body=(bib.split('\n',1)[1] if '\n' in bib else '').split('\nExtracted tables')[0]
    # Numbered entries may wrap; otherwise blank-separated entries are required.
    if re.search(r'(?m)^\s*\[\d+\]',body):
        blocks=re.split(r'(?m)^\s*\[\d+\]\s*',body)
        return [re.sub(r'\s+',' ',b).strip() for b in blocks if b.strip()]
    return [re.sub(r'\s+',' ',b).strip() for b in re.split(r'\n\s*\n',body) if b.strip()]

def check_reference(ref,catalog):
    matches=[r for r in catalog if normalize(ref) in {normalize(x) for x in [r.get('reference',''),*r.get('aliases',[])]}]
    if len(matches)!=1:return finding('A','NEEDS_REVIEW','No unique local catalog record; absence is not fabrication',citation=ref)
    record=matches[0]
    if not record.get('source_url') or not record.get('reviewed'):
        return finding('A','NEEDS_REVIEW','Local record lacks reviewed provenance',citation=ref,record_id=record['id'])
    verdict=record.get('status','NEEDS_REVIEW')
    if verdict not in ('VERIFIED','MISMATCH','NOT_FOUND','RETRACTED','NEEDS_REVIEW'):raise InputError('Invalid catalog status')
    return finding('A',verdict,'Matches explicitly reviewed local evidence record; catalog authority is supplied, not independently established',citation=ref,record_id=record['id'],source_url=record['source_url'],basis=record.get('basis',''),assessment_kind='catalog corroboration')

def assess_claim(item,sources):
    claim=item.get('claim','');source=sources.get(item.get('source_id'))
    if not claim:raise InputError('Claim text required')
    if not source:return finding('B','NEEDS_REVIEW','No linked local source supplied',claim=claim)
    text=source.get('text','');quote=item.get('quote','')
    if not quote or quote not in text:return finding('B','NEEDS_REVIEW','Evidence quote missing or not an exact source substring',claim=claim)
    # Exact assertion corroboration only; no pretend semantic inference from token overlap.
    exact=normalize(claim)==normalize(quote)
    ready=bool(source.get('identity_reviewed') and source.get('source_url'))
    return finding('B','VERIFIED' if exact and ready else 'NEEDS_REVIEW',
        'Exact assertion occurs in identity-reviewed source; underlying truth still requires data checks' if exact and ready else 'Quote located; semantic entailment or source identity needs human review',
        claim=claim,source_id=source['id'],quote=quote,source_sha256=hashlib.sha256(text.encode()).hexdigest(),source_url=source.get('source_url'),assessment_kind='exact textual corroboration')

def validate(context):
    if not isinstance(context,dict) or not context.get('org_id') or not context.get('project_id'):raise InputError('org_id/project_id required')
    for kind in ('datasets','figures','captures','sources','catalog'):
        entries=context.get(kind,[])
        if not isinstance(entries,list) or any(not isinstance(e,dict) or not isinstance(e.get('id'),str) or not e['id'] for e in entries):raise InputError('Invalid '+kind+' entries')
        if len({e['id'] for e in entries})!=len(entries):raise InputError('Duplicate '+kind+' IDs')
        for entry in entries:
            if kind in ('datasets','figures','captures'):
                if entry.get('org_id')!=context['org_id'] or entry.get('project_id')!=context['project_id']:raise InputError('Evidence outside declared scope')
                if not entry.get('path') or not Path(entry['path']).is_file():raise InputError('Evidence file missing')
            if kind=='sources' and not isinstance(entry.get('text'),str):raise InputError('Source text required')
    for kind in ('claims','support_claims'):
        if not isinstance(context.get(kind,[]),list) or any(not isinstance(c,dict) or not isinstance(c.get('claim'),str) or not c['claim'] for c in context.get(kind,[])):raise InputError('Invalid '+kind)
    if not isinstance(context.get('references',[]),list) or any(not isinstance(r,str) or not r.strip() for r in context.get('references',[])):raise InputError('Invalid references')

def analyse(text,*,context,document=None,quantum=True,shots=2048,seed=17):
    validate(context);start=time.monotonic();flags=[];issues=[]
    if not isinstance(text,str):raise InputError('Text required')
    references=list(dict.fromkeys(context.get('references',[])+references_in(text)))
    catalog=context.get('catalog',[]);sources={s['id']:s for s in context.get('sources',[])}
    flags.extend(check_reference(r,catalog) for r in references)
    for item in context.get('support_claims',[]):
        if item['claim'] not in text:raise InputError('Support claim absent from manuscript')
        flags.append(assess_claim(item,sources))
    captures=context.get('captures',[]);datasets=context.get('datasets',[]);figures=context.get('figures',[]);claims=context.get('claims',[])
    for claim in claims:
        if claim['claim'] not in text:raise InputError('Data claim absent from manuscript')
    provenance=verify_captures(captures,context.get('public_keys',{}),org_id=context['org_id'],project_id=context['project_id'],chain_starts=context.get('chain_starts'),expected_heads=context.get('expected_heads'))
    # Every supplied capture is checked, even when no claim links to it.
    flags.extend(finding('C','VERIFIED' if r['valid'] else 'DATA_MISMATCH' if r['status'] in ('TAMPERED_FILE','TAMPERED_RECORD','BAD_SIGNATURE','BROKEN_CHAIN','SCOPE_MISMATCH') else 'UNSIGNED_DATA','Capture signature/file/chain assessment',capture_id=id,evidence=r) for id,r in provenance.items())
    flags.extend(data_checks(text,claims,datasets,figures,captures,provenance,org_id=context['org_id'],project_id=context['project_id']))
    inventory=[]
    for dataset in datasets:
        from .statistics import rows_for
        linked=[c for c in claims if c.get('dataset_id')==dataset['id']]
        try:
            rows=rows_for(dataset['path']);columns=sorted({k for row in rows for k in row})
            flags.append(finding('C','NEEDS_REVIEW' if not linked else 'VERIFIED','Dataset parsed; row/column inventory is not statistical verification',dataset_id=dataset['id'],rows=len(rows),columns=columns,assessment_kind='format only'))
            inventory.append({'id':dataset['id'],'sha256':sha256_file(dataset['path']),'rows':len(rows),'columns':columns,'linked_claims':len(linked)})
        except (ValueError,OSError,TypeError) as exc:flags.append(finding('C','NEEDS_REVIEW','Dataset parsing failed: '+str(exc),dataset_id=dataset['id']))
    for source in sources.values():
        if not any(c.get('source_id')==source['id'] for c in context.get('support_claims',[])):flags.append(finding('B','NEEDS_REVIEW','Source supplied but no explicit claim/quote linked',source_id=source['id']))
    claimed_columns={(c.get('dataset_id'),c.get('column')) for c in claims}
    for d in inventory:
        d['unassessed_columns']=[c for c in d['columns'] if (d['id'],c) not in claimed_columns]
        if d['unassessed_columns']:issues.append('Dataset '+d['id']+' has columns without explicit assessment links: '+', '.join(d['unassessed_columns']))
    # Never silently pass arbitrary prose or automatically inferred methodological choices.
    body,_=split_bibliography(text)
    checked={c['claim'] for c in claims+context.get('support_claims',[])}
    remaining=[s.strip() for s in re.split(r'(?<=[.!?])\s+|\n',body) if s.strip() and s.strip() not in checked]
    if remaining:issues.append('Unlinked manuscript statements require human review; automatic semantic/data linking is not implemented')
    if not references:issues.append('No reference entries provided/extracted; citation coverage is incomplete')
    if not context.get('support_claims'):issues.append('No explicit source-support claims supplied')
    if not captures:issues.append('No signed captures supplied')
    for table in (document or {}).get('tables',[]):flags.append(finding('C','NEEDS_REVIEW','Extracted table needs an explicit dataset/method link',table_id=table['id']))
    mapped={str(Path(f['path']).resolve()) for f in figures}
    for asset in (document or {}).get('figures',[]):
        if str(Path(asset['path']).resolve()) not in mapped:flags.append(finding('C','UNSIGNED_DATA','Extracted figure has no linked signed original',figure_id=asset['id']))
    issues.extend((document or {}).get('warnings',[]))
    for i,f in enumerate(flags):f['flag_id']=f'finding_{i:05d}'
    counts={s:sum(f['status']==s for f in flags) for s in sorted({f['status'] for f in flags})}
    return {'schema_version':'local-quantum-1.0','status':'needs_review' if issues or any(f['needs_human_review'] for f in flags) else 'checks_completed','flags':flags,'provenance':provenance,'dataset_inventory':inventory,'issues':issues,'coverage':{'reference_entries':len(references),'catalog_records':len(catalog),'sources_supplied':len(sources),'explicit_source_claims':len(context.get('support_claims',[])),'explicit_data_claims':len(claims),'unlinked_statement_count':len(remaining),'unlinked_statements':remaining,'automatic_semantic_verification':False},'input_inventory':{kind:[{'id':e['id'],'sha256':sha256_file(e['path']) if e.get('path') else hashlib.sha256(json.dumps(e,sort_keys=True).encode()).hexdigest()} for e in context.get(kind,[])] for kind in ('catalog','sources','datasets','captures','figures')},'summary':counts,'quantum':prioritize(flags,shots,seed) if quantum else {'enabled':False},'network_requests':0,'human_approval_required':True,'elapsed_seconds':round(time.monotonic()-start,3),'checked_at':datetime.now(timezone.utc).isoformat()}

def analyse_document(path,*,context,asset_dir=None,**kwargs):
    document=parse_document(path,asset_dir=asset_dir)
    return analyse(document['text'],context=context,document=document,**kwargs)

def verify(text,*,context=None,**kwargs):
    return analyse(text,context=context or {'org_id':'local','project_id':'local'},**kwargs)['flags']
