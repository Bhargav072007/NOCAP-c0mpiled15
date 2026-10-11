"""End-to-end test on synthetic captures. Run from repo root:  python -m tests.test_synthetic
Generates a real PNG photo, WAV voice note and JSON sensor reading (built-in Python only),
signs them like the Pi would, then tampers with them the ways an attacker might.
Uses a throwaway key and folder, so the real device key and records are untouched."""
import hashlib, json, math, os, shutil, struct, subprocess, sys, tempfile, wave, zlib
from pathlib import Path

tmp = Path(tempfile.mkdtemp())
os.environ["NOCAP_KEY_FILE"] = str(tmp / "keys" / "device_key.pem")
os.environ["NOCAP_DATA_DIR"] = str(tmp / "data")
os.environ["NOCAP_KEY_PASSPHRASE"] = "test-only-passphrase-123"

import signing.record as R
from signing.verify import (verify_record, verify_all, VERIFIED, TAMPERED_FILE,
                            TAMPERED_RECORD, BAD_SIGNATURE, FILE_MISSING)

caps = tmp / "captures"; caps.mkdir()
n = 0


def check(label, got, want):
    """Prints one numbered pass line, or stops with what went wrong."""
    global n; n += 1
    assert got == want, f"{label}: expected {want!r}, got {got!r}"
    print(f"{n:>3} {label:<52} ✓")


# --- synthetic data generators -------------------------------------------------
def make_png(path, w=64, h=48, poke=None):
    """Writes a real PNG (colour gradient). poke=(x, y, rgb) changes one pixel."""
    rows = [[((x * 4) % 256, (y * 5) % 256, 128) for x in range(w)] for y in range(h)]
    if poke:
        x, y, rgb = poke; rows[y][x] = rgb
    raw = b"".join(b"\x00" + bytes(c for px in row for c in px) for row in rows)
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def make_wav(path, seconds=1.0, rate=16000, freq=440):
    """Writes a real WAV voice-note stand-in (a 440 Hz tone)."""
    frames = b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * freq * i / rate)))
                      for i in range(int(seconds * rate)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(frames)


def make_reading(path, temp=21.4):
    """Writes a sensor reading as JSON."""
    path.write_text(json.dumps({"sensor": "BME280", "temperature_c": temp,
                                "humidity_pct": 41.2, "pressure_hpa": 1013.6}))


photo, audio, reading = caps / "2026-10-11T14-02-11.png", caps / "2026-10-11T14-02-11.wav", caps / "reading_001.json"
make_png(photo); make_wav(audio); make_reading(reading)
print(f"Synthetic data: photo {photo.stat().st_size:,} B, audio {audio.stat().st_size:,} B, "
      f"reading {reading.stat().st_size:,} B\n")
originals = {p: p.read_bytes() for p in (photo, audio, reading)}


def restore():
    """Puts every capture back to its original bytes."""
    for p, b in originals.items():
        p.write_bytes(b)


# --- 1. capture session, like a button press on the Pi -------------------------
R.load_key(create=True)                       # what `python -m signing.record` does once
rp = R.make_record(photo, "photo")
ra = R.make_record(audio, "audio")
rr = R.make_record(reading, "reading")
PUB = R.public_key_pem()
(R.data_dir() / "public_key.pem").write_text(PUB)

check("photo signed → VERIFIED", verify_record(rp, photo, PUB), VERIFIED)
check("voice note signed → VERIFIED", verify_record(ra, audio, PUB), VERIFIED)
check("sensor reading signed → VERIFIED", verify_record(rr, reading, PUB), VERIFIED)
check("records chained photo → audio → reading",
      (ra["prev_hash"], rr["prev_hash"]), (rp["record_hash"], ra["record_hash"]))
check("full audit → ok", verify_all(caps, PUB)["ok"], True)

# --- 2. tampering with the files -------------------------------------------------
make_png(photo, poke=(10, 10, (255, 0, 0)))
check("one pixel of photo recoloured → TAMPERED_FILE", verify_record(rp, photo, PUB), TAMPERED_FILE)
restore()

make_wav(audio, seconds=0.9)
check("voice note trimmed by 0.1 s → TAMPERED_FILE", verify_record(ra, audio, PUB), TAMPERED_FILE)
restore()

make_reading(reading, temp=35.0)
check("temperature changed 21.4 → 35.0 → TAMPERED_FILE", verify_record(rr, reading, PUB), TAMPERED_FILE)
restore()

other = caps / "other.png"; make_png(other, w=32, h=32); shutil.copy(other, photo)
check("photo swapped for a different image → TAMPERED_FILE", verify_record(rp, photo, PUB), TAMPERED_FILE)
restore()

photo.unlink()
check("photo deleted → FILE_MISSING", verify_record(rp, photo, PUB), FILE_MISSING)
restore()

# --- 3. tampering with the records ---------------------------------------------
moved = dict(rp, location="Somewhere else")
check("location edited in record → TAMPERED_RECORD", verify_record(moved, photo, PUB), TAMPERED_RECORD)

backdated = dict(rp, captured_at="2020-01-01T00:00:00+00:00")
check("timestamp backdated → TAMPERED_RECORD", verify_record(backdated, photo, PUB), TAMPERED_RECORD)

forged = dict(rp, location="Somewhere else")         # attacker also recomputes the hash…
forged["record_hash"] = hashlib.sha256(
    R.canonical({k: forged[k] for k in forged if k not in ("record_hash", "signature")})).hexdigest()
check("edited + re-hashed (no key to re-sign) → BAD_SIGNATURE", verify_record(forged, photo, PUB), BAD_SIGNATURE)

# --- 4. tampering with the stored history ---------------------------------------
lines = R.records_file().read_text().splitlines()
R.records_file().write_text("\n".join([lines[0], lines[2]]) + "\n")
report = verify_all(caps, PUB)
check("middle record deleted from history → audit fails", report["ok"], False)
print(f"      chain says: {report['chain']}")

R.records_file().write_text("\n".join(lines[:2]) + "\n")
report = verify_all(caps, PUB)
check("newest record deleted from history → audit fails", report["ok"], False)
print(f"      chain says: {report['chain']}")
R.records_file().write_text("\n".join(lines) + "\n")

# --- 5. the command-line audit a judge would see --------------------------------
def cli():
    """Runs `python -m signing.verify <captures>` the way a person would."""
    out = subprocess.run([sys.executable, "-m", "signing.verify", str(caps)], cwd=R.ROOT,
                         capture_output=True, text=True, encoding="utf-8", env=os.environ)
    return out.returncode, out.stdout.strip().splitlines()[-1]

check("CLI on untouched captures → COMPLETELY VERIFIED", cli(), (0, "COMPLETELY VERIFIED"))
make_png(photo, poke=(0, 0, (0, 0, 0)))
check("CLI after one-pixel edit → NOT VERIFIED", cli(), (1, "NOT VERIFIED"))
restore()

shutil.rmtree(tmp)
print(f"\nAll {n} synthetic-data checks pass.")
