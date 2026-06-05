import os
from datetime import datetime
try:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
import config

class BriefingEngine:
    """Strategic Intelligence Generator: Crafting high-impact PDF briefings."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_pdf(self, report_data: dict) -> str:
        """Create a professional Stark Industries themed intelligence report."""
        if not REPORTLAB_AVAILABLE:
            import logging
            logging.getLogger("jarvis.briefing").warning("PDF Generation failed: 'reportlab' module not found.")
            return None

        filename = f"briefing_{report_data['id']}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=LETTER)
        styles = getSampleStyleSheet()
        
        # Custom Stark Styles
        title_style = ParagraphStyle(
            'StarkTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor("#FF8800"),
            spaceAfter=20,
            fontName="Helvetica-Bold"
        )
        
        header_style = ParagraphStyle(
            'StarkHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor("#00AAFF"),
            spaceAfter=12
        )
        
        body_style = ParagraphStyle(
            'StarkBody',
            parent=styles['BodyText'],
            fontSize=10,
            textColor=colors.white,
            leading=14,
            backColor=colors.HexColor("#1A1A1A"),
            borderPadding=10
        )

        elements = []

        # 1. Header
        elements.append(Paragraph("STARK INDUSTRIES — STRATEGIC INTELLIGENCE", title_style))
        elements.append(Paragraph(f"SUBJECT: {report_data['topic']}", header_style))
        elements.append(Paragraph(f"CLEARANCE: LEVEL 7 (PRO) | TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # 2. Executive Summary
        elements.append(Paragraph("EXECUTIVE SUMMARY", header_style))
        elements.append(Paragraph(report_data['summary'], styles['Normal']))
        elements.append(Spacer(1, 20))

        # 3. Key Findings (Trends)
        elements.append(Paragraph("NEURAL TREND ANALYSIS", header_style))
        
        data = [["Trend Node", "Implication"]]
        for trend in report_data.get('trends', []):
            data.append([trend['title'], trend['implication']])
            
        t = Table(data, colWidths=[150, 350])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#333333")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.orange),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.grey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

        # 4. Footer
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("ENCRYPTED VIA JARVIS NEURAL MESH — CONFIDENTIAL", styles['Italic']))

        # Build PDF
        try:
            doc.build(elements)
            return filename
        except Exception as e:
            print(f"PDF Build Error: {e}")
            return ""
