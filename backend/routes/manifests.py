from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..database import get_db

router = APIRouter()

# Fallback domains used before any volumes are added to the database
_FALLBACK_DOMAINS = [
    "iiif.library.ucla.edu",
    "digital.library.ucla.edu",
]


def _allowed_domains(db) -> set[str]:
    """Derive allowed domains from manifest URLs already in the volumes table."""
    rows = db.execute("SELECT manifest_url FROM volumes").fetchall()
    domains = {urlparse(r["manifest_url"]).netloc for r in rows if r["manifest_url"]}
    return domains or set(_FALLBACK_DOMAINS)


@router.get("/proxy")
async def proxy_manifest(url: str, db=Depends(get_db)):
    """Proxy a IIIF manifest to avoid CORS issues in the browser."""
    parsed = urlparse(url)
    allowed = _allowed_domains(db)
    if not any(parsed.netloc == d or parsed.netloc.endswith(f".{d}") for d in allowed):
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
