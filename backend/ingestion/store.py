"""
LanceDB storage module: store and search document chunks with vectors.
One table per project.
"""

from pathlib import Path

import lancedb
import pyarrow as pa

from .embedder import EMBEDDING_DIM

LANCE_DIR = Path.home() / "VibetaffProjects" / ".lancedb"


def _get_db() -> lancedb.DBConnection:
    LANCE_DIR.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(LANCE_DIR))


def _table_name(project_id: str) -> str:
    safe = "".join(c for c in project_id if c.isalnum() or c in "-_")
    return f"docs_{safe}"


def _schema() -> pa.Schema:
    return pa.schema([
        pa.field("id", pa.string()),
        pa.field("text", pa.string()),
        pa.field("chunk_index", pa.int32()),
        pa.field("source_file", pa.string()),
        pa.field("file_type", pa.string()),
        pa.field("metadata_json", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
    ])


def _get_or_create_table(db: lancedb.DBConnection, project_id: str):
    name = _table_name(project_id)
    if name in db.table_names():
        return db.open_table(name)
    return db.create_table(name, schema=_schema())


def store_chunks(
    project_id: str,
    chunks: list[dict],
    vectors: list[list[float]],
    source_file: str,
) -> int:
    """
    Store embedded chunks in LanceDB.
    Returns the number of chunks stored.
    """
    import json
    import uuid

    db = _get_db()
    table = _get_or_create_table(db, project_id)

    records = []
    for chunk, vector in zip(chunks, vectors):
        records.append({
            "id": str(uuid.uuid4()),
            "text": chunk["text"],
            "chunk_index": chunk["chunk_index"],
            "source_file": source_file,
            "file_type": chunk["metadata"].get("file_type", ""),
            "metadata_json": json.dumps(chunk["metadata"], ensure_ascii=False),
            "vector": vector,
        })

    if records:
        table.add(records)

    return len(records)


def search_chunks(
    project_id: str,
    query_vector: list[float],
    top_k: int = 5,
) -> list[dict]:
    """
    Search for the top-K most similar chunks.
    Returns a list of dicts with text, source_file, score, metadata.
    """
    import json

    db = _get_db()
    name = _table_name(project_id)

    if name not in db.table_names():
        return []

    table = db.open_table(name)
    results = table.search(query_vector).limit(top_k).to_list()

    output = []
    for row in results:
        meta = {}
        try:
            meta = json.loads(row.get("metadata_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            pass

        output.append({
            "text": row.get("text", ""),
            "source_file": row.get("source_file", ""),
            "score": row.get("_distance", 0.0),
            "chunk_index": row.get("chunk_index", 0),
            "metadata": meta,
        })

    return output


def delete_file_chunks(project_id: str, source_file: str) -> int:
    """Delete all chunks from a specific source file. Returns count deleted."""
    db = _get_db()
    name = _table_name(project_id)

    if name not in db.table_names():
        return 0

    table = db.open_table(name)
    table.delete(f"source_file = '{source_file}'")
    return 1


def list_indexed_files(project_id: str) -> list[dict]:
    """List all unique source files indexed for a project."""
    db = _get_db()
    name = _table_name(project_id)

    if name not in db.table_names():
        return []

    table = db.open_table(name)
    df = table.to_pandas()

    if df.empty:
        return []

    files = []
    for source_file, group in df.groupby("source_file"):
        files.append({
            "source_file": source_file,
            "chunk_count": len(group),
            "file_type": group.iloc[0].get("file_type", ""),
        })

    return files
