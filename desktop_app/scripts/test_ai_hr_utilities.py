"""
Verification Script: test_ai_hr_utilities.py
Task 4 Test Suite: AI Anomaly Detector & Email Cover Drafter.
"""

import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from services.ai_service import audit_candidate_data_completeness, generate_email_cover


def test_ai_utilities():
    print("=" * 70)
    print("RUNNING TASK 4 TESTS: AI ANOMALY AUDITOR & COVER DRAFTER")
    print("=" * 70)

    # 1. Test Incomplete Candidate
    incomplete_cand = {
        "candidate_name": "Test Missing Data",
        "email": "invalid_email_at_nowhere",
        "mobile": "123",
    }
    warnings = audit_candidate_data_completeness(incomplete_cand, "offer")
    assert any("does not appear to be in a valid format" in w for w in warnings), "Email format check failed"
    assert any("less than 10 digits" in w for w in warnings), "Mobile check failed"
    assert any("Designation" in w for w in warnings), "Designation check failed"
    print("  ✓ Anomaly auditor successfully caught invalid email, short phone, and missing role.")

    # 2. Test Complete Candidate
    complete_cand = {
        "candidate_name": "Ananya Sharma",
        "work_email": "ananya.sharma@dfy.org",
        "mobile": "9811122233",
        "applied_designation": "Medical Officer",
        "department": "Maternal & Child Health",
        "contact_location": "Patna",
        "negotiated_salary": "70000",
        "full_address": "Flat 4B, Bailey Road, Patna",
        "pan_number": "ANANY1234Z",
        "aadhaar_number": "123412341234",
    }
    warnings_clean = audit_candidate_data_completeness(complete_cand, "offer")
    assert len(warnings_clean) == 0, f"Expected 0 warnings for complete candidate, got: {warnings_clean}"
    print("  ✓ Complete candidate passed audit with 0 warnings.")

    # 3. Test Email Cover Drafter for Offer Letter
    offer_mail = generate_email_cover(complete_cand, "offer")
    assert "Offer Letter: Medical Officer" in offer_mail["subject"]
    assert "Dear Ananya Sharma" in offer_mail["body"]
    assert "Doctors For You" in offer_mail["body"]
    print("  ✓ Offer letter email subject and body drafted with personalized details.")

    # 4. Test Email Cover Drafter for Extension Letter
    ext_mail = generate_email_cover(complete_cand, "extension", extra_notes="Reporting date remains unchanged.")
    assert "Extension" in ext_mail["subject"]
    assert "Reporting date remains unchanged." in ext_mail["body"]
    print("  ✓ Extension letter email subject and body drafted with custom notes.")

    print("=" * 70)
    print("ALL TASK 4 TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    test_ai_utilities()
