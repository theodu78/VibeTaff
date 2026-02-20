from pathlib import Path
from tools._base import tool, resolve_safe_path


@tool(
    name="export_to_pdf",
    description="Convertit un fichier Markdown du projet en PDF. Le PDF est créé dans le même dossier que le fichier source.",
    category="files",
    parameters={
        "type": "object",
        "properties": {
            "file_name": {
                "type": "string",
                "description": "Chemin relatif du fichier .md à convertir en PDF (ex: 'rapport.md').",
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

    if not target.suffix.lower() == ".md":
        return f"Erreur : Seuls les fichiers .md peuvent être convertis en PDF. '{file_name}' n'est pas un fichier Markdown."

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Erreur : Impossible de lire '{file_name}'."

    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        font_dir = Path(__file__).parent.parent.parent / "fonts"
        has_unicode_font = False

        if font_dir.exists():
            regular = font_dir / "DejaVuSans.ttf"
            bold = font_dir / "DejaVuSans-Bold.ttf"
            if regular.exists():
                pdf.add_font("DejaVu", "", str(regular), uni=True)
                if bold.exists():
                    pdf.add_font("DejaVu", "B", str(bold), uni=True)
                has_unicode_font = True

        if has_unicode_font:
            pdf.set_font("DejaVu", size=10)
        else:
            pdf.set_font("Helvetica", size=10)

        for line in content.split("\n"):
            stripped = line.strip()

            if stripped.startswith("# "):
                pdf.set_font("DejaVu" if has_unicode_font else "Helvetica", "B", 18)
                pdf.cell(0, 12, stripped[2:], new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
            elif stripped.startswith("## "):
                pdf.set_font("DejaVu" if has_unicode_font else "Helvetica", "B", 14)
                pdf.cell(0, 10, stripped[3:], new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
            elif stripped.startswith("### "):
                pdf.set_font("DejaVu" if has_unicode_font else "Helvetica", "B", 12)
                pdf.cell(0, 8, stripped[4:], new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)
            elif stripped.startswith("- ") or stripped.startswith("* "):
                pdf.set_font("DejaVu" if has_unicode_font else "Helvetica", size=10)
                pdf.cell(8)
                pdf.multi_cell(0, 6, f"• {stripped[2:]}")
            elif stripped == "":
                pdf.ln(4)
            else:
                pdf.set_font("DejaVu" if has_unicode_font else "Helvetica", size=10)
                pdf.multi_cell(0, 6, stripped)

        pdf_name = target.stem + ".pdf"
        pdf_target = resolve_safe_path(project_dir, pdf_name)
        if pdf_target is None:
            return "Erreur : Impossible de créer le fichier PDF."

        pdf.output(str(pdf_target))
        return f"Le PDF '{pdf_name}' a été créé avec succès ({pdf_target.stat().st_size // 1024} Ko)."

    except ImportError:
        return "Erreur : La bibliothèque fpdf2 n'est pas installée. Exécuter 'pip install fpdf2' dans le backend."
    except Exception as e:
        return f"Erreur lors de la création du PDF : {str(e)}"
