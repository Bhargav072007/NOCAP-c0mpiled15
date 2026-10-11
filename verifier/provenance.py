"""Verify the team's signed-record contract with backend-trusted device keys."""
import hashlib
import json
import re
from pathlib import Path
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

FIELDS=('id','type','file_name','file_sha256','captured_at','device_id','location','prev_hash')
GENESIS='0'*64
HEX=re.compile(r'^[0-9a-f]{64}$')

def canonical(record):
    return json.dumps({k:record[k] for k in FIELDS},sort_keys=True,separators=(',',':')).encode()

def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1<<20),b''): h.update(chunk)
    return h.hexdigest()

def verify_record(record,path,public_key):
    try:
        if any(k not in record for k in (*FIELDS,'record_hash','signature')): return 'INVALID_RECORD'
        if record['type'] not in ('photo','audio','reading'): return 'INVALID_RECORD'
        if any(not isinstance(record[k],str) or not HEX.fullmatch(record[k]) for k in ('file_sha256','prev_hash','record_hash')): return 'INVALID_RECORD'
        if sha256_file(path)!=record['file_sha256']: return 'TAMPERED_FILE'
        digest=hashlib.sha256(canonical(record)).hexdigest()
        if digest!=record['record_hash']: return 'TAMPERED_RECORD'
        key=serialization.load_pem_public_key(public_key.encode() if isinstance(public_key,str) else public_key)
        if not isinstance(key,Ed25519PublicKey): return 'INVALID_KEY'
        key.verify(bytes.fromhex(record['signature']),bytes.fromhex(digest))
        return 'VERIFIED'
    except InvalidSignature: return 'BAD_SIGNATURE'
    except (ValueError,TypeError,KeyError,OSError): return 'INVALID_RECORD'

def verify_captures(captures,public_keys, *, org_id,project_id,chain_starts=None,expected_heads=None):
    """Input order is capture order per device. Scope fields come from authenticated backend rows.

    expected_heads must come from the trusted ledger, not the uploaded manifest.
    """
    starts=chain_starts or {};heads=expected_heads or {};results={};by_device={}
    for cap in captures:
        cid=cap['id'];record=cap.get('record',{});device=record.get('device_id','')
        if cid in results: raise ValueError('Duplicate capture ID')
        if cap.get('org_id')!=org_id or cap.get('project_id')!=project_id:
            results[cid]={'status':'SCOPE_MISMATCH','valid':False};continue
        if cid!=record.get('id'):
            results[cid]={'status':'INVALID_RECORD','valid':False};continue
        key=public_keys.get(device)
        state=verify_record(record,cap['path'],key) if key else 'UNKNOWN_DEVICE'
        results[cid]={'status':state,'signature_valid':state=='VERIFIED','valid':False,
                      'trust_level':cap.get('trust_level','device_signed'),'record_hash':record.get('record_hash')}
        by_device.setdefault(device,[]).append(cap)
    for device,group in by_device.items():
        prev=starts.get(device,GENESIS);chain=True
        for cap in group:
            rec=cap['record']
            if rec.get('prev_hash')!=prev or not results[cap['id']]['signature_valid']: chain=False
            prev=rec.get('record_hash')
        anchored=device in heads
        if anchored and prev!=heads[device]: chain=False
        for cap in group:
            item=results[cap['id']]
            item.update(chain_valid=chain,chain_complete=anchored)
            item['valid']=item['signature_valid'] and chain and anchored
            if item['signature_valid'] and not chain: item['status']='BROKEN_CHAIN'
            elif item['signature_valid'] and not anchored: item['status']='UNANCHORED_CHAIN'
    return results
