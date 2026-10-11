"""Translate Segment 3 findings without discarding its audit or trusting upload paths."""
from pathlib import Path


def signature_valid(record, public_key):
    from signing.adapter import verify_record
    return verify_record(record, public_key)


def presentation(analysis):
    """Legacy badge vocabulary is a summary; retain the precise backend verdict."""
    rows = []
    for flag in analysis['flags']:
        status = flag['status']
        badge = (status if status in {'VERIFIED', 'MISMATCH', 'NOT_FOUND'} else
                 'MISMATCH' if status in {'CONTRADICTED', 'DATA_MISMATCH'} else 'UNSUPPORTED')
        rows.append({**flag, 'status': badge, 'backend_status': status,
                     'citation': str(flag.get('citation') or flag.get('capture_id') or
                                     flag.get('dataset_id') or f"Check {flag.get('check', 'review')}"),
                     'claim': str(flag.get('claim') or ''),
                     'reason': str(flag.get('reason') or 'Review the attached evidence.'),
                     'matched_title': str(flag.get('matched_title') or ''),
                     'doi': str(flag.get('doi') or '')})
    return rows


def analyse_workspace(text, *, org_id, captures, devices, selected_ids, store, mode,
                      quantum=False, document=None):
    from tempfile import TemporaryDirectory
    from verifier import analyse
    # This workspace currently has organization scope, not a separate project model.
    context = {'org_id': org_id, 'project_id': org_id, 'captures': [],
               'datasets': [], 'figures': [], 'public_keys': {}, 'expected_heads': {}}
    with TemporaryDirectory(prefix='nocap-review-') as directory:
        total = 0
        for row in captures:
            record = row['payload']
            data = store.get(row['object_key'])
            total += len(data)
            if len(data) > 50 * 1024 * 1024 or total > 100 * 1024 * 1024:
                raise ValueError('Evidence snapshot exceeds the review limit')
            # Opaque generated paths, never a client-supplied local path.
            suffix = Path(record['file_name']).suffix.lower()
            path = Path(directory) / f"evidence_{len(context['captures'])}{suffix}"
            path.write_bytes(data)
            evidence = {'id': row['id'], 'path': str(path), 'org_id': org_id, 'project_id': org_id}
            context['captures'].append({**evidence, 'record': record})
            if row['id'] in selected_ids:
                if record['type'] == 'reading' and suffix in {'.csv', '.json'}:
                    context['datasets'].append({**evidence, 'capture_id': row['id'], 'label': record.get('metadata',{}).get('label') or record['file_name']})
                elif record['type'] == 'photo':
                    context['figures'].append({**evidence, 'capture_id': row['id'], 'label': record.get('metadata',{}).get('label') or record['file_name']})
        for device in devices:
            if device['public_key']:
                context['public_keys'][device['id']] = device['public_key']
            context['expected_heads'][device['id']] = device['last_hash']
        analysis = analyse(text, context=context, mode='offline' if mode=='references' else mode, quantum=quantum, document=document)
        if mode=='references':
            publication_checks(analysis)
        if any(r['payload']['type']=='video' for r in captures):
            analysis['issues'].append('Video file integrity was checked; video content was not scientifically assessed.')
        if any(any(r['payload'].get('metadata',{}).values()) for r in captures):
            analysis['issues'].append('Lab labels are upload annotations, not part of the device signature.')
    # Verifier reports contain hashes/IDs, not temporary paths to storage originals.
    return {'results': presentation(analysis), 'analysis': analysis, 'analysis_mode': mode,
            'fixture': False, 'selected_capture_ids': selected_ids,
            'evidence_contains_demo': any(r['payload'].get('fixture', False) for r in captures)}


def publication_checks(analysis):
    """DOI identity lookups only; never claim model/semantic review without one."""
    from concurrent.futures import ThreadPoolExecutor
    from verifier.citations import doi_in, check_reference
    references=list(dict.fromkeys(f['citation'] for f in analysis['flags'] if f.get('check')=='A' and f.get('citation')))
    selected=[ref for ref in references if doi_in(ref)][:12]
    def check(ref):
        try: result=check_reference(ref)
        except Exception:
            result={'citation':ref,'status':'NEEDS_REVIEW','reason':'Publication service unavailable. Retry later or review the reference manually.','needs_human_review':True}
        return {**result,'check':'A','origin':'publication_metadata_lookup','claim':'',
                'assessment_kind':'publication identity only; source support and scientific claims not assessed'}
    with ThreadPoolExecutor(max_workers=4) as pool:
        checked=list(pool.map(check,selected))
    analysis['flags']=[f for f in analysis['flags'] if not (f.get('check')=='A' and f.get('citation') in selected)]+checked
    for i,flag in enumerate(analysis['flags']):flag['flag_id']=f'finding_{i:05d}'
    analysis['coverage']['publication_lookups']=len(selected)
    analysis['coverage']['references_not_looked_up']=len(references)-len(selected)
    analysis['issues'].append('Publication checks assess DOI/reference identity only. They do not verify scientific conclusions, source support, or all author/year fields.')
    if len(references)>len(selected):analysis['issues'].append('References without a DOI or beyond the 12-reference lookup limit require manual review.')
    analysis['summary']={s:sum(f['status']==s for f in analysis['flags']) for s in {f['status'] for f in analysis['flags']}}
    analysis['status']='needs_review'
    analysis['network_requests']=None
    analysis['network_access_enabled']=True
