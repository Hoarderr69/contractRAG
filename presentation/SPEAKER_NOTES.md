# Contract360 — Manager Briefing · Speaker Notes & Demo Script

A talk-track for the 5-slide deck (`Contract360_Manager_Deck.pptx` / `.html`).
Target audience: senior managers. Aim for ~8–10 minutes + live demo.

---

## Slide 0 — Title

> "Contract360 is an AI assistant for our energy & infrastructure contracts — EPC,
> O&M and PPA agreements. It's built end-to-end on Azure. In the next few minutes
> I'll cover the problem we set out to solve, the solution and how it works, the
> architecture, and then show it live. The headline: **every answer is grounded in
> the actual contract text and cites its source — built for auditability.**"

## Slide 1 — Problem, Solution & Value

- **Problem:** our key contracts are long, dense and high-stakes. Reviewing them —
  obligations, deadlines, payment terms, termination, indemnities — is slow, manual
  work. Generic AI chatbots hallucinate and don't cite sources, so they can't be
  trusted for legal decisions.
- **Solution:** upload a contract, ask in plain English, get an answer drawn from the
  real clause text that cites title, page and source. Clause-aware, with a knowledge
  graph for relationship questions.
- **Value:** faster review and due diligence; audit-ready answers; portfolio-wide
  visibility of obligations and deadlines.
- **One line to land:** "It runs entirely on the Azure stack we already operate — no
  new vendor footprint."

## Slide 1 (cont.) — High-Level Architecture

> "Two pipelines over one shared Azure backbone. **Ingestion** runs once per contract:
> parse → build a tree → clause-aware chunks with embeddings → searchable index,
> optionally extracting a knowledge graph. **Query** runs per question: an LLM router
> picks the best retrieval route — tree, graph or hybrid — then Azure OpenAI answers
> using only what was retrieved, with citations."

## Slide 2 — Detailed Architecture

> "For the engineers in the room: frontend → FastAPI → query pipeline (router →
> retrieval routes → answer generator). Writes go through an async ingestion worker
> pool with live progress. An offline knowledge-graph pipeline adds parties,
> obligations and rights to Cosmos Gremlin. Optional pieces — graph and Document
> Intelligence — are env-toggle. Full interactive diagram is in `ARCHITECTURE.md`."

## Slide 3 — Demo (see script below)

---

## Live Demo Script (~4–5 min)

1. **Upload** a sample contract (PDF). Narrate the progress: parse → embed → index.
2. **Ask:** *"What are the contractor's payment obligations?"* — let the answer stream.
3. **Click a citation** to open the supporting clause. *(This is the trust moment — always do it.)*
4. **Contrast routes:** ask a relationship question (graph) vs. a lookup (tree), call out the route label.
5. **Multi-contract scope:** filter to one contract, then query across several.

**Backup:** have the pre-recorded video ready (insert the link on Slide 3 before the
meeting). If the live environment misbehaves, switch to the video without apology.

### Good demo questions
- "Summarise the termination clauses and any notice periods."
- "What deadlines does the contractor have in the first 90 days?"
- "Which party bears liability for delay, and is there a cap?"
- "List the indemnities granted to the owner."

---

## Likely questions & crisp answers

- **"How do we know it isn't making things up?"** Answers are constrained to retrieved
  clause text and every claim carries a citation you can open and verify.
- **"Where does our data live?"** Inside our Azure tenant — Blob, AI Search, Cosmos,
  Azure OpenAI. No third-party model providers.
- **"Can it handle many contracts?"** Yes — multi-contract scope today; portfolio
  analytics on the roadmap.
- **"What about access control?"** User identity via header today; Azure Entra ID auth
  is the next production step.
- **"What does it cost to run?"** Azure-managed services, scale-to-load on Container
  Apps; embeddings/answers use cost-efficient model tiers (GPT-4 mini, embedding-3-small).
