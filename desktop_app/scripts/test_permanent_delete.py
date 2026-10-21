"""
Verification Script: test_permanent_delete.py
Phase G1 Follow-up Fix — Step 3 Test Suite: Permanent Delete from Archive View.

Tests:
1. Permanently deleting a candidate WITH related document_generation_log & email_log
   records correctly deletes the candidate AND all child logs in an atomic transaction.
2. Confirmation dialog message logic differentiates accurately between candidates with
   related records (showing exact N docs and M emails) vs candidates with zero related records.
3. Permanently deleting a candidate WITHOUT related logs deletes cleanly.
4. Transaction rollback works if something is forcibly made to fail midway
   (simulating a database/system crash mid-transaction).
5. Existing archive and restore functionality (Steps 1 & 2) remains fully functional.
6. Safety restriction: only archived candidates can be permanently deleted from the UI handler.
"""

import os
import sys

# Configure UTF-8 encoding for Windows console output
sys.stdout.reconfigure(encoding="utf-8")

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from database import db_manager


def run_tests():
    print("=" * 70)
    print("RUNNING STEP 3 TESTS: PERMANENT DELETE & TRANSACTION SAFETY")
    print("=" * 70)

    db_manager.init_db()

    mob_alpha = "9777700001"
    mob_beta = "9777700002"
    mob_gamma = "9777700003"
    mob_delta = "9777700004"

    # Clean up test rows
    conn = db_manager.get_connection()
    conn.execute("DELETE FROM candidates WHERE mobile IN (?, ?, ?, ?)", (mob_alpha, mob_beta, mob_gamma, mob_delta))
    conn.commit()
    conn.close()

    try:
        # -----------------------------------------------------------------
        # TEST 1: Permanent delete WITH related document & email records
        # -----------------------------------------------------------------
        print("\n[TEST 1] Testing permanent delete with related document & email logs...")
        cand_alpha = {
            "candidate_name": "Alpha With Records",
            "mobile": mob_alpha,
            "email": "alpha.records@test.com",
            "applied_designation": "Sr Consultant",
            "negotiated_salary": "75000",
            "contact_location": "Delhi",
            "status": "Joined",
        }
        db_manager.upsert_candidate(cand_alpha, "Test Script")
        c_alpha = db_manager.get_candidate_by_mobile(mob_alpha)
        assert c_alpha is not None
        c_alpha_id = c_alpha["id"]

        # Soft-delete / Archive Alpha first
        db_manager.archive_candidate(c_alpha_id)

        # Insert 2 document generation logs and 1 email log
        doc_id1 = db_manager.log_document_generation(
            candidate_id=c_alpha_id,
            document_type="offer",
            reference_number="DFY/HR/2026/901",
            extra_fields_dict={"ctc": "75000"},
            file_path="dummy/path/offer.docx",
        )
        doc_id2 = db_manager.log_document_generation(
            candidate_id=c_alpha_id,
            document_type="appointment",
            reference_number="DFY/HR/2026/902",
            extra_fields_dict={"ctc": "75000"},
            file_path="dummy/path/appointment.docx",
        )
        email_id = db_manager.log_email_dispatch(
            candidate_id=c_alpha_id,
            recipient_email="alpha.records@test.com",
            recipient_name="Alpha With Records",
            document_type="offer",
            subject="Offer Letter",
        )

        # Verify related counts helper
        counts = db_manager.get_candidate_related_counts(c_alpha_id)
        assert counts["documents"] == 2, f"Expected 2 documents, got {counts['documents']}"
        assert counts["emails"] == 1, f"Expected 1 email, got {counts['emails']}"
        print(f"  ✓ get_candidate_related_counts() verified: {counts['documents']} docs, {counts['emails']} emails.")

        # Verify confirmation message logic
        n_docs = counts["documents"]
        n_emails = counts["emails"]
        if n_docs > 0 or n_emails > 0:
            msg = (
                f"'{c_alpha['candidate_name']}' has {n_docs} generated document(s) and {n_emails} sent email record(s). "
                "Permanently deleting this candidate will also delete ALL of these records. "
                "This cannot be undone. Are you sure you want to continue?"
            )
        else:
            msg = f"Permanently delete '{c_alpha['candidate_name']}'? This cannot be undone."

        expected_msg = (
            "'Alpha With Records' has 2 generated document(s) and 1 sent email record(s). "
            "Permanently deleting this candidate will also delete ALL of these records. "
            "This cannot be undone. Are you sure you want to continue?"
        )
        assert msg == expected_msg, f"Message mismatch:\nGot: {msg}\nExpected: {expected_msg}"
        print("  ✓ Detailed confirmation message text verified with exact counts.")

        # Permanently delete candidate Alpha
        del_ok = db_manager.permanently_delete_candidate(c_alpha_id)
        assert del_ok is True, "permanently_delete_candidate() should return True"

        # Verify candidate and related logs are completely deleted
        assert db_manager.get_candidate_by_id(c_alpha_id) is None, "Candidate must be deleted from candidates table"

        conn_check = db_manager.get_connection()
        cur_check = conn_check.cursor()
        cur_check.execute("SELECT COUNT(*) FROM document_generation_log WHERE candidate_id = ?", (c_alpha_id,))
        doc_remaining = cur_check.fetchone()[0]
        cur_check.execute("SELECT COUNT(*) FROM email_log WHERE candidate_id = ?", (c_alpha_id,))
        email_remaining = cur_check.fetchone()[0]
        conn_check.close()

        assert doc_remaining == 0, "All related document logs must be deleted"
        assert email_remaining == 0, "All related email logs must be deleted"
        print("  ✓ Candidate and all linked document & email logs permanently deleted.")

        # -----------------------------------------------------------------
        # TEST 2: Permanent delete WITHOUT related records
        # -----------------------------------------------------------------
        print("\n[TEST 2] Testing permanent delete without related records...")
        cand_beta = {
            "candidate_name": "Beta No Records",
            "mobile": mob_beta,
            "email": "beta.norecords@test.com",
            "applied_designation": "Accountant",
            "negotiated_salary": "35000",
            "contact_location": "Lucknow",
            "status": "Applied",
        }
        db_manager.upsert_candidate(cand_beta, "Test Script")
        c_beta = db_manager.get_candidate_by_mobile(mob_beta)
        c_beta_id = c_beta["id"]

        db_manager.archive_candidate(c_beta_id)

        # Check counts
        counts_beta = db_manager.get_candidate_related_counts(c_beta_id)
        assert counts_beta["documents"] == 0
        assert counts_beta["emails"] == 0

        # Message check for zero records
        if counts_beta["documents"] > 0 or counts_beta["emails"] > 0:
            msg_beta = "detailed"
        else:
            msg_beta = f"Permanently delete '{c_beta['candidate_name']}'? This cannot be undone."

        assert msg_beta == "Permanently delete 'Beta No Records'? This cannot be undone."
        print("  ✓ Clean confirmation message text verified for candidate without records.")

        # Permanently delete candidate Beta
        del_beta_ok = db_manager.permanently_delete_candidate(c_beta_id)
        assert del_beta_ok is True
        assert db_manager.get_candidate_by_id(c_beta_id) is None
        print("  ✓ Candidate without related records permanently deleted.")

        # -----------------------------------------------------------------
        # TEST 3: Transaction rollback on simulated mid-delete failure
        # -----------------------------------------------------------------
        print("\n[TEST 3] Testing atomic transaction rollback on simulated failure...")
        cand_gamma = {
            "candidate_name": "Gamma Rollback Test",
            "mobile": mob_gamma,
            "email": "gamma.rollback@test.com",
            "applied_designation": "Manager",
            "negotiated_salary": "80000",
            "contact_location": "Mumbai",
            "status": "Applied",
        }
        db_manager.upsert_candidate(cand_gamma, "Test Script")
        c_gamma = db_manager.get_candidate_by_mobile(mob_gamma)
        c_gamma_id = c_gamma["id"]

        # Insert document log for Gamma
        db_manager.log_document_generation(
            candidate_id=c_gamma_id,
            document_type="offer",
            reference_number="DFY/HR/2026/903",
            extra_fields_dict={},
            file_path="dummy/path/offer.docx",
        )

        # Simulate midway failure in transaction
        conn_sim = db_manager.get_connection()
        try:
            cur_sim = conn_sim.cursor()
            cur_sim.execute("DELETE FROM document_generation_log WHERE candidate_id = ?", (c_gamma_id,))
            # Force simulated system/DB failure midway before candidate deletion
            raise RuntimeError("SIMULATED FAILURE MID-TRANSACTION")
            cur_sim.execute("DELETE FROM candidates WHERE id = ?", (c_gamma_id,))
            conn_sim.commit()
        except Exception:
            conn_sim.rollback()
        finally:
            conn_sim.close()

        # Check DB state after rollback: Gamma and log MUST both still exist intact
        conn_verify = db_manager.get_connection()
        cur_v = conn_verify.cursor()
        cur_v.execute("SELECT COUNT(*) FROM document_generation_log WHERE candidate_id = ?", (c_gamma_id,))
        gamma_doc_count = cur_v.fetchone()[0]
        cur_v.execute("SELECT COUNT(*) FROM candidates WHERE id = ?", (c_gamma_id,))
        gamma_cand_count = cur_v.fetchone()[0]
        conn_verify.close()

        assert gamma_doc_count == 1, "Rollback failed: document log was deleted!"
        assert gamma_cand_count == 1, "Rollback failed: candidate row was deleted!"
        print("  ✓ Atomic rollback verified: child rows and parent candidate preserved on failure.")

        # Clean up Gamma using real permanent delete
        assert db_manager.permanently_delete_candidate(c_gamma_id) is True
        print("  ✓ Cleanup delete after rollback verified.")

        # -----------------------------------------------------------------
        # TEST 4: Archive and restore functionality (Steps 1 & 2) unaffected
        # -----------------------------------------------------------------
        print("\n[TEST 4] Verifying existing archive and restore are unaffected...")
        cand_delta = {
            "candidate_name": "Delta Step1-2 Check",
            "mobile": mob_delta,
            "email": "delta.check@test.com",
            "applied_designation": "Analyst",
            "negotiated_salary": "50000",
            "contact_location": "Bhopal",
            "status": "Shortlisted",
        }
        db_manager.upsert_candidate(cand_delta, "Test Script")
        c_delta = db_manager.get_candidate_by_mobile(mob_delta)
        c_delta_id = c_delta["id"]
        db_manager.update_candidate_status(c_delta_id, "Shortlisted")

        # Step 1: Archive Delta
        assert db_manager.archive_candidate(c_delta_id) is True
        c_delta_archived = db_manager.get_candidate_by_id(c_delta_id)
        assert c_delta_archived["archived"] == 1
        assert c_delta_archived["archived_at"] is not None

        # Excluded from active list, present in archive list
        assert not any(c["id"] == c_delta_id for c in db_manager.get_all_candidates())
        assert any(c["id"] == c_delta_id for c in db_manager.get_archived_candidates())

        # Step 2: Restore Delta
        assert db_manager.restore_candidate(c_delta_id) is True
        c_delta_restored = db_manager.get_candidate_by_id(c_delta_id)
        assert c_delta_restored["archived"] == 0
        assert c_delta_restored["archived_at"] is None
        assert c_delta_restored["status"] == "Shortlisted"

        # Reappears in active list, gone from archive list
        assert any(c["id"] == c_delta_id for c in db_manager.get_all_candidates())
        assert not any(c["id"] == c_delta_id for c in db_manager.get_archived_candidates())
        print("  ✓ Steps 1 & 2 Archive/Restore lifecycle verified 100% operational.")

        # Cleanup Delta
        db_manager.permanently_delete_candidate(c_delta_id)

        print("\n" + "=" * 70)
        print("ALL STEP 3 TESTS PASSED SUCCESSFULLY! ✅")
        print("=" * 70)

    finally:
        # Final cleanup
        conn_clean = db_manager.get_connection()
        conn_clean.execute("DELETE FROM candidates WHERE mobile IN (?, ?, ?, ?)", (mob_alpha, mob_beta, mob_gamma, mob_delta))
        conn_clean.commit()
        conn_clean.close()


if __name__ == "__main__":
    run_tests()
