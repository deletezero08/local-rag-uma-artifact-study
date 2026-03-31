from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from langchain_core.documents import Document

from .config import settings


@dataclass
class QAChainHandle:
    llm: Any
    retriever: Any
    prompt: Any


def build_qa_chain(llm: Any, retriever: Any, prompt: Any) -> QAChainHandle:
    # The current engine builds prompts manually in query()/stream_query().
    # This handle only preserves the old truthy "qa exists" contract.
    return QAChainHandle(llm=llm, retriever=retriever, prompt=prompt)


def build_retriever(db: Any, mode: str = "rrf") -> Any:
    retrieval_cfg = settings.get("retrieval", {})
    vector_k = int(retrieval_cfg.get("vector_k", 6))

    if mode in {"vector_only", "similarity"}:
        return db.as_retriever(
            search_type="similarity",
            search_kwargs={"k": vector_k},
        )

    fetch_k = max(vector_k * 3, vector_k)
    return db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": vector_k, "fetch_k": fetch_k},
    )


def extract_sources(source_docs: List[Document]) -> List[str]:
    labels: List[str] = []
    seen: set[str] = set()

    for doc in source_docs:
        metadata = doc.metadata or {}
        source_path = str(metadata.get("source", "")).strip()
        if source_path:
            label = Path(source_path).name
        else:
            label = "未知来源"

        page = metadata.get("page")
        if isinstance(page, int):
            label = f"{label} (p.{page + 1})"

        if label not in seen:
            labels.append(label)
            seen.add(label)

    return labels
