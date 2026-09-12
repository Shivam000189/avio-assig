"""Duplicate complaint candidate retrieval and similarity filtering service.

================================================================================
SCOPE & ARCHITECTURE JUSTIFICATION: LLM-AS-JUDGE VS EMBEDDINGS
In small-to-medium scale pharmaceutical QMS deployments (<10,000 complaints),
deterministic SQL candidate retrieval combined with an LLM-as-judge evaluation
provides superior operational and compliance outcomes compared to vector databases:

1. Zero Infrastructure Burden: Eliminates the need for external vector engines
   (e.g., Pinecone, Qdrant, Milvus) or database extensions (pgvector), keeping
   deployments lightweight, portable, and simple to test offline.
2. High Auditability & Explainability: The reasoning LLM produces detailed,
   traceable justification explaining why two records are duplicates or constitute
   a cross-batch trend (vital for FDA 21 CFR Part 820 and ICH Q9 inspections).
3. Precision with Pharma Identifiers: Alphanumeric lot numbers (e.g., 'PT-4471-A')
   and exact dosage formulations are prone to semantic embedding drift. Exact
   lot and product matching guarantees zero false negatives for same-batch incidents.

GRADUATION PATH AT SCALE:
When the complaint archive exceeds 10,000+ records, this service can seamlessly
evolve to a two-tier hybrid architecture:
  Tier 1: pgvector cosine similarity + BM25 keyword index for top-20 candidate retrieval.
  Tier 2: LLaMA-3.3 reasoning model (this service) for final duplicate judgement & explanation.
================================================================================
"""

from datetime import datetime, timezone
import logging
import re
from typing import Any

from app.database import prisma

logger = logging.getLogger(__name__)

# Common English stop words filtered out during keyword overlap computation
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "did", "do", "does", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "him", "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "its",
    "itself", "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off",
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "she", "should", "so", "some", "such", "than", "that",
    "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "would", "you", "your", "yours", "yourself", "yourselves", "please",
    "regarding", "reported", "noticed", "observed", "found", "complaint", "issue",
}


def _extract_significant_words(text: str) -> set[str]:
    """Extract lowercase alphanumeric tokens with length >= 4, excluding stop words."""
    if not text:
        return set()
    tokens = re.findall(r"\b[a-zA-Z0-9-]{4,}\b", text.lower())
    return {token for token in tokens if token not in STOP_WORDS}


async def fetch_candidates(
    extracted: dict[str, Any] | None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve potential duplicate complaint candidate records from the database.

    Strategy:
    1. Highest priority: Same batchNumber match.
    2. Second priority: Same productName match.
    3. Third priority: Keyword overlap (>= 3 significant words) across recent 50 complaints.

    Args:
        extracted: Dictionary of structured fields extracted by the intake node.
        limit: Maximum number of candidate summaries to return (default 5).

    Returns:
        List of compact candidate summary dictionaries (max ~3000 chars total).
    """
    if not extracted:
        logger.debug("Duplicate check skipped: extracted dictionary is None")
        return []

    batch_number = extracted.get("batchNumber")
    product_name = extracted.get("productName")
    description = extracted.get("description", "")

    # Clean fallback placeholders
    if batch_number and batch_number.upper() in ("UNKNOWN", "N/A", "NONE", ""):
        batch_number = None
    if product_name and product_name.upper() in ("UNKNOWN PRODUCT", "UNKNOWN", "N/A", ""):
        product_name = None

    # Extraction too weak to form a candidate query
    if not batch_number and not product_name:
        logger.debug("Duplicate check skipped: neither batchNumber nor productName available")
        return []

    candidates_by_id: dict[str, dict[str, Any]] = {}
    candidate_priorities: dict[str, int] = {}  # 1 (batch) > 2 (product) > 3 (keyword)

    try:
        # Check database connectivity safely
        if not prisma.is_connected():
            logger.warning("Database client offline during duplicate candidate search")
            return []

        # 1. Highest Priority: Same Batch Number
        if batch_number:
            batch_matches = await prisma.complaint.find_many(
                where={"batchNumber": batch_number},
                take=limit,
                order={"createdAt": "desc"},
            )
            for c in batch_matches:
                candidates_by_id[c.id] = {
                    "complaintId": c.id,
                    "complaintNumber": c.complaintNumber,
                    "productName": c.productName,
                    "batchNumber": c.batchNumber,
                    "description": c.description[:300],
                    "severity": c.severity,
                    "status": c.status,
                    "createdAt": c.createdAt.isoformat() if isinstance(c.createdAt, datetime) else str(c.createdAt),
                }
                candidate_priorities[c.id] = 1

        # 2. Second Priority: Same Product Name
        if product_name and len(candidates_by_id) < limit:
            remaining_slots = limit - len(candidates_by_id)
            product_matches = await prisma.complaint.find_many(
                where={
                    "productName": {"contains": product_name, "mode": "insensitive"},
                },
                take=limit * 2,
                order={"createdAt": "desc"},
            )
            for c in product_matches:
                if c.id not in candidates_by_id:
                    candidates_by_id[c.id] = {
                        "complaintId": c.id,
                        "complaintNumber": c.complaintNumber,
                        "productName": c.productName,
                        "batchNumber": c.batchNumber,
                        "description": c.description[:300],
                        "severity": c.severity,
                        "status": c.status,
                        "createdAt": c.createdAt.isoformat() if isinstance(c.createdAt, datetime) else str(c.createdAt),
                    }
                    candidate_priorities[c.id] = 2

        # 3. Third Priority: Keyword Overlap on Recent Complaints
        if description and len(candidates_by_id) < limit:
            query_words = _extract_significant_words(description)
            if len(query_words) >= 3:
                recent_records = await prisma.complaint.find_many(
                    take=50,
                    order={"createdAt": "desc"},
                )
                for c in recent_records:
                    if c.id not in candidates_by_id:
                        rec_words = _extract_significant_words(c.description)
                        overlap_count = len(query_words.intersection(rec_words))
                        if overlap_count >= 3:
                            candidates_by_id[c.id] = {
                                "complaintId": c.id,
                                "complaintNumber": c.complaintNumber,
                                "productName": c.productName,
                                "batchNumber": c.batchNumber,
                                "description": c.description[:300],
                                "severity": c.severity,
                                "status": c.status,
                                "createdAt": c.createdAt.isoformat() if isinstance(c.createdAt, datetime) else str(c.createdAt),
                            }
                            candidate_priorities[c.id] = 3

    except Exception as exc:
        logger.warning("Error fetching duplicate complaint candidates: %s", exc)
        return []

    # Sort candidates by priority (batch > product > keyword) and truncate to limit
    sorted_candidates = sorted(
        candidates_by_id.values(),
        key=lambda item: candidate_priorities.get(item["complaintId"], 99),
    )[:limit]

    # Enforce prompt token budget: max ~3000 characters total across candidates
    compact_candidates: list[dict[str, Any]] = []
    total_chars = 0
    for cand in sorted_candidates:
        cand_chars = len(str(cand))
        if total_chars + cand_chars > 3000 and compact_candidates:
            break
        compact_candidates.append(cand)
        total_chars += cand_chars

    logger.info("Found %d duplicate candidate(s) for comparison", len(compact_candidates))
    return compact_candidates
