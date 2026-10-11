"""Integration test: runs signing/ the way teammates' code (from the build plan) calls it,
plus the mistakes they might make. Run from repo root:  python -m tests.test_integration

  Pi (Pranav)        make_record(path, kind) → json.dumps(record) → upload
  API (Avishkar)     json.loads → save file → verify_record / verify_chain, on a machine
                     with NO private key and NO passphrase (public_key.pem only)
  Ledger (Divyam)    merkle_root over record_hash values
  Dashboard (Bhargav) reads type / captured_at / device_id / location / file_sha256 / signature

Uses a throwaway key and folders, so the real device key and records are untouched."""
import hashlib, json, os, shutil, sqlite3, tempfile, threading
from contextlib import contextmanager
from pathlib import Path

tmp = Path(tempfile.mkdtemp())
PI = {"NOCAP_KEY_FILE": str(tmp / "pi" / "device_key.pem"), "NOCAP_DATA_DIR": str(tmp / "pi" / "data"),
      "NOCAP_KEY_PASSPHRASE": "test-only-passphrase-123", "NOCAP_PUBLIC_KEY_FILE": ""}
os.environ.update({k: v for k, v in PI.items() if v})

import signing.record as R
from signing.verify import (verify_record, verify_chain, verify_all, VERIFIED, TAMPERED_FILE,
                            MALFORMED, FILE_MISSING)

n = 0


def check(label, got, want):
    """Prints one numbered pass line, or stops with what went wrong."""
    global n; n += 1
    assert got == want, f"{label}: expected {want!r}, got {got!r}"
    print(f"{n:>3} {label:<60} ✓")


def raises(fn, exc):
    """Name of the error fn raised ('none' if it didn't), checking it is the expected type."""
    try:
        fn()
    except exc as e:
        return type(e).__name__
    return "none"


@contextmanager
def machine(**env):
    """Pretend to be a different computer: swap the NOCAP_* settings, then put them back."""
    keys = [k for k in os.environ if k.startswith("NOCAP_")]
    saved = {k: os.environ.pop(k) for k in keys}
    os.environ.update({k: v for k, v in env.items() if v is not None})
    try:
        yield
    finally:
        for k in [k for k in os.environ if k.startswith("NOCAP_")]:
            del os.environ[k]
        os.environ.update(saved)


def merkle_root(hashes):
    """Divyam's ledger/merkle.py, copied from the build plan."""
    layer = [bytes.fromhex(h) for h in hashes]
    if not layer:
        return None
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [hashlib.sha256(layer[i] + layer[i + 1]).digest() for i in range(0, len(layer), 2)]
    return layer[0].hex()


# ================= Pi (Pranav's capture.py) ======================================
print("— Pi: capture + sign —")
R.load_key(create=True)                                   # Sanjay's one-time setup
pub_file = Path(PI["NOCAP_DATA_DIR"]) / "public_key.pem"
pub_file.parent.mkdir(parents=True, exist_ok=True); pub_file.write_text(R.public_key_pem())

captures = tmp / "pi" / "captures"; captures.mkdir()
uploads = []                                              # what goes over the network
for ts in ("2026-10-11T14-02-11", "2026-10-11T14-05-40"):
    photo, audio = captures / f"{ts}.jpg", captures / f"{ts}.wav"
    photo.write_bytes(os.urandom(5000)); audio.write_bytes(os.urandom(8000))
    for path, kind in [(photo, "photo"), (audio, "audio")]:   # exactly capture.py's loop
        record = R.make_record(path, kind)
        uploads.append((path, json.dumps(record)))
check("4 captures signed on the Pi", len(uploads), 4)

