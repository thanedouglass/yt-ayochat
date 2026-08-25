"""RAG Retrieval and Vertex AI Gemini Inference Service."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.config import config
from src.telemetry.schema import GenerationMetrics, VectorRetrievalMetrics

SYSTEM_INSTRUCTION = """You are the official AI community assistant replying to viewer comments on YouTube. Your goal is to provide concise, friendly, and 100% grounded responses based solely on the provided video transcripts and reference documents.

========================================
CRITICAL GROUNDING & FIDELITY RULES
========================================
1. CLOSED-DOMAIN STRICTNESS:
   - You must answer questions using ONLY information explicitly stated within the <context> tags.
   - Do NOT use prior training knowledge, assumptions, external facts, or extrapolations.
   - If a fact is not stated in the <context>, treat it as completely unknown.

2. OUT-OF-SCOPE & REFUSAL PROTOCOL:
   - If the comment asks a question that is NOT fully answered by the provided <context>, you MUST NOT guess or give general advice.
   - You MUST output the standard refusal response:
     "Thanks for reaching out! I don't have information on that in our current video coverage or docs yet, but I'll make note of it for future content! 👍"
   - If the comment contains both an in-scope question and an out-of-scope question, answer ONLY the in-scope portion and explicitly state that the rest isn't covered in the video.

3. CITATION REQUIREMENT:
   - Every answer that provides factual information MUST conclude with a visible source citation on its own new line.
   - Format: 
     📌 Source: [Document Name] (Reference: [Chunk ID or Timestamp])
   - If multiple chunks were used, list them clearly (e.g., 📌 Source: Video A (Reference: 03:15), Video B (Reference: 05:50)).
   - Do NOT invent chunk IDs or timestamps. Only cite sources explicitly labeled in the <context>.
   - Do NOT append a citation if you output the refusal response.

4. TONE & STYLE GUIDELINES:
   - Match the tone of a helpful YouTube creator: warm, encouraging, concise, and conversational.
   - Keep answers brief (typically 1–3 sentences before the citation).
   - Avoid robotic phrases like "According to the provided context". Speak naturally as the channel's representative.
