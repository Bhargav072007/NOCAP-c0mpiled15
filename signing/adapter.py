"""Sanjay: signing plugin for Avishkar's API (cloud/api.py).

Configure the API host with:
    NOCAP_SIGNING_PLUGIN=signing.adapter:verify_record

The API checks the uploaded file's SHA-256 itself, then calls this with the
record and the device's enrolled public key. True accepts the capture
(VERIFIED); False makes the API reject it (422); an exception means the
verifier is misconfigured (503).
"""
from __future__ import annotations
from cryptography.exceptions import InvalidSignature
from signing.verify import well_formed, record_hash, load_public_key, _same


def verify_record(record: dict, public_key_pem: str) -> bool:
    """True only if the record's canonical hash AND the device signature are valid.
    A device with no enrolled key is never trusted (False). A malformed enrolled
    key raises ValueError — that's a server setup problem, not a bad capture."""
    if not public_key_pem or not well_formed(record):
        return False
    if not _same(record_hash(record), record["record_hash"]):
        return False
    pub = load_public_key(public_key_pem)
    try:
        pub.verify(bytes.fromhex(record["signature"]), bytes.fromhex(record["record_hash"]))
    except (InvalidSignature, ValueError):
        return False
    return True
