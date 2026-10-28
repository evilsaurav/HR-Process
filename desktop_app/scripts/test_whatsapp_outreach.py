"""
Test Script: test_whatsapp_outreach.py
Verifies:
1. Indian Mobile Number Sanitization for WhatsApp (10-digit Indian standard)
2. WhatsApp Message Generation for Document Release, Selection, Interview, Joining
3. WhatsApp Web URL generation and URL-encoding
4. Integration imports with UI pages
"""

import os
import sys
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from services import candidate_outreach_service


def test_clean_indian_mobile():
    print("Testing clean_indian_mobile...")

    cases = [
        ("+91 98765 43210", "919876543210"),
        ("09876543210", "919876543210"),
        ("9876543210", "919876543210"),
        ("91-98765-43210", "919876543210"),
        ("+91-8123456789", "918123456789"),
        ("7000112233", "917000112233"),
        ("6200112233", "916200112233"),
        ("919876543210", "919876543210"),
        ("", None),
        (None, None),
        ("12345", None),
        ("abcdefghij", None),
    ]

    for raw, expected in cases:
        got = candidate_outreach_service.clean_indian_mobile(raw)
        assert got == expected, f"Failed for '{raw}': got '{got}', expected '{expected}'"
        print(f"  ✓ '{raw}' -> '{got}'")

    print("All mobile cleaning tests passed! ✅\n")


def test_whatsapp_messages():
    print("Testing WhatsApp message templates...")

    candidate = {
        "candidate_name": "Dr. Rohit Sharma",
        "applied_designation": "Medical Officer",
        "contact_location": "Guwahati, Assam",
        "email": "rohit.sharma@example.com",
        "date_joined": "2026-11-01",
    }

    # 1. Document Release
    doc_text = candidate_outreach_service.generate_whatsapp_outreach_text(
        candidate=candidate,
        message_type="document_release",
        document_type="offer",
        reference_number="DFY/OFFER/2026/1042"
    )
    assert "Dr. Rohit Sharma" in doc_text
    assert "Offer Letter" in doc_text
    assert "DFY/OFFER/2026/1042" in doc_text
    assert "Doctors For You" in doc_text
    print("  ✓ Document Release template verified.")

    # 2. Selection
    sel_text = candidate_outreach_service.generate_whatsapp_outreach_text(
        candidate=candidate,
        message_type="selection"
    )
    assert "Dr. Rohit Sharma" in sel_text
    assert "Medical Officer" in sel_text
    assert "Guwahati, Assam" in sel_text
    print("  ✓ Selection template verified.")

    # 3. Joining
    join_text = candidate_outreach_service.generate_whatsapp_outreach_text(
        candidate=candidate,
        message_type="joining"
    )
    assert "Dr. Rohit Sharma" in join_text
    assert "2026-11-01" in join_text
    assert "PAN Card, Aadhaar Card" in join_text
    print("  ✓ Joining template verified.")

    # 4. Interview
    int_text = candidate_outreach_service.generate_whatsapp_outreach_text(
        candidate=candidate,
        message_type="interview"
    )
    assert "Dr. Rohit Sharma" in int_text
    assert "interview schedule" in int_text
    print("  ✓ Interview template verified.\n")


def test_url_construction():
    print("Testing WhatsApp Web URL construction...")

    clean_mobile = "919876543210"
    message = "Namaste Test Candidate!\nOffer Letter Released: DFY/OFFER/101"
    url = candidate_outreach_service.build_whatsapp_web_url(clean_mobile, message)

    assert url.startswith("https://wa.me/919876543210?text=")
    decoded_params = urllib.parse.unquote(url.split("?text=")[1])
    assert decoded_params == message
    print(f"  ✓ URL: {url[:60]}... verified.")
    print("All URL construction tests passed! ✅\n")


def test_module_imports():
    print("Testing UI module imports...")
    import utils.whatsapp_modal
    import pages.joining_process_page
    import pages.document_generation_page
    print("  ✓ utils.whatsapp_modal imported successfully.")
    print("  ✓ pages.joining_process_page imported successfully.")
    print("  ✓ pages.document_generation_page imported successfully.")
    print("All module imports passed! ✅\n")


if __name__ == "__main__":
    test_clean_indian_mobile()
    test_whatsapp_messages()
    test_url_construction()
    test_module_imports()
    print("=" * 60)
    print("ALL WHATSAPP OUTREACH TESTS PASSED 100%! 🎉")
    print("=" * 60)
