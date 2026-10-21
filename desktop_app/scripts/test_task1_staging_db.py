import sys
import os

# Set UTF-8 stdout encoding for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import db_manager

def run_test():
    print("Initializing database...")
    db_manager.init_db()
    
    conn = db_manager.get_connection()
    cur = conn.cursor()

    # 1. Verify candidate welcome email columns
    cur.execute("PRAGMA table_info(candidates)")
    cols = {r[1] for r in cur.fetchall()}
    assert "welcome_email_sent" in cols, "welcome_email_sent column missing"
    assert "welcome_email_sent_at" in cols, "welcome_email_sent_at column missing"
    print("✓ Welcome email tracking columns verified on candidates table.")

    # 2. Verify document_staging table
    cur.execute("PRAGMA table_info(document_staging)")
    staging_cols = {r[1] for r in cur.fetchall()}
    expected_staging = {
        "id", "candidate_id", "document_type", "status", "doc_file_path", 
        "pdf_file_path", "preferred_format", "recipient_email", "recipient_name", 
        "email_subject", "email_body", "created_at", "updated_at"
    }
    assert expected_staging.issubset(staging_cols), f"Missing staging cols: {expected_staging - staging_cols}"
    print("✓ document_staging table schema verified.")

    # Ensure a test candidate exists for staging foreign key
    cur.execute("SELECT id FROM candidates WHERE id = 1")
    if not cur.fetchone():
        cur.execute("""
            INSERT OR IGNORE INTO candidates (id, candidate_name, mobile, applied_designation, status)
            VALUES (1, 'Test Candidate', '9000000001', 'Software Engineer', 'Applied')
        """)
        conn.commit()

    # 3. Test Staging CRUD
    staging_id = db_manager.create_staging_record(
        candidate_id=1,
        document_type="offer_letter",
        status="Staged",
        doc_file_path="output/test.docx",
        pdf_file_path=None,
        preferred_format="pdf",
        recipient_email="test@example.com",
        recipient_name="Test Candidate",
        email_subject="Offer Letter",
        email_body="Congratulations",
        extra_fields={"salary": "50000"},
        discrepancy_warnings=["Missing PAN"]
    )
    assert staging_id > 0, "Failed to create staging record"
    print(f"✓ Created staging record with ID: {staging_id}")
    
    record = db_manager.get_staging_record_by_id(staging_id)
    assert record is not None
    assert record["recipient_name"] == "Test Candidate"
    assert record["status"] == "Staged"
    assert record["extra_fields"] == {"salary": "50000"}
    assert record["discrepancy_warnings"] == ["Missing PAN"]
    print("✓ get_staging_record_by_id verified.")
    
    # Test query by status
    staged_list = db_manager.get_staging_records(status="Staged")
    assert any(s["id"] == staging_id for s in staged_list), "Record not found in get_staging_records"
    print("✓ get_staging_records verified.")

    # 4. Test update
    db_manager.update_staging_record(staging_id, preferred_format="docx", status="Approved")
    updated = db_manager.get_staging_record_by_id(staging_id)
    assert updated["preferred_format"] == "docx"
    assert updated["status"] == "Approved"
    print("✓ update_staging_record verified.")

    # 5. Test staging counts
    counts = db_manager.get_dashboard_staging_counts()
    assert "total" in counts
    assert counts.get("total", 0) > 0
    print(f"✓ get_dashboard_staging_counts verified: {counts}")

    # 6. Test candidate welcome email status
    db_manager.update_candidate_welcome_email_status(1, sent=True)
    cur.execute("SELECT welcome_email_sent, welcome_email_sent_at FROM candidates WHERE id = 1")
    c_row = cur.fetchone()
    assert c_row[0] == 1
    assert c_row[1] is not None

    db_manager.update_candidate_welcome_email_status(1, sent=False)
    cur.execute("SELECT welcome_email_sent, welcome_email_sent_at FROM candidates WHERE id = 1")
    c_row = cur.fetchone()
    assert c_row[0] == 0
    print("✓ update_candidate_welcome_email_status verified.")

    # 7. Test get_selected_candidates_pending_welcome
    cur.execute("UPDATE candidates SET status = 'Selected', welcome_email_sent = 0 WHERE id = 1")
    conn.commit()
    pending = db_manager.get_selected_candidates_pending_welcome()
    assert any(p["id"] == 1 for p in pending), "Candidate 1 not found in pending welcome list"
    
    # Mark sent and ensure it no longer appears in pending
    db_manager.update_candidate_welcome_email_status(1, sent=True)
    pending_after = db_manager.get_selected_candidates_pending_welcome()
    assert not any(p["id"] == 1 for p in pending_after), "Candidate 1 should not appear in pending after sent=True"
    print("✓ get_selected_candidates_pending_welcome verified.")

    # Reset candidate 1 status back to Applied
    cur.execute("UPDATE candidates SET status = 'Applied', welcome_email_sent = 0, welcome_email_sent_at = NULL WHERE id = 1")
    conn.commit()

    # 8. Cleanup test record
    deleted = db_manager.delete_staging_record(staging_id)
    assert deleted is True, "delete_staging_record returned False"
    assert db_manager.get_staging_record_by_id(staging_id) is None
    print("✓ delete_staging_record verified.")
    
    print("\nSUCCESS: Task 1 Database Migration verified successfully.")

if __name__ == "__main__":
    run_test()
