"""Sanjay: make_record() — hashes a capture file, signs a record of it, stores the
record and chains it to the previous one.

Secrets never live in this file or in the repo:
  * the Ed25519 private key is stored OUTSIDE the project (default ~/.nocap/)
    and is encrypted with a passphrase;
  * the passphrase, key path, device id and location come from environment
    variables, normally loaded from a git-ignored `.env` file (see CONTEXT.md).
"""
from __future__ import annotations          # lets the type hints below run on older Python (Pi)
import hashlib, json, os, threading, uuid
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
GENESIS = "0" * 64                          # prev_hash of the very first record
KINDS = ("photo", "audio", "reading")
DEFAULT_DEVICE_ID = "nocap-pi5-01"          # team plan defaults, used if .env doesn't set them
DEFAULT_LOCATION = "EDI Building, Penn State"
_chain_lock = threading.Lock()              # one record at a time, so the chain can't fork


def load_env(path=ROOT / ".env"):
    """Reads KEY=VALUE lines from .env into os.environ. Real environment
    variables win, so nothing already set is overwritten."""
    if not Path(path).exists():
        return
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


load_env()


def key_file() -> Path:
    """Where the private key lives. Outside the repo by default so it can never be committed."""
    return Path(os.environ.get("NOCAP_KEY_FILE", Path.home() / ".nocap" / "device_key.pem"))


def data_dir() -> Path:
    """Folder holding records.jsonl (every record) and last_hash.txt (chain tip)."""
    return Path(os.environ.get("NOCAP_DATA_DIR", ROOT / "data"))


def records_file() -> Path:
    return data_dir() / "records.jsonl"


def chain_file() -> Path:
    return data_dir() / "last_hash.txt"


def public_key_file() -> Path:
    """Where the shareable public key is kept (data/public_key.pem unless NOCAP_PUBLIC_KEY_FILE is set)."""
    return Path(os.environ.get("NOCAP_PUBLIC_KEY_FILE", data_dir() / "public_key.pem"))


def _passphrase() -> bytes:
    """The key passphrase, taken only from the environment and never printed or stored."""
    secret = os.environ.get("NOCAP_KEY_PASSPHRASE", "")
    if len(secret) < 12:
        raise RuntimeError("Set NOCAP_KEY_PASSPHRASE (12+ characters) in .env "
                           "or the environment; the device key is encrypted with it.")
    return secret.encode()


def load_key(create: bool = False) -> Ed25519PrivateKey:
    """Unlocks the encrypted device key. Only creates a new one when create=True
    (done once by `python -m signing.record`), so a machine missing the key gets a
    clear error instead of silently becoming a different device.
    A wrong passphrase raises ValueError."""
    path = key_file()
    if path.exists():
        return serialization.load_pem_private_key(path.read_bytes(), password=_passphrase())
    if not create:
        raise RuntimeError(f"No device key at {path}. On the signing device, run "
                           "`python -m signing.record` once, or copy the shared device key there. "
                           "Machines that only verify don't need it.")
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.BestAvailableEncryption(_passphrase()))
    path.parent.mkdir(parents=True, exist_ok=True)
    # create with owner-only permissions (honoured on Linux / the Pi)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(pem)
    return key


def public_key_pem() -> str:
    """The PUBLIC half of the device key. Safe to share with verifiers.
    Uses the private key if this machine has it; otherwise reads public_key.pem,
    so verify-only machines (like the API laptop) need no secrets."""
    if key_file().exists():
        return load_key().public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    if public_key_file().exists():
        return public_key_file().read_text()
    raise RuntimeError(f"No public key found. Put the device's public_key.pem at "
                       f"{public_key_file()} or set NOCAP_PUBLIC_KEY_FILE.")


def sha256_file(path) -> str:
    """SHA-256 of a file's bytes, read in 1 MB chunks so large audio files are fine."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(d: dict) -> bytes:
    """Deterministic JSON (sorted keys, no spaces) so the same record always hashes the same."""
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def read_tip() -> str:
    """Hash of the newest record, or GENESIS if no record exists yet."""
    path = chain_file()
    return path.read_text().strip() if path.exists() else GENESIS


def _write_tip(record_hash: str):
    """Updates last_hash.txt atomically so a crash can't leave a half-written hash."""
    tmp = chain_file().with_suffix(".tmp")
    tmp.write_text(record_hash)
    os.replace(tmp, chain_file())


def make_record(path, kind, device_id=None, location=None) -> dict:
    """Builds, signs and stores the record for one capture, then advances the chain.
    Accepts a str or Path, and kind in any case ("Photo" → "photo")."""
    kind = str(kind).strip().lower()
    if kind not in KINDS:
        raise ValueError(f"type must be one of {KINDS}, got {kind!r}")
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"capture file not found: {path}")
    key = load_key()                        # fail early, before anything is written
    with _chain_lock:                       # two button presses at once can't fork the chain
        data_dir().mkdir(parents=True, exist_ok=True)
        # records exist but the chain tip is gone: refuse rather than silently start a new chain
        if not chain_file().exists() and load_records():
            raise RuntimeError(f"{chain_file()} is missing but records exist; "
                               "restore it before making new records.")
        rec = {
            "id": f"cap_{uuid.uuid4().hex[:8]}",
            "type": kind,
            "file_name": path.name,
            "file_sha256": sha256_file(path),
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "device_id": device_id or os.environ.get("NOCAP_DEVICE_ID") or DEFAULT_DEVICE_ID,
            "location": location or os.environ.get("NOCAP_LOCATION") or DEFAULT_LOCATION,
            "prev_hash": read_tip(),
        }
        rec["record_hash"] = hashlib.sha256(canonical(rec)).hexdigest()     # hash of the fields above
        rec["signature"] = key.sign(bytes.fromhex(rec["record_hash"])).hex()
        with open(records_file(), "a", encoding="utf-8") as f:              # store the record
            f.write(json.dumps(rec) + "\n")
        _write_tip(rec["record_hash"])                                      # then advance the chain
    return rec


def load_records() -> list[dict]:
    """Every stored record, oldest first. A corrupted line is kept as
    {"corrupt_line": ...} so the audit reports it instead of crashing or hiding it."""
    if not records_file().exists():
        return []
    out = []
    with open(records_file(), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    out.append({"corrupt_line": line.strip()})
    return out


if __name__ == "__main__":
    # python -m signing.record  → creates the device key (first time only) and
    # writes the public key to share with verifiers
    load_key(create=True)
    out = public_key_file()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(public_key_pem())
    print(f"Public key written to {out}")
