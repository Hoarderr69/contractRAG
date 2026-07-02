"""
Query service for Contract360.

Three retrieval routes:
  tree   — Azure AI Search (BM25+vector) + hierarchical tree context expansion.
  graph  — Cosmos Gremlin semantic graph only.
  hybrid — Tree search context + Gremlin semantic graph facts merged.

Returns citations[] alongside the answer so the frontend can render source cards.
"""

import logging
import re as _re
from typing import Dict, List, Optional, Tuple

from app import config
from app.indexing.search_tester import AzureSearchTester
from app.rag.contract_resolver import resolve_scope
from app.rag.query_router import route_question
from app.rag.graph_retriever import graph_native_retrieve
from app.rag.graph_canonical import canonical_graph_retrieve
from app.rag.answer_generator import AnswerGenerator
from app.rag.summary_generator import format_summary_as_answer
from app.services.prompt_builder import build_rag_prompt
from app.storage.artifact_store import get_artifact_store
from app.tree.semantic_retriever import SemanticRetriever
from app.kg.gremlin_writer import contract_has_graph, gremlin_is_configured
from app.kg.local_graph_store import get_local_graph_store

logger = logging.getLogger(__name__)


# ── Document-level summary shortcut ───────────────────────────────────────────

_SUMMARY_PATTERNS = {
    "what is this contract about", "what's this contract about",
    "what is this agreement about", "what's this agreement about",
    "tell me about this contract", "tell me about this agreement",
    "what does this contract cover", "what does this agreement cover",
    "give me a summary", "provide a summary", "contract overview",
    "give me an overview", "overview of this contract", "overview of the contract",
    "high-level summary", "high level summary",
    "summarize this contract", "summarise this contract",
    "summary of this contract", "summary of the contract",
    "summarize the contract", "summarise the contract",
    "summarize this agreement", "summarise this agreement",
    "summary of this agreement", "summary of the agreement",
}


def _is_summary_query(question: str) -> bool:
    q = question.lower().strip()
    return any(pat in q for pat in _SUMMARY_PATTERNS)


# ── Structure / table-of-contents shortcut ────────────────────────────────────

_STRUCTURE_PATTERNS = (
    "what sections", "which sections", "list the sections", "list sections",
    "what articles", "which articles", "list the articles",
    "table of contents", "what is the structure", "what's the structure",
    "outline of", "sections available", "articles available",
    "what sections are available", "what parts of", "structure of",
    "what does the contract contain", "what does this contract contain",
)


def _is_structure_query(question: str) -> bool:
    q = question.lower().strip()
    return any(pat in q for pat in _STRUCTURE_PATTERNS)


# Reused across requests: one Blob client + a per-contract tree cache, so the
# structure shortcut and title-boost don't re-download tree.json (and re-open a
# new Blob connection) on every question — which was exhausting the connection
# pool and triggering "unable to stream download" warnings.
_tree_store = None
_TREE_CACHE: Dict[str, Optional[Dict]] = {}


def _load_tree(contract_id: str) -> Optional[Dict]:
    """
    Load a contract tree from Azure Blob Storage (cached). Trees are only
    persisted in Blob, so the structure shortcut and any tree-based feature read
    from Blob directly regardless of USE_BLOB_ARTIFACTS. Returns None on a miss.
    """
    if contract_id in _TREE_CACHE:
        return _TREE_CACHE[contract_id]

    global _tree_store
    tree: Optional[Dict] = None
    try:
        if _tree_store is None:
            from app.storage.blob_artifact_store import BlobArtifactStore
            _tree_store = BlobArtifactStore()
        tree = _tree_store.get_tree(contract_id)
    except Exception as exc:
        logger.warning("Could not load tree for '%s' from Blob: %s", contract_id, exc)

    _TREE_CACHE[contract_id] = tree
    return tree


