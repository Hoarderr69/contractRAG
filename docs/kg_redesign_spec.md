# Contract360 Knowledge-Graph Redesign — Final Spec

Status: **design locked, ready to build**
Scope: **KG creation only** (extraction → graph). Retrieval upgrade is a separate, later layer.

---

## 0. TL;DR

- **Do NOT re-extract.** The saved extractions in `data/kg/extractions/*_legal_extractions.json`
  have good clause coverage, clean deterministic IDs, and rich relationships. We rebuild a
  clean graph from them with a deterministic transform — no LLM cost.
- The live graph's problems (fragmentation, label drift, lost edges, no cross-contract identity)
  come from the **transform + write** layer and an older mixed-provenance loader, **not** from
  the extractions.
- Fix = a 3-pass rebuild pipeline: **normalize → resolve (de-fragment) → canonicalize (cross-contract)**,
  then write a clean two-tier graph to Cosmos Gremlin.

---

## 1. What the data proved (grounding)

Measured from `data/kg/` + the live Gremlin graph:

| Finding | Evidence | Consequence |
|---|---|---|
| Coverage is fine | extractions cover 142/160, 313/508, 136/203 clauses | **no re-extraction for coverage** |
| Extraction IDs already clean | `party:<contract>:<slug(name)>`, no clause-hash | rebuild kills most fragmentation for free |
| Live-graph fragmentation is from old loader | `Client`×17 in graph, but clean IDs in JSON; graph has `EXTRACTED_ENTITY` (648) + structural edges | rebuild from JSON only, drop old mixed data |
| Parties already mostly `Party` | 1,460 `Party` mentions; Obligor/Obligee ~0 | role-as-label collapse is a tiny, safe transform |
| Label drift is mild | `IMPOSES_OBLIGATION` (1,950) is the main one | normalize a short alias map |
| `IMPOSES_OBLIGATION` edges = clause→obligation | source_id is a clause id with no vertex | redundant with denormalized citation fields → **drop** |
| Real cross-contract signal = regulators + named orgs | NERC, NYISO, FERC, CAISO shared; Con Edison in 5 variants | canonical layer must be role-vs-named aware |
| Role words dominate "overlap" | Seller/Buyer/Party shared across contracts | **never** merge role placeholders across contracts |
| `Edison` trap | `Con Edison` (Consolidated Edison) vs `SCE`/`Edison` (Southern California Edison) | canonicalizer must keep distinct orgs apart |
| Junk inputs exist | `ITEM-Attachment-…` (0 clauses); `Terra-Gen` double-underscore duplicate; status doc in search index | data cleanup pass |

**Do NOT adopt** `data/kg/schema_discovery/ontology_proposal.json → constrained_extraction_schema`:
it has casing bugs (`Paymentobligation`) and re-introduces role-as-label. We reuse only its
**alias clusters** to seed subtypes.

---

## 2. Final ontology (slim core labels + `subtype`)

70 flat types → **~12 core labels**, with fine distinctions on a `subtype` property and
**party-roles expressed on edges, not vertices.**

| Core label | `subtype` examples | Notes |
|---|---|---|
| `Party` | — | ALL party-roles collapse here; role lives on the edge |
| `GovernmentalAuthority` | regulator, iso, court | kept separate — cross-contract backbone (NERC, NYISO, FERC, CAISO) |
| `Obligation` | payment, compliance, reporting, maintenance, indemnity… | subtype seeded from discovery alias clusters |
| `Right` | access, termination, assignment… | |
| `Restriction` | confidentiality, non-assignment… | |
| `TemporalConstraint` | deadline, noticePeriod, frequency, effectiveDate, milestone | collapses Deadline/NoticePeriod/Frequency/EffectiveDate/PerformanceMilestoneDate |
| `Event` | forceMajeure, termination, breach, trigger | collapses ForceMajeureEvent/TerminationEvent/Breach/ObligationTrigger |
| `Condition` | condition, exception | |
| `FinancialTerm` | liability, cost, interestRate, invoice, amount | |
| `Instrument` | agreement, contract, notice, deliverable, insurancePolicy, consent, claim | |
| `Concept` | confidentialInfo, legalRequirement, service, facility, asset | |
| `CanonicalEntity` | org, regulator, person, facility | **NEW — Tier 2 global identity** |

Rationale: fewer labels → better future LLM adherence, far less fragmentation, simpler
traversal. `subtype` stays cheaply filterable in Gremlin (`has('subtype','payment')`).

---

## 3. Two-tier graph model

```
TIER 1 — MENTION layer  (per contract, clause-anchored)  — from extractions
    (Party)-[:OWED_BY]->… etc.   one node per (contract, normalized entity)

TIER 2 — CANONICAL layer (global)                         — built by Pass 3
    (CanonicalEntity)
        ^  RESOLVED_AS  (Party mention → CanonicalEntity), named entities only

Cross-contract = one hop:
    g.V('canonical:org:con_edison').in('RESOLVED_AS').in('OWED_BY')...
```

---

## 4. Node property schema

`kgId` is **kept** — deterministic primary key for idempotent upsert + bridge to citations/search.

### 4.1 Mention node (Tier 1)
```
# Identity
id / kgId        "<label>:<contractId>:<slug(normalizedName)>"   # parties: NO clause-hash
label            core label (Party, Obligation, …)
subtype          fine distinction (payment, deadline, forceMajeure, …) | null
name             raw surface form
normalizedName   cleaned form used for resolution
pk               tenantId            # Cosmos partition key (unchanged)
tenantId, contractId

# Provenance / citation  (unchanged — keep existing rendering working)
sourceClauseId, clauseTitle, sectionTitle, pageStart, pageEnd, sourcePath, evidenceQuote

# Resolution  (NEW — set by Pass 2/3)
entityClass      "named" | "role" | "concept"      # role-vs-named guard result
roleNormalized   buyer|seller|obligor|...  | null  # role placeholders, kept contract-local
canonicalId      FK → CanonicalEntity.id   | null  # named entities only

# Quality / reproducibility  (NEW)
confidence
extractionModel, extractionVersion, extractedAt

# Retrieval bridge  (NEW — reserve hook; populated later, no re-extraction needed)
searchDocId      key into Azure AI Search where this node's embedding lives | null
```

