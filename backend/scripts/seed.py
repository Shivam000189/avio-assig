"""Database seeding script for the Pharmaceutical Customer Complaint Management System.

Populates the database with 6 realistic pharmaceutical complaint records,
including nested documents, CAPA plans, and AI summaries.

Usage:
    python -m scripts.seed (executed from backend/ directory)
"""

import asyncio
from datetime import datetime, timezone
import logging

from app.constants import (
    CapaActionType,
    CapaStatus,
    ComplaintSource,
    ComplaintStatus,
    ComplaintType,
    DocumentFileType,
    Severity,
)
from app.database import prisma

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("seed")


async def clear_database() -> None:
    """Delete existing database records in foreign-key safe order."""
    logger.info("Clearing existing database records in FK-safe order...")
    # Delete children first, then parent complaints
    deleted_summaries = await prisma.complaintsummary.delete_many()
    deleted_capas = await prisma.capa.delete_many()
    deleted_docs = await prisma.complaintdocument.delete_many()
    deleted_complaints = await prisma.complaint.delete_many()

    logger.info(
        "Purged: %d summaries, %d CAPAs, %d documents, %d complaints.",
        deleted_summaries,
        deleted_capas,
        deleted_docs,
        deleted_complaints,
    )


async def seed_data() -> None:
    """Insert 6 realistic pharmaceutical complaints with related records."""
    logger.info("Starting database seeding...")

    complaints_data = [
        # 1. QualityDefect - Chipped tablets
        {
            "complaintNumber": "CMP-2026-0001",
            "complainantName": "St. Jude Hospital Pharmacy",
            "email": "pharmacy@stjude-health.org",
            "phone": "+1-555-019-2831",
            "productName": "Paracetamol 500mg Tablets",
            "batchNumber": "PT-4471-A",
            "expiryDate": datetime(2027, 12, 31, tzinfo=timezone.utc),
            "manufactureDate": datetime(2025, 1, 15, tzinfo=timezone.utc),
            "complaintType": ComplaintType.QUALITY_DEFECT.value,
            "description": "Hospital pharmacy staff discovered multiple chipped and crumbling tablets in blister packs during unit-dose dispensing.",
            "severity": Severity.MAJOR.value,
            "status": ComplaintStatus.IN_PROGRESS.value,
            "source": ComplaintSource.PDF.value,
            "country": "United States",
            "aiSummary": "Chipped and friable Paracetamol 500mg tablets found across multiple blister strips in batch PT-4471-A. Quality defect investigation opened to review tablet press compression forces and die integrity.",
            "rootCause": "Tooling wear on rotary press punch heads causing mechanical shearing during compression.",
            "documents": {
                "create": [
                    {
                        "filename": "incident_report_pt4471a.pdf",
                        "fileType": DocumentFileType.PDF.value,
                        "extractedText": "Quality incident report: Visual inspection confirms 12 chipped tablets out of 100 units sampled from batch PT-4471-A.",
                    }
                ]
            },
            "summary": {
                "create": {
                    "summaryText": "Complaint CMP-2026-0001 details chipped Paracetamol 500mg tablets from batch PT-4471-A reported by St. Jude Hospital Pharmacy. Visual defect rate observed is 12% in inspected blister packs. Packaging line compression parameters and punch tooling integrity are currently under formal investigation."
                }
            },
            "capa": {
                "create": {
                    "actionType": CapaActionType.CORRECTIVE.value,
                    "recommendedAction": "Quarantine remaining inventory of batch PT-4471-A. Inspect and replace worn punch dies on Tableting Press #3. Implement optical tablet inspection prior to blister packaging.",
                    "actionOwner": "Dr. Aris Thorne (QA Operations)",
                    "dueDate": datetime(2026, 4, 15, tzinfo=timezone.utc),
                    "capaStatus": CapaStatus.IN_PROGRESS.value,
                }
            },
        },
        # 2. AdverseEvent - Allergic reaction
        {
            "complaintNumber": "CMP-2026-0002",
            "complainantName": "Oakridge Medical Clinic",
            "email": "clinical-trials@oakridge-clinic.com",
            "phone": "+1-555-014-9982",
            "productName": "Amoxicillin 250mg Capsules",
            "batchNumber": "AX-2209-B",
            "expiryDate": datetime(2027, 8, 30, tzinfo=timezone.utc),
            "manufactureDate": datetime(2024, 8, 10, tzinfo=timezone.utc),
            "complaintType": ComplaintType.ADVERSE_EVENT.value,
            "description": "Patient experienced severe acute dizziness, cutaneous rash, and localized urticaria within 45 minutes of ingesting first dose of Amoxicillin 250mg.",
            "severity": Severity.CRITICAL.value,
            "status": ComplaintStatus.OPEN.value,
            "source": ComplaintSource.EMAIL.value,
            "country": "United States",
            "aiSummary": "Critical adverse event involving severe cutaneous rash and acute dizziness following administration of Amoxicillin 250mg Capsules (Batch AX-2209-B). Escalated to Pharmacovigilance safety committee.",
            "rootCause": None,
            "documents": {
                "create": [
                    {
                        "filename": "patient_adverse_event_email.eml",
                        "fileType": DocumentFileType.EML.value,
                        "extractedText": "From: dr.smith@oakridge-clinic.com; Subject: URGENT: Adverse reaction to Amoxicillin lot AX-2209-B with acute urticaria and dizziness.",
                    }
                ]
            },
            "summary": {
                "create": {
                    "summaryText": "Complaint CMP-2026-0002 records an urgent adverse event of dizziness and severe urticaria after ingestion of Amoxicillin 250mg Capsules batch AX-2209-B. Pharmacovigilance rapid response protocol was triggered for causality assessment. Batch retention samples have been dispatched to QC laboratory for potency and impurity testing."
                }
            },
            "capa": {
                "create": {
                    "actionType": CapaActionType.CORRECTIVE.value,
                    "recommendedAction": "Initiate medical safety review and pharmacovigilance causality assessment. Perform impurity analysis and dissolution testing on retention samples of batch AX-2209-B.",
                    "actionOwner": "Dr. Evelyn Vance (Pharmacovigilance Officer)",
                    "dueDate": datetime(2026, 3, 25, tzinfo=timezone.utc),
                    "capaStatus": CapaStatus.RECOMMENDED.value,
                }
            },
        },
        # 3. LabelingIssue - Wrong expiry date
        {
            "complaintNumber": "CMP-2026-0003",
            "complainantName": "Apex Distribution Logistics",
            "email": "inbound-qa@apexlogistics.com",
            "phone": "+44-20-7946-0192",
            "productName": "Cetirizine 10mg Tablets",
            "batchNumber": "CZ-8812-C",
            "expiryDate": datetime(2028, 5, 31, tzinfo=timezone.utc),
            "manufactureDate": datetime(2025, 5, 1, tzinfo=timezone.utc),
            "complaintType": ComplaintType.LABELING_ISSUE.value,
            "description": "Secondary outer carton displays printed expiry date 'EXP 05/2026' while primary blister foil is correctly stamped 'EXP 05/2028'.",
            "severity": Severity.MINOR.value,
            "status": ComplaintStatus.CLOSED.value,
            "source": ComplaintSource.MANUAL.value,
            "country": "United Kingdom",
            "aiSummary": "Labeling discrepancy on Cetirizine 10mg Tablets batch CZ-8812-C outer carton printing. Resolved via packaging line batch record reconciliation and corrective inkjet coder realignment.",
            "rootCause": "Carton inkjet printer date offset parameter misconfiguration during secondary packaging setup.",
            "documents": {
                "create": [
                    {
                        "filename": "carton_label_inspection.txt",
                        "fileType": DocumentFileType.TXT.value,
                        "extractedText": "Secondary packaging inspection log: Inkjet coder discrepancy identified on Batch CZ-8812-C cartons.",
                    }
                ]
            },
            "summary": {
                "create": {
                    "summaryText": "Complaint CMP-2026-0003 addressed a minor labeling discrepancy between carton and blister expiry dates on Cetirizine 10mg batch CZ-8812-C. Root cause was traced to a date offset entry error on the inkjet coder during packaging setup. Quarantine inspection completed, affected cartons relabeled under QA supervision, and complaint is now closed."
                }
            },
            "capa": {
                "create": {
                    "actionType": CapaActionType.PREVENTIVE.value,
                    "recommendedAction": "Update secondary packaging line setup SOP to include mandatory dual-sign-off verification for inkjet printer date codes prior to line release.",
                    "actionOwner": "Marcus Rivera (Packaging Lead)",
                    "dueDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
                    "capaStatus": CapaStatus.CLOSED.value,
                }
            },
        },
        # 4. PackagingIssue - Empty blister pockets
        {
            "complaintNumber": "CMP-2026-0004",
            "complainantName": "CarePlus Community Pharmacy",
            "email": "orders@careplus-rx.com",
            "phone": "+1-555-018-7711",
            "productName": "Metformin 850mg Tablets",
            "batchNumber": "MF-5530-D",
            "expiryDate": datetime(2027, 10, 31, tzinfo=timezone.utc),
            "manufactureDate": datetime(2024, 10, 15, tzinfo=timezone.utc),
            "complaintType": ComplaintType.PACKAGING_ISSUE.value,
            "description": "Customer returned unopened 10-tablet blister card containing 2 completely empty and unsealed pockets.",
            "severity": Severity.MAJOR.value,
            "status": ComplaintStatus.OPEN.value,
            "source": ComplaintSource.MANUAL.value,
            "country": "United States",
            "aiSummary": "Empty blister pockets discovered in sealed Metformin 850mg packs (Batch MF-5530-D). Investigating blister feeding feeder jams and checkweigher sensitivity settings.",
            "rootCause": None,
            "documents": {
                "create": [
                    {
                        "filename": "empty_blister_photo_report.pdf",
                        "fileType": DocumentFileType.PDF.value,
                        "extractedText": "Visual inspection documentation: Blister strip exhibiting pockets 3 and 7 empty without tablet fill.",
                    }
                ]
            },
            "summary": {
                "create": {
                    "summaryText": "Complaint CMP-2026-0004 reports empty blister cavities in sealed Metformin 850mg packs from batch MF-5530-D. Quality engineering is evaluating feeder track sensors and the in-line optical tablet verification system on Blister Line #2. Investigation remains open pending maintenance audit."
                }
            },
            "capa": {
                "create": {
                    "actionType": CapaActionType.CORRECTIVE.value,
                    "recommendedAction": "Service blister feeder track vibrator and calibrate blister fill sensor sensitivity on Packaging Line #2. Audit checkweigher calibration logs.",
                    "actionOwner": "Sarah Jenkins (Equipment Engineer)",
                    "dueDate": datetime(2026, 4, 30, tzinfo=timezone.utc),
                    "capaStatus": CapaStatus.RECOMMENDED.value,
                }
            },
        },
        # 5. QualityDefect - Broken tablets (Duplicate of #1 for AI detection in Phase 6)
        {
            "complaintNumber": "CMP-2026-0005",
            "complainantName": "MetroHealth Retail Pharmacy",
            "email": "dispensary@metrohealth.net",
            "phone": "+1-555-013-3390",
            "productName": "Paracetamol 500mg Tablets",
            "batchNumber": "PT-4471-A",
            "expiryDate": datetime(2027, 12, 31, tzinfo=timezone.utc),
            "manufactureDate": datetime(2025, 1, 15, tzinfo=timezone.utc),
            "complaintType": ComplaintType.QUALITY_DEFECT.value,
            "description": "Patient brought back box of Paracetamol 500mg stating several broken tablets in blister strip upon opening carton.",
            "severity": Severity.MAJOR.value,
            "status": ComplaintStatus.OPEN.value,
            "source": ComplaintSource.MANUAL.value,
            "country": "United States",
            "aiSummary": "Broken Paracetamol 500mg tablets in batch PT-4471-A reported by patient at retail dispensary. Corresponds to identical batch issue in CMP-2026-0001.",
            "rootCause": None,
            "documents": {
                "create": [
                    {
                        "filename": "customer_return_receipt.txt",
                        "fileType": DocumentFileType.TXT.value,
                        "extractedText": "Retail return log: 1 unit returned due to broken tablets inside sealed aluminum blister foil.",
                    }
                ]
            },
            "summary": {
                "create": {
                    "summaryText": "Complaint CMP-2026-0005 records broken Paracetamol 500mg tablets from batch PT-4471-A reported by MetroHealth Pharmacy. This complaint shares the identical product batch as CMP-2026-0001, indicating a systemic tablet friability/tooling issue during that production run. Cross-referenced with active CAPA on Tableting Press #3."
                }
            },
        },
        # 6. DeliveryIssue - Short shipment
        {
            "complaintNumber": "CMP-2026-0006",
            "complainantName": "Nordic Health Wholesale",
            "email": "receiving@nordichealth.se",
            "phone": "+46-8-123-4567",
            "productName": "Omeprazole 20mg Capsules",
            "batchNumber": "OM-1190-E",
            "expiryDate": datetime(2027, 6, 30, tzinfo=timezone.utc),
            "manufactureDate": datetime(2024, 6, 1, tzinfo=timezone.utc),
            "complaintType": ComplaintType.DELIVERY_ISSUE.value,
            "description": "Consignment delivery received with 8 cases missing (short shipment) against bill of lading for Omeprazole 20mg Capsules.",
            "severity": Severity.MINOR.value,
            "status": ComplaintStatus.IN_PROGRESS.value,
            "source": ComplaintSource.MANUAL.value,
            "country": "Sweden",
            "aiSummary": "Short delivery shipment of 8 cases of Omeprazole 20mg Capsules (Batch OM-1190-E) reported by Nordic Health Wholesale. Carrier reconciliation underway.",
            "rootCause": "Warehouse pallet staging error during international dispatch loading.",
            "documents": {
                "create": [
                    {
                        "filename": "bill_of_lading_reconciliation.pdf",
                        "fileType": DocumentFileType.PDF.value,
                        "extractedText": "Shipping discrepancy: Manifest indicates 50 cases dispatched; Nordic receiving dock verified only 42 cases received.",
                    }
                ]
            },
            "summary": {
                "create": {
                    "summaryText": "Complaint CMP-2026-0006 concerns a short shipment discrepancy of 8 cases of Omeprazole 20mg Capsules (Batch OM-1190-E) received by Nordic Health Wholesale. Warehouse dispatch logs confirm a staging error at the central distribution center. Replacement shipment is in transit."
                }
            },
        },
    ]

    for data in complaints_data:
        complaint = await prisma.complaint.create(
            data=data,
            include={"documents": True, "capa": True, "summary": True},
        )
        logger.info(
            "✓ Inserted complaint [%s] - %s (%s, %s)",
            complaint.complaintNumber,
            complaint.productName,
            complaint.complaintType,
            complaint.severity,
        )

    logger.info("Successfully seeded all %d complaints.", len(complaints_data))


async def main() -> None:
    """Run the seed script lifecycle."""
    try:
        await prisma.connect()
        await clear_database()
        await seed_data()
    finally:
        if prisma.is_connected():
            await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
