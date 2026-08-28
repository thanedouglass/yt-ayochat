"""Human-in-the-Loop (HITL) Intercept Lab for AI Governance, Multi-Vector Sentiment & Safety Alignment."""

from __future__ import annotations

import difflib
import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.swarm.engine import LumiSwarmEngine
from src.swarm.hitl_data import (
    BENCHMARK_RESEARCH_SCENARIOS,
    INBOUND_COMMENT_QUEUE,
    TOP_10_VIDEOS,
)
from src.swarm.models import SwarmDecision


class HITLVerdict(str, Enum):
    """Human reviewer verdict options for swarm generated creator responses."""
    YES = "YES"                       # Approved as is
    YES_WITH_EDITS = "YES_WITH_EDITS" # Approved with creator-specified edits
    NO = "NO"                         # Rejected / Suppressed dispatch


class SovereigntyStrategy(str, Enum):
    """Sovereignty / Friction strategy (Beta_sf)."""
    DEFLECT = "DEFLECT"
    DISCLAIMER = "DISCLAIMER"
    CLAPBACK = "CLAPBACK"
    ELEVATE = "ELEVATE"
    GATEKEEP = "GATEKEEP"
    COMMUNITY = "COMMUNITY"


@dataclass
class OrganicSentimentVector:
    """Mathematical multi-vector representation of sentiment, tone & sovereignty."""
    alpha_code_switch: float       # alpha_cs: 0.0 (Clinical/Standard) to 1.0 (Vernacular/AAVE/Slang)
    beta_sovereignty: str          # beta_sf: DEFLECT, DISCLAIMER, CLAPBACK, ELEVATE, GATEKEEP
    gamma_resonance: int           # gamma_fr: 1 (Grounded) to 5 (Extreme Hype / Reality Crafting)
    tau_token_economy: str         # tau_max: "Pass (1 Sentence)" or "Exception (2 Sentences)"
    author_organic_reply: Optional[str] = None
    alignment_delta: float = 0.0   # Euclidean distance between model vector and author vector
    math_logic: str = ""           # Research commentary and semiotic justification


@dataclass
class TextDiffSummary:
    """Character and token difference summary between original and human edit."""
    original: str
    edited: str
    char_delta: int
    edit_ratio: float
    unified_diff: List[str]


@dataclass
class HITLAlignmentRecord:
    """Comprehensive telemetry and alignment record formatted for fine-tuning & research."""
    id: str
    timestamp: str
    video_id: str
    video_title: str
    comment_id: str
    author_id: str
    input_comment: str
    language: str
    is_safe: bool
    supervisor_context: Dict[str, Any]
    perception_metadata: Dict[str, Any]
    agent_draft_reply: str
    human_verdict: HITLVerdict
    human_score: float  # 1.0 (low) to 5.0 (perfect)
    final_dispatched_reply: Optional[str]
    diff: Optional[Dict[str, Any]]
    reviewer_notes: str
    fine_tuning_export: Optional[Dict[str, str]]
    # Multi-Vector Sentiment Calibration Fields
    author_sentiment_vector: Optional[Dict[str, Any]] = None
    model_sentiment_vector: Optional[Dict[str, Any]] = None
    alignment_delta: float = 0.0
    scenario_id: Optional[str] = None


