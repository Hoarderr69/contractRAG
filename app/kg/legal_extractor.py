import json
import re
import hashlib
from typing import Dict, Any

from openai import AzureOpenAI

from app import config
from app.kg.models import KGNode, LegalExtractionResult

LEGAL_NODE_TYPES = [
    # Layer 1 — Universal (all 8 contracts)
    "Obligee",
    "Obligation",             # renamed from Paymentobligation — covers all 33 obligation subtypes
    "NoticeRecipient",
    "Indemnitor",
    "Obligor",
    "Agreement",
    "ForceMajeureEvent",
    "Indemnitee",
    "InsurancePolicy",

    # Layer 2 — Common (50–75% contracts)
    "Breach",
    "Party",
    "CurePeriod",
    "BreachingParty",
    "NonBreachingParty",      # split from BreachingParty
    "EffectiveDate",
    "PerformanceMilestoneDate", # split from EffectiveDate
    "TerminationEvent",
    "ConfidentialInformation",
    "Contract",
    "Dispute",
    "GovernmentalAuthority",
    "Invoice",
    "Notice",
    "ThirdParty",
    "ObligationTrigger",
    "InsuranceCertificate",
    "Claim",
    "Consent",
    "Deliverable",
    "Facility",
    "InterestRate",
    "LegalRequirement",
    "Liability",
    "ReimbursableCost",
    "Service",
    "TerminationRight",
    "Assignee",               # keep separate
    "Assignor",               # split from Assignee
]

LEGAL_RELATIONSHIP_TYPES = [
    # Layer 1 — Universal
    "IMPOSES_OBLIGATION_ON",
    "INDEMNIFIES",
    "CAPS_LIABILITY_OF",
    "GIVES_NOTICE_TO",
    "GRANTS_ACCESS_TO",
    "GRANTS_RIGHT_TO",
    "NOTIFIES",
    "PAYS",
    "PROVIDES_NOTICE_TO",
    "REIMBURSES",
    "TRIGGERS_OBLIGATION_OF",

    # Layer 2 — Common (use the canonical forms from the proposal)
    "APPLIES_TO",
    "OBLIGATES",
    "SURVIVES_TERMINATION_OF",
    "COOPERATES_WITH",
    "DELIVERS",
    "MAINTAINS",
    "MAKES_PAYMENT_TO",
    "PROVIDES",
    "REQUIRES_NOTICE_FROM",
    "LIMITS_INDEMNITY_OBLIGATION_OF",
    "ASSIGNS_RIGHTS_TO",
    "REQUIRES_COMPLIANCE_WITH",
    "BEARS_COSTS_OF",
    "COMPLIES_WITH",
    "NAMES_AS_ADDITIONAL_INSURED",
    "EXCUSES_BREACH_OF",
    "TRIGGERS_CURE_PERIOD_OF",
    "IMPOSES_OBLIGATION_ON",
    "FALLS_WITHIN_INDEMNITY_SCOPE_OF",
    "TERMINATES",
]

def slugify(value: str, max_len: int = 80) -> str:
    value = value or "unknown"
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:max_len] or "unknown"


def short_hash(value: str, length: int = 8) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


