"""
Unit Test: test_utility_services.py
Verifies the 3 new Operational Utility Services:
1. Executive HR Daily Summary Exporter (Excel workbook with executive overview & action items).
2. Bulk Document ZIP Packager (for Accounts & Audit handover).
3. Candidate Outreach WhatsApp / SMS Text Generator & Interview Bio-Data Slip.
"""

import os
import sys
import zipfile
import tempfile

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from services import hr_report_exporter
from services import zip_export_service
from services import candidate_outreach_service


def run_tests():
    print("=" * 70)
    print("RUNNING TASK 3 TESTS: OPERATIONAL UTILITY SERVICES")
    print("=" * 70)

    # 1. Test Executive HR Daily Summary Exporter
    print("\n[TEST 1] Testing Executive Daily Summary Excel Exporter...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = os.path.join(tmp_dir, "test_summary.xlsx")
        out = hr_report_exporter.export_daily_executive_summary(report_path)

        assert os.path.exists(out), f"Report not created at {out}"
        assert os.path.getsize(out) > 1000, "Report file is suspiciously small"
        print(f"  ✓ Executive Summary generated at: {os.path.basename(out)} ({os.path.getsize(out)} bytes)")

    # 2. Test Bulk Document ZIP Packager
    print("\n[TEST 2] Testing Bulk Document ZIP Packager...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create 2 dummy files to zip
        f1 = os.path.join(tmp_dir, "Offer_Aarav.pdf")
        f2 = os.path.join(tmp_dir, "Offer_Meera.pdf")
        with open(f1, "w") as fp:
            fp.write("Dummy PDF 1")
        with open(f2, "w") as fp:
            fp.write("Dummy PDF 2")

        zip_out = os.path.join(tmp_dir, "DFY_Audit_Letters.zip")
        ok, res_path, err = zip_export_service.create_bulk_document_zip([f1, f2], target_zip_path=zip_out)

        assert ok is True, f"ZIP packaging failed: {err}"
        assert os.path.exists(res_path), f"ZIP file not found at {res_path}"
        with zipfile.ZipFile(res_path, "r") as zf:
            namelist = zf.namelist()
            assert "Offer_Aarav.pdf" in namelist
            assert "Offer_Meera.pdf" in namelist
            assert len(namelist) == 2
        print(f"  ✓ ZIP file successfully packaged {len(namelist)} documents into {os.path.basename(res_path)}")

    # 3. Test Candidate Outreach WhatsApp Text & Bio-Data Slip
    print("\n[TEST 3] Testing WhatsApp Candidate Message Drafter & Bio-Data Slip...")
    mock_candidate = {
        "candidate_name": "Rohan Verma",
        "mobile": "9876543210",
        "email": "rohan.verma@example.com",
        "applied_designation": "Field Coordinator",
        "contact_location": "Patna, Bihar",
        "negotiated_salary": "22000",
        "highest_education": "MSW (Master of Social Work)",
        "total_experience": "2.5",
        "date_joined": "2026-11-01",
        "department": "PPSA Bihar",
    }

    # Selection Message
    msg_sel = candidate_outreach_service.generate_whatsapp_outreach_text(mock_candidate, message_type="selection")
    assert "Rohan Verma" in msg_sel
    assert "Field Coordinator" in msg_sel
    assert "Patna, Bihar" in msg_sel
    assert "Doctors For You" in msg_sel
    print("  ✓ WhatsApp Selection text generated:")
    print("    " + msg_sel.replace("\n", "\n    "))

    # Interview Reminder Message
    msg_int = candidate_outreach_service.generate_whatsapp_outreach_text(mock_candidate, message_type="interview")
    assert "interview" in msg_int.lower()
    print("  ✓ WhatsApp Interview text generated.")

    # Candidate Bio-Data Slip
    slip = candidate_outreach_service.generate_candidate_bio_data_slip(mock_candidate)
    assert "Rohan Verma" in slip
    assert "MSW" in slip
    assert "₹22,000" in slip or "22000" in slip
    print("  ✓ Candidate Bio-Data Slip generated.")

    print("\n" + "=" * 70)
    print("ALL TASK 3 TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