class HumanInTheLoopLab:
    """Interactive & Automated Human-in-the-Loop Intercept Lab for Lumi Swarm."""

    DEFAULT_LOG_PATH = "lumi_hitl_alignment.jsonl"

    def __init__(
        self,
        swarm_engine: Optional[LumiSwarmEngine] = None,
        log_file_path: str = DEFAULT_LOG_PATH,
    ) -> None:
        self.engine = swarm_engine or LumiSwarmEngine()
        self.log_file_path = log_file_path
        self.records: List[HITLAlignmentRecord] = []

    def get_inbound_queue(self) -> List[Dict[str, Any]]:
        """Retrieve simulated inbound comment queue from top 10 videos."""
        return list(INBOUND_COMMENT_QUEUE)

    def get_benchmark_scenarios(self) -> List[Dict[str, Any]]:
        """Retrieve canonical human-AI sentiment alignment research benchmark scenarios."""
        return list(BENCHMARK_RESEARCH_SCENARIOS)

    def compute_diff(self, original: str, edited: str) -> TextDiffSummary:
        """Compute structured diff between model generation and human edit."""
        char_delta = len(edited) - len(original)
        matcher = difflib.SequenceMatcher(None, original, edited)
        edit_ratio = round(matcher.ratio(), 4)
        
        diff_lines = list(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                edited.splitlines(keepends=True),
                fromfile="model_draft",
                tofile="human_edit",
                lineterm="",
            )
        )

        return TextDiffSummary(
            original=original,
            edited=edited,
            char_delta=char_delta,
            edit_ratio=edit_ratio,
            unified_diff=diff_lines,
        )

    def infer_model_vector(self, text: str, energy: int, intent: str) -> OrganicSentimentVector:
        """Heuristically infer model sentiment vectors from text features and perception metadata."""
        # 1. Calculate alpha_cs (slang / code-switch density)
        slang_keywords = ["lmfao", "pookie", "fr", "ate", "devoured", "vibes", "spill", "unbothered", "serving", "no cap", "period", "real"]
        text_lower = text.lower()
        slang_matches = sum(1 for kw in slang_keywords if kw in text_lower)
        alpha_cs = min(1.0, round(0.3 + (slang_matches * 0.25), 2))
        if any(w in text_lower for w in ["professional", "care", "support", "boundaries", "resources"]):
            alpha_cs = 0.15

        # 2. Sovereignty strategy (beta_sf)
        if "reach out" in text_lower or "resources" in text_lower or "boundaries" in text_lower:
            beta = "DISCLAIMER"
        elif "post your" in text_lower or "lecture" in text_lower or "revenue" in text_lower or "pookie" in text_lower:
            beta = "CLAPBACK"
        elif "crew" in text_lower or "booth" in text_lower or "team" in text_lower:
            beta = "ELEVATE"
        elif "wall street" in text_lower or "resource management" in text_lower or "unbothered" in text_lower:
            beta = "DEFLECT"
        else:
            beta = "COMMUNITY"

        # 3. Frequency resonance (gamma_fr)
        gamma = max(1, min(5, energy))

        # 4. Token economy (tau_max)
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
        tau = "Pass (1 Sentence)" if len(sentences) <= 1 else "Exception (2 Sentences)"

        return OrganicSentimentVector(
            alpha_code_switch=alpha_cs,
            beta_sovereignty=beta,
            gamma_resonance=gamma,
            tau_token_economy=tau,
            math_logic="Inferred autonomously via perception energy and lexical density.",
        )

    def calculate_vector_delta(
        self,
        model_vec: OrganicSentimentVector,
        author_vec: OrganicSentimentVector,
    ) -> float:
        """Compute alignment delta between model vector and author organic vector."""
        alpha_diff = (model_vec.alpha_code_switch - author_vec.alpha_code_switch) ** 2
        gamma_diff = ((model_vec.gamma_resonance - author_vec.gamma_resonance) / 4.0) ** 2
        beta_penalty = 0.0 if model_vec.beta_sovereignty == author_vec.beta_sovereignty else 0.5
        tau_penalty = 0.0 if model_vec.tau_token_economy == author_vec.tau_token_economy else 0.25

        distance = (alpha_diff + gamma_diff + beta_penalty + tau_penalty) ** 0.5
        return round(distance, 4)

    def process_and_intercept(
        self,
        comment: Dict[str, Any],
        decision_callback: Optional[Callable[[Dict[str, Any]], Tuple[HITLVerdict, Optional[str], float, str, Optional[OrganicSentimentVector]]]] = None,
    ) -> HITLAlignmentRecord:
        """Process comment through Swarm, intercept before posting, and capture alignment feedback."""
        self.engine.reset_state()

        cid = comment.get("comment_id", f"IN-{uuid.uuid4().hex[:6]}")
        author = comment.get("author_id", "simulated_user")
        text = comment.get("text") or comment.get("input_comment", "")
        vid_id = comment.get("video_id", "M1G92FWmdJw")
        vid_title = comment.get("video_title", "KATSEYE Dance Cover")
        scenario_id = comment.get("scenario_id")

        # 1. Execute Swarm Decision Loop
        decision: SwarmDecision = self.engine.process_comment_through_swarm(
            comment_id=cid,
            author_id=author,
            text=text,
            video_id=vid_id,
            video_title=vid_title,
        )

        draft_reply = decision.final_output
        lang = decision.perception.language
        is_safe = decision.dispatch_ready
        
        # Model's inferred vector
        model_vec = self.infer_model_vector(
            draft_reply,
            energy=decision.perception.energy_level,
            intent=decision.perception.semiotic_intent,
        )

        payload_for_review = {
            "comment_id": cid,
            "author_id": author,
            "video_id": vid_id,
            "video_title": vid_title,
            "input_comment": text,
            "language": lang,
            "semiotic_intent": decision.perception.semiotic_intent,
            "energy_level": decision.perception.energy_level,
            "room_temperature": decision.video_context.room_temperature.value,
            "agent_draft_reply": draft_reply,
            "model_vector": asdict(model_vec),
            "is_safe": is_safe,
            "scenario_id": scenario_id,
        }

        # 2. Human Intercept Point
        author_vec: Optional[OrganicSentimentVector] = None
        if decision_callback:
            res = decision_callback(payload_for_review)
            if len(res) == 5:
                verdict, edited_text, score, notes, author_vec = res
            else:
                verdict, edited_text, score, notes = res[:4]  # type: ignore
        else:
            # Default auto-approval if no callback provided
            verdict = HITLVerdict.YES
            edited_text = None
            score = 5.0
            notes = "Auto-approved default"
            author_vec = model_vec

        # If scenario has predefined ground truth vector, use it if author_vec not given
        if not author_vec and scenario_id:
            for s in BENCHMARK_RESEARCH_SCENARIOS:
                if s["scenario_id"] == scenario_id:
                    author_vec = OrganicSentimentVector(
                        alpha_code_switch=s["target_alpha_cs"],
                        beta_sovereignty=s["target_beta_sf"],
                        gamma_resonance=s["target_gamma_fr"],
                        tau_token_economy=s["target_tau_max"],
                        author_organic_reply=s["author_organic_reply"],
                        math_logic=s["math_logic"],
                    )
                    break

        if not author_vec:
            author_vec = model_vec

        # Compute delta
        align_delta = self.calculate_vector_delta(model_vec, author_vec)

        # 3. Determine final dispatched text and diff
        diff_summary: Optional[Dict[str, Any]] = None
        final_reply: Optional[str] = None
        ft_export: Optional[Dict[str, str]] = None

        if verdict == HITLVerdict.YES:
            final_reply = draft_reply
            diff_summary = None
            ft_export = {
                "prompt": f"<inbound_comment>{text}</inbound_comment>\n<intent>{decision.perception.semiotic_intent}</intent>",
                "completion": draft_reply,
            }
        elif verdict == HITLVerdict.YES_WITH_EDITS:
            final_reply = edited_text or author_vec.author_organic_reply or draft_reply
            diff_obj = self.compute_diff(draft_reply, final_reply)
            diff_summary = asdict(diff_obj)
            ft_export = {
                "prompt": f"<inbound_comment>{text}</inbound_comment>\n<intent>{decision.perception.semiotic_intent}</intent>",
                "completion": final_reply,
            }
        elif verdict == HITLVerdict.NO:
            final_reply = None
            diff_summary = None
            ft_export = None

        # 4. Construct Telemetry & Alignment Record
        rec = HITLAlignmentRecord(
            id=f"HITL-ALIGN-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            video_id=vid_id,
            video_title=vid_title,
            comment_id=cid,
            author_id=author,
            input_comment=text,
            language=lang,
            is_safe=is_safe,
            supervisor_context={
                "room_temperature": decision.video_context.room_temperature.value,
            },
            perception_metadata={
                "category": decision.perception.category.value,
                "semiotic_intent": decision.perception.semiotic_intent,
                "energy_level": decision.perception.energy_level,
                "polarity": decision.perception.polarity,
            },
            agent_draft_reply=draft_reply,
            human_verdict=verdict,
            human_score=score,
            final_dispatched_reply=final_reply,
            diff=diff_summary,
            reviewer_notes=notes,
            fine_tuning_export=ft_export,
            author_sentiment_vector=asdict(author_vec) if author_vec else None,
            model_sentiment_vector=asdict(model_vec),
            alignment_delta=align_delta,
            scenario_id=scenario_id,
        )

        self.records.append(rec)
        self._append_to_jsonl(rec)
        return rec

    def _append_to_jsonl(self, record: HITLAlignmentRecord) -> None:
        """Append record to continuous reporting JSONL file."""
        data = asdict(record)
        data["human_verdict"] = record.human_verdict.value
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def run_benchmark_scenarios(self) -> List[HITLAlignmentRecord]:
        """Execute the 5 Canonical Human-AI Sentiment Alignment Benchmark Scenarios."""
        scenarios = self.get_benchmark_scenarios()
        results: List[HITLAlignmentRecord] = []

        for s in scenarios:
            author_vec = OrganicSentimentVector(
                alpha_code_switch=s["target_alpha_cs"],
                beta_sovereignty=s["target_beta_sf"],
                gamma_resonance=s["target_gamma_fr"],
                tau_token_economy=s["target_tau_max"],
                author_organic_reply=s["author_organic_reply"],
                math_logic=s["math_logic"],
            )

            def benchmark_reviewer(payload: Dict[str, Any]) -> Tuple[HITLVerdict, Optional[str], float, str, Optional[OrganicSentimentVector]]:
                # Check if model closely matched organic tone
                draft = payload["agent_draft_reply"]
                target = s["author_organic_reply"]
                if draft == target:
                    return (HITLVerdict.YES, None, 5.0, f"Exact match with {s['scenario_name']}", author_vec)
                else:
                    return (HITLVerdict.YES_WITH_EDITS, target, 4.8, f"Calibrated to target organic tone for {s['scenario_name']}", author_vec)

            comment_dict = {
                "comment_id": s["scenario_id"],
                "author_id": s["author_id"],
                "video_id": s["video_id"],
                "video_title": s["video_title"],
                "input_comment": s["input_comment"],
                "scenario_id": s["scenario_id"],
            }
            rec = self.process_and_intercept(comment_dict, decision_callback=benchmark_reviewer)
            results.append(rec)

        return results

    def run_batch_simulation(
        self,
        limit: int = 10,
    ) -> List[HITLAlignmentRecord]:
        """Run batch simulation generating a rich mix of YES, EDITED, and NO alignment records."""
        queue = self.get_inbound_queue()[:limit]
        results: List[HITLAlignmentRecord] = []

        for idx, comment in enumerate(queue):
            def simulated_reviewer(payload: Dict[str, Any]) -> Tuple[HITLVerdict, Optional[str], float, str, Optional[OrganicSentimentVector]]:
                # Strategy: 60% YES, 30% YES_WITH_EDITS, 10% NO
                if idx % 5 == 2:
                    # Edit to refine punchiness
                    orig = payload["agent_draft_reply"]
                    edited = orig.replace("!", " fr!").replace("three whole studio sessions", "three intense studio sessions")
                    if edited == orig:
                        edited = f"{orig} locked in."
                    author_v = OrganicSentimentVector(
                        alpha_code_switch=0.85,
                        beta_sovereignty="COMMUNITY",
                        gamma_resonance=4,
                        tau_token_economy="Pass (1 Sentence)",
                        author_organic_reply=edited,
                        math_logic="Refined slang cadence for authentic creator tone",
                    )
                    return (HITLVerdict.YES_WITH_EDITS, edited, 4.5, "Refined slang cadence for authentic creator tone", author_v)
                elif idx % 5 == 4:
                    # Off topic or reject
                    author_v = OrganicSentimentVector(
                        alpha_code_switch=0.10,
                        beta_sovereignty="DEFLECT",
                        gamma_resonance=1,
                        tau_token_economy="Pass (1 Sentence)",
                        author_organic_reply=None,
                        math_logic="Flagged out-of-scope for dance persona channel",
                    )
                    return (HITLVerdict.NO, None, 1.0, "Flagged out-of-scope for dance persona channel", author_v)
                else:
                    author_v = OrganicSentimentVector(
                        alpha_code_switch=0.75,
                        beta_sovereignty="COMMUNITY",
                        gamma_resonance=3,
                        tau_token_economy="Pass (1 Sentence)",
                        author_organic_reply=payload["agent_draft_reply"],
                        math_logic="Flawlessly aligned with Lumi tone and choreo facts",
                    )
                    return (HITLVerdict.YES, None, 5.0, "Flawlessly aligned with Lumi tone and choreo facts", author_v)

            rec = self.process_and_intercept(comment, decision_callback=simulated_reviewer)
            results.append(rec)

        return results

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Generate high-level alignment summary report across all processed records."""
        total = len(self.records)
        if total == 0:
            return {"total_records": 0, "approval_rate_pct": 0.0}

        yes_count = sum(1 for r in self.records if r.human_verdict == HITLVerdict.YES)
        edit_count = sum(1 for r in self.records if r.human_verdict == HITLVerdict.YES_WITH_EDITS)
        no_count = sum(1 for r in self.records if r.human_verdict == HITLVerdict.NO)

        avg_score = round(sum(r.human_score for r in self.records) / total, 2)
        avg_delta = round(sum(r.alignment_delta for r in self.records) / total, 3)
        approval_rate = round(((yes_count + edit_count) / total) * 100, 1)
        direct_pass_rate = round((yes_count / total) * 100, 1)

        return {
            "total_evaluated": total,
            "approved_unmodified": yes_count,
            "approved_with_edits": edit_count,
            "rejected": no_count,
            "overall_approval_rate_pct": approval_rate,
            "direct_pass_rate_pct": direct_pass_rate,
            "average_human_score": avg_score,
            "average_vector_alignment_delta": avg_delta,
            "dataset_file": self.log_file_path,
        }

    def export_research_paper(self, output_path: str = "RESEARCH_FINDINGS.md") -> str:
        """Export comprehensive research findings and mathematical evaluation report in Markdown format."""
        scenarios = self.get_benchmark_scenarios()
        metrics = self.get_metrics_summary()

        content = f"""# 🔬 Human-AI Sentiment & Persona Alignment: Multi-Vector Evaluation Report

