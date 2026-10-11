"""
Local SQLite database test for the NoCap backend (synthetic / TEST_ONLY).

This module proves, end to end, that the real NoCap ORM model (``cloud.models.Capture``)
can store and retrieve three synthetic captures in a throwaway local SQLite database:

  1. A photo capture    (real ``test_photo.jpg``)
  2. An audio capture    (real ``test_audio.wav``)
  3. A sensor capture    (real ``test_sensor.json``)

For each capture we compute the REAL SHA-256 of the file at runtime (we never hardcode
the digest), insert a single row using the EXACT column names from the real schema, then
retrieve all rows and assert the IDs, file types, filenames, hashes, and TEST_ONLY labels.

Hard constraints honored by this file:
  * SQLite ONLY. We build our own ``sqlite:///<tmp_path>/nocap_test.db`` engine and call
    ``Base.metadata.create_all(engine)`` ourselves. We never use ``cloud.database.engine``
    or ``cloud.database.SessionLocal``.
  * No AWS / S3 / RDS: we never import ``cloud.s3_service`` or ``boto3``. We also pin
    ``DATABASE_URL`` to a local sqlite value BEFORE importing any ``cloud.*`` module so
    the unused module-level engine in ``cloud.database`` can never target RDS.
  * We do NOT modify any ``cloud/`` file. We adapt to the real schema as-is.
  * Synthetic data only; every record is labeled TEST_ONLY via ``user_id="TEST_ONLY"``
    and a ``TEST_ONLY_`` filename prefix inside ``s3_key``.
  * No invented digital signatures and no VERIFIED labels: the ``Capture`` schema has no
    ``verified`` boolean and no ``signature`` column (verified by introspection), so there
    is simply no field that could hold a fake signature or a VERIFIED flag. We therefore set
    neither field, which satisfies the rule by schema design.

Schema adaptation (see .agents/tasks/plan.md, sections A & B):
  * There is NO ``filename`` column     -> filename is stored as the prefix of ``s3_key``.
  * There is NO ``hash``/``digest`` col  -> the 64-char SHA-256 hex is stored in ``s3_key``
                                            after a ``::`` delimiter: ``<filename>::<sha256>``.
  * There is NO ``label``/``note`` col   -> TEST_ONLY is carried by ``user_id="TEST_ONLY"``
                                            plus the ``TEST_ONLY_`` filename prefix.
  * There is NO ``verified`` column      -> nothing to set (see B.3 comment below).
  * There is NO ``signature`` column     -> nothing to set (see B.3 comment below).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# IMPORTANT: pin DATABASE_URL to a local sqlite value BEFORE importing any
# cloud.* module. cloud.database reads DATABASE_URL (defaulting to a local
# sqlite file) at import time to build a module-level engine. load_dotenv()
# does not override an already-set env var, so this guarantees that even if a
# real .env appears later, the unused module-level engine never points at AWS
# RDS. (This test never uses that engine anyway.)
# ---------------------------------------------------------------------------
import os

os.environ["DATABASE_URL"] = "sqlite:///./nocap_test_unused.db"

import hashlib
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the REAL declarative base and capture model (read-only usage).
from cloud.database import Base
from cloud.models import Capture

# ---------------------------------------------------------------------------
# Expected TEST_ONLY capture definitions: (filename, content_type / MIME).
# The "type" of each capture is represented by its MIME type in content_type,
# because the real schema has no dedicated "type" column.
# ---------------------------------------------------------------------------
EXPECTED_CAPTURES = [
    ("test_photo.jpg", "image/jpeg"),        # photo
    ("test_audio.wav", "audio/wav"),         # audio
    ("test_sensor.json", "application/json"),  # sensor
]


def _sha256_of(path: Path) -> str:
    """Compute the real SHA-256 hex digest of a file's bytes at runtime."""
    with path.open("rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _build_s3_key(filename: str, sha256_hex: str) -> str:
    """Build the value stored in ``s3_key``: ``TEST_ONLY_<filename>::<sha256>``.

    A dedicated hash column does not exist, so the 64-char digest is carried
    inside ``s3_key`` after a ``::`` delimiter. ``s3_key`` is VARCHAR(512), so
    there is ample room (filename ~20 chars + ``::`` + 64 hex chars).
    """
    return f"TEST_ONLY_{filename}::{sha256_hex}"


@pytest.fixture()
def temp_db(tmp_path):
    """Create a fresh, isolated local SQLite database for one test.

    Builds the test's OWN engine bound to a file inside the pytest ``tmp_path``
    and creates all tables with ``Base.metadata.create_all(engine)``. Returns a
    tuple ``(engine, session_factory)``. Each test gets its own database so the
    tests are fully isolated from one another and from any real database.
    """
    db_path = tmp_path / "nocap_test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    yield engine, Session
    # Drop tables so we do not leak anything between tests/iterations.
    Base.metadata.drop_all(engine)
    engine.dispose()


def _insert_three_captures(Session, fixture_paths: dict[str, Path]) -> list[Capture]:
    """Insert the three TEST_ONLY captures and return the inserted rows.

    NOTE on verified / signature (see plan B.3):
        The real ``Capture`` schema has NO ``verified`` boolean and NO
        ``signature``/``digital_signature`` column (verified by column
        introspection: columns are exactly
        ``['id', 'user_id', 's3_key', 'content_type', 'status', 'created_at']``).
        Therefore these records are inherently unsigned and unverifiable. This
        satisfies the rule that we do not invent valid digital signatures and do
        not label unsigned records VERIFIED -- there is no field that could be
        set to a fake signature or to VERIFIED. We deliberately set NEITHER a
        ``verified`` nor a ``signature`` attribute.
    """
    rows: list[Capture] = []
    with Session() as session:
        for filename, content_type in EXPECTED_CAPTURES:
            # Pick the matching fixture file.
            if filename.endswith(".jpg"):
                file_path = fixture_paths["photo"]
            elif filename.endswith(".wav"):
                file_path = fixture_paths["audio"]
            else:
                file_path = fixture_paths["sensor"]

            sha256_hex = _sha256_of(file_path)
            s3_key = _build_s3_key(filename, sha256_hex)

            capture = Capture(
                user_id="TEST_ONLY",                # marks every row as test data
                s3_key=s3_key,                        # filename + real SHA-256
                content_type=content_type,            # MIME type == capture "type"
                status="pending",
            )
            session.add(capture)
            rows.append(capture)
        session.commit()
        # Refresh so server_default columns (created_at, id) are populated.
        for row in rows:
            session.refresh(row)
    return rows


def _retrieve_all(Session) -> list[Capture]:
    """Retrieve all Capture rows ordered by id."""
    with Session() as session:
        return session.query(Capture).order_by(Capture.id).all()


# ===========================================================================
# Tests
# ===========================================================================


def test_three_captures_inserted_and_retrieved(temp_db, fixture_paths):
    """Verify that exactly three TEST_ONLY captures are inserted and retrievable."""
    engine, Session = temp_db
    _insert_three_captures(Session, fixture_paths)
    rows = _retrieve_all(Session)
    assert len(rows) == 3, f"expected exactly 3 records, got {len(rows)}"


def test_capture_ids_are_unique_integers(temp_db, fixture_paths):
    """Verify each retrieved capture has a unique integer primary key id."""
    engine, Session = temp_db
    _insert_three_captures(Session, fixture_paths)
    rows = _retrieve_all(Session)
    ids = [row.id for row in rows]
    assert all(isinstance(i, int) for i in ids), f"ids must be ints: {ids}"
    assert len(set(ids)) == 3, f"ids must be unique: {ids}"


def test_capture_types_match_expected_mime(temp_db, fixture_paths):
    """Verify each capture's content_type (MIME) matches its expected type."""
    engine, Session = temp_db
    _insert_three_captures(Session, fixture_paths)
    rows = _retrieve_all(Session)
    expected_mimes = [ct for _fn, ct in EXPECTED_CAPTURES]
    actual_mimes = [row.content_type for row in rows]
    assert actual_mimes == expected_mimes, (
        f"MIME types mismatch: expected {expected_mimes}, got {actual_mimes}"
    )


def test_filenames_match_expected(temp_db, fixture_paths):
    """Verify the filename portion of s3_key matches, with TEST_ONLY_ prefix."""
    engine, Session = temp_db
    _insert_three_captures(Session, fixture_paths)
    rows = _retrieve_all(Session)
    for row, (expected_fn, _ct) in zip(rows, EXPECTED_CAPTURES):
        filename, _sep, _digest = row.s3_key.partition("::")
        assert filename == f"TEST_ONLY_{expected_fn}", (
            f"filename mismatch: expected TEST_ONLY_{expected_fn}, got {filename}"
        )
        assert filename.startswith("TEST_ONLY_"), (
            f"filename must be TEST_ONLY-prefixed: {filename}"
        )


def test_stored_hashes_match_real_sha256(temp_db, fixture_paths):
    """Verify the stored SHA-256 equals the recomputed real SHA-256 of each file."""
    engine, Session = temp_db
    _insert_three_captures(Session, fixture_paths)
    rows = _retrieve_all(Session)
    for row, (expected_fn, _ct) in zip(rows, EXPECTED_CAPTURES):
        if expected_fn.endswith(".jpg"):
            file_path = fixture_paths["photo"]
        elif expected_fn.endswith(".wav"):
            file_path = fixture_paths["audio"]
        else:
            file_path = fixture_paths["sensor"]
        expected_hash = _sha256_of(file_path)
        _filename, _sep, stored_hash = row.s3_key.partition("::")
        assert stored_hash == expected_hash, (
            f"hash mismatch for {expected_fn}: expected {expected_hash}, "
            f"got {stored_hash}"
        )
        # A SHA-256 hex digest is always 64 hex chars.
        assert len(stored_hash) == 64 and all(
            c in "0123456789abcdef" for c in stored_hash
        ), f"stored hash is not a 64-char hex digest: {stored_hash}"


def test_records_labeled_test_only(temp_db, fixture_paths):
    """Verify every record is labeled TEST_ONLY via user_id and filename prefix."""
    engine, Session = temp_db
    _insert_three_captures(Session, fixture_paths)
    rows = _retrieve_all(Session)
    for row in rows:
        assert row.user_id == "TEST_ONLY", (
            f"user_id must be TEST_ONLY: {row.user_id!r}"
        )
        assert row.s3_key.startswith("TEST_ONLY_"), (
            f"s3_key must start with TEST_ONLY_: {row.s3_key!r}"
        )


def test_no_verified_or_signature_columns_invented(temp_db):
    """Confirm the real schema has no verified/signature columns (compliance check).

    This is a structural assertion: we verify that ``Capture`` exposes no
    ``verified`` and no ``signature``/``digital_signature`` column, which is what
    guarantees we cannot accidentally invent a valid signature or mark an
    unsigned record VERIFIED. We assert instead of just commenting so a future
    schema change is caught.
    """
    column_names = {c.name for c in Capture.__table__.columns}
    assert "verified" not in column_names, (
        "schema unexpectedly has a 'verified' column; review the test"
    )
    assert "signature" not in column_names and "digital_signature" not in column_names, (
        "schema unexpectedly has a signature column; review the test"
    )


def test_created_at_is_auto_populated(temp_db, fixture_paths):
    """Verify created_at is automatically populated by the database (server_default)."""
    engine, Session = temp_db
    _insert_three_captures(Session, fixture_paths)
    rows = _retrieve_all(Session)
    for row in rows:
        assert row.created_at is not None, "created_at must be populated by the DB"


def test_summary_of_three_records(temp_db, fixture_paths, capsys):
    """End-to-end smoke test: insert, retrieve, and print a human-readable summary.

    This prints the three retrieved records (id, type, filename, SHA-256, user_id,
    status, created_at) and re-asserts all the core properties in one place so the
    printed summary is only emitted when the records are actually correct.
    """
    engine, Session = temp_db
    _insert_three_captures(Session, fixture_paths)
    rows = _retrieve_all(Session)

    assert len(rows) == 3
    expected_mimes = [ct for _fn, ct in EXPECTED_CAPTURES]
    actual_mimes = [row.content_type for row in rows]
    assert actual_mimes == expected_mimes

    print("\n================ NoCap TEST_ONLY Capture Summary ================")
    for row in rows:
        filename, _sep, digest = row.s3_key.partition("::")
        print(
            f"id={row.id} | type={row.content_type} | filename={filename} | "
            f"sha256={digest} | user_id={row.user_id} | status={row.status} | "
            f"created_at={row.created_at}"
        )
    print("==================================================================")
