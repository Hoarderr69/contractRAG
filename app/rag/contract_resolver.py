"""
Two-stage contract scope resolution for Contract360.

Stage 1 (UI):       the user's sidebar selection forms the *candidate set*.
                    Empty selection = the full indexed portfolio.
Stage 2 (question): within that candidate set, narrow to the contract(s) the
                    question actually names (e.g. "...in the Edison contract").

If the question names no candidate, the candidate set is returned unchanged —
we never narrow to nothing, and we never widen beyond the UI selection.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Tokens that carry no distinguishing signal for a contract name. A contract id
# like "Con_Edison_Service_Agreement_2019" should match on "edison", not on
# "agreement" or "2019".
_STOPWORD_TOKENS = {
    "the", "of", "and", "a", "an", "for", "to", "in", "on", "by", "with",
    "agreement", "agreements", "contract", "contracts", "service", "services",
    "master", "amended", "restated", "amendment", "exhibit", "schedule",
    "inc", "llc", "lp", "corp", "co", "company", "ltd", "plc",
    "between", "dated", "final", "executed", "signed", "draft", "v", "vs",
    # Document-type tokens shared by many contracts — too weak to disambiguate
    # on their own (e.g. "epc" appears in 3 different EPC contracts).
    "epc", "ppa", "om", "oandm", "template", "corrected", "public", "item",
    "attachment", "operations", "maintenance", "support", "corporate",
}

# Hand-tuned aliases: maps a phrase a user might type to a token that appears in
# the contract id. Extend as new contracts/party names appear.
_ALIASES = {
    "con edison": "edison",
    "consolidated edison": "edison",
    "socal": "socal",
    "so cal": "socal",
    "southern california": "socal",
    "sce": "sce",
    "nypa": "nypa",
    "power authority": "nypa",
    "new york power authority": "nypa",
    # Demo-contract party/name aliases
    "nyiso": "nyiso",
    "nextera": "nxteraepcagt",   # NYISO/NextEra EPC agreement
    "national grid": "ngrd",
    "empire state": "empirestateln",
    "duke": "duke",
    "lfgte": "lfgte",
    "duke energy": "duke",
    "terra-gen": "terra",
    "terra gen": "terra",
    "sunpower": "sunpower",
    "solar": "solar",
}

# Word boundary so "edison" doesn't match inside "edisonville", etc.
_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return _WORD_RE.findall((text or "").lower())


def _distinctive_tokens(contract_id: str) -> set:
    """Significant lower-cased tokens for a contract id (stopwords removed)."""
    toks = {t for t in _tokens(contract_id) if t not in _STOPWORD_TOKENS and len(t) > 1}
    # Drop pure years / numbers — they rarely disambiguate and often collide.
    toks = {t for t in toks if not t.isdigit()}
    return toks


def _question_tokens(question: str) -> set:
    q = (question or "").lower()
    toks = set(_tokens(q))
    # Fold in alias hits as their canonical token.
    for phrase, canonical in _ALIASES.items():
        if phrase in q:
            toks.add(canonical)
    return toks


def resolve_scope(
    question: str,
    candidate_ids: List[str],
) -> Tuple[List[str], Optional[str]]:
    """
    Narrow `candidate_ids` to the contract(s) named in `question`.

    Returns (resolved_ids, reason).
      - resolved_ids: a subset of candidate_ids (or the full list if no match).
      - reason: human-readable note, or None when nothing was narrowed.
    """
    if not candidate_ids or len(candidate_ids) == 1:
        # Nothing to narrow: portfolio resolved elsewhere, or already single.
        return candidate_ids, None

    qtoks = _question_tokens(question)
    if not qtoks:
        return candidate_ids, None

    # Generic domain words that must never drive a *substring* match
    # (e.g. "power" ⊂ "sunpower" would wrongly pull in the Sunpower contract).
    _GENERIC_SUBSTR_SKIP = {
        "power", "purchase", "energy", "total", "cost", "costs", "estimated",
        "amount", "billed", "rate", "engineering", "system", "solar", "states",
        "estate", "corporate", "purchased", "pricing", "scope",
    }

    def _match_strength(cid: str) -> int:
        """Number of distinct question tokens that hit this contract's tokens."""
        ctoks = _distinctive_tokens(cid)
        score = 0
        for qt in qtoks:
            if qt in ctoks:
                score += 1
                continue
            # Substring overlap for longer, distinctive tokens
            # (e.g. "empire" ⊂ "empirestateln").
            if len(qt) < 5 or qt in _GENERIC_SUBSTR_SKIP:
                continue
            if any((qt in ct or ct in qt) for ct in ctoks):
                score += 1
        return score

    scored = [(cid, _match_strength(cid)) for cid in candidate_ids]
    best = max((s for _, s in scored), default=0)
    # Keep only the strongest-matching tier. When one contract matches more of
    # the question than the others (e.g. NYISO EPC on 2 tokens vs NextEra O&M on
    # 1), this drops the weaker, noisier matches that hurt retrieval recall.
    matched = [cid for cid, s in scored if s == best and s > 0]

    if matched and len(matched) < len(candidate_ids):
        names = ", ".join(c.replace("_", " ") for c in matched)
        logger.info(
            "Contract resolver: narrowed %d candidates → %s via question text.",
            len(candidate_ids), matched,
        )
        return matched, f"Scoped to {names} based on the question."

    # No match, or matched everything — leave the candidate set untouched.
    return candidate_ids, None