# ================= API laptop (Avishkar's cloud/api.py) ===========================
print("\n— API laptop: no private key, no passphrase, only public_key.pem —")
api = tmp / "api"; FILES = api / "files"; FILES.mkdir(parents=True)
api_key_path = api / "nope" / "device_key.pem"
with machine(NOCAP_KEY_FILE=str(api_key_path), NOCAP_DATA_DIR=str(api / "data"),
             NOCAP_PUBLIC_KEY_FILE=str(pub_file)):
    PUBKEY = R.public_key_pem()                           # api.py line: PUBKEY = public_key_pem()
    check("public_key_pem() works with no secrets on the machine", PUBKEY, pub_file.read_text())
    check("…and did NOT create a new key there", api_key_path.exists(), False)

    db = sqlite3.connect(":memory:"); db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE captures(id TEXT PRIMARY KEY, seq INTEGER, file_sha256 TEXT, record TEXT, path TEXT)")

    def add_capture(file_path, record_str):
        """POST /captures, as in the plan."""
        rec = json.loads(record_str)
        dest = FILES / rec["file_name"]; shutil.copy(file_path, dest)
        status = verify_record(rec, dest, PUBKEY)
        seq = db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM captures").fetchone()[0]
        db.execute("INSERT OR REPLACE INTO captures VALUES(?,?,?,?,?)",
                   (rec["id"], seq, rec["file_sha256"], record_str, str(dest)))
        return status

    def list_captures():
        """GET /captures, as in the plan."""
        out = []
        for r in db.execute("SELECT * FROM captures ORDER BY seq"):
            rec = json.loads(r["record"])
            out.append(rec | {"status": verify_record(rec, r["path"], PUBKEY)})
        return out

    def ledger():
        """GET /ledger, as in the plan."""
        recs = [json.loads(r["record"]) for r in db.execute("SELECT record FROM captures ORDER BY seq")]
        ok, msg = verify_chain(recs)
        return {"records": recs, "chain_ok": ok, "chain_msg": msg,
                "merkle_root": merkle_root([r["record_hash"] for r in recs])}

    check("every upload → VERIFIED", {add_capture(p, s) for p, s in uploads}, {VERIFIED})
    caps = list_captures()
    check("GET /captures shows all VERIFIED", {c["status"] for c in caps}, {VERIFIED})
    led = ledger()
    check("GET /ledger → chain intact", (led["chain_ok"], led["chain_msg"]), (True, "chain intact"))
    check("Merkle root (Divyam) computes over record hashes", len(led["merkle_root"] or ""), 64)

    # Bhargav's dashboard reads these fields
    c = caps[0]
    fields_ok = all(isinstance(c[k], str) for k in ("type", "captured_at", "device_id", "location",
                                                    "file_sha256", "signature"))
    check("dashboard fields present and text", fields_ok, True)
    check("dashboard slices sha256/signature without error",
          (len(c["file_sha256"][:32]), len(c["signature"][:32])), (32, 32))
    check("device_id / location match the plan",
          (c["device_id"], c["location"]), ("nocap-pi5-01", "EDI Building, Penn State"))

    # someone edits a stored photo on the server
    stored = Path(db.execute("SELECT path FROM captures ORDER BY seq").fetchone()["path"])
    stored.write_bytes(b"edited")
    check("edited photo on server → GET /captures shows TAMPERED_FILE",
          list_captures()[0]["status"], TAMPERED_FILE)

    # ---- mistakes on the API side ----
    print("\n— API-side mistakes —")
    good = json.loads(uploads[1][1]); f = FILES / good["file_name"]
    check("upload JSON is a list, not a record → MALFORMED", verify_record([good], f, PUBKEY), MALFORMED)
    check("signature sent as a number → MALFORMED", verify_record(dict(good, signature=123), f, PUBKEY), MALFORMED)
    check("field missing → MALFORMED",
          verify_record({k: v for k, v in good.items() if k != "prev_hash"}, f, PUBKEY), MALFORMED)
    check("file path None → FILE_MISSING", verify_record(good, None, PUBKEY), FILE_MISSING)
    check("public key passed as bytes → still VERIFIED", verify_record(good, f, PUBKEY.encode()), VERIFIED)
    check("public key omitted (None) → uses public_key.pem → VERIFIED", verify_record(good, f), VERIFIED)
    check("garbage public key → clear ValueError (not silent BAD_SIGNATURE)",
          raises(lambda: verify_record(good, f, "not a key"), ValueError), "ValueError")
    check("verify_chain with junk entries → False, no crash",
          verify_chain([None, "x", 5])[0], False)

    # ---- signing plugin the real cloud/api.py loads (NOCAP_SIGNING_PLUGIN) ----
    print("\n— signing.adapter:verify_record (cloud/api.py plugin contract) —")
    from signing.adapter import verify_record as plugin
    from cryptography.hazmat.primitives import serialization as ser
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as K
    rd = json.loads(uploads[1][1])
    other_pem = K.generate().public_key().public_bytes(ser.Encoding.PEM, ser.PublicFormat.SubjectPublicKeyInfo).decode()
    check("genuine record + device key → True", plugin(rd, PUBKEY), True)
    check("location edited → False", plugin(dict(rd, location="Elsewhere"), PUBKEY), False)
    check("forged signature → False", plugin(dict(rd, signature="00" * 64), PUBKEY), False)
    check("another device's key → False", plugin(rd, other_pem), False)
    check("device enrolled with no key ('') → False", plugin(rd, ""), False)
    check("record missing a field → False", plugin({k: v for k, v in rd.items() if k != "id"}, PUBKEY), False)
    check("garbage enrolled key → ValueError (API answers 503)",
          raises(lambda: plugin(rd, "not a key"), ValueError), "ValueError")

    # ---- seed script run on the API laptop by mistake ----
    seed = api / "seed.jpg"; seed.write_bytes(b"demo")
    check("make_record on a machine without the key → RuntimeError",
          raises(lambda: R.make_record(seed, "photo"), RuntimeError), "RuntimeError")
    check("…no key was created and no record written",
          (api_key_path.exists(), (api / "data" / "records.jsonl").exists()), (False, False))