def _build_toc_answer(tree: Dict, contract_id: str) -> str:
    """
    Walk the contract tree and render its section/article headings as a clean
    outline. Vector search can't enumerate structure, so this reads the tree
    directly (the source of truth for the document hierarchy).
    """
    lines: List[str] = []

    def _walk(node: Dict, depth: int) -> None:
        # Skip the synthetic document root; render everything beneath it.
        node_type = (node.get("nodeType") or "").lower()
        title = (node.get("title") or "").strip()
        children = node.get("children", []) or []

        is_root = node_type == "document" or depth < 0
        # A heading is a non-leaf node (has children) or an explicit section/article.
        is_heading = bool(children) or node_type in {"section", "article"}

        if not is_root and title and is_heading and depth <= 2:
            indent = "  " * depth
            lines.append(f"{indent}- {title}")

        if depth <= 2:
            for child in children:
                _walk(child, depth + 1)

    _walk(tree, -1)

    name = contract_id.replace("_", " ")
    if not lines:
        return f"No structured section outline is available for **{name}**."
    body = "\n".join(lines[:80])
    return (
        f"Here is the section structure of **{name}**:\n\n{body}"
    )


# ── Citation extraction ────────────────────────────────────────────────────────

def _docs_to_citations(docs: list, route: str = "tree") -> List[Dict]:
    """Convert raw search/tree docs to structured citation objects."""
    citations = []
    seen = set()
    for doc in docs:
        cid   = doc.get("contractId") or ""
        title = doc.get("title") or doc.get("sectionTitle") or ""
        page_start = doc.get("pageStart") or ""
        page_end   = doc.get("pageEnd") or ""
        key = f"{cid}|{title}|{page_start}"
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "id":            doc.get("kgId") or doc.get("nodeId") or key,
            "contractId":    cid,
            "contractName":  cid.replace("_", " "),
            "clauseTitle":   title,
            "sectionTitle":  doc.get("sectionTitle") or "",
            "pageRange":     f"{page_start}–{page_end}" if page_start else "",
            "sourcePath":    doc.get("sourcePath") or "",
            "evidenceQuote": _clean_quote(doc.get("text")),
            "route":         route,
            "score":         round(doc.get("score", 0), 4),
        })
    return citations


def _chunks_to_citations(chunks: list) -> List[Dict]:
    """Convert SemanticRetriever chunk objects to citations."""
    citations = []
    seen = set()
    for chunk in chunks:
        cid   = chunk.get("contractId") or ""
        title = chunk.get("title") or chunk.get("sectionTitle") or ""
        page_start = chunk.get("pageStart") or ""
        page_end   = chunk.get("pageEnd") or ""
        key = f"{cid}|{title}|{page_start}"
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "id":            chunk.get("kgId") or chunk.get("nodeId") or key,
            "contractId":    cid,
            "contractName":  cid.replace("_", " "),
            "clauseTitle":   title,
            "sectionTitle":  chunk.get("sectionTitle") or "",
            "pageRange":     f"{page_start}–{page_end}" if page_start else "",
            "sourcePath":    chunk.get("sourcePath") or "",
            "evidenceQuote": _clean_quote(chunk.get("text")),
            "route":         "tree",
            "score":         round(chunk.get("score", 0), 4),
        })
    return citations


# ── Retrieval helpers — return (context_str, citations) ───────────────────────

_THIN_CONTEXT_MARKERS = (
    "no azure ai search results",
    "no graph",
    "no facts",
    "no results",
    "not found",
)


def _context_is_thin(context: Optional[str]) -> bool:
    """
    True when a retrieved context carries essentially no usable evidence —
    empty, only section headers/separators, or an explicit "nothing found"
    marker. Used to trigger a tree-search fallback.
    """
    if not context:
        return True
    # Strip separator/header decoration ("=" rules and ALL-CAPS section labels).
    meaningful = [
        ln for ln in context.splitlines()
        if ln.strip() and set(ln.strip()) != {"="} and not ln.strip().isupper()
    ]
    body = " ".join(meaningful).strip()
    if len(body) < 200:
        return True
    low = body.lower()
    return any(m in low for m in _THIN_CONTEXT_MARKERS)


def _clean_quote(text: Optional[str], limit: int = 220) -> str:
    """Trim an evidence quote to a sentence/word boundary so cards don't cut mid-word."""
    if not text:
        return ""
    t = text.strip()
    if len(t) <= limit:
        return t
    head = t[:limit]
    # Prefer the last sentence end, else the last space.
    cut = max(head.rfind(". "), head.rfind("; "))
    if cut < limit * 0.5:
        cut = head.rfind(" ")
    if cut <= 0:
        cut = limit
    return head[:cut].rstrip(" ,;:") + "…"


