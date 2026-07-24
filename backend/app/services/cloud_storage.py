from __future__ import annotations
from pathlib import Path
import httpx
from ..config import get_settings

class StorageError(RuntimeError): pass

class CloudStorage:
    def __init__(self):
        self.settings=get_settings()
    @property
    def enabled(self):
        return bool(self.settings.supabase_url and self.settings.supabase_service_role_key)
    def upload(self, local_path: str | Path, object_name: str, content_type: str="application/octet-stream") -> str:
        if not self.enabled: return str(local_path)
        path=Path(local_path)
        url=f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/{self.settings.supabase_storage_bucket}/{object_name.lstrip('/')}"
        headers={"Authorization":f"Bearer {self.settings.supabase_service_role_key}","apikey":self.settings.supabase_service_role_key,"Content-Type":content_type,"x-upsert":"true"}
        with path.open("rb") as handle:
            response=httpx.post(url,headers=headers,content=handle.read(),timeout=60)
        if response.status_code >= 300: raise StorageError(f"Supabase Storage upload failed ({response.status_code}): {response.text[:300]}")
        return object_name
    def signed_url(self, object_name: str, expires_in: int=900) -> str | None:
        if not self.enabled: return None
        url=f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/sign/{self.settings.supabase_storage_bucket}/{object_name.lstrip('/')}"
        headers={"Authorization":f"Bearer {self.settings.supabase_service_role_key}","apikey":self.settings.supabase_service_role_key}
        response=httpx.post(url,headers=headers,json={"expiresIn":expires_in},timeout=30)
        if response.status_code >= 300: raise StorageError(f"Signed URL failed ({response.status_code})")
        signed=response.json().get("signedURL")
        return f"{self.settings.supabase_url.rstrip('/')}/storage/v1{signed}" if signed else None
cloud_storage=CloudStorage()
