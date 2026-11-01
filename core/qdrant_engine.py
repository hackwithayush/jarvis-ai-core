"""
JARVIS Autonomous Intelligence 2.0 — Qdrant Semantic Knowledge Retrieval Engine
Provides ultra-fast local dense vector indexing, hybrid semantic search,
and RAG context retrieval across documents, codebases, and past mission logs.
"""
import os
import re
import uuid
import time
import logging
from typing import Dict, Any, List, Optional, Union

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
from fastembed import TextEmbedding

import config

logger = logging.getLogger("jarvis.qdrant_engine")


class QdrantEngine:
    """
    Enterprise Vector Search & Semantic RAG Engine powered by Qdrant.
    Manages dense vector storage across documents, codebases, and mission histories.
    """

    VECTOR_DIM = 384
    MODEL_NAME = "BAAI/bge-small-en-v1.5"

    COLLECTIONS = {
        "documents": "jarvis_documents",
        "codebase": "jarvis_codebase",
        "missions": "jarvis_missions"
    }

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.join(getattr(config, "DATA_DIR", "data"), "qdrant_knowledge")
        os.makedirs(self.storage_path, exist_ok=True)
        
        self.client: Optional[QdrantClient] = None
        self.embed_model: Optional[TextEmbedding] = None
        self._init_engine()

    def _init_engine(self):
        """Initializes the persistent Qdrant client and FastEmbed ONNX model."""
        try:
            # Check for remote Qdrant configuration first
            qdrant_url = getattr(config, "QDRANT_URL", None) or os.getenv("QDRANT_URL")
            qdrant_api_key = getattr(config, "QDRANT_API_KEY", None) or os.getenv("QDRANT_API_KEY")

            if qdrant_url:
                self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
                logger.info(f"Connected to remote Qdrant cluster at: {qdrant_url}")
            else:
                self.client = QdrantClient(path=self.storage_path)
                logger.info(f"Local embedded Qdrant initialized at: {self.storage_path}")

            # Lazy-load FastEmbed
            self.embed_model = TextEmbedding(model_name=self.MODEL_NAME)
            logger.info(f"FastEmbed ONNX dense model initialized: {self.MODEL_NAME} ({self.VECTOR_DIM}d)")

            # Initialize standard collections
            for alias, col_name in self.COLLECTIONS.items():
                self._ensure_collection(col_name)

        except Exception as e:
            logger.error(f"QdrantEngine initialization error: {e}", exc_info=True)
            self.client = None
            self.embed_model = None

    def _ensure_collection(self, collection_name: str):
        """Ensures the target vector collection exists with cosine distance metric."""
        if not self.client:
            return
        try:
            if not self.client.collection_exists(collection_name):
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=self.VECTOR_DIM, distance=Distance.COSINE)
                )
                logger.info(f"Created Qdrant vector collection: '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to verify/create collection '{collection_name}': {e}")

    def is_available(self) -> bool:
        """Returns True if Qdrant and the embedding model are operational."""
        return self.client is not None and self.embed_model is not None

    def embed_text(self, text: str) -> List[float]:
        """Generates a 384-dimensional dense vector embedding from text."""
        if not self.embed_model:
            return [0.0] * self.VECTOR_DIM
        clean = (text or "").strip()
        if not clean:
            return [0.0] * self.VECTOR_DIM
        embeddings = list(self.embed_model.embed([clean]))
        return embeddings[0].tolist()

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
        """Splits a document into overlapping semantic chunks on sentence boundaries."""
        if not text:
            return []
        if len(text) <= chunk_size:
            return [text.strip()]

        sentences = re.split(r"(?<=[.!?\n])\s+", text)
        chunks = []
        current = ""

        for s in sentences:
            if not s:
                continue
            if len(current) + len(s) + 1 <= chunk_size:
                current = f"{current} {s}".strip() if current else s
            else:
                if current:
                    chunks.append(current)
                # Overlap tail
                overlap_text = current[-overlap:] if len(current) > overlap else ""
                current = f"{overlap_text} {s}".strip() if overlap_text else s

        if current and current not in chunks:
            chunks.append(current)

        return chunks

    # ─── Document Ingestion ───────────────────────────────────────────────────

    def index_document(
        self,
        content: str,
        title: str = "Untitled Document",
        category: str = "general",
        source: str = "user_upload",
        collection_key: str = "documents",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Chunks and indexes a text document into the specified Qdrant collection.
        """
        if not self.is_available():
            return {"status": "error", "error": "Qdrant engine unavailable."}
        if not content or not content.strip():
            return {"status": "error", "error": "Empty content payload."}

        col_name = self.COLLECTIONS.get(collection_key, collection_key)
        self._ensure_collection(col_name)

        chunks = self.chunk_text(content.strip())
        points = []
        base_meta = metadata or {}

        for idx, chunk in enumerate(chunks):
            doc_uuid = uuid.uuid4().hex
            vec = self.embed_text(chunk)
            payload = {
                "doc_id": doc_uuid,
                "title": title,
                "category": category,
                "source": source,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "text": chunk,
                "timestamp": time.time(),
                **base_meta
            }
            points.append(PointStruct(id=doc_uuid, vector=vec, payload=payload))

        try:
            self.client.upsert(collection_name=col_name, points=points)
            logger.info(f"Indexed document '{title}' ({len(chunks)} chunks) into '{col_name}'.")
            return {
                "status": "success",
                "collection": col_name,
                "title": title,
                "chunks_indexed": len(chunks)
            }
        except Exception as e:
            logger.error(f"Failed to upsert points to Qdrant: {e}")
            return {"status": "error", "error": str(e)}

    def index_file(self, filepath: str, category: str = "files", collection_key: str = "documents") -> Dict[str, Any]:
        """
        Reads and indexes a file into Qdrant using the universal parser.
        """
        if not os.path.exists(filepath):
            return {"status": "error", "error": f"File '{filepath}' not found."}

        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            return self.index_document(
                content=content,
                title=filename,
                category=category,
                source=filepath,
                collection_key=collection_key
            )
        except Exception as e:
            logger.error(f"Failed to read and index file '{filepath}': {e}")
            return {"status": "error", "error": str(e)}

    def index_workspace(self, workspace_path: str, max_files: int = 150) -> Dict[str, Any]:
        """
        Crawls and indexes source code files (.py, .js, .html, .md) in a workspace into 'jarvis_codebase'.
        """
        if not os.path.isdir(workspace_path):
            return {"status": "error", "error": f"Workspace directory '{workspace_path}' not found."}

        col_name = self.COLLECTIONS["codebase"]
        self._ensure_collection(col_name)

        allowed_exts = {".py", ".md", ".json", ".js", ".ts", ".html", ".css"}
        ignored_dirs = {".venv", ".venv_browser", ".git", "__pycache__", "node_modules", "data"}

        indexed_count = 0
        total_chunks = 0

        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in allowed_exts:
                    fpath = os.path.join(root, file)
                    rel_path = os.path.relpath(fpath, workspace_path)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read(25000) # Read up to 25KB per file
                        if text and len(text.strip()) > 30:
                            res = self.index_document(
                                content=text,
                                title=rel_path,
                                category="source_code",
                                source=fpath,
                                collection_key="codebase"
                            )
                            if res.get("status") == "success":
                                indexed_count += 1
                                total_chunks += res.get("chunks_indexed", 0)
                                if indexed_count >= max_files:
                                    break
                    except Exception as e:
                        logger.debug(f"Skipping file {file}: {e}")
            if indexed_count >= max_files:
                break

        logger.info(f"Workspace indexing complete: {indexed_count} files ({total_chunks} chunks).")
        return {
            "status": "success",
            "files_indexed": indexed_count,
            "total_chunks": total_chunks,
            "collection": col_name
        }

    # ─── Semantic Search & Retrieval ──────────────────────────────────────────

    def search(
        self,
        query: str,
        collection_key: str = "documents",
        limit: int = 5,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes dense semantic vector similarity search against the target collection.
        Returns top-matching chunks with cosine similarity score and metadata.
        """
        if not self.is_available():
            return []
        if not query or not query.strip():
            return []

        col_name = self.COLLECTIONS.get(collection_key, collection_key)
        self._ensure_collection(col_name)

        try:
            q_vec = self.embed_text(query.strip())
            
            # Optional category filter
            q_filter = None
            if category:
                q_filter = Filter(
                    must=[FieldCondition(key="category", match=MatchValue(value=category))]
                )

            res = self.client.query_points(
                collection_name=col_name,
                query=q_vec,
                query_filter=q_filter,
                limit=limit
            )

            results = []
            for point in res.points:
                payload = point.payload or {}
                results.append({
                    "id": point.id,
                    "score": round(float(point.score), 4),
                    "text": payload.get("text", ""),
                    "title": payload.get("title", "Untitled"),
                    "category": payload.get("category", "general"),
                    "source": payload.get("source", ""),
                    "chunk_index": payload.get("chunk_index", 0),
                    "timestamp": payload.get("timestamp", 0)
                })

            return results
        except Exception as e:
            logger.error(f"Qdrant search error: {e}", exc_info=True)
            return []

    def get_rag_context(self, query: str, collection_key: str = "documents", limit: int = 3) -> str:
        """
        Retrieves top relevant chunks and formats them as a clean Markdown RAG block for LLM prompts.
        """
        hits = self.search(query=query, collection_key=collection_key, limit=limit)
        if not hits:
            return ""

        formatted_chunks = []
        for h in hits:
            formatted_chunks.append(
                f"**[Source: {h['title']} | Score: {h['score']:.2f}]**\n{h['text']}"
            )

        context_block = "\n\n---\n\n".join(formatted_chunks)
        return f"\n### RELEVANT KNOWLEDGE BASE CONTEXT (QDRANT RAG):\n{context_block}\n"

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics for all managed Qdrant collections."""
        if not self.is_available():
            return {"status": "offline", "collections": {}}

        stats = {}
        for alias, col_name in self.COLLECTIONS.items():
            try:
                if self.client.collection_exists(col_name):
                    info = self.client.get_collection(col_name)
                    stats[alias] = {
                        "collection_name": col_name,
                        "points_count": getattr(info, "points_count", 0),
                        "status": getattr(info, "status", "ready")
                    }
                else:
                    stats[alias] = {"collection_name": col_name, "points_count": 0, "status": "not_created"}
            except Exception as e:
                stats[alias] = {"collection_name": col_name, "error": str(e)}

        return {"status": "online", "storage_path": self.storage_path, "collections": stats}

    def delete_document(self, doc_id: str, collection_key: str = "documents") -> Dict[str, Any]:
        """Removes a point by ID from the specified collection."""
        if not self.is_available():
            return {"status": "error", "error": "Qdrant unavailable"}

        col_name = self.COLLECTIONS.get(collection_key, collection_key)
        try:
            self.client.delete(collection_name=col_name, points_selector=[doc_id])
            return {"status": "success", "deleted_id": doc_id, "collection": col_name}
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global Singleton Instance
qdrant_engine = QdrantEngine()