# Title-boost: words that carry no signal when matching a question to a node title.
_TITLE_STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "to", "and", "or", "what", "which",
    "are", "is", "does", "do", "this", "that", "contract", "agreement", "section",
    "clause", "article", "terms", "term", "provisions", "provision", "costs", "cost",
    "general", "mentioned", "available", "me", "tell", "about", "with", "by",
}


def _title_tokens(text: str) -> set:
    toks = _re.findall(r"[a-z0-9]+", (text or "").lower())
    return {t for t in toks if t not in _TITLE_STOPWORDS and len(t) > 2}


def _title_match_nodes(question: str, tree: Optional[Dict],
                       exclude_ids: set, contract_id: Optional[str] = None) -> List[Dict]:
    """
    Find tree nodes whose TITLE strongly matches the question, to recover
    specific named sections/tables that vector ranking buries (e.g. a numbers
    table titled "ASO Estimated Total Costs").

    Strictly gated so it can't explode context:
      - specificity: >= 2 distinctive (non-stopword) title tokens hit the question
      - size:        leaf-ish nodes only (small text, few children, not a heading)
      - count:       at most TITLE_BOOST_MAX_NODES
      - dedup:       skip nodes already retrieved by vector search

    Contract-name tokens are removed from the question first, so repeating the
    contract name (e.g. "...in the Solar System O&M agreement") can't match the
    scope node — only the distinctive intent words drive the boost.
    """
    if not tree:
        return []
    qtoks = _title_tokens(question) - _title_tokens(contract_id or "")
    if not qtoks:
        return []

    scored: List[tuple] = []

    def _walk(node: Dict) -> None:
        node_id = node.get("nodeId")
        title = node.get("title") or ""
        text = node.get("text") or ""
        children = node.get("children", []) or []
        node_type = (node.get("nodeType") or "").lower()

        ttoks = _title_tokens(title)
        overlap = len(ttoks & qtoks)

        # Size gate: skip headings/containers and over-long nodes.
        is_leafish = (
            node_type not in {"document", "article"}
            and len(children) <= 3
            and 40 <= len(text) <= config.MAX_SEARCH_DOC_CHARS * 2
        )

        if (
            node_id
            and node_id not in exclude_ids
            and overlap >= 2
            and is_leafish
        ):
            scored.append((overlap, node))

        for child in children:
            _walk(child)

    _walk(tree)
    if not scored:
        return []

    scored.sort(key=lambda x: x[0], reverse=True)
    return [n for _, n in scored[: config.TITLE_BOOST_MAX_NODES]]


def _tree_node_to_doc(node: Dict, contract_id: str) -> Dict:
    """Shape a tree node like a search doc so it flows through the normal context
    + citation path. High score so it ranks first in the SOURCES list."""
    return {
        "contractId":  contract_id,
        "nodeId":      node.get("nodeId"),
        "kgId":        node.get("kgId"),
        "title":       node.get("title"),
        "sectionTitle": node.get("sectionTitle") or "",
        "clauseTitle": node.get("title"),
        "text":        node.get("text"),
        "pageStart":   node.get("pageStart"),
        "pageEnd":     node.get("pageEnd"),
        "sourcePath":  node.get("sourcePath") or "",
        "score":       1.0,
    }


def _format_search_docs(docs: list) -> str:
    """
    Render search docs into context, bounded so a large top-k can't dilute the
    answer or balloon cost. Each doc's text is capped to MAX_SEARCH_DOC_CHARS and
    the whole block to MAX_CONTEXT_CHARS (same budget as build_rag_prompt).
    """
    if not docs:
        return "No Azure AI Search results found."
    parts = []
    for idx, doc in enumerate(docs, start=1):
        text = (doc.get("text") or "")[: config.MAX_SEARCH_DOC_CHARS]
        parts += [
            "=" * 80,
            f"SEARCH RESULT {idx}  [CONTRACT: {doc.get('contractId', 'unknown')}]",
            "=" * 80,
            f"Contract ID: {doc.get('contractId')}",
            f"Title: {doc.get('title')}",
            f"Section: {doc.get('sectionTitle')}",
            f"Pages: {doc.get('pageStart')}-{doc.get('pageEnd')}",
            f"Source path: {doc.get('sourcePath')}",
            "",
            text,
            "",
        ]
    return "\n".join(parts)[: config.MAX_CONTEXT_CHARS]


