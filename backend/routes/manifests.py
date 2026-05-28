from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()

ALLOWED_DOMAINS = [
    "iiif.library.ucla.edu",
    "digital.library.ucla.edu",
    "iiif.library.ucla.edu",
]


@router.get("/proxy")
async def proxy_manifest(url: str):
    """Proxy a IIIF manifest to avoid CORS issues in the browser."""
    parsed = urlparse(url)
    if not any(parsed.netloc.endswith(d) for d in ALLOWED_DOMAINS):
        raise HTTPException(status_code=400, detail=f"Domain not in allowlist: {parsed.netloc}")

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        try:
            resp = await client.get(
                url,
                headers={"Accept": "application/ld+json,application/json;q=0.9,*/*;q=0.8"},
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Upstream returned {e.response.status_code}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch manifest: {e}")

    return JSONResponse(content=data, headers={"Cache-Control": "public, max-age=3600"})
