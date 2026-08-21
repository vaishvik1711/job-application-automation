"""
Job-site credential management routes.

Security contract (see backend/CLAUDE.md):
- passwords are Fernet-encrypted at rest with CREDENTIAL_ENCRYPTION_KEY
- GET returns masked username hints only — never a password or ciphertext
- PUT with an empty password keeps the existing one
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session
from api.schemas import ApiResponse
from database.models import SiteCredential
from security.crypto import (
    CredentialCryptoError,
    encrypt_secret,
    encryption_configured,
    mask_username,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Must match browser/sites/detect_site — the only sites we will ever store.
ALLOWED_SITES = ("jobbank", "greenhouse", "lever")


def _credential_hint(site: str, cred: Optional[SiteCredential]) -> dict:
    """Masked display shape for one site. `site` always wins over anything
    derived from the (possibly absent) DB row."""
    if cred is None:
        return {
            "site": site,
            "configured": False,
            "username_hint": None,
            "updated_at": None,
        }
    return {
        "site": site,
        "configured": bool(cred.password_encrypted),
        "username_hint": mask_username(cred.username) if cred.username else None,
        # NOTE: password_encrypted is deliberately never serialized.
        "updated_at": cred.updated_at.isoformat() if cred.updated_at else None,
    }


@router.get("/settings/credentials", response_model=ApiResponse)
async def list_credentials(session: AsyncSession = Depends(get_db_session)):
    """List configured job-site logins as masked hints (no secrets)."""
    result = await session.execute(select(SiteCredential))
    creds = {c.site: c for c in result.scalars().all()}
    return ApiResponse(data={
        "encryption_configured": encryption_configured(),
        "sites": [_credential_hint(site, creds.get(site)) for site in ALLOWED_SITES],
    })


@router.put("/settings/credentials/{site}", response_model=ApiResponse)
async def save_credentials(
    site: str,
    body: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Store or update a job-site login. Empty password keeps the existing one."""
    site = site.lower().strip()
    if site not in ALLOWED_SITES:
        raise HTTPException(status_code=400, detail=f"Unsupported site: {site}")
    if not encryption_configured():
        raise HTTPException(
            status_code=400,
            detail="CREDENTIAL_ENCRYPTION_KEY is not set on the server — cannot store credentials",
        )

    username = (body.get("username") or "").strip() or None
    password = body.get("password")
    extra = body.get("extra") if isinstance(body.get("extra"), dict) else {}

    result = await session.execute(select(SiteCredential).where(SiteCredential.site == site))
    cred = result.scalars().first()
    if cred is None:
        cred = SiteCredential(site=site)
        session.add(cred)

    if username is not None:
        cred.username = username
    if password:  # empty string / null → keep existing
        try:
            cred.password_encrypted = encrypt_secret(str(password))
        except CredentialCryptoError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    if extra:
        merged = dict(cred.extra or {})
        merged.update(extra)
        cred.extra = merged

    await session.flush()
    logger.info("Credential stored for site=%s (password never logged)", site)
    return ApiResponse(data=_credential_hint(site, cred), message="Credentials saved")


@router.delete("/settings/credentials/{site}", response_model=ApiResponse)
async def delete_credentials(
    site: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Remove a stored login entirely."""
    site = site.lower().strip()
    if site not in ALLOWED_SITES:
        raise HTTPException(status_code=400, detail=f"Unsupported site: {site}")

    result = await session.execute(select(SiteCredential).where(SiteCredential.site == site))
    cred = result.scalars().first()
    if cred is not None:
        await session.delete(cred)
        await session.flush()
    return ApiResponse(data={"site": site, "configured": False}, message="Credentials removed")
