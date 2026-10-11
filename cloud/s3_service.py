"""
S3 file operations for NoCap.

All methods are stubs — they read configuration from environment variables
but do not make live AWS calls yet.  Replace `pass` / `raise NotImplementedError`
with real boto3 calls in a future task.

Environment variables (see .env.example):
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    AWS_REGION          (default: us-east-2)
    S3_BUCKET_NAME
"""

import os
from typing import BinaryIO

import boto3
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def _get_s3_client():
    """Return a boto3 S3 client configured from environment variables."""
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-2"),
    )


_BUCKET: str = os.getenv("S3_BUCKET_NAME", "")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def upload_file(file_obj: BinaryIO, s3_key: str, content_type: str = "application/octet-stream") -> str:
    """
    Upload a file-like object to S3.

    Args:
        file_obj:     An open binary file-like object (e.g. from FastAPI's UploadFile).
        s3_key:       The destination key inside the S3 bucket.
        content_type: MIME type of the file.

    Returns:
        The S3 key of the uploaded object.

    Raises:
        NotImplementedError: Until implemented.
    """
    raise NotImplementedError("upload_file is not yet implemented")


def download_file(s3_key: str) -> bytes:
    """
    Download a file from S3 and return its contents as bytes.

    Args:
        s3_key: The S3 key to download.

    Returns:
        Raw file bytes.

    Raises:
        NotImplementedError: Until implemented.
    """
    raise NotImplementedError("download_file is not yet implemented")


def delete_file(s3_key: str) -> None:
    """
    Delete an object from S3.

    Args:
        s3_key: The S3 key to delete.

    Raises:
        NotImplementedError: Until implemented.
    """
    raise NotImplementedError("delete_file is not yet implemented")


def generate_presigned_url(s3_key: str, expiry_seconds: int = 3600) -> str:
    """
    Generate a pre-signed URL that allows temporary public access to an object.

    Args:
        s3_key:         The S3 key of the object.
        expiry_seconds: How long the URL remains valid (default: 1 hour).

    Returns:
        A pre-signed HTTPS URL string.

    Raises:
        NotImplementedError: Until implemented.
    """
    raise NotImplementedError("generate_presigned_url is not yet implemented")
