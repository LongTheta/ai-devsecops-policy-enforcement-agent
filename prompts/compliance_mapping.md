# Compliance Mapping Prompt

Use this prompt when mapping findings to control families (engineering review only).

## Instructions

Map each finding to **broad** NIST-style control families. Use only these families:

- **AC** – Access Control
- **AU** – Audit and Accountability
- **CM** – Configuration Management
- **IA** – Identification and Authentication
- **IR** – Incident Response
- **RA** – Risk Assessment
- **SA** – System and Services Acquisition
- **SC** – System and Communications Protection
- **SI** – System and Information Integrity

Provide a short rationale for each mapping. Do **not** claim formal compliance. State clearly:

"These mappings support engineering review and are not formal compliance determinations."

## Input

- Finding (id, title, category, description)
- Optional: compliance_mode (e.g. fedramp-moderate)

## Output

- control_family, rationale, note (disclaimer).
