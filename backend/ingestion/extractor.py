"""
Extraction module: File → Markdown text.
Dispatches based on file extension.
"""

from pathlib import Path

import pymupdf4llm
import pandas as pd
from bs4 import BeautifulSoup


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls", ".csv", ".eml", ".msg"}


def extract(file_path: Path) -> tuple[str, dict]:
    """
    Extract text content from a file and return (markdown_text, metadata).
    Raises ValueError for unsupported file types.
    """
    ext = file_path.suffix.lower()
    metadata = {
        "source_file": file_path.name,
        "file_type": ext,
        "file_size_bytes": file_path.stat().st_size,
    }

    if ext == ".pdf":
        return _extract_pdf(file_path, metadata)
    elif ext == ".docx":
        return _extract_docx(file_path, metadata)
    elif ext in (".xlsx", ".xls"):
        return _extract_excel(file_path, metadata)
    elif ext == ".csv":
        return _extract_csv(file_path, metadata)
    elif ext in (".eml", ".msg"):
        return _extract_email(file_path, metadata)
    else:
        raise ValueError(
            f"Type de fichier '{ext}' non supporté. "
            f"Formats acceptés : {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )


def _extract_pdf(file_path: Path, metadata: dict) -> tuple[str, dict]:
    md_text = pymupdf4llm.to_markdown(str(file_path))
    page_count = _count_pdf_pages(file_path)
    metadata["page_count"] = page_count
    return md_text, metadata


def _count_pdf_pages(file_path: Path) -> int:
    try:
        import pymupdf
        doc = pymupdf.open(str(file_path))
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0


def _extract_docx(file_path: Path, metadata: dict) -> tuple[str, dict]:
    md_text = pymupdf4llm.to_markdown(str(file_path))
    return md_text, metadata


def _extract_excel(file_path: Path, metadata: dict) -> tuple[str, dict]:
    xls = pd.ExcelFile(file_path, engine="openpyxl")
    parts = []
    total_rows = 0

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        total_rows += len(df)
        md_table = f"## Feuille : {sheet_name}\n\n"
        md_table += df.to_markdown(index=False)
        parts.append(md_table)

    metadata["sheet_count"] = len(xls.sheet_names)
    metadata["total_rows"] = total_rows
    return "\n\n---\n\n".join(parts), metadata


def _extract_csv(file_path: Path, metadata: dict) -> tuple[str, dict]:
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Impossible de lire '{file_path.name}' : encodage non reconnu.")

    metadata["total_rows"] = len(df)
    return df.to_markdown(index=False), metadata


def _extract_email(file_path: Path, metadata: dict) -> tuple[str, dict]:
    ext = file_path.suffix.lower()

    if ext == ".eml":
        return _extract_eml(file_path, metadata)
    else:
        return _extract_msg(file_path, metadata)


def _extract_eml(file_path: Path, metadata: dict) -> tuple[str, dict]:
    import email
    from email import policy

    with open(file_path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    headers = {
        "from": msg.get("From", ""),
        "to": msg.get("To", ""),
        "date": msg.get("Date", ""),
        "subject": msg.get("Subject", ""),
    }
    metadata.update(headers)

    body = msg.get_body(preferencelist=("plain", "html"))
    content = ""
    if body:
        raw = body.get_content()
        if body.get_content_type() == "text/html":
            soup = BeautifulSoup(raw, "lxml")
            content = soup.get_text(separator="\n", strip=True)
        else:
            content = raw

    md = f"# Email\n\n"
    md += f"- **De** : {headers['from']}\n"
    md += f"- **À** : {headers['to']}\n"
    md += f"- **Date** : {headers['date']}\n"
    md += f"- **Objet** : {headers['subject']}\n\n"
    md += f"---\n\n{content}"

    return md, metadata


def _extract_msg(file_path: Path, metadata: dict) -> tuple[str, dict]:
    raw = file_path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    soup = BeautifulSoup(text, "lxml")
    content = soup.get_text(separator="\n", strip=True)

    md = f"# Email (.msg)\n\n{content}"
    return md, metadata
