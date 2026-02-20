"""
Semantic chunking module: Markdown text → list of chunks.
Key rule (premortem §3): table headers are repeated at the start of every chunk.
"""

import re

TARGET_CHUNK_TOKENS = 800
OVERLAP_TOKENS = 50
APPROX_CHARS_PER_TOKEN = 4

TARGET_CHUNK_CHARS = TARGET_CHUNK_TOKENS * APPROX_CHARS_PER_TOKEN
OVERLAP_CHARS = OVERLAP_TOKENS * APPROX_CHARS_PER_TOKEN

_TABLE_HEADER_RE = re.compile(
    r"^(\|.+\|)\n(\|[\s\-:]+\|)", re.MULTILINE
)


def chunk_markdown(text: str, metadata: dict) -> list[dict]:
    """
    Split markdown text into semantic chunks.
    Each chunk is a dict with keys: text, metadata, chunk_index.
    """
    if not text.strip():
        return []

    sections = _split_by_headings(text)
    chunks = []
    chunk_index = 0

    for section in sections:
        heading = section["heading"]
        body = section["body"]

        if _is_table_content(body):
            table_chunks = _chunk_table(body, heading, metadata, chunk_index)
            chunks.extend(table_chunks)
            chunk_index += len(table_chunks)
        else:
            text_chunks = _chunk_text(body, heading, metadata, chunk_index)
            chunks.extend(text_chunks)
            chunk_index += len(text_chunks)

    return chunks


def _split_by_headings(text: str) -> list[dict]:
    heading_pattern = re.compile(r"^(#{1,4}\s+.+)$", re.MULTILINE)
    parts = heading_pattern.split(text)

    sections = []
    current_heading = ""

    i = 0
    while i < len(parts):
        part = parts[i]
        if heading_pattern.match(part.strip()):
            current_heading = part.strip()
            body = parts[i + 1] if i + 1 < len(parts) else ""
            sections.append({"heading": current_heading, "body": body.strip()})
            i += 2
        else:
            if part.strip():
                sections.append({"heading": current_heading, "body": part.strip()})
            i += 1

    return sections if sections else [{"heading": "", "body": text}]


def _is_table_content(text: str) -> bool:
    lines = [l for l in text.split("\n") if l.strip()]
    if len(lines) < 2:
        return False
    pipe_lines = sum(1 for l in lines if l.strip().startswith("|"))
    return pipe_lines / len(lines) > 0.5


def _extract_table_header(text: str) -> str | None:
    match = _TABLE_HEADER_RE.search(text)
    if match:
        return match.group(0)
    return None


def _chunk_table(text: str, heading: str, metadata: dict, start_index: int) -> list[dict]:
    """Chunk table content, repeating column headers in each chunk."""
    header = _extract_table_header(text)
    lines = text.split("\n")

    data_lines = []
    header_lines_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if header and header_lines_count < 2 and (
            stripped == header.split("\n")[0].strip()
            or re.match(r"^\|[\s\-:]+\|$", stripped)
        ):
            header_lines_count += 1
            continue
        data_lines.append(line)

    if not data_lines:
        prefix = f"{heading}\n\n" if heading else ""
        return [_make_chunk(prefix + text, metadata, start_index)]

    header_prefix = ""
    if heading:
        header_prefix += heading + "\n\n"
    if header:
        header_prefix += header + "\n"

    chunks = []
    current_lines: list[str] = []
    current_len = len(header_prefix)

    for line in data_lines:
        line_len = len(line) + 1
        if current_len + line_len > TARGET_CHUNK_CHARS and current_lines:
            chunk_text = header_prefix + "\n".join(current_lines)
            chunks.append(_make_chunk(chunk_text, metadata, start_index + len(chunks)))
            current_lines = []
            current_len = len(header_prefix)
        current_lines.append(line)
        current_len += line_len

    if current_lines:
        chunk_text = header_prefix + "\n".join(current_lines)
        chunks.append(_make_chunk(chunk_text, metadata, start_index + len(chunks)))

    return chunks


def _chunk_text(text: str, heading: str, metadata: dict, start_index: int) -> list[dict]:
    """Chunk plain text with paragraph-aware splitting."""
    if len(text) <= TARGET_CHUNK_CHARS:
        prefix = f"{heading}\n\n" if heading else ""
        return [_make_chunk(prefix + text, metadata, start_index)]

    paragraphs = re.split(r"\n{2,}", text)
    chunks = []
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_len = len(para) + 2
        if current_len + para_len > TARGET_CHUNK_CHARS and current_parts:
            prefix = f"{heading}\n\n" if heading else ""
            chunk_text = prefix + "\n\n".join(current_parts)
            chunks.append(_make_chunk(chunk_text, metadata, start_index + len(chunks)))

            overlap_text = current_parts[-1] if current_parts else ""
            current_parts = [overlap_text] if len(overlap_text) <= OVERLAP_CHARS else []
            current_len = sum(len(p) + 2 for p in current_parts)

        current_parts.append(para)
        current_len += para_len

    if current_parts:
        prefix = f"{heading}\n\n" if heading else ""
        chunk_text = prefix + "\n\n".join(current_parts)
        chunks.append(_make_chunk(chunk_text, metadata, start_index + len(chunks)))

    return chunks


def _make_chunk(text: str, metadata: dict, chunk_index: int) -> dict:
    return {
        "text": text.strip(),
        "chunk_index": chunk_index,
        "metadata": {**metadata, "chunk_index": chunk_index},
    }
