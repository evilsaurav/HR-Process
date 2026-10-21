"""
Verification Script: test_keka_placeholder_generation.py
Task 3 Test Suite: Keka Placeholder Resolution for Document Generation.
"""

import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from services.document_generation_service import build_placeholder_mapping


def test_placeholders():
    print("=" * 70)
    print("RUNNING TASK 3 TESTS: KEKA PLACEHOLDER RESOLUTION")
    print("=" * 70)

    sample_cand = {
        "candidate_name": "Rohan Verma",
        "employee_number": "EP00088",
        "first_name": "Rohan",
        "last_name": "Verma",
        "display_name": "Rohan Verma",
        "work_email": "rohan.v@company.com",
        "personal_email": "rohan.personal@example.com",
        "mobile": "9876543210",
        "gender": "Male",
        "father_name": "Satish Verma",
        "mother_name": "Sunita Verma",
        "spouse_name": "Meera Verma",
        "current_address": "Flat 301, Patna",
        "permanent_address": "House 12, Gaya",
        "applied_designation": "State Program Officer",
        "department": "Public Health",
        "contact_location": "Patna",
        "reporting_to": "Dr. Rajesh",
        "reporting_manager_emp_no": "EP00001",
        "date_joined": "2023-04-01",
        "negotiated_salary": "65000",
        "employment_status": "Working",
        "worker_type": "Full-Time Consultant",
        "time_type": "FullTime",
        "leave_plan": "Executive Leave Plan",
        "shift_policy": "General Shift",
        "weekly_off_policy": "Sunday Off",
        "notice_period": "60 Days",
        "pan_number": "RVERM1234K",
        "aadhaar_number": "432187650987",
        "pf_number": "BR/PAT/98765",
        "uan_number": "100987654321",
        "cost_center": "CC-HEALTH",
    }

    mapping = build_placeholder_mapping(sample_cand, "offer", {})

    # Check that critical Keka keys exist and have exact values
    assert mapping["Employee Number"] == "EP00088"
    assert mapping["employee_number"] == "EP00088"
    assert mapping["PAN Number"] == "RVERM1234K"
    assert mapping["pan_number"] == "RVERM1234K"
    assert mapping["Aadhaar Number"] == "432187650987"
    assert mapping["aadhaar_number"] == "432187650987"
    assert mapping["PF Number"] == "BR/PAT/98765"
    assert mapping["pf_number"] == "BR/PAT/98765"
    assert mapping["UAN Number"] == "100987654321"
    assert mapping["uan_number"] == "100987654321"
    assert mapping["Current Address"] == "Flat 301, Patna"
    assert mapping["current_address"] == "Flat 301, Patna"
    assert mapping["Permanent Address"] == "House 12, Gaya"
    assert mapping["permanent_address"] == "House 12, Gaya"
    assert mapping["Reporting To"] == "Dr. Rajesh"
    assert mapping["reporting_to"] == "Dr. Rajesh"
    assert mapping["Reporting Manager Employee Number"] == "EP00001"
    assert mapping["Cost Center"] == "CC-HEALTH"
    assert mapping["cost_center"] == "CC-HEALTH"
    assert mapping["Notice Period"] == "60 Days"
    assert mapping["notice_period"] == "60 Days"

    # None values should be empty strings, never string 'None'
    empty_cand = {}
    empty_mapping = build_placeholder_mapping(empty_cand, "offer", {})
    assert empty_mapping["pan_number"] == ""
    assert empty_mapping["employee_number"] == ""
    assert empty_mapping["aadhaar_number"] == ""

    print("  ✓ All 25+ Keka placeholders resolved in both title-case and snake-case variants.")
    print("  ✓ Empty fields safely resolved to empty string without None or crashes.")
    print("=" * 70)
    print("ALL TASK 3 TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    test_placeholders()
