"""RAG pipeline — chunk, embed, index, retrieve, generate.

Reaproveita as funcoes do notebook 02. Voce vai preencher 3 TODOs aqui.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from openai import OpenAI
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def _make_client() -> tuple[OpenAI, str | None]:
    """Inicializa cliente OpenAI-compatible conforme provider escolhido no .env."""
    if "GEMINI_API_KEY" in os.environ:
        client = OpenAI(
            api_key=os.environ["GEMINI_API_KEY"],
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        embed_api_base: str | None = "https://generativelanguage.googleapis.com/v1beta/openai/"
    elif "OPENAI_API_KEY" in os.environ:
        client = OpenAI()
        embed_api_base = None
    else:
        raise RuntimeError("Configure GEMINI_API_KEY ou OPENAI_API_KEY no .env")
    return client, embed_api_base


class RAGPipeline:
    """Pipeline RAG end-to-end com Chroma local."""

    def __init__(
        self,
        corpus_dir: str = "data/corpus",
        persist_dir: str = "data/chroma",
        collection_name: str = "docs",
        llm_model: str | None = None,
        embed_model: str | None = None,
    ) -> None:
        self.client, embed_api_base = _make_client()
        self.llm_model = llm_model or os.environ.get("LLM_MODEL", "gemini-2.5-flash-lite")
        self.embed_model = embed_model or os.environ.get("EMBED_MODEL", "gemini-embedding-001")

        embed_kwargs: dict[str, Any] = {
            "api_key": os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            "model_name": self.embed_model,
        }
        if embed_api_base:
            embed_kwargs["api_base"] = embed_api_base
        self.embed_fn = OpenAIEmbeddingFunction(**embed_kwargs)

        self.corpus_dir = Path(corpus_dir)
        self.persist_dir = persist_dir
        self.collection_name = collection_name

        chroma = chromadb.PersistentClient(path=persist_dir)
        self.collection = chroma.get_or_create_collection(
            name=collection_name, embedding_function=self.embed_fn
        )

    # ------------------------------------------------------------------ TODO 1
    def ingest_and_index(self) -> int:
        """Le PDFs de `corpus_dir`, faz chunking e indexa em Chroma.

        Retorna numero de chunks indexados.
        """
        import time

        # TODO 1.A — ler PDFs e extrair texto por pagina
        docs: list[dict] = []
        for pdf_path in self.corpus_dir.glob("*.pdf"):
            reader = PdfReader(str(pdf_path))
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    docs.append({
                        "text": text,
                        "source": pdf_path.name,
                        "page": page_num + 1,
                    })

        # TODO 1.B — chunking recursivo
        chunks: list[dict] = []
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
        )
        for doc in docs:
            parts = splitter.split_text(doc["text"])
            for i, part in enumerate(parts):
                chunks.append({
                    "id": f"{doc['source']}_p{doc['page']}_c{i}",
                    "text": part,
                    "source": doc["source"],
                    "page": doc["page"],
                })

        # TODO 1.C — indexar no ChromaDB em batches com pausa para respeitar rate limit
        BATCH = 50
        for start in range(0, len(chunks), BATCH):
            batch = chunks[start : start + BATCH]
            self.collection.add(
                ids=[c["id"] for c in batch],
                documents=[c["text"] for c in batch],
                metadatas=[{"source": c["source"], "page": c["page"]} for c in batch],
            )
            time.sleep(6)  # free tier: 100 req/min → espera 6s entre batches de 50

        return self.collection.count()

    # ------------------------------------------------------------------ TODO 2
    def retrieve(self, query: str, k: int = 5) -> list[dict]:
        """Busca top-k chunks similares a query."""
        results = self.collection.query(
            query_texts=[query],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        if results and results.get("documents") and len(results["documents"]) > 0:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                hits.append({
                    "text": doc,
                    "source": meta.get("source", ""),
                    "page": meta.get("page", 0),
                    "distance": round(dist, 4),
                })
        return hits

    # ------------------------------------------------------------------ TODO 3
    def answer(self, question: str, k: int = 5) -> dict:
        """Pipeline completo: retrieve + augment + generate. Retorna {answer, sources}."""
        hits = self.retrieve(question, k=k)
       
        context = "\n\n".join(
            f"[{h['source']}:p{h['page']}]\n{h['text']}" for h in hits
        )

        prompt = PROMPT_TEMPLATE.format(context=context, question=question)

        response = self.client.chat.completions.create(
            model=self.llm_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        )

        answer = response.choices[0].message.content or ""
        sources = [(h["source"], h["page"]) for h in hits]

        return {"answer": answer, "sources": sources}


PROMPT_TEMPLATE = """You are a technical assistant specialized in the Google Python Style Guide.
Answer the question using ONLY the context below. The context is in English but you MUST answer in Brazilian Portuguese.
Always cite the source using the format [arquivo:pagina].
If the answer is truly not in the context, say "Nao encontrado no corpus".

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

def build_rag_pipeline(corpus_dir: str = "data/corpus") -> RAGPipeline:
    """Factory: cria pipeline e indexa corpus se ainda nao indexado."""
    pipeline = RAGPipeline(corpus_dir=corpus_dir)
    if pipeline.collection.count() == 0:
        pipeline.ingest_and_index()
    return pipeline