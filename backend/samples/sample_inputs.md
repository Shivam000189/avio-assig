# Sample Complaint Inputs for AI Pipeline Testing & Demos

These standardized test cases evaluate extraction fidelity, completeness checking, severity risk scoring, CAPA formulation, and root-cause hypothesis generation across various pharmaceutical incident types.

---

## Phase 5 Document Upload Samples Matrix (`backend/samples/files/`)

| File Name | Format | Incident Type / Category | Expected Severity | Completeness Check Flags | Key Nodes in Pipeline |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `complaint_tablet_chipping.pdf` | Text PDF (Generated) | Physical friability & crumbling tablets (`QualityDefect`) | **Major** (15d SLA) | `is_complete: true`<br/>`missing_fields: []` | **Risk Assess** (physical defect), **CAPA** (compression tooling audit), **Root Cause** (binder/granulation) |
| `complaint_wrong_expiry.pdf` | Text PDF (Generated) | Secondary carton date mismatch (`LabelingIssue`) | **Minor** (30d SLA) | `is_complete: true`<br/>`missing_fields: []` | **Risk Assess** (no health risk), **CAPA** (cartoner vision inspection verify) |
| `complaint_adverse_event.eml` | RFC-822 MIME Email | Pediatric acute reaction + particulate (`AdverseEvent`) | **Critical** (3d SLA) | `is_complete: true`<br/>`missing_fields: []` | **Parser** (header extraction), **Risk Assess** (severe harm), **CAPA** (reconstitution line hold / quarantine) |
| `complaint_missing_batch.txt` | Raw Plain Text | Discolored tablets & pungent odor missing batch & email | **Major** | `is_complete: false`<br/>`missing_fields: ["batchNumber", "email"]` | **Completeness** (flags missing batch & email), **Summarize** (highlights info gap) |
| `complaint_duplicate_chipping.txt` | Raw Plain Text | Second pharmacy report for batch `PT-4471-A` | **Major** | `is_complete: true`<br/>`missing_fields: []` | **Duplicate Detection (Phase 6)** & batch clustering |

---

## Sample 1: Clean & Complete Hospital Intake (Expected: Major)
**Intake Channel**: Email / Manual  
**Expected Category**: `QualityDefect`  
**Expected Severity**: `Major` (SLA: 15 Days)  
**Expected Completeness**: `is_complete: true`

```text
From: Dr. Marcus Vance <m.vance@stjude-hospital.org>
To: Quality Assurance <complaints@pharmamanufacturer.com>
Date: Mon, 16 Mar 2026 09:15:00 -0500
Subject: Quality Complaint: Friable and Chipped Paracetamol 500mg Tablets

Dear QA Team,

During routine inpatient unit-dose dispensing this morning at St. Jude Hospital Pharmacy, our clinical pharmacy staff identified a recurring defect with Paracetamol 500mg Tablets (Batch Number: PT-4471-A, Expiry Date: 2027-12-31). 

Multiple blister cards exhibited crumbling and chipped edges across approximately 15% of the sampled blister pockets. There is no evidence of patient administration or adverse clinical reaction; however, the friability prevents accurate unit-dose administration. We have quarantined 240 unopened boxes from this batch.

Please initiate an investigation and provide Return Material Authorization (RMA) instructions.

Sincerely,
Dr. Marcus Vance, PharmD
Director of Inpatient Pharmacy Services
St. Jude Hospital Pharmacy, Boston, MA, United States
Phone: +1-555-019-2831
```

---

## Sample 2: Messy & Incomplete Patient Report (Expected: Major, Incomplete)
**Intake Channel**: Manual / Phone Transcription  
**Expected Category**: `PackagingIssue`  
**Expected Severity**: `Major`  
**Expected Completeness**: `is_complete: false` (`missing_fields`: `["batchNumber"]`)

```text
transcription of voicemail received on patient support hotline:
hi my name is Eleanor Rigby and i am calling because i just opened a new box of Metformin 850mg tablets that i picked up yesterday from my local drugstore in Chicago. when i pushed the foil on the blister pack two of the pockets were completely empty with no pill inside even though the foil seal was intact! i really need my daily medication and i want to know if the rest of the pills in the box are safe to take. you can reach me at 555-014-9922. i threw the outer box away so i don't have the batch number stamped on the cardboard anymore, please call me back as soon as possible.
```

---

## Sample 3: Critical Adverse Event with Clinical Harm (Expected: Critical)
**Intake Channel**: Email / Urgent Pharmacovigilance  
**Expected Category**: `AdverseEvent`  
**Expected Severity**: `Critical` (SLA: 3 Days)  
**Expected Completeness**: `is_complete: true`

```text
URGENT SAFETY NOTIFICATION: Clinical Adverse Reaction Report
Reporter: Dr. Sarah Lin, MD (Attending Physician, Oakridge Emergency Clinic)
Email: s.lin@oakridge-health.org
Phone: +1-555-018-7744
Country: United States

Patient Identifier: PT-9021
Product Administered: Amoxicillin 250mg Capsules
Batch Number: AX-2209-B
Expiry Date: 2027-08-30

Description of Incident:
A 34-year-old female patient presented to the emergency department approximately 45 minutes following oral ingestion of the first dose of Amoxicillin 250mg Capsules (Batch: AX-2209-B). Patient had no documented prior history of penicillin allergy. The patient developed acute cutaneous erythema, facial angioedema, respiratory wheezing (stridor), and profound hypotension (BP 82/50 mmHg).

Emergency intervention required immediate intramuscular epinephrine (0.3mg), IV methylprednisolone, and continuous oxygen therapy. Patient was stabilized in the acute trauma bay and subsequently admitted to the intensive care unit for 24-hour hemodynamic monitoring. Retention sample blister strip was secured from the patient's family for analytical testing.

Immediate QA and Pharmacovigilance escalation requested.
```

---

## Sample 4: Minor Labeling / Offset Printing Discrepancy (Expected: Minor)
**Intake Channel**: Manual / Warehouse Log  
**Expected Category**: `LabelingIssue`  
**Expected Severity**: `Minor` (SLA: 30 Days)  
**Expected Completeness**: `is_complete: true`

```text
Warehouse Receiving Discrepancy Log #WH-8812
Logged by: Arthur Pendelton (Apex Logistics Distribution Center, London, UK)
Email: inbound-qa@apexlogistics.co.uk | Phone: +44-20-7946-0192

Product Name: Cetirizine 10mg Tablets
Batch Number: CZ-8812-C
Manufacture Date: 2025-05-01
Expiry Date: 2028-05-31

Incident Details:
During inbound inspection of 50 shippers of Cetirizine 10mg Tablets (Batch CZ-8812-C), QA receiving staff noted that the primary blister foil is correctly stamped with expiry date 'EXP 05/2028', but the secondary carton displays an inkjet date code of 'EXP 05/2026' due to a printer offset glitch during carton packing. The blister seals, tablet appearance, and inner leaf leaflets are all intact and compliant. 

Stock has been placed in quarantine area Q-4 pending re-coding or disposition instructions.
```
