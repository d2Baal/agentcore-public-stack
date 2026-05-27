"""Public branding endpoint — no authentication required."""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from apis.app_api.admin.branding.models import BrandingConfigResponse
from apis.app_api.admin.branding import service, repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/branding", tags=["branding"])

_ALLOWED_ASSET_TYPES = {"logo_light", "logo_dark", "favicon"}


@router.get("", response_model=BrandingConfigResponse)
async def get_public_branding():
    """
    Return the current branding configuration.

    Public endpoint — no authentication required.  Called by the SPA at startup
    so the login page and pre-auth screens use the correct brand colors and logos.

    Logo/favicon URLs are returned as stable API-relative paths
    (e.g. ``/branding/asset/logo_light``) that redirect to a fresh S3 presigned
    URL on every browser request, so they never expire.
    """
    try:
        return await service.get_branding_response()
    except Exception:
        logger.exception("Error fetching public branding config")
        # Degrade gracefully — return empty config so defaults apply
        return BrandingConfigResponse()


@router.get("/asset/{asset_type}")
async def get_branding_asset(asset_type: str):
    """Redirect to a fresh S3 presigned GET URL for the requested branding asset.

    This stable endpoint is what the SPA embeds in ``<img src>``.  On each
    browser request the redirect target is regenerated, so the image never
    expires regardless of how long the SPA has been open.

    Public endpoint — no authentication required.
    """
    if asset_type not in _ALLOWED_ASSET_TYPES:
        raise HTTPException(status_code=404, detail="Unknown asset type")
    try:
        config = await repository.get_branding()
    except Exception:
        raise HTTPException(status_code=503, detail="Branding unavailable")
    if not config:
        raise HTTPException(status_code=404, detail="No branding configured")
    s3_key = getattr(config, f"{asset_type}_s3_key", None)
    if not s3_key:
        raise HTTPException(status_code=404, detail="Asset not uploaded")
    presigned_url = service._presigned_get_url(s3_key)
    return RedirectResponse(url=presigned_url, status_code=302)