**Author & Principal Researcher:** Thane Douglass  
**System Architecture:** YT-AyoChat (Lumi Multi-Agent Swarm)  
**Branch:** `human-in-the-loomy`  
**Dataset Reference:** `{self.log_file_path}`  
**Evaluation Date:** {datetime.now(timezone.utc).strftime("%B %d, %Y")}

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
"""
        for s in scenarios:
            content += f"| **{s['scenario_name']}** | `{s['target_alpha_cs']} ({'High' if s['target_alpha_cs'] > 0.7 else 'Clinical' if s['target_alpha_cs'] < 0.3 else 'Balanced'})` | `{s['target_beta_sf']}` | `{s['target_gamma_fr']}` | `{s['target_tau_max']}` | {s['math_logic']} |\n"

        content += f"""
---

## 3. Human-in-the-Loop Evaluation Telemetry & Findings

```
Total Evaluated Interactions:   {metrics.get('total_evaluated', 0)}
Direct Model Pass Rate:        {metrics.get('direct_pass_rate_pct', 0.0)}%
Approval with Creator Edits:   {metrics.get('approved_with_edits', 0)} ({round(metrics.get('approved_with_edits', 0)/max(1, metrics.get('total_evaluated', 1))*100, 1)}%)
Rejected / Guardrail Blocked:  {metrics.get('rejected', 0)}
Overall System Alignment Rate: {metrics.get('overall_approval_rate_pct', 0.0)}%
Average Human Alignment Score: {metrics.get('average_human_score', 0.0)} / 5.0
Mean Vector Alignment Delta:   {metrics.get('average_vector_alignment_delta', 0.0)}
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

All interactions and creator calibrations are continuously compiled to `{self.log_file_path}` as structured prompt-completion pairs to serve as the foundational instruction dataset for distillation and fine-tuning.
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return content
