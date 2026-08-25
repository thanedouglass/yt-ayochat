"""RAG document pipeline for an 'Unofficial Guide' domain.

Requirements:
- OPENAI_API_KEY must be set in your environment.
- Install dependencies:
  pip install langchain-chroma langchain-openai langchain-text-splitters langchain-core
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

COLLECTION_NAME = "unofficial-guide"
CHROMA_PERSIST_DIRECTORY = Path("./chroma_db")


@dataclass(frozen=True)
class RetrievedChunk:
    source: str
    chunk: str


def build_unofficial_guide_documents() -> List[Document]:
    """Create 10+ source documents with source metadata for attribution."""
    raw_documents = [
        ("guide_01_getting_started.txt", "Start each project by defining a single goal, then list only the first three actions. This keeps momentum high and reduces decision fatigue."),
        ("guide_02_daily_rhythm.txt", "Use a 50/10 focus rhythm: fifty minutes deep work, ten minutes review. During review, write one sentence about what changed."),
        ("guide_03_note_taking.txt", "Capture notes in the format: context, decision, next step. This structure improves retrieval when you revisit old entries."),
        ("guide_04_debugging.txt", "When debugging, reproduce the issue in the smallest environment first. Record exact inputs and expected outputs before changing code."),
        ("guide_05_code_reviews.txt", "In reviews, prioritize correctness, security, and maintainability. Defer style-only concerns unless they block understanding."),
        ("guide_06_release_checklist.txt", "Before release, verify migrations, rollback plan, monitoring alerts, and user communication. A checklist prevents avoidable incidents."),
        ("guide_07_api_design.txt", "Prefer explicit API contracts with versioned fields. Breaking changes must include compatibility notes and deprecation windows."),
        ("guide_08_incident_response.txt", "For incidents, assign one incident lead and one communications lead. Frequent, short updates reduce confusion and duplicate work."),
        ("guide_09_documentation.txt", "Good docs answer: what is this, who is it for, and how to use it in five minutes. Include examples before edge cases."),
        ("guide_10_learning_loops.txt", "After every project, run a short retrospective with: keep doing, stop doing, start doing. Convert outcomes into concrete tasks."),
    ]

    return [
        Document(page_content=content, metadata={"source": source})
        for source, content in raw_documents
    ]


def chunk_documents(documents: List[Document]) -> List[Document]:
    """Split docs into overlapping chunks using recursive character splitting.

    Chunk strategy:
    - chunk_size=500: large enough to preserve local context for semantic search,
      while still small enough to keep embeddings focused.
    - chunk_overlap=100: repeats a small tail of each chunk into the next chunk,
      reducing boundary information loss when important context spans chunk edges.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)


def build_vector_store(chunks: List[Document]) -> Chroma:
    """Embed chunks with text-embedding-3-small and store in local ChromaDB."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_PERSIST_DIRECTORY),
        collection_name=COLLECTION_NAME,
    )


def retrieve_top_chunks(query: str, k: int = 3) -> List[RetrievedChunk]:
    """Return top-k similar chunks with source metadata attribution."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vector_store = Chroma(
        persist_directory=str(CHROMA_PERSIST_DIRECTORY),
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )
    results = vector_store.similarity_search(query, k=k)
    return [
        RetrievedChunk(
            source=result.metadata.get("source", "unknown"),
            chunk=result.page_content,
        )
        for result in results
    ]


def main() -> None:
    documents = build_unofficial_guide_documents()
    chunks = chunk_documents(documents)
    build_vector_store(chunks)

    query = "How should we handle project retrospectives?"
    top_chunks = retrieve_top_chunks(query=query, k=3)
    print(f"Top {len(top_chunks)} chunks for query: {query!r}")
    for i, item in enumerate(top_chunks, start=1):
        print(f"{i}. source={item.source}\\n   chunk={item.chunk}\\n")


if __name__ == "__main__":
    main()
