"""
Resume file persistence against Supabase Storage.

The container filesystem is ephemeral on Railway — every deploy wipes
generated files while the `resumes` DB rows survive. Generated resumes are
therefore uploaded to the existing `resumes` bucket under a deterministic
key (`generated/{resume_id}/{filename}`) so downloads survive redeploys:

    download = disk hit ? stream : materialize from Storage (cache to disk)

All supabase-py calls are synchronous and wrapped in asyncio.to_thread.
Failures here are logged and swallowed by callers — persistence is a
best-effort enhancement, never a reason to fail a generation.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BUCKET = "resumes"


def storage_key_for(resume_id: int, filename: str) -> str:
    """Deterministic object key so downloads survive redeploys."""
    return f"generated/{resume_id}/{Path(filename).name}"


def _get_sb():
    from api.dependencies import get_supabase_client
    return get_supabase_client()


async def persist_resume_file(resume_id: int, filename: str, local_path: str) -> bool:
    """Upload a generated resume to Storage. Returns False on any failure."""
    try:
        sb = _get_sb()
        data = await asyncio.to_thread(Path(local_path).read_bytes)

        def _upload():
            sb.storage.from_(BUCKET).upload(
                path=storage_key_for(resume_id, filename),
                file=data,
                file_options={"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "upsert": "true"},
            )

        await asyncio.to_thread(_upload)
        logger.info("Persisted resume %s to Storage as %s", resume_id, storage_key_for(resume_id, filename))
        return True
    except Exception as e:
        logger.warning("Could not persist resume %s to Storage (download falls back to disk only): %s", resume_id, e)
        return False


async def materialize_resume(resume_id: int, filename: str, local_path: str) -> Optional[str]:
    """Fetch a resume from Storage into local_path. Returns the path or None."""
    try:
        sb = _get_sb()
        data = await asyncio.to_thread(sb.storage.from_(BUCKET).download, storage_key_for(resume_id, filename))
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        await asyncio.to_thread(_write_bytes, local_path, data)
        logger.info("Materialized resume %s from Storage to %s", resume_id, local_path)
        return local_path
    except Exception as e:
        logger.info("Resume %s not available in Storage: %s", resume_id, e)
        return None


def _write_bytes(path: str, data: bytes):
    with open(path, "wb") as f:
        f.write(data)
