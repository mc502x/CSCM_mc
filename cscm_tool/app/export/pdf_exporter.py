"""PDF catalogue export (FR-045). Uses fpdf2 — pure Python, no system
dependency, consistent with the no-cloud/offline-deployable constraint
(docs/11-security-architecture.md §12, NFR-008)."""

from fpdf import FPDF

_MAX_CELL_CHARS = 24


def build_pdf(rows: list[dict], notice: str | None = None) -> bytes:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()

    if notice:
        pdf.set_font("Helvetica", style="B", size=10)
        pdf.set_text_color(180, 0, 0)
        pdf.cell(0, 8, notice)
        pdf.ln(10)
        pdf.set_text_color(0, 0, 0)

    if not rows:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 10, "No records.")
        return bytes(pdf.output())

    columns = list(rows[0].keys())
    col_width = pdf.epw / len(columns)

    pdf.set_font("Helvetica", style="B", size=7)
    for col in columns:
        pdf.cell(col_width, 6, str(col)[:_MAX_CELL_CHARS], border=1)
    pdf.ln()

    pdf.set_font("Helvetica", size=7)
    for row in rows:
        for col in columns:
            pdf.cell(col_width, 6, str(row.get(col, ""))[:_MAX_CELL_CHARS], border=1)
        pdf.ln()

    return bytes(pdf.output())
