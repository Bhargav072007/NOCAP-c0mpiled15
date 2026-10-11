"""Segment 3 entry points: verify(text), analyse(text, context), analyse_document(path)."""
from datetime import datetime,timezone
from .citations import check_reference
from .claims import extract_citations,source_for,judge_support
from .llm import ModelError
from .parser import text_batches

__all__=['verify','analyse','analyse_document']

def verify(text: str, *, judge=None,legacy=False,domain='mixed',sources=None) -> list[dict]:
    if not isinstance(text,str): raise TypeError('text must be a string')
    if domain not in ('academic','legal','mixed'): raise ValueError('domain must be academic, legal or mixed')
    if not text.strip(): return []
    from .legal import is_legal,check_legal_reference,source_for_case,extract_legal_items
    items=[];audits=[];seen=set()
    for batch in text_batches(text):
        extracted,audit=extract_citations(batch,judge,with_audit=True)
        audits.append(audit)
        for item in extracted:
            key=(item['claim'],item['citation'])
            if key not in seen: items.append(item);seen.add(key)
    if domain in ('mixed','legal'):
        for item in extract_legal_items(text):
            # Model-linked case entries take precedence over whole-line fallback claims.
            if not any(item['citation'] in existing['citation'] for existing in items): items.append(item)
    results=[]
    for item in items:
        legal=domain=='legal' or (domain=='mixed' and is_legal(item['citation']))
        if item['unresolved']:
            res={'citation':item['citation'],'status':'NEEDS_REVIEW','reason':'Citation marker could not be linked to a supplied reference','confidence':0.0}
        else: res=check_legal_reference(item['citation'],item) if legal else check_reference(item['citation'],item)
        res.update(claim=item['claim'],extraction_audit=audits,check='A',domain='legal' if legal else 'academic',
            checked_at=datetime.now(timezone.utc).isoformat(),suggested_fix='Review reference metadata and source evidence',
            matched_title=res.get('matched_title'),doi=res.get('doi'),confidence_kind='uncalibrated_heuristic')
        res['citation_status']=res['status'];res['citation_reason']=res['reason'];res['citation_confidence']=res.get('confidence',0);res['claim_status']='NOT_CHECKED'
        res['retraction_check']=res.get('retraction_check','unknown')
        if res['status']=='VERIFIED':
            supplied=(sources or {}).get(item['citation']) or (sources or {}).get(res.get('doi'))
            # Full text supplied by the authenticated backend retains declared provenance.
            source=supplied if supplied is not None else source_for_case(res) if legal else source_for(res['doi']) if res.get('doi') else {'text':'','scope':'missing'}
            if isinstance(source,str): source={'text':source,'scope':'full_text','provider':'User-supplied full text','trust_level':'uploaded','identity_verified':False}
            res['source_evidence']=source;res['retraction_check']=source.get('retraction','not_applicable' if legal else 'unknown')
            if source.get('retraction')=='retracted':
                res.update(status='RETRACTED',citation_status='RETRACTED',citation_reason='Provider marks the cited work retracted',reason='Provider marks the cited work retracted')
            elif item['claim']:
                try: verdict=judge_support(item['claim'],source.get('text',''),judge)
                except ModelError as exc: verdict={'status':'NEEDS_REVIEW','reason':str(exc),'confidence':0.0}
                if supplied is not None and not source.get('identity_verified'):
                    verdict=dict(verdict);verdict.update(status='NEEDS_REVIEW',reason='Supplied source identity needs confirmation; '+verdict['reason'])
                if legal and source.get('text') and not source.get('majority_identified'):
                    verdict=dict(verdict);verdict.update(status='NEEDS_REVIEW',reason='Controlling/majority opinion not identified; '+verdict['reason'])
                res['check']='A+B';res['claim_status']=verdict['status'];res['claim_evidence']=verdict
                res.update(status='VERIFIED' if verdict['status']=='SUPPORTED' else verdict['status'],reason=verdict['reason'],
                    confidence=min(res.get('confidence',0),verdict['confidence']),suggested_fix=verdict.get('suggested_fix','Retrieve full source and request human review'))
        res['severity']='high' if res['status'] in {'NOT_FOUND','MISMATCH','RETRACTED','CONTRADICTED'} else 'low' if res['status']=='VERIFIED' else 'medium'
        res['needs_human_review']=res['status']!='VERIFIED'
        if legacy:
            res['detailed_status']=res['status']
            res['status']={'RETRACTED':'MISMATCH','CONTRADICTED':'UNSUPPORTED','PARTIAL':'UNSUPPORTED','NEEDS_REVIEW':'UNSUPPORTED'}.get(res['status'],res['status'])
        results.append(res)
    return results


