"""Sanjay: verify_record(), verify_chain() and verify_all().

Verification needs only the PUBLIC key, never the private key or passphrase,
so anyone can check a capture without being able to forge one.
Bad input (wrong types, junk records) returns a status instead of crashing,
so a mistake elsewhere can't take the verifier down.
"""
from __future__ import annotations          # lets the type hints below run on older Python (Pi)
import hashlib, hmac, sys
from pathlib import Path
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from signing.record import (canonical, sha256_file, GENESIS, load_records, read_tip,
                            public_key_pem, public_key_file)

SIGNED_FIELDS = ("id", "type", "file_name", "file_sha256", "captured_at",
                 "device_id", "location", "prev_hash")
REQUIRED_FIELDS = SIGNED_FIELDS + ("record_hash", "signature")

# Possible results of verify_record()
VERIFIED = "VERIFIED"                # file and record are exactly as signed
TAMPERED_FILE = "TAMPERED_FILE"      # the photo/audio/reading bytes changed
TAMPERED_RECORD = "TAMPERED_RECORD"  # a record field (location, time, …) changed
BAD_SIGNATURE = "BAD_SIGNATURE"      # forged, or signed by a different device
FILE_MISSING = "FILE_MISSING"        # the capture file can't be found
MALFORMED = "MALFORMED"              # record is missing fields or isn't valid


def _same(a: str, b: str) -> bool:
    """Constant-time string compare, so timing can't leak how much of a hash matched."""
    return hmac.compare_digest(str(a), str(b))


def well_formed(rec) -> bool:
    """True if rec is a dict with every required field present as a string (Contract 1)."""
    return isinstance(rec, dict) and all(isinstance(rec.get(k), str) for k in REQUIRED_FIELDS)


def record_hash(rec: dict) -> str:
    """Recomputes a record's hash from its signed fields."""
    return hashlib.sha256(canonical({k: rec[k] for k in SIGNED_FIELDS})).hexdigest()


def load_public_key(pubkey_pem=None) -> Ed25519PublicKey:
    """Parses a PEM public key (str or bytes) and makes sure it is Ed25519.
    None means "use this project's public key" (see public_key_pem()).
    A bad key raises ValueError with a clear message — it's a setup mistake, not tampering."""
    if pubkey_pem is None:
        pubkey_pem = public_key_pem()
    if isinstance(pubkey_pem, str):
        pubkey_pem = pubkey_pem.encode()
    try:
        pub = serialization.load_pem_public_key(pubkey_pem)
    except (ValueError, TypeError) as e:
        raise ValueError("public key is not a valid PEM public key "
                         "(pass the contents of public_key.pem)") from e
    if not isinstance(pub, Ed25519PublicKey):
        raise ValueError("public key is not Ed25519")
    return pub


def verify_record(rec: dict, file_path, pubkey_pem=None) -> str:
    """Checks one capture against its record, returning one of the statuses above.
    Order: record shape → file hash → record hash → signature."""
    pub = load_public_key(pubkey_pem)
    if not well_formed(rec):
        return MALFORMED
    if file_path is None or not Path(file_path).is_file():
        return FILE_MISSING
    if not _same(sha256_file(file_path), rec["file_sha256"]):
        return TAMPERED_FILE
    if not _same(record_hash(rec), rec["record_hash"]):
        return TAMPERED_RECORD
    try:
        pub.verify(bytes.fromhex(rec["signature"]), bytes.fromhex(rec["record_hash"]))
    except (InvalidSignature, ValueError):
        return BAD_SIGNATURE
    return VERIFIED


def verify_chain(records: list[dict], expected_tip: str | None = None) -> tuple[bool, str]:
    """Checks records (oldest first) form an unbroken chain.
    Catches edited, deleted, inserted or reordered records; with expected_tip
    (the saved last_hash.txt) it also catches records removed from the end."""
    prev = GENESIS
    for i, r in enumerate(records):
        if not well_formed(r):
            return False, f"record #{i} is malformed"
        if not _same(record_hash(r), r["record_hash"]):
            return False, f"record {r['id']} was altered"
        if not _same(r["prev_hash"], prev):
            return False, f"chain broken at {r['id']} (record missing or reordered before it)"
        prev = r["record_hash"]
    if expected_tip is not None and not _same(prev, expected_tip):
        return False, ("chain end doesn't match last_hash.txt "
                       "(newest record(s) deleted, or last_hash.txt edited/deleted)")
    return True, "chain intact"


def verify_all(files_dir, pubkey_pem=None) -> dict:
    """Full audit of the stored records: every capture in files_dir plus the chain."""
    records = load_records()
    results = {}
    for i, r in enumerate(records):
        rid = r.get("id") if isinstance(r, dict) and isinstance(r.get("id"), str) else f"#{i}"
        if rid in results:                  # duplicate id: keep both results visible
            rid = f"{rid} (#{i})"
        name = r.get("file_name") if isinstance(r, dict) else None
        # Path(...).name stops a record's file_name from pointing outside files_dir
        path = Path(files_dir) / Path(name).name if isinstance(name, str) and name else None
        results[rid] = verify_record(r, path, pubkey_pem)
    chain_ok, chain_msg = verify_chain(records, read_tip())
    all_ok = chain_ok and all(s == VERIFIED for s in results.values())
    return {"ok": all_ok, "records": results, "chain": chain_msg}


if __name__ == "__main__":
    # python -m signing.verify <captures_folder> [public_key.pem]
    if len(sys.argv) < 2:
        sys.exit("usage: python -m signing.verify <captures_folder> [public_key.pem]")
    pem_path = Path(sys.argv[2]) if len(sys.argv) > 2 else public_key_file()
    report = verify_all(sys.argv[1], pem_path.read_text())
    for rid, status in report["records"].items():
        print(f"{rid}: {status}")
    print(f"chain: {report['chain']}")
    print("COMPLETELY VERIFIED" if report["ok"] else "NOT VERIFIED")
    sys.exit(0 if report["ok"] else 1)
