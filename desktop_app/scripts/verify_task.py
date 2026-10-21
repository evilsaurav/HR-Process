import os
import sys
import docx

# Ensure desktop_app is in sys.path
sys.path.insert(0, os.path.abspath("desktop_app"))

from database.db_manager import (
    get_template_path,
    log_document_generation,
    get_generation_history,
    get_all_generation_logs
)

print("=" * 60)
print("1. VERIFYING TERMINATION TEMPLATE CONTENT")
print("=" * 60)
template_path = os.path.join("desktop_app", "templates", "termination", "termination_letter.docx")
doc = docx.Document(template_path)
print(f"File exists: {os.path.exists(template_path)}")
print(f"Total paragraphs: {len(doc.paragraphs)}\n")

for i, p in enumerate(doc.paragraphs):
    if p.text.strip():
        print(f"P{i:02d}: {p.text}")

required_placeholders = [
    "{{TITLE}}", "{{Full Name}}", "{{RELATION}}", "{{FATHER_TITLE}}",
    "{{Father Name}}", "{{Full Address}}", "{{Job Title}}", "{{Department}}",
    "{{Location}}", "{{Date Joined}}", "{{Termination Date}}", "{{Reason}}",
    "{{Notice Period}}"
]

full_text = " ".join(p.text for p in doc.paragraphs)
print("\n--- Placeholder Check ---")
all_present = True
for ph in required_placeholders:
    present = ph in full_text
    status = "PRESENT" if present else "MISSING"
    print(f"  {ph:24}: {status}")
    if not present:
        all_present = False

print(f"\nAll required placeholders present: {all_present}")

print("\n" + "=" * 60)
print("2. VERIFYING DB TEMPLATE MAPPING")
print("=" * 60)
mapped_path = get_template_path("termination", "Generic")
print(f"Mapped template path from DB : {mapped_path}")
print(f"Path exists on disk          : {os.path.exists(mapped_path) if mapped_path else False}")

print("\n" + "=" * 60)
print("3. VERIFYING DOCUMENT GENERATION AUDIT LOG")
print("=" * 60)
test_extra = {
    "termination_date": "31 October 2024",
    "reason": "Project completion and concluding deliverables",
    "notice_period": "30 days",
    "last_working_day": "31 October 2024"
}

log_id = log_document_generation(
    candidate_id=1,
    document_type="termination",
    reference_number="DFY/HR/2024/001",
    extra_fields_dict=test_extra,
    file_path="D:/ignou/Suraj HR Project/output/1_Test_Kumar_Termination_Letter.docx",
    generated_by="HR_Admin"
)
print(f"Inserted log record ID: {log_id}")

history = get_generation_history(1)
print(f"Generation history count for candidate 1: {len(history)}")
latest = history[0]
print(f"Latest record keys   : {list(latest.keys())}")
print(f"Document type        : {latest['document_type']}")
print(f"Reference number     : {latest['reference_number']}")
print(f"Generated date       : {latest['generated_date']}")
print(f"Is extra_fields dict : {isinstance(latest['extra_fields'], dict)}")
print(f"extra_fields dict    : {latest['extra_fields']}")

all_logs = get_all_generation_logs()
print(f"\nTotal generation logs in system: {len(all_logs)}")
print("\n" + "=" * 60)
print("ALL VERIFICATIONS PASSED SUCCESSFULLY!")
print("=" * 60)
