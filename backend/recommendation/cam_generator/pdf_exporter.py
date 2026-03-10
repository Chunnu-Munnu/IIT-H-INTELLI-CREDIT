"""
PDF CAM generator using ReportLab.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from loguru import logger
from app.constants import CRORE, LAKH


def format_inr(paise: int) -> str:
    rupees = paise / 100
    if abs(rupees) >= CRORE:
        return f"INR {rupees / CRORE:.2f} Cr"
    elif abs(rupees) >= LAKH:
        return f"INR {rupees / LAKH:.2f} L"
    return f"INR {rupees:,.0f}"


DECISION_COLORS_HEX = {
    "APPROVE": colors.HexColor("#1B8731"),
    "APPROVE_WITH_CONDITIONS": colors.HexColor("#E67E22"),
    "REFER": colors.HexColor("#D35400"),
    "REJECT": colors.HexColor("#C0392B"),
}


class PDFExporter:

    def export(self, cam_data: dict, output_path: str) -> str:
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("Title", parent=styles["Title"], textColor=colors.HexColor("#1F3864"), fontSize=18)
        h1_style = ParagraphStyle("H1", parent=styles["Heading1"], textColor=colors.HexColor("#1F3864"), fontSize=14)
        body_style = styles["Normal"]
        body_style.fontSize = 10

        story = []

        # ─── Title ────────────────────────────────────────────────────────────
        story.append(Paragraph("CREDIT APPRAISAL MEMORANDUM", title_style))
        story.append(Paragraph("Prepared by Intelli-Credit AI Engine", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(f"Company: <b>{cam_data.get('company_name', '')}</b>", body_style))
        story.append(Paragraph(f"Date: {cam_data.get('generated_at', '')}", body_style))
        story.append(Paragraph(f"Case ID: {cam_data.get('case_id', '')}", body_style))
        story.append(Spacer(1, 0.2 * inch))

        # ─── Decision ─────────────────────────────────────────────────────────
        decision = cam_data.get("decision", "N/A")
        decision_color = DECISION_COLORS_HEX.get(decision, colors.black)
        decision_style = ParagraphStyle("Decision", fontSize=16, textColor=decision_color, fontName="Helvetica-Bold")
        story.append(Paragraph(f"RECOMMENDATION: {decision}", decision_style))
        story.append(Spacer(1, 0.2 * inch))

        # ─── Summary Table ─────────────────────────────────────────────────────
        summary_data = [
            ["Credit Score", "Risk Grade", "Default Probability", "Recommended Limit"],
            [
                str(cam_data.get("credit_score", "N/A")) + "/850",
                cam_data.get("risk_grade", "N/A"),
                f"{cam_data.get('default_probability', 0)*100:.1f}%",
                format_inr(cam_data.get("recommended_limit_paise", 0)),
            ]
        ]
        tbl = Table(summary_data, colWidths=[1.7 * inch] * 4)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.2 * inch))

        # ─── Five Cs ──────────────────────────────────────────────────────────
        story.append(Paragraph("FIVE Cs ASSESSMENT", h1_style))
        five_cs = cam_data.get("five_cs", {})
        if five_cs:
            five_c_data = [["Dimension", "Score", "Assessment"]]
            for dim, score in five_cs.items():
                if dim == "Composite":
                    continue
                assessment = "Strong" if score >= 70 else ("Adequate" if score >= 50 else "Weak")
                five_c_data.append([dim, str(score), assessment])
            five_c_tbl = Table(five_c_data, colWidths=[2 * inch, 1.5 * inch, 3 * inch])
            five_c_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E4057")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]))
            story.append(five_c_tbl)
            story.append(Spacer(1, 0.15 * inch))

        # ─── Reasons ──────────────────────────────────────────────────────────
        story.append(Paragraph("DECISION RATIONALE", h1_style))
        for reason in cam_data.get("reasons", []):
            story.append(Paragraph(f"• {reason}", body_style))
        story.append(Spacer(1, 0.1 * inch))

        # ─── Loan Structure ───────────────────────────────────────────────────
        story.append(Paragraph("LOAN STRUCTURE", h1_style))
        story.append(Paragraph(f"Interest Rate: <b>{cam_data.get('interest_rate_pct', 0)}% p.a.</b> (MCLR-linked)", body_style))
        fb = cam_data.get("facility_breakup", {})
        if fb:
            loan_data = [["Facility Type", "Amount"]]
            for facility, paise in fb.items():
                loan_data.append([facility.replace("_", " ").title(), format_inr(paise)])
            loan_tbl = Table(loan_data, colWidths=[4 * inch, 2.5 * inch])
            loan_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(loan_tbl)
        story.append(Spacer(1, 0.1 * inch))

        # ─── AI Explanation ───────────────────────────────────────────────────
        story.append(Paragraph("AI MODEL EXPLANATION (SHAP)", h1_style))
        narrative = cam_data.get("score_narrative", "")
        if narrative:
            story.append(Paragraph(narrative.replace("\n", "<br/>"), body_style))

        story.append(Spacer(1, 0.1 * inch))

        # ─── Covenants ────────────────────────────────────────────────────────
        story.append(Paragraph("COVENANTS & CONDITIONS", h1_style))
        for cov in cam_data.get("covenants", []):
            story.append(Paragraph(f"• {cov}", body_style))

        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(
            "<i>CONFIDENTIAL — Prepared by Intelli-Credit AI Engine. Not for external distribution.</i>",
            ParagraphStyle("Footer", parent=styles["Normal"], textColor=colors.grey, fontSize=8, alignment=TA_CENTER)
        ))

        doc.build(story)
        logger.info(f"CAM PDF exported: {output_path}")
        return output_path