def _tree_retrieve(
    question: str,
    contract_id: Optional[str],
    contract_ids: Optional[List[str]],
    top: int,
    structural_scope: Optional[Dict],
) -> Tuple[str, List[Dict]]:
    """Returns (context_string, citations)."""
    if structural_scope:
        searcher = AzureSearchTester()
        docs = searcher.retrieve_structural_scope(
            structure_type=structural_scope["type"],
            identifier=structural_scope["identifier"],
            contract_id=contract_id,
            contract_ids=contract_ids,
            top=100,
        )
        return _format_search_docs(docs), _docs_to_citations(docs)

    # Normalise: treat empty list same as None (portfolio-wide)
    if contract_ids is not None and len(contract_ids) == 0:
        contract_ids = None

    if contract_id and not contract_ids:
        retriever = SemanticRetriever(contract_id=contract_id)
        chunks = retriever.retrieve(query=question, top_k=top, contract_id=contract_id)
        if chunks:
            context = build_rag_prompt(query=question, retrieved_chunks=chunks)
            return context, _chunks_to_citations(chunks)

    searcher = AzureSearchTester()
    docs = searcher.hybrid_search(
        query=question,
        contract_id=contract_id,
        contract_ids=contract_ids,
        top=top,
    )

    # Title-boost: for a single-contract scope, recover specific named sections
    # (e.g. a numbers table) that vector ranking buries. Gated + deduped, then
    # prepended so the assembled context still respects the global budget.
    boost_cid = contract_id or (contract_ids[0] if contract_ids and len(contract_ids) == 1 else None)
    if boost_cid:
        seen_ids = {d.get("nodeId") for d in docs} | {d.get("kgId") for d in docs}
        title_nodes = _title_match_nodes(question, _load_tree(boost_cid), seen_ids, boost_cid)
        if title_nodes:
            boosted = [_tree_node_to_doc(n, boost_cid) for n in title_nodes]
            titles = ", ".join((n.get("title") or "")[:40] for n in title_nodes)
            logger.info("Title-boost: injected %d node(s) → %s", len(boosted), titles)
            docs = boosted + docs

    logger.info("Tree search: %d docs from AI Search", len(docs))
    return _format_search_docs(docs), _docs_to_citations(docs)


def _hybrid_retrieve(
    question: str,
    contract_id: Optional[str],
    contract_ids: Optional[List[str]],
    top: int,
) -> Tuple[str, List[Dict]]:
    """Returns (context_string, citations). Merges tree + graph contexts."""
    tree_context, tree_citations = _tree_retrieve(
        question=question,
        contract_id=contract_id,
        contract_ids=contract_ids,
        top=top,
        structural_scope=None,
    )
    # Re-label tree citations as hybrid
    for c in tree_citations:
        c["route"] = "hybrid"

    graph_context, graph_facts = _graph_retrieve(
        question=question,
        contract_id=contract_id,
        contract_ids=contract_ids,
    )

    # Prefer fact-level graph citations; fall back to scope cards if none.
    graph_citations = _graph_facts_to_citations(graph_facts)
    if not graph_citations:
        scope_ids = contract_ids or ([contract_id] if contract_id else [])
        seen_ids = {c["contractId"] for c in tree_citations}
        graph_citations = [
            {
                "id": cid, "contractId": cid, "contractName": cid.replace("_", " "),
                "clauseTitle": "Knowledge Graph", "sectionTitle": "", "pageRange": "",
                "sourcePath": "", "evidenceQuote": "", "route": "graph", "score": 1.0,
            }
            for cid in scope_ids if cid not in seen_ids
        ]

    combined = (
        "=" * 80 + "\n"
        "TREE SEARCH CONTEXT (Azure AI Search + Hierarchical Expansion)\n"
        + "=" * 80 + "\n"
        + tree_context
        + "\n\n"
        + "=" * 80 + "\n"
        "GRAPH CONTEXT (Cosmos Gremlin Semantic Facts)\n"
        + "=" * 80 + "\n"
        + graph_context
    )
    return combined, tree_citations + graph_citations


# ── Graph availability check ───────────────────────────────────────────────────

