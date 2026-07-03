# Contract360 — Demo Video Script (~3 minutes)

**Setup before recording:** App running with 2–3 contracts already ingested (at least one graph-enabled), one fresh PDF ready on the desktop to upload, browser at the chat UI, terminal hidden. Record at 1080p, trim all dead air.

---

## SCENE 1 — The Hook (0:00–0:20)

**Screen:** A dense contract PDF, scrolling fast through pages of legal text.

> **Narration:** "This is a 60-page commercial contract. Somewhere in here is a termination clause, a payment deadline, and an obligation your team is about to miss. Finding it takes a lawyer an hour. Contract360 finds it in seconds — with the exact clause cited."

**Cut to:** The Contract360 chat interface, clean and empty.

---

## SCENE 2 — Upload & Ingestion (0:20–0:50)

**Screen:** Drag the PDF onto the Upload Panel. Progress bar and stage indicators animate: *uploading → parsing → embedding → indexing → done*.

> **Narration:** "Drop in any contract. Contract360 parses it with Azure Document Intelligence, rebuilds its structure as a clause-level tree — articles, sections, clauses — then embeds and indexes every clause. No manual tagging. No templates."

**Screen:** Contract appears in the sidebar.

> **Narration:** "Under a minute later, it's ready to question."

*(Recording tip: speed up the ingestion wait 4–8x with a timelapse cut.)*

---

## SCENE 3 — Ask Anything (0:50–1:30)

**Screen:** Type: **"What are the termination for convenience terms?"** Answer streams in.

> **Narration:** "Ask in plain English. An LLM router reads your question, decides the best retrieval strategy, and pulls only the relevant clauses."

**Screen:** Click **"Show sources"** — expand the citations showing the source path, e.g. `demo > 4. Termination > 4.2 Termination for Convenience`.

> **Narration:** "Every answer is grounded. Each citation traces to the exact article, section, and clause it came from — so you never have to take the AI's word for it."

---

## SCENE 4 — The Differentiator: Four Retrieval Routes (1:30–2:20)

**Screen:** Ask three questions in sequence, letting each answer land briefly.

1. **"Summarize Article XII."**

> **Narration:** "Structural questions use TreeRAG — it navigates the contract's actual hierarchy, pulling the section with its parent and sibling clauses for full context."

2. **"What obligations does the Supplier owe, and by when?"**

> **Narration:** "Semantic questions hit the knowledge graph. During ingestion, Contract360 extracts parties, obligations, rights, and deadlines into a graph database — so it answers from structured facts, not just similar-looking text."

3. **Follow-up: "What happens if they miss that deadline?"**

> **Narration:** "And it holds a real conversation. 'They' and 'that deadline' are resolved from chat history before retrieval even starts. Hybrid mode combines vector search with graph expansion to connect the clause to its consequences."

*(Optional overlay: a small graphic flashing `search · tree · graph · hybrid` as each route fires.)*

---

## SCENE 5 — Sessions & Scale (2:20–2:40)

**Screen:** Open the sidebar — show multiple sessions, click the contract filter, switch sessions.

> **Narration:** "Every conversation is a persistent session, filterable by contract. Ask about one agreement or your whole portfolio."

---

## SCENE 6 — Close (2:40–3:00)

**Screen:** Quick architecture card (one slide): React → FastAPI → LLM Router → Azure AI Search + Cosmos Gremlin + TreeRAG → GPT-4.

> **Narration:** "Contract360. Upload a contract, ask a question, get a cited answer — powered by a router that picks the right retrieval strategy every time. Contracts, answered."

**Screen:** Logo / repo URL. End.

---

## Delivery notes

- **Pace:** ~140 words/min narration; every scene cuts on action, not on silence.
- **The money shots:** the ingestion stage dots completing, the citation expanding, and the follow-up question resolving "they" — make sure all three are clearly visible.
- **One rule:** never show an empty answer or a loading spinner for more than 2 seconds — cut it.
