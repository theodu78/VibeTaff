"""
Pipeline orchestration: Extract → Chunk → Embed → Store.
Single entry point: ingest_file().
"""

import logging
from pathlib import Path

from .extractor import extract, SUPPORTED_EXTENSIONS
from .chunker import chunk_markdown
from .embedder import embed_texts
from .store import store_chunks

logger = logging.getLogger(__name__)


def ingest_file(file_path: Path, project_id: str = "default") -> dict:
    """
    Full ingestion pipeline for a single file.
    Returns a summary dict with status and stats.
    """
    if not file_path.exists():
        return {"status": "error", "message": f"Fichier introuvable : {file_path.name}"}

    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return {
            "status": "error",
            "message": (
                f"Type '{ext}' non supporté. "
                f"Formats acceptés : {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        }

    try:
        logger.info(f"[1/4] Extraction de '{file_path.name}'...")
        markdown_text, metadata = extract(file_path)

        if not markdown_text.strip():
            return {
                "status": "error",
                "message": f"Aucun contenu extractible dans '{file_path.name}'.",
            }

        logger.info(f"[2/4] Chunking ({len(markdown_text)} caractères)...")
        chunks = chunk_markdown(markdown_text, metadata)

        if not chunks:
            return {
                "status": "error",
                "message": f"Le chunking n'a produit aucun résultat pour '{file_path.name}'.",
            }

        logger.info(f"[3/4] Embedding ({len(chunks)} chunks)...")
        texts = [c["text"] for c in chunks]
        vectors = embed_texts(texts)

        logger.info(f"[4/4] Stockage dans LanceDB...")
        stored = store_chunks(project_id, chunks, vectors, file_path.name)

        logger.info(f"Pipeline terminé : {stored} chunks stockés pour '{file_path.name}'.")
        return {
            "status": "ok",
            "file_name": file_path.name,
            "file_type": ext,
            "chars_extracted": len(markdown_text),
            "chunks_created": len(chunks),
            "chunks_stored": stored,
            "metadata": metadata,
        }

    except Exception as e:
        logger.exception(f"Erreur pipeline pour '{file_path.name}'")
        return {
            "status": "error",
            "message": f"Erreur lors du traitement de '{file_path.name}' : {str(e)}",
        }