def _make_search_anchor():
    """Phase-2 bridge: vector/keyword search → relevant clause ids for graph anchoring."""
    def _anchor(question: str, scope: Optional[List[str]]) -> List[str]:
        try:
            searcher = AzureSearchTester()
            docs = searcher.hybrid_search(query=question, contract_ids=scope, top=8)
            return [d.get("kgId") for d in docs if d.get("kgId")]
        except Exception:
            return []
    return _anchor


_MAX_GRAPH_CITATIONS = 25


def _graph_facts_to_citations(facts: List[Dict]) -> List[Dict]:
    """Build citation cards from graph facts (with page/clause provenance)."""
    citations, seen = [], set()
    for f in facts:
        cid = f.get("contractId") or ""
        title = f.get("clauseTitle") or f.get("name") or ""
        ps, pe = f.get("pageStart"), f.get("pageEnd")
        key = f"{cid}|{title}|{ps}"
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "id":            f.get("kgId") or key,
            "contractId":    cid,
            "contractName":  cid.replace("_", " "),
            "clauseTitle":   title,
            "sectionTitle":  "",
            "pageRange":     f"{ps}–{pe}" if ps else "",
            "sourcePath":    "",
            "evidenceQuote": _clean_quote(f.get("evidenceQuote")),
            "route":         "graph",
            "score":         float(f.get("confidence") or 0.0),
        })
        if len(citations) >= _MAX_GRAPH_CITATIONS:
            break
    return citations


