"""Sanjay's signing checks. Run from repo root:  python -m tests.test_signing
Uses a throwaway key, passphrase and data folder, so the real device key and chain are untouched."""
import json, os, shutil, tempfile
from pathlib import Path

tmp = Path(tempfile.mkdtemp())
os.environ["NOCAP_KEY_FILE"] = str(tmp / "keys" / "device_key.pem")
os.environ["NOCAP_DATA_DIR"] = str(tmp / "data")
os.environ["NOCAP_KEY_PASSPHRASE"] = "test-only-passphrase-123"

import signing.record as R
from signing.verify import (verify_record, verify_chain, verify_all, VERIFIED, TAMPERED_FILE,
                            TAMPERED_RECORD, BAD_SIGNATURE, FILE_MISSING, MALFORMED)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

R.load_key(create=True)                        # what `python -m signing.record` does once
PUB = R.public_key_pem()
caps = tmp / "captures"; caps.mkdir()
photo = caps / "photo.jpg"; photo.write_bytes(os.urandom(4096))


def check(n, label, got, want):
    assert got == want, f"{label}: expected {want!r}, got {got!r}"
    print(f"{n:>3} {label:<46} ✓")


# --- secrets stay hidden ---------------------------------------------------
pem = Path(os.environ["NOCAP_KEY_FILE"]).read_bytes()
check(1, "private key file is encrypted", b"ENCRYPTED PRIVATE KEY" in pem, True)
os.environ["NOCAP_KEY_PASSPHRASE"] = "wrong-passphrase-xyz"
try:
    R.load_key(); wrong = "loaded"
except ValueError:
    wrong = "rejected"
os.environ["NOCAP_KEY_PASSPHRASE"] = "test-only-passphrase-123"
check(2, "wrong passphrase is rejected", wrong, "rejected")
del os.environ["NOCAP_KEY_PASSPHRASE"]
try:
    R.load_key(); missing = "loaded"
except RuntimeError:
    missing = "refused"
os.environ["NOCAP_KEY_PASSPHRASE"] = "test-only-passphrase-123"
check(3, "missing passphrase is refused", missing, "refused")

# --- one record --------------------------------------------------------------
rec = R.make_record(photo, "photo")
check(4, "original → VERIFIED", verify_record(rec, photo, PUB), VERIFIED)
check(5, "record stored in records.jsonl", R.load_records(), [rec])
check(6, "last_hash.txt = record_hash", R.read_tip(), rec["record_hash"])
stored = R.records_file().read_text() + R.chain_file().read_text()
check(7, "no secret in stored data", "PRIVATE" in stored or "passphrase" in stored, False)

edited = caps / "edited.jpg"; shutil.copy(photo, edited)
data = bytearray(edited.read_bytes()); data[0] ^= 1; edited.write_bytes(bytes(data))
check(8, "one byte changed → TAMPERED_FILE", verify_record(rec, edited, PUB), TAMPERED_FILE)
check(9, "location changed → TAMPERED_RECORD",
      verify_record(dict(rec, location="Somewhere else"), photo, PUB), TAMPERED_RECORD)
check(10, "zeroed signature → BAD_SIGNATURE",
      verify_record(dict(rec, signature="00" * 64), photo, PUB), BAD_SIGNATURE)
check(11, "garbage signature → BAD_SIGNATURE",
      verify_record(dict(rec, signature="not-hex"), photo, PUB), BAD_SIGNATURE)
other = Ed25519PrivateKey.generate().public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
check(12, "other device's key → BAD_SIGNATURE", verify_record(rec, photo, other), BAD_SIGNATURE)
check(13, "file deleted → FILE_MISSING", verify_record(rec, caps / "gone.jpg", PUB), FILE_MISSING)
no_sig = {k: v for k, v in rec.items() if k != "signature"}
check(14, "field missing → MALFORMED", verify_record(no_sig, photo, PUB), MALFORMED)
try:
    R.make_record(photo, "unknown"); bad_type = "accepted"
except ValueError:
    bad_type = "rejected"
check(15, "make_record('unknown') raises", bad_type, "rejected")

# --- the chain ---------------------------------------------------------------
recs = [rec] + [R.make_record(photo, "photo") for _ in range(3)]
tip = R.read_tip()
check(16, "4 records → chain intact", verify_chain(recs, tip), (True, "chain intact"))
check(17, "middle deleted → chain broken", verify_chain([recs[0], recs[2], recs[3]], tip)[0], False)
check(18, "reordered → chain broken", verify_chain([recs[1], recs[0], recs[2], recs[3]], tip)[0], False)
check(19, "newest deleted → doesn't match last_hash", verify_chain(recs[:3], tip)[0], False)
altered = [recs[0], dict(recs[1], location="X")] + recs[2:]
check(20, "record edited → chain fails", verify_chain(altered, tip)[0], False)

# --- full audit ----------------------------------------------------------------
report = verify_all(caps, PUB)
check(21, "verify_all → COMPLETELY VERIFIED", report["ok"], True)
photo.write_bytes(b"swapped")
report = verify_all(caps, PUB)
check(22, "verify_all after swap → NOT VERIFIED", report["ok"], False)
check(23, "  …every record reports TAMPERED_FILE", set(report["records"].values()), {TAMPERED_FILE})

# --- the hash file (last_hash.txt) ---------------------------------------------
R.chain_file().write_text("f" * 64)
ok, msg = verify_chain(R.load_records(), R.read_tip())
check(24, "hash file edited → chain fails", ok, False)
check(25, "  …message names last_hash.txt", "last_hash.txt" in msg, True)
R.chain_file().unlink()
count = len(R.load_records())
try:
    R.make_record(photo, "photo"); refused = "accepted"
except RuntimeError:
    refused = "refused"
check(26, "hash file deleted → make_record refuses", refused, "refused")
check(27, "  …no record was added", len(R.load_records()), count)

shutil.rmtree(tmp)
print("\nAll signing tests pass.")