### 4.2 Canonical entity node (Tier 2 — NEW)
```
id               "canonical:<entityClass>:<slug>"     e.g. canonical:org:con_edison
label            "CanonicalEntity"
canonicalName    "Con Edison"
aliases          ["Consolidated Edison", "Consolidated Edison Company of New York, Inc.", …]
entityClass      org | regulator | person | facility
contractIds      [ …every contract it appears in… ]   # powers cross-contract directly
mentionCount     int
pk               tenantId
searchDocId      embedding key | null
```

---

## 5. Edge property schema
```
# Identity
edgeId           "<label>:<sourceId>:<targetId>"      # deterministic → idempotent upsert
label            canonical relationship (OWED_BY, HAS_DEADLINE, …)
role             optional — when a party-role is folded onto the edge

# Scope (denormalized for fast filtered traversal)
tenantId, contractId

# Provenance
evidenceQuote, sourceClauseId, confidence
```
New edge type (the cross-contract glue): **`RESOLVED_AS`**  (Party mention → CanonicalEntity).

**Dropped on rebuild:** `IMPOSES_OBLIGATION` (clause→obligation, redundant with denormalized
citation fields and has no clause vertex). Any edge whose endpoints don't both resolve to a
written vertex is logged + skipped (not silently lost).

---

## 6. The rebuild pipeline (deterministic, no LLM)

New package `app/kg/resolution/`. Input: `data/kg/extractions/*_legal_extractions.json`.

### Pass 1 — `ontology_normalizer.py`  (per clause)
- Map drifted labels → canonical (`IMPOSES_OBLIGATION`→drop; node casing fixes; role-labels→`Party`+edge role).
- Assign `label` + `subtype` from the slim ontology (subtype map seeded from discovery clusters).
- Drop junk labels; keep-and-log anything unmapped (never silently discard).

### Pass 2 — `entity_resolver.py`  (per contract)
- `normalizedName` (case/whitespace/punct/possessive folding).
- Classify each Party mention → `entityClass` via **deterministic rules**:
  - role gazetteer (Party, Parties, Buyer, Seller, Contractor, Either/Each/Other Party,
    Disclosing/Receiving/Defaulting/Non-Defaulting/Breaching Party, Guarantor, Lender…) → `role`
  - proper-noun / `Inc|LLC|LP|Corp|Authority|Commission` / known-org gazetteer → `named`
  - else → `concept`/leave as mention
- Merge mentions sharing `(contractId, label, normalizedName)` into one node → de-fragmentation.

### Pass 3 — `canonicalizer.py`  (global)
- For `named` mentions only: cluster across contracts into `CanonicalEntity`.
  - alias map (Con Edison family; NextEra family) + a hard **block-list of distinct orgs**
    so `Con Edison` ≠ `SCE`/Southern California Edison.
  - regulators/ISOs (NERC, NYISO, FERC, CAISO, SERC) → shared `entityClass: regulator`.
- Emit `CanonicalEntity` nodes + `RESOLVED_AS` edges; fill `contractIds[]`, `aliases[]`.
- **Role placeholders are never canonicalized across contracts.**

### Orchestrator — `app/scripts/rebuild_semantic_kg.py`
1. `clear_semantic_kg --all`  (wipe the mixed-provenance graph)
2. run Pass 1→3 over all extraction JSONs
3. write Tier 1 + Tier 2 to Gremlin (RU-aware, reuse `GremlinWriter`)
4. print a before/after report (vertex/edge counts, fragmentation %, canonical count)

### Data cleanup — `app/scripts/cleanup_inputs.py`
- skip `ITEM-Attachment-…` (0 clauses)
- dedupe `Terra-Gen_SJCE__PPA__PUBLIC_1` vs `Terra-Gen_SJCE_PPA_PUBLIC_1` in the search index
- remove `semantic_rag_current_status_and_execution_plan` from the search index

---

## 7. Live ingestion (after backfill is proven)
Wire Pass 1 (always) + a per-contract Pass 2 into `worker.py` `_run_kg_pipeline`, and run
Pass 3 as a periodic/global step (canonical layer needs all contracts). Until then, the
rebuild script is the source of truth.

---

## 8. What this fixes (acceptance criteria)
- [ ] One node per party per contract (no `Client`×17).
- [ ] One `Con Edison` canonical node spanning its 5 variants; `SCE` kept separate.
- [ ] NERC/NYISO/FERC/CAISO shared across contracts via `CanonicalEntity`.
- [ ] Role words (Seller/Buyer/Party) NOT merged across contracts.
- [ ] No edges lost silently; drift labels normalized.
- [ ] `contractId` on nodes AND edges → fast scoped traversal.
- [ ] `searchDocId` hook present on every node (retrieval upgrade needs no re-extraction).
- [ ] "Con Edison's obligations" returns the complete set; cross-contract queries traverse real identities.

---

## 9. Explicitly out of scope (later, separate)
- Retrieval upgrade (vector-anchored subgraph, agentic tools, community summaries).
- Re-extraction for richer indemnity/payment facts (only if quality proves insufficient after rebuild).
- Embedding population into Azure AI Search (hook reserved now).
```
