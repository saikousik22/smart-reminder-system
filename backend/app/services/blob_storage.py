import logging
from datetime import datetime, timezone, timedelta
from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
    BlobSasPermissions,
)
from app.config import get_settings

logger = logging.getLogger(__name__)


def _parse_conn_str(conn_str: str) -> dict:
    """Split 'Key=Value;Key=Value' — partition on first '=' handles base64 values."""
    result = {}
    for segment in conn_str.split(";"):
        if "=" in segment:
            key, _, value = segment.partition("=")
            result[key] = value
    return result


def _container_client():
    settings = get_settings()
    return BlobServiceClient.from_connection_string(
        settings.AZURE_STORAGE_CONNECTION_STRING
    ).get_container_client(settings.AZURE_CONTAINER_NAME)


def upload_audio(blob_path: str, data: bytes, content_type: str = "audio/wav") -> None:
    """Upload bytes to private blob storage."""
    blob = _container_client().get_blob_client(blob_path)
    blob.upload_blob(
        data,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
    )


def generate_sas_url(blob_path: str, expiry_hours: int = 24) -> str:
    """Return a time-limited SAS URL so Twilio can fetch a private audio blob."""
    settings = get_settings()
    parsed = _parse_conn_str(settings.AZURE_STORAGE_CONNECTION_STRING)
    account_name = parsed["AccountName"]
    account_key = parsed["AccountKey"]

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=settings.AZURE_CONTAINER_NAME,
        blob_name=blob_path,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
    )
    return (
        f"https://{account_name}.blob.core.windows.net"
        f"/{settings.AZURE_CONTAINER_NAME}/{blob_path}?{sas_token}"
    )


def delete_audio(blob_path: str) -> None:
    try:
        _container_client().get_blob_client(blob_path).delete_blob()
    except Exception as exc:
        logger.warning(f"Could not delete blob '{blob_path}': {exc}")


def copy_audio(source_path: str, dest_path: str) -> None:
    """Server-side copy within the same container."""
    container = _container_client()
    source_url = container.get_blob_client(source_path).url
    container.get_blob_client(dest_path).start_copy_from_url(source_url)
