"""
Sample PDF Generator for Pharmaceutical Complaint Management System (QMS).

Design Justification:
We use `reportlab` for programmatic PDF creation because it renders crisp, native text streams
with proper font encodings into standard PDF canvas objects. This guarantees 100% reproducible
text-extractable PDF files for testing parsers (`pypdf`) without needing external binary tools
or OCR.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def create_tablet_chipping_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1E3A8A'),
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
    )
    
    story = [
        Paragraph("PHARMACEUTICAL PRODUCT QUALITY COMPLAINT FORM", title_style),
        Spacer(1, 10),
        Paragraph("<b>Document Reference:</b> QMS-EXT-2026-0889 | <b>Date of Report:</b> 2026-04-14", body_style),
        Spacer(1, 12),
        Paragraph("1. Complainant & Healthcare Facility Information", heading_style),
        Paragraph("<b>Complainant Name:</b> Pharmacist Maria Garcia<br/>"
                  "<b>Facility:</b> Farmacia Central Madrid<br/>"
                  "<b>Address:</b> Calle Mayor 45, 28013 Madrid, Spain<br/>"
                  "<b>Email:</b> maria.garcia@farmaciacentral.es<br/>"
                  "<b>Phone:</b> +34 91 555 0192", body_style),
        Spacer(1, 10),
        Paragraph("2. Product & Batch Details", heading_style),
        Paragraph("<b>Product Name:</b> Paracetamol 500mg Film-Coated Tablets<br/>"
                  "<b>Batch / Lot Number:</b> PT-4471-A<br/>"
                  "<b>Manufacturing Date:</b> 2025-10-12 | <b>Expiry Date:</b> 2028-10-31<br/>"
                  "<b>Dosage Form:</b> Solid Oral Tablet (Blister pack of 20)", body_style),
        Spacer(1, 10),
        Paragraph("3. Incident & Defect Description", heading_style),
        Paragraph(
            "Upon opening two distinct commercial boxes from shipment lot PT-4471-A, dispensing staff "
            "and patients observed significant physical defects. Approximately 4 out of 10 tablets in "
            "the inspected blister strips showed excessive chipping around the edges, surface crumbling, "
            "and visible transverse cracking across the scoring line. One patient reported that the tablet "
            "fragmented into powder upon push-through extraction from the foil blister.<br/><br/>"
            "No adverse patient health consequences or toxic reactions have been reported to date, but "
            "defective units have been quarantined at the pharmacy storage to prevent further distribution.",
            body_style
        ),
        Spacer(1, 10),
        Paragraph("4. Initial Containment & Storage", heading_style),
        Paragraph("48 unsold blister packs from batch PT-4471-A have been segregated in the pharmacy quarantine locker "
                  "under controlled room temperature (20°C - 25°C). Samples are held available for QA inspection and pickup.", body_style)
    ]
    
    doc.build(story)


def create_wrong_expiry_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0F766E'),
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
    )
    
    story = [
        Paragraph("PACKAGING & LABELING DISCREPANCY NOTIFICATION", title_style),
        Spacer(1, 10),
        Paragraph("<b>Reference Number:</b> LAB-NOTIF-2026-0312 | <b>Date:</b> 2026-05-02", body_style),
        Spacer(1, 12),
        Paragraph("1. Reporting Entity", heading_style),
        Paragraph("<b>Reporter:</b> Dr. John Keller (Chief Dispensing Pharmacist)<br/>"
                  "<b>Organization:</b> Keller Apotheke & Pharmacy Services<br/>"
                  "<b>Email:</b> contact@kellerpharmacy.de<br/>"
                  "<b>Phone:</b> +49 89 2345 6789", body_style),
        Spacer(1, 10),
        Paragraph("2. Product Identification", heading_style),
        Paragraph("<b>Product:</b> Cetirizine 10mg Film-Coated Tablets (Box of 30)<br/>"
                  "<b>Batch Number:</b> CZ-8812-C<br/>"
                  "<b>Blister Foil Print:</b> EXP: 12/2026 | LOT: CZ-8812-C<br/>"
                  "<b>Outer Secondary Carton Print:</b> EXP: 12/2029 | LOT: CZ-8812-C", body_style),
        Spacer(1, 10),
        Paragraph("3. Defect Description & Investigation Request", heading_style),
        Paragraph(
            "During routine incoming stock verification, our receiving pharmacist noticed a direct date mismatch "
            "between the primary packaging and the secondary folding box. The outer carton displays an expiration "
            "date of 12/2029 (a 5-year shelf life), whereas the internal aluminum-PVC blister foil is stamped with "
            "the approved 3-year expiration date of 12/2026.<br/><br/>"
            "This is a packaging line coding/printing error. There is no defect in the physical integrity of the "
            "tablets themselves, and no patients have received these incorrectly marked cartons. We request corrected "
            "labeling instructions or authorization to return 120 cartons from batch CZ-8812-C.",
            body_style
        )
    ]
    
    doc.build(story)


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    
    chipping_pdf = out_dir / "complaint_tablet_chipping.pdf"
    expiry_pdf = out_dir / "complaint_wrong_expiry.pdf"
    
    create_tablet_chipping_pdf(chipping_pdf)
    print(f"Generated: {chipping_pdf}")
    
    create_wrong_expiry_pdf(expiry_pdf)
    print(f"Generated: {expiry_pdf}")
