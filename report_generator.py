"""
Generates a maintenance summary as a PDF report, similar to what
real utilities produce for transformer health tracking.
"""

import os
import time
from fpdf import FPDF
import config


def generate_pdf_report(stats: dict):
    os.makedirs(config.REPORT_OUTPUT_DIR, exist_ok=True)
    filename = os.path.join(
        config.REPORT_OUTPUT_DIR,
        f"maintenance_report_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
    )

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Transformer Maintenance Report", ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 11)

    rows = [
        ("Total readings taken", stats.get("count", 0)),
        ("Total alerts triggered", stats.get("alerts", 0)),
        ("Anomalies detected", stats.get("anomalies", 0)),
        ("Peak temperature (C)", stats.get("peak_temp", "-")),
        ("Peak current (A)", stats.get("peak_current", "-")),
        ("Minimum health score (%)", stats.get("min_health", "-")),
    ]
    for label, value in rows:
        pdf.cell(90, 8, label, border=0)
        pdf.cell(0, 8, str(value), ln=True)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Recommendation", ln=True)
    pdf.set_font("Helvetica", "", 11)
    verdict = (
        "Immediate inspection recommended - multiple alerts triggered."
        if stats.get("alerts", 0) > 3
        else "System operating within acceptable range."
    )
    pdf.multi_cell(0, 7, verdict)

    pdf.output(filename)
    return filename