def _ground_and_generate(
    generator,
    question: str,
    context: str,
    route: str,
    citations: List[Dict],
    chat_history: List[Dict[str, str]],
    active_ids: Optional[List[str]],
):
    """
    Rank citations, expose them to the LLM as a numbered SOURCES list, let it
    cite [S#] inline, then return only the cited cards. Falls back to top-ranked
    few if the model cites nothing. Strips [S#] markers from the displayed answer.
    """
    ranked = sorted(citations, key=lambda c: c.get("score", 0.0), reverse=True)

    # Content-level dedup: collapse cards that point at the same clause even
    # when their internal ids differ (tree vs graph builders can both emit it).
    deduped, seen_keys = [], set()
    for c in ranked:
        key = (
            c.get("contractId", ""),
            (c.get("clauseTitle") or "").strip().lower(),
            c.get("pageRange", ""),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(c)
    ranked = deduped

    if ranked:
        lines = ["", "", "=" * 70, "SOURCES (cite the supporting one inline as [S#]):", "=" * 70]
        for i, c in enumerate(ranked, 1):
            pg = f" ({c['pageRange']})" if c.get("pageRange") else ""
            lines.append(f"[S{i}] {c.get('clauseTitle') or c.get('contractName')}"
                         f" — {c.get('contractName')}{pg}")
        context = context + "\n".join(lines)

    answer, follow_ups = generator.generate(
        question=question, context=context, route=route,
        chat_history=chat_history, active_contract_ids=active_ids,
    )

    used = [int(n) for n in _re.findall(r"\[S(\d+)\]", answer)]
    seen_set, order = set(), []
    for n in used:
        if 1 <= n <= len(ranked) and n not in seen_set:
            seen_set.add(n)
            order.append(n)

    grounded = [ranked[n - 1] for n in order] if order else ranked[:8]
    clean = _re.sub(r"\s*\[S\d+\]", "", answer)
    return clean, follow_ups, grounded


def _graph_retrieve(question: str, contract_id: Optional[str],
                    contract_ids: Optional[List[str]]):
    """Graph retrieval: canonical (Gremlin) when available, local store otherwise."""
    if gremlin_is_configured():
        try:
            ctx, facts = canonical_graph_retrieve(
                question, contract_id=contract_id, contract_ids=contract_ids,
                search_anchor_fn=_make_search_anchor(),
            )
            if ctx and ctx.strip():
                return ctx, _graph_facts_to_citations(facts)
        except Exception as exc:
            logger.warning("Canonical graph retrieval failed (%s) — falling back.", exc)

    legacy = graph_native_retrieve(question, contract_id=contract_id, contract_ids=contract_ids)
    return legacy, []

def _graph_available(contract_id: Optional[str], contract_ids: Optional[List[str]]) -> bool:
    if gremlin_is_configured():
        # Cloud path: for multi-contract or portfolio, Gremlin is enough.
        if contract_ids and len(contract_ids) > 1:
            return True
        if not contract_id and not contract_ids:
            return True
        cid = contract_id or (contract_ids[0] if contract_ids else None)
        return bool(cid and contract_has_graph(cid))

    # Local path: check in-memory store (loaded from data/kg/extractions/).
    local = get_local_graph_store()
    if not local.has_any_data():
        return False
    if contract_ids and len(contract_ids) > 1:
        return local.kg_exists_any(contract_ids)
    if not contract_id and not contract_ids:
        return local.has_any_data()
    cid = contract_id or (contract_ids[0] if contract_ids else None)
    return bool(cid and local.kg_exists(cid))


# ── Main entry point ───────────────────────────────────────────────────────────

def answer_question(
    question: str,
    contract_id: Optional[str],
    contract_ids: Optional[List[str]] = None,
    top: int = 8,
    route_override: str = "auto",
    return_context: bool = False,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> Dict:
    """
    Route, retrieve, and answer a question.

    Returns {
      route, reason, rewritten_query, answer,
      citations: List[Dict],
      follow_up_suggestions: List[str],
      context?: str
    }
    """
    # Normalise empty list to None so all downstream checks work consistently
    if contract_ids is not None and len(contract_ids) == 0:
        contract_ids = None

    logger.info("──────── Q: %r", question[:100])

    # ── Scope resolution: narrow to contracts the question names ──────
    scope_reason: Optional[str] = None
    if contract_ids:
        candidate_pool = list(contract_ids)
    elif contract_id:
        candidate_pool = [contract_id]
    else:
        try:
            candidate_pool = AzureSearchTester().list_contract_ids()
        except Exception as exc:
            logger.warning("Contract resolver: could not list contracts (%s).", exc)
            candidate_pool = []

    resolved_ids, scope_reason = resolve_scope(question, candidate_pool)
    if scope_reason:
        contract_ids = resolved_ids
        contract_id = None

    # Effective single contract: explicit contract_id, or a scope that resolved
    # to exactly one contract. Used by the summary/structure shortcuts.
    single_cid = contract_id or (contract_ids[0] if contract_ids and len(contract_ids) == 1 else None)
    logger.info("Scope: %s", single_cid or contract_ids or "portfolio (all contracts)")

    # ── 0a. Structure / table-of-contents shortcut ────────────────────
    if _is_structure_query(question) and single_cid and route_override == "auto":
        tree = _load_tree(single_cid)
        if tree:
            logger.info("Shortcut: structure/TOC for %s (no LLM)", single_cid)
            answer = _build_toc_answer(tree, single_cid)
            result: Dict = {
                "route":                 "structure",
                "reason":                "Document section outline read from the contract tree.",
                "rewritten_query":       question,
                "answer":                answer,
                "citations":             [],
                "follow_up_suggestions": [],
            }
            if return_context:
                result["context"] = f"Tree outline for: {single_cid}"
            return result

    # ── 0. Document-level summary shortcut ────────────────────────────
    if _is_summary_query(question) and single_cid and route_override == "auto":
        store = get_artifact_store()
        summary = store.load_summary(single_cid)
        if summary:
            logger.info("Shortcut: pre-generated summary for %s (no LLM)", single_cid)
            answer = format_summary_as_answer(summary)
            result: Dict = {
                "route":                "summary",
                "reason":               "Pre-generated document summary.",
                "rewritten_query":      question,
                "answer":               answer,
                "citations":            [],
                "follow_up_suggestions": [],
            }
            if return_context:
                result["context"] = f"Pre-generated summary for: {single_cid}"
            return result

    # ── 1. Route ──────────────────────────────────────────────────────
    query_plan = route_question(question, chat_history=chat_history)
    route            = query_plan["route"]
    reason           = query_plan["reasoning"]
    rewritten_query  = query_plan["rewritten_query"]
    structural_scope = query_plan["structural_scope"]

    if route_override and route_override != "auto":
        route = route_override
        reason = f"User override: {route_override}"

    # Demo switch: force graph/hybrid onto the deterministic tree route so a
    # partial/stale graph can't answer "does not contain ..." before tree runs.
    if getattr(config, "DISABLE_GRAPH_ROUTE", False) and route in {"graph", "hybrid"}:
        route = "tree"
        reason = "Graph routing disabled — using tree search."
    else:
        graph_ok = _graph_available(contract_id, contract_ids)
        if route in {"graph", "hybrid"} and not graph_ok:
            route = "tree"
            reason = "No knowledge graph available for this contract — using tree search."

    if scope_reason:
        reason = f"{reason} ({scope_reason})"

    logger.info("Final route: %s — %s", route, reason)

    # Retrieval query. The router's rewrite is non-deterministic run-to-run, so
    # blending it in destabilises ranking. A long, self-contained question never
    # needs it — only short, anaphoric follow-ups ("what about its deadlines?")
    # do. So use the rewrite ONLY for short questions that have history to
    # resolve; otherwise retrieve on the raw question (fully deterministic).
    _is_short_followup = len(question.split()) <= 12
    if (chat_history
            and _is_short_followup
            and rewritten_query
            and rewritten_query.strip().lower() != question.strip().lower()):
        retrieval_query = rewritten_query
    else:
        retrieval_query = question

    # ── 2. Retrieve ────────────────────────────────────────────────────
    citations: List[Dict] = []

    if route == "graph":
        context, citations = _graph_retrieve(
            retrieval_query,
            contract_id=contract_id,
            contract_ids=contract_ids,
        )
        # Reliability guard: if the graph yields little or no usable context,
        # fall back to tree search instead of answering "Not found". A contract
        # may have only a partial graph (or none for some topics), and tree
        # search almost always has the underlying clause text.
        if _context_is_thin(context):
            logger.info("Graph context thin — falling back to tree retrieval.")
            context, citations = _tree_retrieve(
                question=retrieval_query,
                contract_id=contract_id,
                contract_ids=contract_ids,
                top=top,
                structural_scope=structural_scope,
            )
            route = "tree"
            reason = f"{reason} (graph context sparse — fell back to tree search)"
        elif not citations:
            scope_ids = contract_ids or ([contract_id] if contract_id else [])
            citations = [
                {
                    "id": cid, "contractId": cid, "contractName": cid.replace("_", " "),
                    "clauseTitle": "Knowledge Graph", "sectionTitle": "", "pageRange": "",
                    "sourcePath": "", "evidenceQuote": "", "route": "graph", "score": 1.0,
                }
                for cid in scope_ids
            ]

    elif route == "hybrid":
        context, citations = _hybrid_retrieve(
            question=retrieval_query,
            contract_id=contract_id,
            contract_ids=contract_ids,
            top=top,
        )
        # If hybrid produced no real citations (both halves thin), retry as tree.
        if _context_is_thin(context) and not citations:
            logger.info("Hybrid context thin — falling back to tree retrieval.")
            context, citations = _tree_retrieve(
                question=retrieval_query,
                contract_id=contract_id,
                contract_ids=contract_ids,
                top=top,
                structural_scope=structural_scope,
            )
            route = "tree"
            reason = f"{reason} (hybrid context sparse — fell back to tree search)"

    else:  # tree
        context, citations = _tree_retrieve(
            question=retrieval_query,
            contract_id=contract_id,
            contract_ids=contract_ids,
            top=top,
            structural_scope=structural_scope,
        )

    logger.info("Retrieved: context=%d chars | %d candidate sources", len(context), len(citations))

    # ── 3. Generate answer + follow-up suggestions ─────────────────────
    active_ids: List[str] = []
    if contract_ids:
        active_ids = list(contract_ids)
    elif contract_id:
        active_ids = [contract_id]

    generator = AnswerGenerator()
    answer, follow_ups, citations = _ground_and_generate(
        generator,
        question=question,
        context=context,
        route=route,
        citations=citations,
        chat_history=chat_history or [],
        active_ids=active_ids or None,
    )
    logger.info("Answer ready: route=%s | %d cited sources | %d follow-ups",
                route, len(citations), len(follow_ups))

    result: Dict = {
        "route":                 route,
        "reason":                reason,
        "rewritten_query":       rewritten_query,
        "answer":                answer,
        "citations":             citations,
        "follow_up_suggestions": follow_ups,
    }
    if return_context:
        result["context"] = context

    return result
