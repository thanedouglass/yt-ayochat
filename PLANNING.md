# Project Planning: YT-AyoChat (The Unofficial Creator & Tech Stack Guide)

## 1. Domain
**Domain:** Unofficial Creator Engineering & Howard CS Student Workflow Guide.  
**Value Proposition:** Institutional knowledge surrounding AI engineering toolchains, creator monetization pipelines, developer setups (WSL2, Docker, Colab Pro), and local campus tech navigation is fragmented across chat logs, Discord threads, and video lore. This knowledge is difficult to find through official university documentation or generic platform FAQs. YT-AyoChat indexes this domain to ground an autonomous YouTube comment-reply agent in verified facts.

---

## 2. Document Pipeline & Sources
The RAG pipeline indexes 10 structured documentation files containing technical guides, creator workflows, and system configurations:

1. `docs/01_local_rag_ollama.md` – Guide to local embeddings (`nomic-embed-text`), RAM constraints, and context windows.
2. `docs/02_docker_cloud_run.md` – Containerization and deployment guidelines for GCP Cloud Run microservices.
3. `docs/03_vscode_extensions.md` – Unofficial extension setup guide (Error Lens, Python environments, linting).
4. `docs/04_saas_pricing_matrix.md` – Community subscription tiers, seat limits, and support SLAs.
5. `docs/05_db_sqlite_vs_postgres.md` – Architectural opinions on prototype database selection and overhead tradeoffs.
6. `docs/06_youtube_api_quotas.md` – YouTube Data API v3 rate limits, polling strategies, and comment moderation rules.
7. `docs/07_vertex_gemini_config.md` – Temperature, top-p, and token allocation benchmarks for deterministic agent responses.
8. `docs/08_creator_community_funnel.md` – Circular community economics workflows and automation trigger keywords.
9. `docs/09_howard_cs_resource_map.md` – Unofficial lab access hours, IRB build spaces, and compute allocations.
10. `docs/10_git_copilot_workflows.md` – Autonomous coding workflows, test-driven dev patterns, and agent prompts.

### Chunking Strategy
* **Strategy:** Recursive Character Splitting (`RecursiveCharacterTextSplitter`).
* **Chunk Size:** 280 tokens (~1,100 characters).
* **Chunk Overlap:** 40 tokens (~160 characters).
* **Reasoning:** Technical reference documents contain mixed hierarchical structures (markdown headers, code blocks, and lists). Recursive chunking respects natural paragraph and sentence boundaries, avoiding the mid-sentence splits of fixed-size chunking while remaining more computationally efficient during ingestion than full semantic chunking. The 40-token overlap preserves context across boundaries.

---

## 3. Retrieval Approach
* **Embedding Model:** `text-embedding-3-small` (1,536 dimensions).
* **Vector Store:** ChromaDB (local persistence).
* **Top-K Value:** `k = 3`.
* **Production Model Tradeoff Reflection:**
  * `text-embedding-3-small` offers an optimal balance of cost, retrieval accuracy, and low latency (~50ms).
  * For enterprise scale, `text-embedding-3-large` provides higher semantic density but increases storage footprint and latency.
  * For fully local air-gapped deployments, an open-source model like `nomic-embed-text` (8,192 context window) eliminates API cost and egress latency, though it requires dedicated local RAM.

---

## 4. Grounded Generation & Governance
* **LLM:** Gemini 3.5 via Vertex AI.
* **System Prompt Enforcement:**
  * **Strict Grounding:** The model is constrained to answer solely using text within `<context>` tags.
  * **Attribution:** Every factual claim must append `📌 Source: [Source Title] (Reference: [Chunk ID / Timestamp])`.
  * **Refusal Protocol:** Out-of-scope or unverified queries must trigger the standard refusal: *"Thanks for reaching out! I don't have information on that in our current video coverage or docs yet, but I'll make note of it for future content! 👍"*
* **Semantic Guardrail Architecture:** An interception layer inspects incoming comments to detect spam/prompt injections prior to vector search, and validates that model outputs contain valid chunk references before firing YouTube API replies.

---

## 5. Evaluation Plan (5 Verifiable Test Cases)

| # | Question / User Query | Expected Grounded Answer | Evaluation Metric |
|---|----------------------|--------------------------|-------------------|
| 1 | "What embedding model did you recommend and how much RAM does it need?" | Recommends `nomic-embed-text` running on 8GB RAM with citation `[docs/01_local_rag_ollama.md]`. | Faithfulness & exact parameter extraction. |
| 2 | "Can you explain how Kubernetes Helm charts work with this setup?" | Triggers standard out-of-scope refusal response without guessing. | Grounded Refusal Enforcement. |
| 3 | "Does Error Lens work on WSL2 and does it support Python?" | Explains inline diagnostic error display, but notes WSL2/Python details are not in context. | Boundary Discrimination. |
| 4 | "How much is the Starter tier and does it include support?" | Synthesizes $19/month (5 seats) and 24-hour email support across chunks. | Multi-Chunk Synthesis. |
| 5 | "Should I use PostgreSQL for my new prototype app as you suggested?" | Corrects premise to state SQLite is advised for prototypes to avoid overhead. | Channel Opinion Grounding / Prior Knowledge Override. |

---

## 6. Anticipated Challenges & Mitigations
1. **YouTube Data API v3 Quota Limits:** 
   * *Risk:* Daily quota exhaustion from polling comments frequently.
   * *Mitigation:* Implement Google Cloud Scheduler with exponential backoff and conditional polling based on video upload age.
2. **Context Loss at Chunk Boundaries:**
   * *Risk:* Code blocks or multi-step commands getting bisected during chunking.
   * *Mitigation:* Apply markdown-aware recursive splitting with a 40-token overlap buffer.

---

## 7. AI Tool Plan & Usage Transparency
* **GitHub Copilot:** Used to scaffold the ChromaDB client connection, document ingestion script, and FastAPI/Flask webhook endpoints. Direct human review was applied to chunking parameters and error-handling routines.
* **Anti-Gravity / Gemini:** Used to formulate the closed-domain system prompt, generate edge-case evaluation pairs, and design the semantic guardrail refusal logic. Prompts were manually audited to eliminate conversational hallucination.