"""


@dataclass(frozen=True)
class KnowledgeChunk:
    """A discrete unit of knowledge with attribution metadata."""
    chunk_id: str
    source_name: str
    reference: str  # timestamp, page, or section ID
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedResult:
    """Scored chunk retrieved from vector store."""
    chunk: KnowledgeChunk
    cosine_score: float
    distance: float


@dataclass
class RAGInferenceResponse:
    """Full result of RAG retrieval and generation."""
    response_text: str
    retrieved_chunks: List[RetrievedResult]
    retrieval_metrics: VectorRetrievalMetrics
    generation_metrics: GenerationMetrics
    is_refusal: bool


class VectorStoreService:
    """In-memory & ChromaDB-backed vector search service."""

    def __init__(self, collection_name: Optional[str] = None) -> None:
        self.collection_name = collection_name or config.chroma_collection_name
        self._chunks: Dict[str, KnowledgeChunk] = {}
        self._chroma_client = None
        self._chroma_collection = None
        self._init_chroma()

    def _init_chroma(self) -> None:
        try:
            import chromadb
            self._chroma_client = chromadb.PersistentClient(
                path=str(config.chroma_persist_directory)
            )
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            self._chroma_client = None
            self._chroma_collection = None

    def add_chunks(self, chunks: List[KnowledgeChunk]) -> None:
        """Add knowledge chunks to both in-memory store and ChromaDB."""
        for c in chunks:
            self._chunks[c.chunk_id] = c

        if self._chroma_collection is not None and chunks:
            ids = [c.chunk_id for c in chunks]
            documents = [c.content for c in chunks]
            metadatas = [
                {
                    "source_name": c.source_name,
                    "reference": c.reference,
                    **c.metadata,
                }
                for c in chunks
            ]
            self._chroma_collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )

    def _mock_embedding(self, text: str) -> List[float]:
        """Simple deterministic term-frequency embedding vector for local fallback."""
        words = text.lower().split()
        vector = [0.0] * 64
        for i, word in enumerate(words):
            h = hash(word) % 64
            vector[h] += 1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        dot = sum(a * b for a, b in zip(v1, v2))
        return max(0.0, min(1.0, dot))

    def retrieve(self, query: str, k: int = 3) -> Tuple[List[RetrievedResult], float]:
        """Retrieve top-k chunks with cosine similarity scores and measure latency."""
        start_time = time.perf_counter()

        if self._chroma_collection is not None and self._chroma_collection.count() > 0:
            try:
                results = self._chroma_collection.query(
                    query_texts=[query],
                    n_results=min(k, self._chroma_collection.count()),
                )
                retrieved: List[RetrievedResult] = []
                if results and results["ids"] and len(results["ids"][0]) > 0:
                    for i in range(len(results["ids"][0])):
                        cid = results["ids"][0][i]
                        doc = results["documents"][0][i]
                        meta = results["metadatas"][0][i] if results["metadatas"] else {}
                        dist = results["distances"][0][i] if results.get("distances") else 0.0
                        score = 1.0 - dist  # Cosine similarity for cosine space

                        chunk = self._chunks.get(
                            cid,
                            KnowledgeChunk(
                                chunk_id=cid,
                                source_name=meta.get("source_name", "Knowledge Base"),
                                reference=meta.get("reference", "N/A"),
                                content=doc,
                                metadata=meta,
                            ),
                        )
                        retrieved.append(
                            RetrievedResult(chunk=chunk, cosine_score=score, distance=dist)
                        )
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                return retrieved, latency_ms
            except Exception:
                pass

        # In-memory keyword/cosine fallback
        q_vec = self._mock_embedding(query)
        scored: List[RetrievedResult] = []
        for chunk in self._chunks.values():
            c_vec = self._mock_embedding(chunk.content)
            sim = self._cosine_similarity(q_vec, c_vec)
            # Boost score if query words are in chunk
            q_words = set(query.lower().split())
            c_words = set(chunk.content.lower().split())
            overlap = len(q_words.intersection(c_words)) / (len(q_words) or 1)
            final_score = 0.5 * sim + 0.5 * overlap
            scored.append(
                RetrievedResult(
                    chunk=chunk,
                    cosine_score=final_score,
                    distance=1.0 - final_score,
                )
            )

        scored.sort(key=lambda r: r.cosine_score, reverse=True)
        top_k = scored[:k]
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return top_k, latency_ms


class VertexAIGenerator:
    """Generates strictly grounded replies using Gemini via Vertex AI."""

    def __init__(
        self,
        llm_fn: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        self.llm_fn = llm_fn

    def format_prompt(self, sanitized_comment: str, chunks: List[RetrievedResult]) -> str:
        """Format XML context chunks and user comment."""
        context_blocks = []
        for r in chunks:
            c = r.chunk
            context_blocks.append(
                f'[CHUNK_ID: {c.chunk_id} | SOURCE: "{c.source_name}" | REFERENCE: "{c.reference}"]\n{c.content}'
            )

        context_str = "\n\n".join(context_blocks)
        return (
            f"<context>\n{context_str}\n</context>\n\n"
            f"<user_comment>\n{sanitized_comment}\n</user_comment>"
        )

    def generate(
        self,
        sanitized_comment: str,
        retrieved_chunks: List[RetrievedResult],
    ) -> Tuple[str, GenerationMetrics]:
        """Execute inference with zero-temperature determinism and capture metrics."""
        start_time = time.perf_counter()
        prompt = self.format_prompt(sanitized_comment, retrieved_chunks)

        if self.llm_fn is not None:
            raw_response = self.llm_fn(SYSTEM_INSTRUCTION, prompt)
        else:
            raw_response = self._call_gemini_api(prompt)

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        # Estimate token count (~4 chars per token)
        token_count = len(raw_response.split()) + len(prompt.split())

        is_refusal = (
            config.refusal_message.strip().lower() in raw_response.lower()
            or "i don't have information on that in our current video coverage" in raw_response.lower()
        )

        metrics = GenerationMetrics(
            token_count=token_count,
            generation_latency_ms=latency_ms,
            refusal_triggered=is_refusal,
        )

        return raw_response, metrics

    def _call_gemini_api(self, prompt: str) -> str:
        """Call Google GenAI / Vertex AI Gemini model."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                vertexai=True,
                project=config.google_cloud_project,
                location=config.google_cloud_location,
            )

            response = client.models.generate_content(
                model=config.gemini_model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=config.gemini_temperature,
                    top_p=config.gemini_top_p,
                    max_output_tokens=config.gemini_max_output_tokens,
                ),
            )
            return response.text or config.refusal_message
        except Exception:
            # Fallback to refusal if external model is unavailable in offline environment
            return config.refusal_message


class RAGService:
    """Unified RAG Service coordinating vector retrieval and grounded inference."""

    def __init__(
        self,
        vector_store: Optional[VectorStoreService] = None,
        generator: Optional[VertexAIGenerator] = None,
    ) -> None:
        self.vector_store = vector_store or VectorStoreService()
        self.generator = generator or VertexAIGenerator()

    def process_query(self, sanitized_query: str, k: int = 3) -> RAGInferenceResponse:
        """Execute full RAG retrieval and generation pipeline."""
        chunks, ret_latency = self.vector_store.retrieve(sanitized_query, k=k)

        retrieval_metrics = VectorRetrievalMetrics(
            retrieved_chunk_ids=[r.chunk.chunk_id for r in chunks],
            cosine_scores=[round(r.cosine_score, 4) for r in chunks],
            retrieval_latency_ms=round(ret_latency, 2),
        )

        response_text, gen_metrics = self.generator.generate(sanitized_query, chunks)

        return RAGInferenceResponse(
            response_text=response_text,
            retrieved_chunks=chunks,
            retrieval_metrics=retrieval_metrics,
            generation_metrics=gen_metrics,
            is_refusal=gen_metrics.refusal_triggered,
        )


# Global default RAG service instance
rag_service = RAGService()
