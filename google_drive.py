"""Google Drive upload module cho Epione Content Agent."""

from __future__ import annotations

import json
import os
import mimetypes
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/drive"]
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gcp-key.json")


class GoogleDriveUploader:
    """Upload ảnh lên Google Drive (Shared Drive hoặc My Drive), tự tạo & cache thư mục theo sản phẩm."""

    def __init__(self, root_folder_id: str):
        self.root_folder_id = root_folder_id
        self.service = self._build_service()
        self._folder_cache: dict = {}

    def _build_service(self):
        # Ưu tiên env var GCP_KEY_JSON (cho Vercel/cloud), fallback sang file
        key_json = os.getenv("GCP_KEY_JSON")
        if key_json:
            info = json.loads(key_json)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )
        else:
            creds = service_account.Credentials.from_service_account_file(
                KEY_FILE, scopes=SCOPES
            )
        return build("drive", "v3", credentials=creds)

    # ------ Folder management ------

    def _find_folder(self, name: str, parent_id: str) -> Optional[str]:
        """Tìm folder theo tên trong parent."""
        q = (
            f"name='{name}' and '{parent_id}' in parents "
            f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        results = self.service.files().list(
            q=q,
            fields="files(id, name)",
            spaces="drive",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files = results.get("files", [])
        return files[0]["id"] if files else None

    def _create_folder(self, name: str, parent_id: str) -> str:
        """Tạo folder mới trong parent, trả về folder id."""
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = self.service.files().create(
            body=metadata,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        return folder["id"]

    def get_or_create_folder(self, product_name: str) -> str:
        """Lấy (hoặc tạo) folder cho sản phẩm. Dùng cache."""
        if product_name in self._folder_cache:
            return self._folder_cache[product_name]

        folder_id = self._find_folder(product_name, self.root_folder_id)
        if not folder_id:
            folder_id = self._create_folder(product_name, self.root_folder_id)

        self._folder_cache[product_name] = folder_id
        return folder_id

    # ------ Upload ------

    def upload_file(self, filepath: str, product_name: str) -> dict:
        """Upload file vào thư mục sản phẩm trên Drive.

        Returns:
            dict với id, name, webViewLink, webContentLink
        """
        folder_id = self.get_or_create_folder(product_name)

        filename = os.path.basename(filepath)
        mime_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"

        metadata = {
            "name": filename,
            "parents": [folder_id],
        }
        media = MediaFileUpload(filepath, mimetype=mime_type, resumable=True)

        file = self.service.files().create(
            body=metadata,
            media_body=media,
            fields="id, name, webViewLink, webContentLink",
            supportsAllDrives=True,
        ).execute()

        # Cho phép anyone có link xem được
        try:
            self.service.permissions().create(
                fileId=file["id"],
                body={"type": "anyone", "role": "reader"},
                supportsAllDrives=True,
            ).execute()
        except Exception:
            pass  # Shared Drive có thể không cho set permission riêng

        return {
            "id": file["id"],
            "name": file["name"],
            "webViewLink": file.get("webViewLink", ""),
            "webContentLink": file.get("webContentLink", ""),
            "folder": product_name,
        }

    def list_folders(self) -> list:
        """Liệt kê tất cả sub-folder trong root folder."""
        q = (
            f"'{self.root_folder_id}' in parents "
            f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        results = self.service.files().list(
            q=q,
            fields="files(id, name)",
            spaces="drive",
            orderBy="name",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        return results.get("files", [])

    def list_files_in_folder(self, folder_name: str) -> list:
        """Liệt kê files trong 1 folder sản phẩm."""
        folder_id = self.get_or_create_folder(folder_name)
        q = (
            f"'{folder_id}' in parents "
            f"and mimeType!='application/vnd.google-apps.folder' and trashed=false"
        )
        results = self.service.files().list(
            q=q,
            fields="files(id, name, webViewLink, webContentLink, mimeType, size)",
            spaces="drive",
            orderBy="createdTime desc",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        return results.get("files", [])
