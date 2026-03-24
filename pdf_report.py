# pdf_report.py
"""PDF report generation for EPL-1000."""
from io import BytesIO
try:
    from fpdf import FPDF
    _FPDF_OK = True
except ImportError:
    _FPDF_OK = False


def generate_pdf(club_data, axes_labels, logic_desc, snapshot=None):
    if not _FPDF_OK:
        return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, f"EPL-1000 Report: {club_data['name']}", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Total Score: {int(club_data['total'])} / 1000", ln=True, align="C")
    pdf.ln(6)

    # Axes
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Score Breakdown", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for ax in axes_labels:
        score = int(club_data["axes"].get(ax, 0))
        desc = logic_desc.get(ax, "")
        pdf.cell(0, 7, f"  {ax}: {score} / 200  --  {desc}", ln=True)
    pdf.ln(4)

    # Snapshot
    if snapshot:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "Club Snapshot", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for k, v in snapshot.items():
            pdf.cell(0, 7, f"  {k}: {v}", ln=True)

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "EPL-1000 by Hikaru Scoring. For informational purposes only.", align="C")

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