with machine(NOCAP_KEY_FILE=str(api_key_path), NOCAP_DATA_DIR=str(api / "data2"),
             NOCAP_KEY_PASSPHRASE="some-other-passphrase"):
    check("machine with a passphrase but no key/public file → clear error, no new key",
          (raises(R.public_key_pem, RuntimeError), api_key_path.exists()), ("RuntimeError", False))

# ================= Pi-side mistakes ==============================================
print("\n— Pi-side mistakes —")
x = captures / "x.jpg"; x.write_bytes(os.urandom(100))
rec = R.make_record(str(x), " Photo ")
check("kind ' Photo ' and str path accepted → stored as 'photo'", rec["type"], "photo")
tip_before = R.read_tip()
check("missing file → FileNotFoundError",
      raises(lambda: R.make_record(captures / "nope.jpg", "photo"), FileNotFoundError), "FileNotFoundError")
check("…chain not advanced", R.read_tip(), tip_before)
check("kind 'unknown' → ValueError", raises(lambda: R.make_record(x, "unknown"), ValueError), "ValueError")

errors = []
def press():
    try:
        R.make_record(x, "photo")
    except Exception as e:                                # noqa: BLE001 - record any failure
        errors.append(e)
threads = [threading.Thread(target=press) for _ in range(10)]
[t.start() for t in threads]; [t.join() for t in threads]
recs = R.load_records()
check("10 simultaneous button presses → no errors", errors, [])
check("…chain still intact", verify_chain(recs, R.read_tip()), (True, "chain intact"))
check("…every record links to a different previous one",
      len({r["prev_hash"] for r in recs}), len(recs))

with open(R.records_file(), "a", encoding="utf-8") as fh:
    fh.write("{this is not json\n")
report = verify_all(captures, R.public_key_pem())
check("corrupted line in records.jsonl → audit fails, no crash", report["ok"], False)

# ================= older Python on the Pi =========================================
import signing.verify as V
check("type hints stored as text (safe on Python 3.7–3.9)",
      all(isinstance(a, str) for a in V.verify_chain.__annotations__.values()), True)

shutil.rmtree(tmp)
print(f"\nAll {n} integration checks pass.")
