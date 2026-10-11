"""Check C: provenance, numbers, figures, reuse and unsupported strong wording."""
import json
import re
from .parser import split_bibliography,text_batches
from .statistics import recompute,compare_reported,DataError
from .images import similarity,possible_reuse,ImageError

STRONG=re.compile(r'\b(cures?|proves?|always|guarantees?|statistically significant)\b',re.I)

def flag(status,claim,reason,evidence=None,confidence=.85,suggested_fix='Review the linked original data and revise the sentence'):
    return {'check':'C','status':status,'claim':claim,'citation':'','matched_title':None,'doi':None,
        'reason':reason,'evidence':evidence or {},'confidence':confidence,'confidence_kind':'uncalibrated_heuristic',
        'severity':'high' if status=='DATA_MISMATCH' else 'low' if status=='VERIFIED' else 'medium',
        'needs_human_review':status!='VERIFIED','suggested_fix':suggested_fix}


def data_checks(text,claims,datasets,figures,captures,provenance, *, org_id,project_id):
    results=[];by_dataset={d['id']:d for d in datasets};by_capture={c['id']:c for c in captures}
    by_figure={f['id']:f for f in figures}
    for claim in claims:
        sentence=claim['claim'];dataset=by_dataset.get(claim.get('dataset_id'))
        if dataset:
            if dataset.get('org_id')!=org_id or dataset.get('project_id')!=project_id:
                results.append(flag('NEEDS_REVIEW',sentence,'Dataset belongs to a different organization/project',confidence=0));continue
            if claim.get('automatic_link') and not any(x and x in sentence for x in (dataset.get('label'),dataset['id'])):
                results.append(flag('NEEDS_REVIEW',sentence,'Suggested dataset link requires human confirmation',{'dataset_id':dataset['id']},.5));continue
            state=provenance.get(dataset.get('capture_id'),{})
            if not state.get('valid'):
                status='DATA_MISMATCH' if state.get('status') in ('TAMPERED_FILE','TAMPERED_RECORD','BAD_SIGNATURE','BROKEN_CHAIN','SCOPE_MISMATCH') else 'UNSIGNED_DATA'
                results.append(flag(status,sentence,'Linked dataset lacks verified signature and anchored intact chain',{'dataset_id':dataset['id'],'provenance':state}))
            elif dataset.get('path')!=by_capture[dataset['capture_id']]['path']:
                results.append(flag('DATA_MISMATCH',sentence,'Dataset path is not the verified capture file',{'dataset_id':dataset['id']}));continue
            if claim.get('unit') and dataset.get('unit') and claim['unit']!=dataset['unit']:
                results.append(flag('NEEDS_REVIEW',sentence,'Measurement units differ; no conversion assumed',{'claimed_unit':claim['unit'],'source_unit':dataset['unit']},.5));continue
            try:
                computed=recompute(dataset['path'],claim)
                reported=claim.get('reported');actual=computed['value_for_claim']
                evidence={'dataset_id':dataset['id'],'capture_id':dataset.get('capture_id'),'computed':computed,
                          'reported':reported,'trust_level':state.get('trust_level','uploaded')}
                if reported is not None and actual is not None:
                    operator=claim.get('operator','=')
                    if operator not in ('=','<','<=','>','>='): raise DataError('Unsupported reported-value operator')
                    matches={'=':lambda:compare_reported(reported,actual,metric=claim['metric'],decimals=claim.get('decimals'),rtol=claim.get('rtol',.01),atol=claim.get('atol',1e-8)),
                        '<':lambda:actual<reported,'<=':lambda:actual<=reported,'>':lambda:actual>reported,'>=':lambda:actual>=reported}[operator]()
                    results.append(flag('VERIFIED' if matches and state.get('valid') else 'NEEDS_REVIEW' if matches else 'DATA_MISMATCH',sentence,
                        'Reported value matches linked data' if matches else 'Reported value differs from recomputed statistic',evidence))
                if claim.get('significant'):
                    alpha=claim.get('alpha',.05)
                    if not 0<alpha<1: raise DataError('alpha must be between 0 and 1')
                    if computed.get('p_value',1)>=alpha:
                        results.append(flag('OVERCLAIM',sentence,'Specified test does not support statistical significance',evidence,.95))
            except (DataError,OSError,ValueError,KeyError) as exc:
                results.append(flag('NEEDS_REVIEW',sentence,'Cannot safely recompute linked result: '+str(exc),{'dataset_id':dataset['id']},0))
        elif claim.get('dataset_id') or claim.get('metric','none')!='none':
            results.append(flag('UNSIGNED_DATA',sentence,'No linked underlying dataset supplied',confidence=.7))
        figure=by_figure.get(claim.get('figure_id'))
        if figure: results.extend(check_figure(figure,by_capture,provenance,sentence,org_id,project_id))
    linked_figures={c.get('figure_id') for c in claims}
    for figure in figures:
        if figure['id'] not in linked_figures:
            results.extend(check_figure(figure,by_capture,provenance,figure.get('label',''),org_id,project_id))
    for match in possible_reuse(figures):
        results.append(flag('IMAGE_REUSED','', 'Similar panels have different condition labels; human review required',match,.75,
                            'Confirm whether reuse is intentional and disclose the shared panel'))
    body,_=split_bibliography(text)
    for sentence in re.split(r'(?<=[.!?])\s+|\n',body):
        if STRONG.search(sentence):
            results.append(flag('OVERCLAIM',sentence,'Strong wording requires justification; wording signal alone does not establish an error',
                                {'trigger':STRONG.search(sentence).group()},.6,'Replace absolute wording or link supporting quantitative/source evidence'))
    return results

def check_figure(figure,captures,provenance,sentence,org_id,project_id):
    if figure.get('org_id')!=org_id or figure.get('project_id')!=project_id:
        return [flag('NEEDS_REVIEW',sentence,'Figure scope not confirmed',{'figure_id':figure['id']},0)]
    cid=figure.get('capture_id');original=captures.get(cid);state=provenance.get(cid,{})
    if not original or not state.get('valid'):
        status='DATA_MISMATCH' if state.get('status') in ('TAMPERED_FILE','TAMPERED_RECORD','BAD_SIGNATURE','BROKEN_CHAIN','SCOPE_MISMATCH') else 'UNSIGNED_DATA'
        return [flag(status,sentence,'Figure has no linked verified capture',{'figure_id':figure['id'],'provenance':state},.8)]
    if original.get('record',{}).get('type')!='photo':
        return [flag('NEEDS_REVIEW',sentence,'Linked capture is not a photo',{'capture_id':cid},0)]
    try: match=similarity(figure['path'],original['path'],crop=figure.get('crop'))
    except (ImageError,OSError) as exc:
        return [flag('NEEDS_REVIEW',sentence,'Image comparison unavailable: '+str(exc),confidence=0)]
    evidence={'figure_id':figure['id'],'capture_id':cid,'comparison':match,'provenance':state}
    if match['kind']=='exact_hash':
        return [flag('VERIFIED',sentence,'Figure bytes exactly match verified signed capture',evidence,.99)]
    if match['kind']!='different':
        return [flag('NEEDS_REVIEW',sentence,'Perceptual match suggests resizing/compression/cropping; confirm transformation',evidence,.75)]
    return [flag('DATA_MISMATCH',sentence,'Figure differs from linked signed original; confirm edits or provide crop mapping',evidence,.9)]
