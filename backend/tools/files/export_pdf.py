import re
from pathlib import Path
from tools._base import tool, resolve_safe_path


@tool(
    name="export_to_pdf",
    description=(
        "Convertit un fichier Markdown en PDF. Le PDF est créé dans le même dossier. "
        "QUAND l'utiliser : quand l'utilisateur demande d'exporter ou de 'faire un PDF' d'un document. "
        "PRÉREQUIS : le fichier .md doit déjà exister — crée-le d'abord avec write_project_note si besoin."
    ),
    category="files",
    parameters={
        "type": "object",
        "properties": {
            "file_name": {
                "type": "string",
                "description": "Chemin relatif du fichier .md à convertir en PDF (ex: 'rapport.md', 'carbone/guide.md').",
            },
        },
        "required": ["file_name"],
    },
)
def export_to_pdf(args: dict, project_id: str, project_dir: Path) -> str:
    file_name = args.get("file_name", "").strip()
    if not file_name:
        return "Erreur : Aucun nom de fichier fourni."

    target = resolve_safe_path(project_dir, file_name)
    if target is None:
        return f"Erreur : Le chemin '{file_name}' sort du périmètre du projet."

    if not target.exists():
        return f"Erreur : Le fichier '{file_name}' n'existe pas."

    if target.suffix.lower() != ".md":
        return f"Erreur : Seuls les fichiers .md peuvent être convertis."

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Erreur : Impossible de lire '{file_name}'."

    try:
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=12)
        pdf.set_margins(15, 12, 15)
        pdf.add_page()

        font_dir = Path(__file__).parent.parent.parent / "fonts"
        has_uf = False

        if font_dir.exists():
            regular = font_dir / "DejaVuSans.ttf"
            bold = font_dir / "DejaVuSans-Bold.ttf"
            if regular.exists():
                pdf.add_font("DejaVu", "", str(regular), uni=True)
                if bold.exists():
                    pdf.add_font("DejaVu", "B", str(bold), uni=True)
                has_uf = True

        fn = "DejaVu" if has_uf else "Helvetica"

        def sf(style="", size=10):
            pdf.set_font(fn, style, size)

        def clean(t: str) -> str:
            t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
            t = t.replace("__", "").replace("`", "")
            if not has_uf:
                t = t.encode("latin-1", errors="replace").decode("latin-1")
            return t

        def write_text(text: str, size=9, style="", indent=0):
            """Write text with explicit left margin reset."""
            sf(style, size)
            x = pdf.l_margin + indent
            pdf.set_x(x)
            w = pdf.w - x - pdf.r_margin
            if w < 20:
                x = pdf.l_margin
                pdf.set_x(x)
                w = pdf.w - pdf.l_margin - pdf.r_margin
            pdf.multi_cell(w, size * 0.5, clean(text),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        prev_empty = False
        table_rows: list[list[str]] = []

        def flush_table():
            nonlocal table_rows
            if not table_rows:
                return
            num_cols = max(len(r) for r in table_rows)
            if num_cols == 0:
                table_rows = []
                return

            avail = pdf.w - pdf.l_margin - pdf.r_margin
            col_w = avail / num_cols

            for ri, row in enumerate(table_rows):
                sf("B" if ri == 0 else "", 8)
                pdf.set_x(pdf.l_margin)
                for ci in range(num_cols):
                    cell_text = clean(row[ci].strip()) if ci < len(row) else ""
                    if len(cell_text) > 45:
                        cell_text = cell_text[:42] + "..."
                    pdf.cell(col_w, 4.5, cell_text, border=1,
                             new_x=XPos.RIGHT, new_y=YPos.TOP)
                pdf.ln()

            pdf.ln(1.5)
            table_rows = []

        for line in content.split("\n"):
            stripped = line.strip()

            if stripped.startswith("|") and stripped.endswith("|"):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if all(set(c) <= {"-", ":", " "} for c in cells if c):
                    continue
                table_rows.append(cells)
                continue

            if table_rows:
                flush_table()

            if not stripped:
                if not prev_empty:
                    pdf.ln(1.5)
                prev_empty = True
                continue
            prev_empty = False

            if stripped.startswith("# "):
                write_text(stripped[2:], size=16, style="B")
                pdf.ln(1)
            elif stripped.startswith("## "):
                write_text(stripped[3:], size=12, style="B")
                pdf.ln(0.5)
            elif stripped.startswith("### "):
                write_text(stripped[4:], size=11, style="B")
                pdf.ln(0.5)
            elif stripped.startswith("#### "):
                write_text(stripped[5:], size=10, style="B")
            elif stripped == "---" or stripped == "***":
                pdf.ln(1)
                y = pdf.get_y()
                pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
                pdf.ln(2)
            elif re.match(r"^[-*]\s", stripped):
                write_text(f"• {stripped[2:]}", size=9, indent=4)
            elif re.match(r"^\s{2,}[-*]\s", line):
                text = line.strip()[2:]
                write_text(f"◦ {text}", size=8, indent=8)
            elif re.match(r"^\d+\.\s", stripped):
                write_text(stripped, size=9, indent=4)
            else:
                write_text(stripped, size=9)

        if table_rows:
            flush_table()

        pdf_path = target.with_suffix(".pdf")
        pdf.output(str(pdf_path))
        size_kb = pdf_path.stat().st_size // 1024
        return f"Le PDF '{pdf_path.name}' a été créé ({size_kb} Ko)."

    except ImportError:
        return "Erreur : fpdf2 n'est pas installée. Lancer 'pip install fpdf2'."
    except Exception as e:
        return f"Erreur PDF : {str(e)}"