class LegalLLMExtractor:
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION,
        )

    def build_prompt(self, clause: KGNode) -> str:
        node_types_str = "\n".join(f"  - {t}" for t in LEGAL_NODE_TYPES)
        rel_types_str = "\n".join(f"  - {t}" for t in LEGAL_RELATIONSHIP_TYPES)

        return f"""
You are a legal contract knowledge graph extraction expert.

Extract legal-semantic entities and relationships from the clause below.
Use ONLY the allowed types listed. Do not invent new types.

ALLOWED ENTITY TYPES:
{node_types_str}

ALLOWED RELATIONSHIP TYPES:
{rel_types_str}

EXTRACTION RULES:
1. Extract only information explicitly supported by the text. Do not hallucinate.
2. Every entity id must be stable and deterministic: format "<type_lowercase>:<contract_id>:<slug_of_name>"
3. Every relationship source_id and target_id must refer to an extracted entity id OR the source clause id.
4. The source clause id is: {clause.kgId}
5. Confidence is a float 0.0–1.0 reflecting how explicitly the text supports this extraction.
6. evidenceQuote must be a verbatim excerpt from the clause text (max 200 chars). Use null if none.
7. Do not create duplicate entities for the same real-world party or concept within one clause.
8. Normalize party names to their contract-defined role (e.g. "Contractor", "Owner", "Either Party") — do not use document-specific company names.
9. If the clause imposes a duty or obligation on a party, create an Obligation entity and an IMPOSES_OBLIGATION_ON relationship from the clause to that obligation.
10. If the clause identifies a party bearing the obligation, create that party as an Obligor and link: Obligor --TRIGGERS_OBLIGATION_OF--> Obligation.
11. If the clause identifies the party receiving the benefit, create that party as an Obligee and link: Obligation --OBLIGATES--> Obligee.
12. If the clause contains an indemnification, create Indemnitor and Indemnitee entities and an INDEMNIFIES relationship.
13. If the clause caps or limits liability, create a Liability entity and a CAPS_LIABILITY_OF relationship.
14. If the clause references a force majeure event, create a ForceMajeureEvent entity.
15. If the clause defines a cure period, create a CurePeriod entity and a TRIGGERS_CURE_PERIOD_OF relationship from the triggering event to it.
16. If the clause contains a notice requirement, create a Notice entity with a GIVES_NOTICE_TO or PROVIDES_NOTICE_TO relationship.
17. If the clause concerns confidential information, create a ConfidentialInformation entity.
18. If the clause grants a termination right, create a TerminationRight and a TerminationEvent entity where applicable.
19. Store deadline values, notice periods, and monetary caps as properties on the relevant entity (e.g. {{"days": 30, "unit": "calendar days"}}), not as separate entity types.
20. Return valid JSON only — no prose, no markdown fences.

CONTRACT CONTEXT:
Contract ID: {clause.contractId}
Clause ID: {clause.kgId}
Clause title: {clause.title}
Clause type hint: {clause.clauseTypeHint}
Pages: {clause.pageStart}–{clause.pageEnd}

CLAUSE TEXT:
\"\"\"
{clause.text}
\"\"\"

Return JSON in exactly this shape:
{{
  "source_clause_id": "{clause.kgId}",
  "source_clause_title": "{clause.title}",
  "source_page_start": {clause.pageStart},
  "source_page_end": {clause.pageEnd},
  "entities": [
    {{
      "id": "obligation:{clause.contractId}:example_slug",
      "type": "Obligation",
      "name": "Short descriptive name",
      "properties": {{"deadline_days": 30}},
      "confidence": 0.9,
      "evidenceQuote": "verbatim excerpt from the clause text"
    }}
  ],
  "relationships": [
    {{
      "source_id": "{clause.kgId}",
      "target_id": "obligation:{clause.contractId}:example_slug",
      "type": "IMPOSES_OBLIGATION_ON",
      "properties": {{}},
      "confidence": 0.9,
      "evidenceQuote": "verbatim excerpt from the clause text"
    }}
  ]
}}
"""

    def extract_from_clause(self, clause: KGNode) -> LegalExtractionResult:
        prompt = self.build_prompt(clause)

        response = self.client.chat.completions.create(
            model=config.AZURE_OPENAI_CHAT_DEPLOYMENT,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You extract legal contract knowledge graphs as strict JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                },
            ],
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        data = self.repair_ids(data, clause)

        return LegalExtractionResult(**data)

    def repair_ids(self, data: Dict[str, Any], clause: KGNode) -> Dict[str, Any]:
        id_map = {}

        for ent in data.get("entities", []):
            old_id = ent.get("id")
            ent_type = ent.get("type", "Entity")
            name = ent.get("name", "unknown")

            if (
                not old_id
                or old_id == "unknown"
                or " " in old_id
                or old_id.count(":") < 2
            ):
                new_id = (
                    f"{ent_type.lower()}:"
                    f"{clause.contractId}:"
                    f"{short_hash(clause.kgId + name)}:"
                    f"{slugify(name)}"
                )
                ent["id"] = new_id
                if old_id:
                    id_map[old_id] = new_id

        for rel in data.get("relationships", []):
            if rel.get("source_id") in id_map:
                rel["source_id"] = id_map[rel["source_id"]]
            if rel.get("target_id") in id_map:
                rel["target_id"] = id_map[rel["target_id"]]

        data["source_clause_id"] = clause.kgId
        data["source_clause_title"] = clause.title
        data["source_page_start"] = clause.pageStart
        data["source_page_end"] = clause.pageEnd

        return data