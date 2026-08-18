"""Citation-backed search for offline training-data evidence checks."""

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

import httpx

from config import settings


@dataclass(frozen=True)
class EvidenceSource:
    title: str
    url: str
    snippet: str
    site_name: str = ""
    published_at: str = ""


@dataclass(frozen=True)
class ClaimEvidence:
    claim: str
    claim_hash: str
    query: str
    provider: str
    sources: list[EvidenceSource]
    error: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "claim_hash": self.claim_hash,
            "query": self.query,
            "provider": self.provider,
            "sources": [asdict(source) for source in self.sources],
            "error": self.error,
        }


def claim_hash(claim: str) -> str:
    return hashlib.sha256(claim.strip().casefold().encode("utf-8")).hexdigest()


def _search_query(destination: str, claim: str) -> str:
    return " ".join(part for part in (destination.strip(), claim.strip()) if part)


async def retrieve_claim_evidence(destination: str, claim: str) -> ClaimEvidence:
    """Search Bocha and return citations only; it never declares a claim true."""
    query = _search_query(destination, claim)
    evidence_id = claim_hash(claim)
    if not settings.auto_eval_evidence_enabled:
        return ClaimEvidence(claim, evidence_id, query, "bocha", [], "evidence retrieval disabled")
    if not settings.bocha_api_key:
        return ClaimEvidence(claim, evidence_id, query, "bocha", [], "Bocha API key is not configured")

    payload = {"query": query, "count": 5, "summary": False}
    headers = {"Authorization": f"Bearer {settings.bocha_api_key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=settings.bocha_search_timeout) as client:
            response = await client.post(settings.bocha_search_api_base, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return ClaimEvidence(claim, evidence_id, query, "bocha", [], str(exc))

    pages = body.get("data", {}).get("webPages", {}).get("value", [])
    sources = [
        EvidenceSource(
            title=str(page.get("name") or ""),
            url=str(page.get("url") or ""),
            snippet=str(page.get("snippet") or ""),
            site_name=str(page.get("siteName") or ""),
            published_at=str(page.get("datePublished") or ""),
        )
        for page in pages
        if isinstance(page, dict) and page.get("url")
    ]
    return ClaimEvidence(claim, evidence_id, query, "bocha", sources)


async def retrieve_evidence_for_claims(destination: str, claims: list[str]) -> list[ClaimEvidence]:
    """Fetch a bounded, de-duplicated set of claim citation bundles."""
    unique_claims = list(dict.fromkeys(claim.strip() for claim in claims if claim and claim.strip()))
    limit = settings.auto_eval_evidence_max_claims
    return [await retrieve_claim_evidence(destination, claim) for claim in unique_claims[:limit]]
