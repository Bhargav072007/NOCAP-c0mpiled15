"""
Shared pytest fixtures for the NoCap local database tests.

This module provides a session-scoped fixture that generates three REAL,
deterministic, TEST_ONLY synthetic capture files under ``tests/fixtures/``:

  * ``test_photo.jpg``  -- a minimal valid JPEG (real SOI ``FFD8`` + JFIF APP0 +
                            EOI ``FFD9``). Pure bytes, no Pillow dependency.
  * ``test_audio.wav``  -- 0.1 s of silence, 44100 Hz, 16-bit mono, built with the
                            stdlib ``wave`` module. No third-party audio library.
  * ``test_sensor.json`` -- a realistic fake sensor reading, clearly labeled
                            TEST_ONLY, written as pretty-printed JSON.

Only the Python standard library is used (``os``, ``struct``, ``wave``, ``json``).
Because the file bytes are fixed, the SHA-256 digests are identical on every run.

The generated files under ``tests/fixtures/`` are TEST_ONLY artifacts. They are
NOT committed or pushed (honor the "do not commit / push" rule).
"""

from __future__ import annotations

import json
import os
import struct
import wave
from pathlib import Path

import pytest

# Directory that holds the generated synthetic fixtures. Lives next to this
# conftest so the fixtures are co-located with the tests that consume them.
FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"


def _write_test_jpeg(path: Path) -> None:
    """Write a minimal but valid JPEG file using pure bytes (no Pillow).

    Structure (a real, parseable JFIF JPEG):
      SOI marker   FF D8
      APP0/JFIF    FF E0 + length(16) + "JFIF\0" + version + density units + density
      EOI marker   FF D9
    Total length is 22 bytes; the magic bytes are ``FFD8FF`` and it ends with
    ``FFD9``, exactly as a JPEG must.
    """
    # Start Of Image
    soi = b"\xff\xd8"
    # APP0 marker + JFIF identifier block (length includes the 2 length bytes)
    app0 = (
        b"\xff\xe0"
        + (16).to_bytes(2, "big")          # APP0 segment length = 16
        + b"JFIF\x00"                       # identifier + zero terminator
        + b"\x01\x01"                       # JFIF version 1.1
        + b"\x00"                           # density units: 0 = no units
        + b"\x00\x01\x00\x01"               # X density = 1, Y density = 1
        + b"\x00\x00"                       # thumbnail width/height = 0 (none)
    )
    # End Of Image
    eoi = b"\xff\xd9"
    path.write_bytes(soi + app0 + eoi)


def _write_test_wav(path: Path) -> None:
    """Write a minimal valid WAV file: 0.1 s of silence, 44100 Hz, 16-bit mono.

    Uses only the stdlib ``wave`` module. 4410 frames at 44100 Hz == 0.1 s.
    Each 16-bit sample is two zero bytes.
    """
    n_frames = 4410  # 44100 Hz * 0.1 s
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)            # mono
        wf.setsampwidth(2)            # 16-bit
        wf.setframerate(44100)        # 44.1 kHz
        wf.writeframes(b"\x00\x00" * n_frames)


def _write_test_sensor_json(path: Path) -> None:
    """Write a realistic fake sensor reading as JSON, clearly labeled TEST_ONLY."""
    payload = {
        "sensor_id": "TEST_ONLY_sensor_001",
        "label": "TEST_ONLY",
        "timestamp": "2026-10-11T20:00:00Z",
        "location": {"lat": 37.7749, "lon": -122.4194},
        "readings": [
            {"name": "temperature_c", "value": 22.4},
            {"name": "humidity_pct", "value": 61.2},
            {"name": "battery_v", "value": 3.7},
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _ensure_fixtures() -> dict[str, Path]:
    """Idempotently create the three fixture files and return their paths.

    Safe to call multiple times: the bytes are deterministic, so the files are
    overwritten with identical content (and therefore identical SHA-256).
    """
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "photo": FIXTURES_DIR / "test_photo.jpg",
        "audio": FIXTURES_DIR / "test_audio.wav",
        "sensor": FIXTURES_DIR / "test_sensor.json",
    }
    _write_test_jpeg(paths["photo"])
    _write_test_wav(paths["audio"])
    _write_test_sensor_json(paths["sensor"])
    return paths


@pytest.fixture(scope="session")
def fixture_paths() -> dict[str, Path]:
    """Session fixture: ensure the three TEST_ONLY synthetic files exist.

    Returns a mapping ``{"photo": Path, "audio": Path, "sensor": Path}``
    pointing at real files whose bytes are deterministic.
    """
    return _ensure_fixtures()
