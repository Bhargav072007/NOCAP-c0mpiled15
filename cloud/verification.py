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
        analysis = analyse(text, context=context, mode=mode, quantum=quantum, document=document)
        if any(r['payload']['type']=='video' for r in captures):
            analysis['issues'].append('Video file integrity was checked; video content was not scientifically assessed.')
        if any(any(r['payload'].get('metadata',{}).values()) for r in captures):
            analysis['issues'].append('Lab labels are upload annotations, not part of the device signature.')
    # Verifier reports contain hashes/IDs, not temporary paths to storage originals.
    return {'results': presentation(analysis), 'analysis': analysis, 'analysis_mode': mode,
            'fixture': False, 'selected_capture_ids': selected_ids,
            'evidence_contains_demo': any(r['payload'].get('fixture', False) for r in captures)}
