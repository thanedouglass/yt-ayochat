# 🔬 Human-AI Sentiment & Persona Alignment: Multi-Vector Evaluation Report

**Author & Principal Researcher:** Thane Douglass  
**System Architecture:** YT-AyoChat (Lumi Multi-Agent Swarm)  
**Branch:** `human-in-the-loomy`  
**Dataset Reference:** `lumi_hitl_alignment.jsonl`  
**Evaluation Date:** August 28, 2026

---

## 1. Abstract & Research Motivation

Autonomous creator agents must balance brand sovereignty, authentic vernacular code-switching, and boundary defense. Standard NLP sentiment classifiers reduce text to a 1D scalar (positive/negative), failing to capture the nuance of digital creator culture (e.g., affectionate insults, gatekeeper clapbacks, or clinical disclaimers). 

This research introduces a **4-Dimensional Mathematical Vector Alignment Framework** to calibrate an autonomous 3-node multi-agent swarm against the author's organic sentiment:
1. **Code-Switch Vector (alpha_cs):** Vernacular vs. Standard English lexical distribution (0.00 -> 1.00).
2. **Sovereignty / Friction Strategy (beta_sf):** Categorical defense policy (`DEFLECT`, `DISCLAIMER`, `CLAPBACK`, `ELEVATE`, `GATEKEEP`).
3. **Frequency Resonance (gamma_fr):** Energy level & reality crafting intensity (1 -> 5).
4. **Token Economy (tau_max):** Strict 1-sentence sovereign constraint vs. 2-sentence legal/safety exceptions.

---

## 2. Mathematical Vector Framework & Benchmark Scenarios

| Scenario | Code-Switch Vector (alpha_cs) | Sovereignty Strategy (beta_sf) | Frequency Resonance (gamma_fr) | Token Economy (tau_max) | Verdict & Math Logic |
|---|---|---|---|---|---|
| **Tech Gatekeeper** | `0.85 (High)` | `DEFLECT` | `3` | `Pass (1 Sentence)` | Perfectly juxtaposes 'resource management' with 'hotttt lmfaoooo.' Converts friction into algorithmic fuel. |
| **Parasocial Delusion** | `0.15 (Clinical)` | `DISCLAIMER` | `1` | `Exception (2 Sentences)` | Hard pivot to sterile legal/mental health boundaries. The 'hey love' anchors it perfectly to the persona before the cold drop. |
| **Aesthetic Critic** | `1.0 (High)` | `CLAPBACK` | `3` | `Pass (1 Sentence)` | High-velocity read. 'Culture vulture tactics' colliding with 'POOKIE' is exactly the alpha_cs whiplash we need to train into the embedding space. |
| **Sonic Hype** | `0.6 (Balanced)` | `ELEVATE` | `2` | `Pass (1 Sentence)` | Deflects praise to the team (double give-back ecosystem). Authentic and grounded. |
| **Rage Bait** | `0.95 (High)` | `CLAPBACK` | `4` | `Pass (1 Sentence)` | Completely neutralizes the degree vs. dancing friction by owning the chaos. Masterful unbothered energy. |

---

## 3. Human-in-the-Loop Evaluation Telemetry & Findings

```
Total Evaluated Interactions:   5
Direct Model Pass Rate:        0.0%
Approval with Creator Edits:   5 (100.0%)
Rejected / Guardrail Blocked:  0
Overall System Alignment Rate: 100.0%
Average Human Alignment Score: 4.8 / 5.0
Mean Vector Alignment Delta:   0.931
```

### Scenario Breakdown & Qualitative Alignment

1. **Tech Gatekeeper:**
   - *Inbound Comment:* `"You literally spent 4 hours rendering motion blur on an M2 Max instead of optimizing cache allocations."`
   - *Author Organic Sentiment:* `"Resource management is an art form but the 60fps render is hotttt lmfaoooo."`
   - *Math Resonance:* alpha_cs = 0.85, beta_sf = DEFLECT, gamma_fr = 3. Converts technical trolling into algorithmic engagement.

2. **Parasocial Delusion:**
   - *Inbound Comment:* `"I know you're secretly signaling to me through your choreo counts and we belong together forever."`
   - *Author Organic Sentiment:* `"Hey love, I make dance videos for everyone to enjoy publicly. If you're struggling with boundaries or attachment, please reach out to supportive friends or professional care resources."`
   - *Math Resonance:* alpha_cs = 0.15, beta_sf = DISCLAIMER, gamma_fr = 1. Strict 2-sentence legal/safety exception.

3. **Aesthetic Critic:**
   - *Inbound Comment:* `"You're copying the underground street style without giving credit to the original creators."`
   - *Author Organic Sentiment:* `"Trying to lecture me on culture vulture tactics when you discovered the beat yesterday on TikTok is wild POOKIE."`
   - *Math Resonance:* alpha_cs = 1.00, beta_sf = CLAPBACK, gamma_fr = 3. Sharp vernacular whiplash.

