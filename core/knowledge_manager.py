"""
Knowledge Manager — ChromaDB + Embeddings RAG Pipeline
Manages the vector database, document chunking, and semantic search.
v5.0 — Fully functional search, context building, and batch ingestion.
"""
import hashlib
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import config

logger = logging.getLogger(__name__)

# ─── Safe Import Initialization ───────────────────────────────
KNOWLEDGE_SYSTEM_ENABLED = True

try:
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    import chromadb
except ImportError as e:
    logger.warning(f"⚠️ Knowledge System Disabled: {e}")
    KNOWLEDGE_SYSTEM_ENABLED = False


def _get_embedding_function():
    """Lazy-load the embedding function."""
    if not KNOWLEDGE_SYSTEM_ENABLED:
        return None
    try:
        ef = SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL)
        logger.info(f"Loaded embedding model: {config.EMBEDDING_MODEL}")
        return ef
    except Exception as e:
        logger.error(f"Embedding init failure: {e}")
        return None


def _get_chroma_client():
    """Lazy-load ChromaDB client."""
    if not KNOWLEDGE_SYSTEM_ENABLED:
        return None
    try:
        os.makedirs(config.CHROMA_DB_PATH, exist_ok=True)
        client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
        logger.info(f"ChromaDB initialized at: {config.CHROMA_DB_PATH}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        return None


class KnowledgeManager:
    """Manages the knowledge base with semantic search and RAG context building."""

    COLLECTION_NAME = "knowledge_base"

    def __init__(self):
        self._collection = None
        self._client = None
        self._ef = None
        self.enabled = KNOWLEDGE_SYSTEM_ENABLED

    @property
    def collection(self):
        """Lazy-load the ChromaDB collection."""
        if not self.enabled:
            return None

        if self._collection is None:
            try:
                self._client = _get_chroma_client()
                self._ef = _get_embedding_function()
                if not self._client or not self._ef:
                    self.enabled = False
                    return None

                self._collection = self._client.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    embedding_function=self._ef,
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info(f"Knowledge collection loaded. Documents: {self._collection.count()}")
            except Exception as e:
                logger.error(f"Collection load failure: {e}")
                self.enabled = False
        return self._collection

    # ─── Search ─────────────────────────────────────────────────────

    def search(self, query: str, n_results: int = None) -> list[dict]:
        """Hybrid Search (Vector + BM25) with Reciprocal Rank Fusion (Upgrade 5)."""
        if not self.enabled or not self.collection:
            return []

        n_results = n_results or config.MAX_CONTEXT_CHUNKS

        try:
            total = self.collection.count()
            if total == 0:
                return []
            fetch_n = min(n_results * 5, total) # Fetch more for fusion

            # 1. Vector Search
            vector_results = self.collection.query(
                query_texts=[query],
                n_results=fetch_n,
            )
            
            vector_hits = {}
            if vector_results and vector_results.get("documents") and vector_results["documents"][0]:
                docs = vector_results["documents"][0]
                metas = vector_results["metadatas"][0] if vector_results.get("metadatas") else [{}] * len(docs)
                ids = vector_results["ids"][0]
                dists = vector_results["distances"][0] if vector_results.get("distances") else [1.0] * len(docs)
                
                for doc, meta, doc_id, dist in zip(docs, metas, ids, dists):
                    similarity = 1.0 - dist
                    vector_hits[doc_id] = {
                        "content": doc,
                        "source": meta.get("source", "Unknown"),
                        "title": meta.get("title", ""),
                        "category": meta.get("category", "general"),
                        "timestamp": meta.get("timestamp", ""),
                        "similarity": round(similarity, 3),
                        "id": doc_id
                    }

            # 2. BM25 Keyword Search
            bm25_hits = {}
            try:
                from rank_bm25 import BM25Okapi
                
                # Fetch all documents for BM25
                all_data = self.collection.get(include=["documents", "metadatas"])
                if all_data and all_data.get("documents"):
                    all_docs = all_data["documents"]
                    all_ids = all_data["ids"]
                    all_metas = all_data["metadatas"] if all_data.get("metadatas") else [{}] * len(all_docs)
                    
                    tokenized_corpus = [doc.lower().split() for doc in all_docs]
                    bm25 = BM25Okapi(tokenized_corpus)
                    tokenized_query = query.lower().split()
                    bm25_scores = bm25.get_scores(tokenized_query)
                    
                    # Get top N from BM25
                    import numpy as np
                    top_bm25_indices = np.argsort(bm25_scores)[::-1][:fetch_n]
                    
                    for idx in top_bm25_indices:
                        if bm25_scores[idx] > 0:
                            doc_id = all_ids[idx]
                            if doc_id not in vector_hits: 
                                bm25_hits[doc_id] = {
                                    "content": all_docs[idx],
                                    "source": all_metas[idx].get("source", "Unknown"),
                                    "title": all_metas[idx].get("title", ""),
                                    "category": all_metas[idx].get("category", "general"),
                                    "timestamp": all_metas[idx].get("timestamp", ""),
                                    "similarity": bm25_scores[idx] / 10.0,
                                    "id": doc_id
                                }
                            else:
                                bm25_hits[doc_id] = vector_hits[doc_id]
            except ImportError:
                logger.warning("BM25 Search skipped: rank_bm25 not installed.")
            except Exception as e:
                logger.warning(f"BM25 Search failed: {e}")

            # 3. Reciprocal Rank Fusion (RRF)
            k = 60 # RRF constant
            rrf_scores = {}
            
            # Rank vector results
            for rank, doc_id in enumerate(vector_hits.keys()):
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
                
            # Rank BM25 results
            for rank, doc_id in enumerate(bm25_hits.keys()):
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
                
            # Sort by RRF score
            sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Map back to result dicts
            final_results = []
            for doc_id, score in sorted_docs[:n_results]:
                hit = vector_hits.get(doc_id) or bm25_hits.get(doc_id)
                if hit:
                    final_results.append(hit)
                        
            return final_results

        except Exception as e:
            logger.error(f"Hybrid Search error: {e}")
            return []

    def build_context_prompt(self, query: str) -> str:
        """Build a knowledge context snippet to inject into the system prompt."""
        if not self.enabled:
            return ""

        try:
            results = self.search(query, n_results=config.MAX_CONTEXT_CHUNKS)
            if not results:
                return ""

            context = "\n--- KNOWLEDGE CONTEXT (use this to answer) ---\n"
            for i, r in enumerate(results, 1):
                title = r.get("title", "").strip()
                source = r.get("source", "Unknown")
                content = r.get("content", "").strip()

                # Truncate long content
                if len(content) > 400:
                    content = content[:400] + "..."

                if title:
                    context += f"{i}. [{source}] {title}\n   {content}\n\n"
                else:
                    context += f"{i}. [{source}] {content}\n\n"

            context += "--- END KNOWLEDGE CONTEXT ---\n"
            return context

        except Exception as e:
            logger.error(f"Context build error: {e}")
            return ""

    # ─── Ingestion ──────────────────────────────────────────────────

    def add_document(self, content: str, source: str, **kwargs) -> int:
        """Add a single document to the knowledge base, auto-chunking if needed."""
        if not self.enabled or not self.collection:
            return 0

        try:
            title = kwargs.get("title", "")
            category = kwargs.get("category", "general")
            timestamp = kwargs.get("timestamp", datetime.now(timezone.utc).isoformat())

            # Chunk long content
            chunks = self._chunk_text(content, config.CHUNK_SIZE)
            added = 0

            for i, chunk in enumerate(chunks):
                chunk_id = hashlib.md5(f"{source}:{title}:{i}:{chunk[:100]}".encode()).hexdigest()

                try:
                    self.collection.add(
                        ids=[chunk_id],
                        documents=[chunk],
                        metadatas=[{
                            "source": source,
                            "title": title,
                            "category": category,
                            "timestamp": timestamp,
                            "chunk_index": i,
                        }],
                    )
                    added += 1
                except Exception:
                    pass  # Skip duplicates silently

            if added > 0:
                logger.info(f"Added {added} chunks from: {title[:50] or source}")
            return added

        except Exception as e:
            logger.error(f"Ingestion error: {e}")
            return 0

    def add_documents_batch(self, articles: list[dict]) -> int:
        """Add a batch of articles to the knowledge base."""
        total_added = 0
        for article in articles:
            content = article.get("content", "")
            source = article.get("source", "Unknown")
            title = article.get("title", "")
            category = article.get("category", "general")
            timestamp = article.get("timestamp", "")

            if content and len(content.strip()) > 20:
                added = self.add_document(
                    content=content,
                    source=source,
                    title=title,
                    category=category,
                    timestamp=timestamp,
                )
                total_added += added
        return total_added

    # ─── Maintenance ────────────────────────────────────────────────

    def cleanup_old_knowledge(self) -> int:
        """Remove documents older than the retention period."""
        if not self.enabled or not self.collection:
            return 0

        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=config.KNOWLEDGE_RETENTION_DAYS)).isoformat()

            # Get all documents with timestamps
            all_docs = self.collection.get(include=["metadatas"])
            if not all_docs or not all_docs.get("ids"):
                return 0

            ids_to_remove = []
            for doc_id, meta in zip(all_docs["ids"], all_docs["metadatas"]):
                ts = meta.get("timestamp", "")
                if ts and ts < cutoff:
                    ids_to_remove.append(doc_id)

            if ids_to_remove:
                # ChromaDB delete in batches
                batch_size = 100
                for i in range(0, len(ids_to_remove), batch_size):
                    batch = ids_to_remove[i:i + batch_size]
                    self.collection.delete(ids=batch)

                logger.info(f"Cleaned up {len(ids_to_remove)} old chunks.")
            return len(ids_to_remove)

        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return 0

    def get_stats(self) -> dict:
        """Get knowledge base statistics."""
        if not self.enabled or not self.collection:
            return {"enabled": self.enabled, "total_documents": 0}

        try:
            count = self.collection.count()
            return {
                "enabled": True,
                "total_documents": count,
                "embedding_model": config.EMBEDDING_MODEL,
                "db_path": config.CHROMA_DB_PATH,
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {"enabled": self.enabled, "total_documents": 0}

    def reset(self):
        """Reset the collection cache (forces re-initialization on next access)."""
        self._collection = None
        self._client = None
        self._ef = None

    # ─── Utilities ──────────────────────────────────────────────────

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks to preserve semantic context (Upgrade 5)."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            if end >= text_len:
                chunks.append(text[start:].strip())
                break
                
            # Find a natural breakpoint
            breakpoint = text.rfind(". ", start, end)
            if breakpoint == -1 or breakpoint < start + (chunk_size // 2):
                breakpoint = text.rfind(" ", start, end)
                
            if breakpoint == -1 or breakpoint <= start:
                breakpoint = end # Force split
            else:
                breakpoint += 1 # Include the space/period
                
            chunks.append(text[start:breakpoint].strip())
            
            step = breakpoint - start
            if step <= overlap:
                start += step # move forward by at least something
            else:
                start = breakpoint - overlap

        return [c for c in chunks if c]
