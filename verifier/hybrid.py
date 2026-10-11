"""Local evidence, online A/B, OpenAI scientific review, then Qiskit review search."""
import hashlib
import json
import time
from . import local
from .parser import parse_document
from .quantum import prioritize

def analyse(text, *, context, mode='hybrid', judge=None, domain='mixed',
            quantum=True, shots=2048, seed=17, document=None,
            run_citations=True, extract_claims=True, scientific=True):
    if mode not in ('offline','hybrid'): raise local.InputError('mode must be offline or hybrid')
    if mode=='offline':
        return local.analyse(text,context=context,document=document,quantum=quantum,shots=shots,seed=seed)
    # Validate all explicit evidence before spending API calls.
    local.validate(context)
    if not isinstance(text,str): raise local.InputError('Text required')
    if domain not in ('mixed','academic','legal'): raise local.InputError('Invalid domain')
    for item in context.get('claims',[])+context.get('support_claims',[]):
        if item['claim'] not in text: raise local.InputError('Explicit claim absent from manuscript')
    start=time.monotonic()
    from .llm import get_judge, ModelError
    from .science import assess_science, dataset_integrity
    from .claims import judge_support
    from .auto_data import extract_data_claims
    from .online import verify as online_verify
    enriched=dict(context);enriched['claims']=list(context.get('claims',[]))
    api_flags=[];issues=[];extraction_audit=[];online=[];science_report=None;research_audit=[]
    queries=context.get('research_queries',[])
    if not isinstance(queries,list) or len(queries)>3 or any(not isinstance(q,str) or not 1<=len(q.strip())<=300 for q in queries):
        raise local.InputError('Invalid research_queries: at most three nonempty strings of at most 300 characters')
    source_map={};science_sources=list(context.get('sources',[]))
    for source in science_sources:
        for key in (source.get('citation'),source.get('doi')):
            if key: source_map[key]={**source,'identity_verified':bool(source.get('identity_reviewed'))}
    api_ready=True
    try: judge=judge or get_judge()
    except ModelError as exc:
        api_ready=False;issues.append(str(exc))
        api_flags.append(local.finding('API','NEEDS_REVIEW',str(exc),severity='medium',confidence=0))
    if api_ready and extract_claims:
        try:
            inferred,extraction_audit=extract_data_claims(text,context.get('datasets',[]),context.get('figures',[]),judge)
            enriched['claims'].extend(c for c in inferred if not any(c['claim']==e['claim'] and c.get('metric')==e.get('metric') for e in enriched['claims']))
        except ModelError as exc:
            issues.append(str(exc));api_flags.append(local.finding('C','NEEDS_REVIEW','Automatic data linking failed: '+str(exc)))
    if api_ready and run_citations:
        try:
            online=online_verify(text,judge=judge,domain=domain,sources=source_map)
            for result in online:
                a={**result,'check':'A','status':result['citation_status'],
                   'reason':result.get('citation_reason',result['reason']), 'origin':'live_publication_lookup'}
                a['needs_human_review']=a['status']!='VERIFIED';api_flags.append(a)
                if result.get('claim_status')!='NOT_CHECKED':
                    b={**result,'check':'B','status':'VERIFIED' if result['claim_status']=='SUPPORTED' else result['claim_status'],
                       'origin':getattr(judge,'provider','model')+'_source_comparison'}
                    b['needs_human_review']=b['status']!='VERIFIED';api_flags.append(b)
                source=result.get('source_evidence')
                if source and source.get('text'):
                    id='retrieved_'+hashlib.sha256((result.get('doi') or result['citation']).encode()).hexdigest()[:16]
                    if id not in {s['id'] for s in science_sources} and not any(
                        s.get('text')==source['text'] or (result.get('doi') and s.get('doi')==result['doi']) for s in science_sources):
                        science_sources.append({**source,'id':id,'identity_reviewed':source.get('identity_verified',source.get('trust_level')=='external'),
                            'source_url':source.get('url') or result.get('source_url')})
        except ModelError as exc:
            issues.append(str(exc));api_flags.append(local.finding('A+B','NEEDS_REVIEW',str(exc)))
    elif not run_citations: issues.append('Live citation retrieval explicitly skipped')
    if api_ready:
        for item in context.get('support_claims',[]):
            source=next((s for s in context.get('sources',[]) if s['id']==item.get('source_id')),None)
            if not source: continue
            try:
                result=judge_support(item['claim'],source['text'],judge)
                trusted=bool(source.get('identity_reviewed') and source.get('source_url'))
                status=('VERIFIED' if result['status']=='SUPPORTED' else result['status']) if trusted else 'NEEDS_REVIEW'
                api_flags.append(local.finding('B',status,result['reason'] if trusted else 'Supplied source identity requires review. '+result['reason'],
                    claim=item['claim'],source_id=source['id'],evidence=result,origin=getattr(judge,'provider','model')+'_source_comparison',confidence=result['confidence']))
            except ModelError as exc:
                issues.append(str(exc));api_flags.append(local.finding('B','NEEDS_REVIEW',str(exc),claim=item['claim']))
    report=local.analyse(text,context=enriched,document=document,quantum=False)
    diagnostics=dataset_integrity(context.get('datasets',[]))
    if api_ready and scientific:
        if queries:
            from .research import independent_sources
            discovered,research_audit=independent_sources(queries)
            science_sources.extend(s for s in discovered if not any(e.get('text')==s['text'] or (s.get('doi') and e.get('doi')==s['doi']) for e in science_sources))
            if not discovered:issues.append('Independent literature search returned no accessible source evidence')
        science_report=assess_science(text,science_sources,judge=judge,diagnostics=diagnostics,
            deterministic_flags=report['flags'])
        science_report['independent_literature_search']=bool(queries)
        science_report['research_audit']=research_audit
        api_flags.extend(science_report['flags']);issues.extend(science_report['issues'])
    elif not scientific: issues.append('Scientific review explicitly skipped')
    report['flags'].extend(api_flags)
    report['issues']=['Statements without validated evidence links remain for human review; model analysis does not guarantee exhaustive linking'
        if issue=='Unlinked manuscript statements require human review; automatic semantic/data linking is not implemented' else issue for issue in report['issues']]
    report['issues'].extend(issues)
    # Local catalog and model evidence remain separate, with disagreement explicitly surfaced.
    for flag in api_flags:
        if flag.get('check')!='A': continue
        for local_flag in report['flags']:
            if local_flag.get('assessment_kind')=='catalog corroboration' and local_flag.get('citation')==flag.get('citation') and local_flag['status']!=flag['status']:
                report['issues'].append('Local catalog and live citation result disagree: '+flag['citation'])
    for i,flag in enumerate(report['flags']):
        flag['flag_id']=f'finding_{i:05d}'
        flag.setdefault('severity','high' if flag['status'] in ('MISMATCH','NOT_FOUND','RETRACTED','CONTRADICTED','DATA_MISMATCH') else 'low' if flag['status']=='VERIFIED' else 'medium')
        flag.setdefault('confidence',None);flag.setdefault('confidence_kind','not_calibrated')
        flag.setdefault('suggested_fix','Inspect the linked evidence and revise or resolve with a reviewer')
        flag.update(org_id=context['org_id'],project_id=context['project_id'])
        claim=flag.get('claim')
        if claim and claim in text:
            position=text.index(claim);flag['claim_location']={'start':position,'end':position+len(claim)}
    report.update(schema_version='hybrid-3.0',mode='hybrid',org_id=context['org_id'],project_id=context['project_id'],paper_sha256=hashlib.sha256(text.encode()).hexdigest(),
        scientific_assessment=science_report or {'enabled':False,'reason':'API unavailable or scientific review skipped','certifies_scientific_accuracy':False},
        dataset_diagnostics=diagnostics,data_extraction_audit=extraction_audit,
        api={'provider':getattr(judge,'provider','unknown'),'configured':api_ready,'model':getattr(judge,'model',None),
             'store':getattr(judge,'store',None),'citation_pipeline_requested':run_citations,'data_linking_requested':extract_claims},
        network_requests=None,network_access_enabled=True,
        elapsed_seconds=round(time.monotonic()-start,3))
    report['coverage'].update(automatic_semantic_verification=api_ready,
        coverage_note='Unlinked statements/columns refer to local explicit-link coverage; model analysis is nonexhaustive',
        automatic_data_claims=len(enriched['claims'])-len(context.get('claims',[])),
        scientific_review_requested=scientific,scientific_review_completed=bool(science_report) and not science_report['issues'],
        external_sources_for_science=len(science_sources))
    report['summary']={s:sum(f['status']==s for f in report['flags']) for s in sorted({f['status'] for f in report['flags']})}
    report['status']='needs_review' if report['issues'] or any(f['needs_human_review'] for f in report['flags']) else 'checks_completed'
    report['quantum']=prioritize(report['flags'],shots,seed) if quantum else {'enabled':False}
    return report

def analyse_document(path, *, context, asset_dir=None, **kwargs):
    document=parse_document(path,asset_dir=asset_dir)
    report=analyse(document['text'],context=context,document=document,**kwargs)
    report['parsed_document']={k:v for k,v in document.items() if k!='text'}
    return report

def verify(text, *, context=None, **kwargs):
    if not isinstance(text,str):raise local.InputError('Text required')
    if not text.strip():return []
    return analyse(text,context=context or {'org_id':'local','project_id':'local'},**kwargs)['flags']
