"""
Local in-memory graph store built from data/kg/extractions/*.json.

Drop-in backend for GraphNativeRetriever when Cosmos Gremlin is not configured.
Exposes the same public API so graph_retriever.py needs no structural change.
"""

import json
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set

from app import config

logger = logging.getLogger(__name__)

_STORE: Optional["LocalGraphStore"] = None


def get_local_graph_store() -> "LocalGraphStore":
    global _STORE
    if _STORE is None:
        _STORE = LocalGraphStore()
        _STORE.load()
    return _STORE


class LocalGraphStore:
    def __init__(self):
        # entity_id → normalized entity dict (with clause metadata merged in)
        self._entities: Dict[str, Dict] = {}
        # entity_type → [entity_ids]
        self._by_type: Dict[str, List[str]] = defaultdict(list)
        # rel_type → source_id → [target_ids]
        self._out: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        # rel_type → target_id → [source_ids]
        self._in: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        # contract_id → set of entity_ids
        self._by_contract: Dict[str, Set[str]] = defaultdict(set)

    # ── Loading ────────────────────────────────────────────────────────────────

    def load(self):
        extractions_dir = config.KG_EXTRACTIONS_DIR
        if not extractions_dir.exists():
            logger.warning("LocalGraphStore: extractions dir not found at %s", extractions_dir)
            return
        files = sorted(extractions_dir.glob("*_legal_extractions.json"))
        logger.info("LocalGraphStore: loading %d extraction files", len(files))
        for f in files:
            contract_id = f.name.replace("_legal_extractions.json", "")
            try:
                with open(f, encoding="utf-8") as fp:
                    records = json.load(fp)
                self._ingest(contract_id, records)
            except Exception as exc:
                logger.warning("LocalGraphStore: skipping %s — %s", f.name, exc)
        logger.info(
            "LocalGraphStore: %d entities across %d contracts",
            len(self._entities),
            len(self._by_contract),
        )

    def _ingest(self, contract_id: str, records: List[Dict]):
        for rec in records:
            clause_meta = {
                "contractId":     contract_id,
                "sourceClauseId": rec.get("source_clause_id"),
                "clauseTitle":    rec.get("source_clause_title"),
                "pageStart":      rec.get("source_page_start"),
                "pageEnd":        rec.get("source_page_end"),
            }
            for e in rec.get("entities", []):
                eid = e["id"]
                # Don't overwrite a richer entry from another clause
                if eid not in self._entities:
                    self._entities[eid] = {
                        "kgId":          eid,
                        "name":          e.get("name"),
                        "legalType":     e.get("type"),
                        "confidence":    e.get("confidence"),
                        "evidenceQuote": e.get("evidenceQuote"),
                        **clause_meta,
                    }
                self._by_type[e.get("type", "unknown")].append(eid)
                self._by_contract[contract_id].add(eid)

            for r in rec.get("relationships", []):
                rtype, src, tgt = r["type"], r["source_id"], r["target_id"]
                self._out[rtype][src].append(tgt)
                self._in[rtype][tgt].append(src)

    # ── Scope helpers ──────────────────────────────────────────────────────────

    def _scope(self, ids: List[str], contract_id=None, contract_ids=None) -> List[str]:
        allowed: Optional[Set[str]] = None
        if contract_id:
            allowed = {contract_id}
        if contract_ids:
            allowed = (allowed or set()) | set(contract_ids)
        if allowed is None:
            return ids
        return [i for i in ids if self._entities.get(i, {}).get("contractId") in allowed]

    def _by_types(self, types: List[str], contract_id=None, contract_ids=None) -> List[Dict]:
        ids: List[str] = []
        for t in types:
            ids.extend(self._by_type.get(t, []))
        ids = list(dict.fromkeys(ids))
        ids = self._scope(ids, contract_id, contract_ids)
        return [self._entities[i] for i in ids if i in self._entities]

    def _follow_out(self, src_ids: List[str], rel_type: str) -> List[str]:
        out: List[str] = []
        for s in src_ids:
            out.extend(self._out[rel_type].get(s, []))
        return list(dict.fromkeys(out))

    def _follow_in(self, tgt_ids: List[str], rel_type: str) -> List[str]:
        out: List[str] = []
        for t in tgt_ids:
            out.extend(self._in[rel_type].get(t, []))
        return list(dict.fromkeys(out))

    # ── Party matching ─────────────────────────────────────────────────────────

    _PARTY_LABELS = [
        "Party", "Obligor", "Obligee", "Indemnitor", "Indemnitee",
        "BreachingParty", "NonBreachingParty", "NoticeRecipient",
    ]

    def _party_ids(self, name: str, contract_id=None, contract_ids=None) -> List[str]:
        name_lower = name.lower()
        matches: List[str] = []
        for pt in self._PARTY_LABELS:
            for eid in self._scope(self._by_type.get(pt, []), contract_id, contract_ids):
                ename = (self._entities.get(eid, {}).get("name") or "").lower()
                if name_lower in ename or ename in name_lower:
                    matches.append(eid)
        return list(dict.fromkeys(matches))

    # ── Public query API (mirrors GraphNativeRetriever) ───────────────────────

    def get_all_obligations(self, contract_id=None, contract_ids=None) -> List[Dict]:
        return self._by_types(["Obligation"], contract_id, contract_ids)

    def get_obligations_by_party(self, party_name: str, contract_id=None, contract_ids=None) -> List[Dict]:
        # Obligation -OWED_BY-> Party   →   follow IN edges of OWED_BY from party
        party_ids = self._party_ids(party_name, contract_id, contract_ids)
        ob_ids = self._follow_in(party_ids, "OWED_BY")
        ob_ids = self._scope(ob_ids, contract_id, contract_ids)
        return [self._entities[i] for i in ob_ids if i in self._entities]

    def get_obligations_owed_to_party(self, party_name: str, contract_id=None, contract_ids=None) -> List[Dict]:
        # Obligation -OWED_TO-> Party
        party_ids = self._party_ids(party_name, contract_id, contract_ids)
        ob_ids = self._follow_in(party_ids, "OWED_TO")
        ob_ids = self._scope(ob_ids, contract_id, contract_ids)
        return [self._entities[i] for i in ob_ids if i in self._entities]

    def get_obligations_with_deadlines(self, contract_id=None, contract_ids=None) -> List[Dict]:
        """
        Returns obligations that have a HAS_DEADLINE edge, enriched with:
          - deadlineName / deadlineEvidence  (from the Deadline vertex)
          - responsibleParty                 (from OWED_BY edge — who must meet it)
        """
        ob_ids = self._scope(self._by_type.get("Obligation", []), contract_id, contract_ids)
        result: List[Dict] = []
        for ob_id in ob_ids:
            dl_ids = self._out["HAS_DEADLINE"].get(ob_id, [])
            if not dl_ids:
                continue
            ob = dict(self._entities.get(ob_id, {}))
            dl = self._entities.get(dl_ids[0], {})
            # Responsible party via OWED_BY
            p_ids = self._out["OWED_BY"].get(ob_id, [])
            party_name = self._entities.get(p_ids[0], {}).get("name") if p_ids else None
            ob["deadlineName"]     = dl.get("name") or dl.get("evidenceQuote", "")[:80]
            ob["deadlineEvidence"] = dl.get("evidenceQuote")
            ob["responsibleParty"] = party_name
            result.append(ob)
        return result

    def get_rights(self, contract_id=None, contract_ids=None) -> List[Dict]:
        return self._by_types(["Right"], contract_id, contract_ids)

    def get_restrictions(self, contract_id=None, contract_ids=None) -> List[Dict]:
        return self._by_types(["Restriction"], contract_id, contract_ids)

    def get_indemnity_facts(self, contract_id=None, contract_ids=None) -> List[Dict]:
        items = self._by_types(["Indemnitor", "Indemnitee"], contract_id, contract_ids)
        result: List[Dict] = []
        for item in items:
            if item.get("legalType") == "Indemnitor":
                tgt_ids = self._out["INDEMNIFIES"].get(item["kgId"], [])
                indemnitee = self._entities.get(tgt_ids[0], {}).get("name") if tgt_ids else None
                result.append({**item, "indemnitee": indemnitee})
            else:
                result.append(item)
        return result

    def get_termination_facts(self, contract_id=None, contract_ids=None) -> List[Dict]:
        return self._by_types(["TerminationEvent", "TerminationRight"], contract_id, contract_ids)

    def get_breach_cure_facts(self, contract_id=None, contract_ids=None) -> List[Dict]:
        return self._by_types(["Breach", "CurePeriod"], contract_id, contract_ids)

    def get_notice_facts(self, contract_id=None, contract_ids=None) -> List[Dict]:
        return self._by_types(["Notice", "NoticeRecipient", "NoticePeriod"], contract_id, contract_ids)

    def get_payment_facts(self, contract_id=None, contract_ids=None) -> List[Dict]:
        return self._by_types(["Invoice", "ReimbursableCost", "InterestRate"], contract_id, contract_ids)

    def get_liability_facts(self, contract_id=None, contract_ids=None) -> List[Dict]:
        return self._by_types(["Liability"], contract_id, contract_ids)

    def get_shared_parties(self, contract_ids=None) -> Dict[str, List[str]]:
        party_contracts: Dict[str, Set[str]] = defaultdict(set)
        for pt in self._PARTY_LABELS:
            for eid in self._by_type.get(pt, []):
                e = self._entities.get(eid, {})
                name = e.get("name")
                cid  = e.get("contractId")
                if name and cid:
                    if not contract_ids or cid in set(contract_ids):
                        party_contracts[name].add(cid)
        return {n: sorted(cs) for n, cs in party_contracts.items() if len(cs) > 1}

    def get_obligations_grouped_by_contract(self, contract_ids=None) -> Dict[str, List[Dict]]:
        return self._group_by_contract(self.get_all_obligations(contract_ids=contract_ids))

    def get_deadlines_grouped_by_contract(self, contract_ids=None) -> Dict[str, List[Dict]]:
        return self._group_by_contract(self.get_obligations_with_deadlines(contract_ids=contract_ids))

    def _group_by_contract(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        grouped: Dict[str, List[Dict]] = defaultdict(list)
        for item in items:
            grouped[item.get("contractId") or "unknown"].append(item)
        return dict(grouped)

    # ── Availability checks ────────────────────────────────────────────────────

    def kg_exists(self, contract_id: str) -> bool:
        return bool(self._by_contract.get(contract_id))

    def kg_exists_any(self, contract_ids: List[str]) -> bool:
        return any(self.kg_exists(cid) for cid in contract_ids)

    def has_any_data(self) -> bool:
        return bool(self._entities)

    def list_contracts(self) -> List[str]:
        return list(self._by_contract.keys())

    def get_obligation_burden_analysis(
        self,
        contract_id: Optional[str] = None,
        contract_ids: Optional[List[str]] = None,
        top_parties: int = 5,
        examples_per_party: int = 3,
    ) -> str:
        """
        Pre-aggregated obligation burden analysis suitable as LLM context.
        Returns a compact string: party counts + percentages + example obligations,
        grouped by contract.  Designed for the cross-contract comparison demo question.
        """
        scope_ids: Optional[List[str]] = None
        if contract_ids:
            scope_ids = contract_ids
        elif contract_id:
            scope_ids = [contract_id]

        ob_ids = self._scope(self._by_type.get("Obligation", []), contract_id, contract_ids)

        # Group obligations by contract then by responsible party
        # Structure: contract_id -> party_name -> [obligation dicts]
        from collections import defaultdict
        by_contract: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))

        for ob_id in ob_ids:
            ob = self._entities.get(ob_id, {})
            cid = ob.get("contractId", "unknown")
            p_ids = self._out["OWED_BY"].get(ob_id, [])
            pname = self._entities.get(p_ids[0], {}).get("name", "Unassigned") if p_ids else "Unassigned"
            by_contract[cid][pname].append(ob)

        lines: List[str] = [
            "=" * 80,
            "OBLIGATION BURDEN ANALYSIS — KNOWLEDGE GRAPH",
            "=" * 80,
            "",
            "INSTRUCTIONS: Answer as an analytical summary.",
            "  - State which party role carries the most obligations in each contract.",
            "  - Compare the Contractor vs Owner/Client ratio across contracts.",
            "  - Note whether the imbalance is consistent or varies.",
            "",
        ]

        for cid in sorted(by_contract.keys()):
            party_map = by_contract[cid]
            total = sum(len(v) for v in party_map.values())
            sorted_parties = sorted(party_map.items(), key=lambda x: -len(x[1]))

            lines.append(f"CONTRACT: {cid}")
            lines.append(f"Total obligations: {total}")
            lines.append("Obligation distribution by party:")

            for pname, obs in sorted_parties[:top_parties]:
                pct = 100 * len(obs) // total if total else 0
                lines.append(f"  {pname}: {len(obs)} obligations ({pct}%)")
                for ex in obs[:examples_per_party]:
                    ev = (ex.get("evidenceQuote") or "")[:100]
                    lines.append(f"    • {ex.get('name', '(unnamed)')}")
                    if ev:
                        lines.append(f"      Evidence: \"{ev}\"")
            lines.append("")

        return "\n".join(lines)