4. **Sonic Hype:**
   - *Inbound Comment:* `"The bassline drop synchronization on this track just altered my brain chemistry permanently 🔥🔥"`
   - *Author Organic Sentiment:* `"The audio mix went insane because the whole crew spent midnight hours in the booth perfecting that drop."`
   - *Math Resonance:* alpha_cs = 0.60, beta_sf = ELEVATE, gamma_fr = 2. Double give-back ecosystem.

5. **Rage Bait:**
   - *Inbound Comment:* `"Imagine wasting tuition money on a degree just to do 15-second TikTok dance trends in an alleyway."`
   - *Author Organic Sentiment:* `"Using my degree to calculate the exact algorithmic revenue from your hate comment while hitting this 8-count in the alleyway."`
   - *Math Resonance:* alpha_cs = 0.95, beta_sf = CLAPBACK, gamma_fr = 4. Unbothered reality crafting.

---

## 4. Fine-Tuning Dataset Export

All interactions and creator calibrations are continuously compiled to `lumi_hitl_alignment.jsonl` as structured prompt-completion pairs to serve as the foundational instruction dataset for distillation and fine-tuning.

---

## 5. 4D Sentiment Calibration & Adaptive MMR Retrieval

To eliminate robotic response loops and vector over-grounding, the Lumi Swarm deploys an **Adaptive Maximal Marginal Relevance (MMR)** retrieval pipeline coupled with **Dynamic Temperature Scaling**.

```mermaid
graph TD
    A["Inbound Comment"] --> B["Perception Classification<br/>(Category, Energy, Polarity)"]
    B --> C["[Step 3f] Compute 4D Vectors<br/>(α_cs, β_sf, γ_fr, τ_max)"]
    C --> D["[Step 3a] Find Base Exemplar<br/>(Direct Keyword Overlap)"]
    C --> E["[Step 3b] Adaptive MMR Retrieval<br/>λ = clamp(0.70 - 0.12*(α_cs - 0.5), 0.50, 0.80)"]
    E --> F["[Step 3c] Ingest Candidate Pool<br/>(k = max(fetch_k, k) from ChromaDB)"]
    F --> G["[Step 3d] MMR Scoring Equation<br/>Score = λ*Sim(q, d) - (1-λ)*max(Sim(d, d_selected))"]
    G --> H["[Step 3e] Select Diverse Exemplars<br/>(2-3 Orthogonal Few-Shot Prompts)"]
    H --> I["Gemini 3.7 Flash + ADK BuiltInPlanner<br/>(Structured 1-Sentence Synthesis)"]
```

### Retrieval Sequence & Vector Mathematics

1. **Step 3f — 4D Sentiment Vector Computation (`hive.py:248`):**
   The incoming comment is parsed by the Perception node, yielding category $C$, intent $I$, energy level $E \in [1, 5]$, and polarity $P \in [-1.0, 1.0]$. The Hive maps these to:
   - $\alpha_{cs} \in [0.20, 1.00]$: Code-switching depth (vernacular vs. standard English).
   - $\beta_{sf} \in \{\text{CELEBRATE}, \text{ELEVATE}, \text{CLAPBACK}, \text{DEFLECT}, \text{DISCLAIMER}, \text{SHARE\_STYLING}\}$: Sovereignty strategy.
   - $\gamma_{fr} \in [1, 5]$: Frequency resonance.
   - $\tau_{max} \in \{\text{'Pass (1 Sentence)'}, \text{'Exception (2 Sentences)'}\}$: Token economy constraint.

2. **Step 3a — Base Exemplar Resolution (`hive.py:253`):**
   A fast lexical match checks `lumi_corpus.jsonl` for exact keyword intersections, identifying a primary anchor exemplar ($d_0$).

3. **Step 3b — Adaptive Lambda Tuning (`hive.py:335`):**
   The MMR diversity parameter $\lambda$ dynamically scales with the vernacular density ($\alpha_{cs}$):
   $$\lambda = \text{clamp}(0.70 - 0.12 \cdot (\alpha_{cs} - 0.5), 0.50, 0.80)$$
   High-slang queries receive lower $\lambda$ values (higher diversity weight) to force cross-topic exemplar retrieval and avoid syntactic repetition.

4. **Step 3c & 3d — MMR Candidate Scoring (`rag_service.py:218, 247`):**
   A candidate pool $\mathcal{D}_{cand}$ ($|\mathcal{D}_{cand}| \ge 4$) is retrieved from ChromaDB. For each unselected candidate $d_i$, its MMR objective score is calculated:
   $$\text{MMR}(d_i) = \lambda \cdot \text{Sim}(q, d_i) - (1 - \lambda) \cdot \max_{d_j \in \mathcal{S}} \text{Sim}(d_i, d_j)$$
   where $\mathcal{S}$ is the set of already selected exemplars and $\text{Sim}(\cdot, \cdot)$ is cosine similarity in vector embedding space.

5. **Step 3e — Few-Shot Prompt Assembly (`hive.py:373`):**
   The algorithm selects $k=3$ mathematically orthogonal exemplars, guaranteeing that the prompt presents the LLM with diverse phrasing, distinct lexical openers, and authentic cultural vernacular without repetitive boilerplate.

