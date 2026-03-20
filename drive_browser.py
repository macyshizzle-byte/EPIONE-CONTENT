"""Browse và download ảnh từ Google Drive folder (hỗ trợ Shared Drive)."""

import io
import json
import os
from typing import Optional, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

GCP_KEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drive-key.json")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

IMAGE_MIMES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "image/svg+xml", "image/bmp", "image/tiff",
}

# Root folder ID — dùng để detect Shared Drive
DRIVE_ROOT = os.getenv("DRIVE_FOLDER_ID", "")


def _get_service():
    """Tạo Google Drive API service từ service account key."""
    # Ưu tiên env var GCP_DRIVE_KEY_JSON (cho Vercel), fallback sang file
    key_json = os.getenv("GCP_DRIVE_KEY_JSON")
    if key_json:
        info = json.loads(key_json)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES,
        )
    else:
        creds = service_account.Credentials.from_service_account_file(
            GCP_KEY_PATH, scopes=SCOPES,
        )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _is_shared_drive(folder_id: str) -> bool:
    """Check nếu folder_id là Shared Drive root (bắt đầu bằng 0A)."""
    return folder_id.startswith("0A")


def _list_kwargs(folder_id: str, query: str, page_size: int,
                 page_token: Optional[str], fields: str,
                 order_by: Optional[str] = None):
    """Build kwargs cho files().list() — tự detect Shared Drive."""
    kwargs = {
        "q": query,
        "pageSize": page_size,
        "fields": fields,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
    }
    if page_token:
        kwargs["pageToken"] = page_token
    if order_by:
        kwargs["orderBy"] = order_by

    # Nếu là Shared Drive root, dùng corpora=drive + driveId
    if _is_shared_drive(folder_id):
        kwargs["corpora"] = "drive"
        kwargs["driveId"] = folder_id
    elif _is_shared_drive(DRIVE_ROOT):
        # Sub-folder trong Shared Drive vẫn cần corpora=drive
        kwargs["corpora"] = "drive"
        kwargs["driveId"] = DRIVE_ROOT

    return kwargs


def list_drive_images(folder_id: str, page_token: Optional[str] = None, page_size: int = 30):
    """Liệt kê ảnh trong folder Drive.

    Returns:
        dict với keys: files, nextPageToken
    """
    service = _get_service()

    # Với Shared Drive root, list tất cả file trong drive (không filter parent)
    if _is_shared_drive(folder_id):
        mime_clauses = " or ".join(f"mimeType='{m}'" for m in IMAGE_MIMES)
        query = f"({mime_clauses}) and trashed = false"
    else:
        query = f"'{folder_id}' in parents and trashed = false"
        mime_clauses = " or ".join(f"mimeType='{m}'" for m in IMAGE_MIMES)
        query += f" and ({mime_clauses})"

    kwargs = _list_kwargs(
        folder_id, query, page_size, page_token,
        fields="nextPageToken, files(id, name, mimeType, size, thumbnailLink, createdTime, modifiedTime)",
        order_by="modifiedTime desc",
    )
    result = service.files().list(**kwargs).execute()

    files = []
    for f in result.get("files", []):
        thumb = f.get("thumbnailLink", "")
        # Tăng kích thước thumbnail
        if thumb and "=s" in thumb:
            thumb = thumb.split("=s")[0] + "=s400"
        files.append({
            "id": f["id"],
            "name": f["name"],
            "mimeType": f["mimeType"],
            "size": int(f.get("size", 0)),
            "thumbnail": thumb,
            "createdTime": f.get("createdTime", ""),
            "modifiedTime": f.get("modifiedTime", ""),
        })

    return {
        "files": files,
        "nextPageToken": result.get("nextPageToken"),
    }


def list_drive_folders(folder_id: str):
    """Liệt kê sub-folders trong một folder."""
    service = _get_service()

    if _is_shared_drive(folder_id):
        # Shared Drive root: list top-level folders
        query = f"mimeType='application/vnd.google-apps.folder' and trashed = false"
    else:
        query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed = false"

    kwargs = _list_kwargs(
        folder_id, query, 100, None,
        fields="files(id, name, modifiedTime)",
        order_by="name",
    )
    result = service.files().list(**kwargs).execute()

    return result.get("files", [])


def download_drive_file(file_id: str) -> Tuple[bytes, str, str]:
    """Download file từ Drive.

    Returns:
        (file_bytes, filename, mime_type)
    """
    service = _get_service()

    # Lấy metadata
    meta = service.files().get(
        fileId=file_id,
        fields="name, mimeType, size",
        supportsAllDrives=True,
    ).execute()

    # Download content
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    buffer.seek(0)
    return buffer.read(), meta["name"], meta["mimeType"]
