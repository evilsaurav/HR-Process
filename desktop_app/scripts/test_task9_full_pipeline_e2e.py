"""
End-to-End Integration Verification & Full Regression Suite
Task 9 Verification Script

Covers:
1. Flow 1 (Candidate Joining & Welcome Email staging)
2. Flow 2 (Keka Master Ingestion & Smart Rule Detection)
3. Flow 3 (Staging Quality Gate, preview, inline fix, instant regeneration)
4. Flow 4 (Final Go Bulk Dispatch, atomic sequence consumption, audit trail)
5. Flow 5 (Executive Dashboard real-time action card metrics reflection)
6. Complete Regression Run of Tasks 1-8 and 74-column Keka Master Ingestion
"""

import os
import sys
import time
import subprocess
import unittest.mock
import datetime

# Configure UTF-8 stdout encoding for Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from database import db_manager
from services import (
    smart_rule_detector,
    document_staging_service,
    dashboard_service,
    email_service,
)


def log_step(title: str, detail: str = ""):
    print(f"\n{'='*75}\n>>> {title}\n{'='*75}")
    if detail:
        print(detail)


def run_e2e_integration_flows() -> bool:
    """
    Executes the 5 uninterrupted end-to-end integration flows.
    """
    print("\n" + "=" * 75)
    print("PART 1: COMPREHENSIVE END-TO-END HR PIPELINE INTEGRATION FLOWS")
    print("=" * 75)

    db_manager.init_db()

    # Ensure reference sequence exists for atomic sequence testing
    ref_cfg = db_manager.get_reference_config("hr_reference")
    if not ref_cfg:
        db_manager.save_reference_config("hr_reference", "DFY/HR/2026/{SEQ}", 4, 1, 9999)
        ref_cfg = db_manager.get_reference_config("hr_reference")

    seq_initial = ref_cfg["current_number"]
    test_mobile = "9999988881"
    test_email = "ananya.sharma.test@doctorsforyou.org"
    created_candidate_id = None
    created_staging_id = None
    generated_files = []

    try:
        # =====================================================================
        # FLOW 1: Candidate Joining & Welcome Email Staging
        # =====================================================================
        log_step("FLOW 1: Candidate Joining & Welcome Email Staging",
                 "Creating applicant, marking Selected, verifying pending queue, simulating dispatch.")

        # Clean any preexisting candidate with test mobile and create test applicant
        conn = db_manager.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM candidates WHERE mobile = ?", (test_mobile,))
        conn.commit()

        # Step 1.1: Create test applicant in Applied state
        cur.execute("""
            INSERT INTO candidates (candidate_name, mobile, email, applied_designation, department, status, welcome_email_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Dr. Ananya Sharma", test_mobile, test_email, "District Coordinator", "Public Health Emergency", "Applied", 0))
        created_candidate_id = cur.lastrowid
        conn.commit()
        conn.close()
        assert created_candidate_id > 0, "Failed to insert test applicant"
        print(f"  [1.1] Candidate inserted with ID: {created_candidate_id} (Status: Applied)")

        # Verify candidate is NOT in pending welcome list yet
        pending_initial = db_manager.get_selected_candidates_pending_welcome()
        assert not any(c["id"] == created_candidate_id for c in pending_initial), (
            "Candidate should not be in pending welcome emails before being Selected"
        )

        # Step 1.2: Mark candidate status = 'Selected'
        db_manager.update_candidate(created_candidate_id, {"status": "Selected", "welcome_email_sent": 0})
        cand_selected = db_manager.get_candidate_by_id(created_candidate_id)
        assert cand_selected["status"] == "Selected", "Candidate status update failed"
        print("  [1.2] Candidate status advanced to 'Selected'.")

        # Step 1.3: Verify candidate appears in pending welcome list
        pending_after_selected = db_manager.get_selected_candidates_pending_welcome()
        target_cand = next((c for c in pending_after_selected if c["id"] == created_candidate_id), None)
        assert target_cand is not None, "Selected candidate not found in pending welcome emails"
        assert target_cand["candidate_name"] == "Dr. Ananya Sharma"
        assert target_cand["email"] == test_email
        print(f"  [1.3] Verified candidate {created_candidate_id} in get_selected_candidates_pending_welcome().")

        # Step 1.4: Simulate welcome email dispatch & update welcome_email_sent
        db_manager.update_candidate_welcome_email_status(created_candidate_id, sent=True)
        # Log to email_log for full audit trail
        db_manager.log_email_dispatch(
            recipient_email=test_email,
            recipient_name="Dr. Ananya Sharma",
            document_type="welcome_email",
            subject="Welcome to Doctors For You! - Next Steps",
            attachment_filename=None,
            attachment_path=None,
            sent_by="HR Desktop (Welcome Flow)",
            status="Sent",
            error_message=None,
            candidate_id=created_candidate_id
        )
        print("  [1.4] Welcome email dispatch simulated and logged.")

        # Step 1.5: Verify candidate is removed from pending list
        pending_after_sent = db_manager.get_selected_candidates_pending_welcome()
        assert not any(c["id"] == created_candidate_id for c in pending_after_sent), (
            "Candidate was not removed from pending welcome emails after dispatch!"
        )
        cand_updated = db_manager.get_candidate_by_id(created_candidate_id)
        assert cand_updated["welcome_email_sent"] == 1
        assert cand_updated["welcome_email_sent_at"] is not None
        print("  [1.5] Verified candidate removed from pending list with welcome_email_sent=1.")
        print("  ✓ Flow 1 Passed successfully!")

        # =====================================================================
        # FLOW 2: Keka Master Ingestion & Smart Rule Detection
        # =====================================================================
        log_step("FLOW 2: Keka Master Ingestion & Smart Rule Detection",
                 "Simulating Keka joinee sync and classifying document need automatically.")

        # Step 2.1: Update candidate to 'Joined' active employee (as synced from Keka)
        db_manager.update_candidate(created_candidate_id, {
            "status": "Joined",
            "employment_status": "Active",
            "employee_number": "DFY-9991",
            "date_of_joining": datetime.date.today().strftime("%Y-%m-%d"),
            "legal_entity": "Doctors For You"
        })
        cand_for_scan = db_manager.get_candidate_by_id(created_candidate_id)
        print(f"  [2.1] Employee record synced: Emp #{cand_for_scan['employee_number']}, Status: Joined / Active.")

        # Step 2.2: Run Smart Rule Detection on active joinee without prior offer
        doc_need = smart_rule_detector.classify_candidate_document_need(cand_for_scan, history=[])
        assert doc_need["suggested_doc_type"] == "offer_letter", (
            f"Expected 'offer_letter', got '{doc_need['suggested_doc_type']}'"
        )
        assert doc_need["priority"] == "High"
        assert doc_need["trigger_reason"] == "Active joinee without prior offer letter on file"
        print(f"  [2.2] Smart rule accurately classified: Suggested='{doc_need['suggested_doc_type']}', "
              f"Priority='{doc_need['priority']}', Reason='{doc_need['trigger_reason']}'.")

        # Step 2.3: Verify extension rule classification
        cand_extension_scenario = dict(cand_for_scan)
        cand_extension_scenario["extension_of_service_till"] = "2026-12-31"
        ext_need = smart_rule_detector.classify_candidate_document_need(cand_extension_scenario)
        assert ext_need["suggested_doc_type"] == "extension_letter"
        assert ext_need["trigger_reason"] == "Service extension date or tenure recorded"
        print("  [2.3] Extension rule scenario verified successfully.")
        print("  ✓ Flow 2 Passed successfully!")

        # =====================================================================
        # FLOW 3: Staging Quality Gate & Inline Fix
        # =====================================================================
        log_step("FLOW 3: Staging Quality Gate & Inline Fix",
                 "Generating non-consuming draft, verifying draft reference, inline editing & instant regeneration.")

        seq_before_staging = db_manager.get_reference_config("hr_reference")["current_number"]

        # Step 3.1: Generate Draft to Staging
        draft_res = document_staging_service.generate_draft_to_staging(
            candidate_id=created_candidate_id,
            document_type="offer_letter",
            preferred_format="docx"
        )
        assert draft_res["success"] is True, f"Draft generation failed: {draft_res.get('error')}"
        created_staging_id = draft_res["staging_id"]
        assert created_staging_id > 0
        doc_path = draft_res["doc_file_path"]
        generated_files.append(doc_path)
        assert os.path.exists(doc_path), f"Draft document missing at {doc_path}"
        print(f"  [3.1] Draft generated in staging (ID: {created_staging_id}) at: {os.path.basename(doc_path)}")

        # Step 3.2: Verify draft reference is non-consuming
        seq_after_staging = db_manager.get_reference_config("hr_reference")["current_number"]
        assert seq_after_staging == seq_before_staging, (
            f"Atomic sequence was prematurely incremented! Before: {seq_before_staging}, After: {seq_after_staging}"
        )
        staging_rec = db_manager.get_staging_record_by_id(created_staging_id)
        assert staging_rec["status"] == "Staged"
        print(f"  [3.2] Verified non-consuming reference behavior (Sequence retained at {seq_after_staging}).")

        # Step 3.3: Perform Inline Fix & Instant Document Regeneration
        fix_res = document_staging_service.inline_fix_and_regenerate(
            staging_id=created_staging_id,
            updated_candidate_fields={
                "negotiated_salary": "72000",
                "department": "Disaster Response Unit"
            }
        )
        assert fix_res["success"] is True, f"Inline fix failed: {fix_res.get('error')}"
        print("  [3.3] Inline fix performed (salary: 72000, dept: Disaster Response Unit).")

        # Step 3.4: Verify database update & sequence preservation
        cand_post_fix = db_manager.get_candidate_by_id(created_candidate_id)
        assert cand_post_fix["negotiated_salary"] == "72000"
        assert cand_post_fix["department"] == "Disaster Response Unit"

        seq_after_fix = db_manager.get_reference_config("hr_reference")["current_number"]
        assert seq_after_fix == seq_before_staging, (
            f"Sequence altered during inline fix! Expected {seq_before_staging}, got {seq_after_fix}"
        )
        assert os.path.exists(fix_res["doc_file_path"])
        print("  [3.4] Verified candidate data updated in DB & sequence unchanged during inline fix.")
        print("  ✓ Flow 3 Passed successfully!")

        # =====================================================================
        # FLOW 4: Final Go Bulk Dispatch & Audit Trail
        # =====================================================================
        log_step("FLOW 4: Final Go Bulk Dispatch & Audit Trail",
                 "Dispatching staged record, consuming official reference, and checking audit logs.")

        seq_before_dispatch = db_manager.get_reference_config("hr_reference")["current_number"]

        # Helper mock for SMTP dispatch to verify audit log and avoid real network call
        def mock_dispatch_email(*args, **kwargs):
            to_addr = kwargs.get("to_addr") or (args[0] if len(args) > 0 else test_email)
            cid = kwargs.get("candidate_id") or created_candidate_id
            doc_t = kwargs.get("document_type") or "offer_letter"
            subj = kwargs.get("subject", "Offer Letter - Doctors For You")
            r_name = kwargs.get("recipient_name", "Dr. Ananya Sharma")
            att = kwargs.get("attachment_path")
            db_manager.log_email_dispatch(
                recipient_email=to_addr,
                recipient_name=r_name,
                document_type=doc_t,
                subject=subj,
                attachment_filename=os.path.basename(att) if att else None,
                attachment_path=att,
                sent_by=kwargs.get("sent_by", "HR Desktop (Final Go)"),
                status="Sent",
                error_message=None,
                candidate_id=cid
            )
            return True, "Mock email dispatched successfully"

        # Step 4.1: Execute final go dispatch
        with unittest.mock.patch("services.email_service.send_email_smtp", side_effect=mock_dispatch_email):
            dispatch_res = document_staging_service.final_go_dispatch(
                staging_ids=[created_staging_id],
                send_async=False
            )

        assert dispatch_res["total"] == 1, f"Expected total 1, got {dispatch_res['total']}"
        assert dispatch_res["sent"] == 1, f"Expected sent 1, got {dispatch_res['sent']} (errors: {dispatch_res.get('errors')})"
        print(f"  [4.1] Final Go dispatch completed: {dispatch_res}")

        # Step 4.2: Verify official sequence number atomically incremented
        seq_after_dispatch = db_manager.get_reference_config("hr_reference")["current_number"]
        assert seq_after_dispatch == seq_before_dispatch + 1, (
            f"Expected official reference sequence to increment from {seq_before_dispatch} to {seq_before_dispatch + 1}, got {seq_after_dispatch}"
        )
        print(f"  [4.2] Verified atomic sequence consumption: {seq_before_dispatch} -> {seq_after_dispatch}.")

        # Step 4.3: Verify staging record status and official reference
        staged_final = db_manager.get_staging_record_by_id(created_staging_id)
        assert staged_final["status"] == "Dispatched", f"Expected 'Dispatched', got '{staged_final['status']}'"
        assert staged_final["reference_number"] is not None
        assert "DRAFT" not in staged_final["reference_number"]
        assert staged_final["dispatched_at"] is not None
        official_ref = staged_final["reference_number"]
        print(f"  [4.3] Verified staging record #{created_staging_id} status='Dispatched', Ref='{official_ref}'.")

        # Step 4.4: Verify audit logs in document_generation_log and email_log
        conn = db_manager.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, candidate_id, document_type, reference_number
            FROM document_generation_log
            WHERE candidate_id = ? AND reference_number = ?
        """, (created_candidate_id, official_ref))
        gen_log = cur.fetchone()
        assert gen_log is not None, f"Audit log entry missing in document_generation_log for ref {official_ref}"
        print(f"  [4.4a] Verified document_generation_log audit entry (ID: {gen_log[0]}).")

        cur.execute("""
            SELECT id, candidate_id, recipient_email, status
            FROM email_log
            WHERE candidate_id = ? AND document_type = 'offer_letter'
            ORDER BY id DESC LIMIT 1
        """, (created_candidate_id,))
        email_log_row = cur.fetchone()
        assert email_log_row is not None, "Audit log entry missing in email_log for offer_letter dispatch"
        assert email_log_row[3] in ("Sent", "Success"), f"Unexpected email log status: {email_log_row[3]}"
        print(f"  [4.4b] Verified email_log audit entry (ID: {email_log_row[0]}, Status: {email_log_row[3]}).")
        conn.close()
        print("  ✓ Flow 4 Passed successfully!")

        # =====================================================================
        # FLOW 5: Executive Dashboard Real-Time Action Card Metrics Reflection
        # =====================================================================
        log_step("FLOW 5: Executive Dashboard Real-Time Action Card Metrics Reflection",
                 "Verifying operational counters reflect live database state accurately.")

        # Step 5.1: Retrieve stats and verify structure
        stats = dashboard_service.get_dashboard_stats()
        required_keys = [
            "pending_welcome_emails",
            "letters_to_generate",
            "staged_letters_ready",
            "dispatched_today",
            "total_candidates",
            "selected_candidates",
            "in_interview",
            "in_pipeline",
            "joined_candidates"
        ]
        for k in required_keys:
            assert k in stats, f"Missing key in dashboard stats: {k}"
            assert isinstance(stats[k], int), f"Stat '{k}' is not an integer: {stats[k]}"
        print("  [5.1] All dashboard stats keys validated with correct types.")

        # Step 5.2: Dispatched today reflects the dispatch
        assert stats["dispatched_today"] >= 1, (
            f"Expected dispatched_today >= 1 after Flow 4 dispatch, got {stats['dispatched_today']}"
        )
        print(f"  [5.2] Verified dispatched_today counter: {stats['dispatched_today']}.")

        # Step 5.3: Dynamic verification of pending_welcome_emails metric
        base_pending = stats["pending_welcome_emails"]
        conn = db_manager.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO candidates (candidate_name, mobile, status, welcome_email_sent)
            VALUES (?, ?, ?, ?)
        """, ("Temp Metric Joinee", "9999988889", "Selected", 0))
        temp_cid = cur.lastrowid
        conn.commit()
        conn.close()
        stats_bump = dashboard_service.get_dashboard_stats()
        assert stats_bump["pending_welcome_emails"] == base_pending + 1, (
            f"Expected {base_pending + 1}, got {stats_bump['pending_welcome_emails']}"
        )

        db_manager.update_candidate_welcome_email_status(temp_cid, sent=True)
        stats_resolved = dashboard_service.get_dashboard_stats()
        assert stats_resolved["pending_welcome_emails"] == base_pending, (
            f"Expected {base_pending}, got {stats_resolved['pending_welcome_emails']}"
        )

        # Step 5.4: Dynamic verification of staged_letters_ready metric
        base_staged = stats["staged_letters_ready"]
        temp_sid = db_manager.create_staging_record(
            candidate_id=temp_cid,
            document_type="offer_letter",
            status="Staged"
        )
        stats_staged_bump = dashboard_service.get_dashboard_stats()
        assert stats_staged_bump["staged_letters_ready"] == base_staged + 1, (
            f"Expected {base_staged + 1}, got {stats_staged_bump['staged_letters_ready']}"
        )

        db_manager.delete_staging_record(temp_sid)
        stats_staged_resolved = dashboard_service.get_dashboard_stats()
        assert stats_staged_resolved["staged_letters_ready"] == base_staged, (
            f"Expected {base_staged}, got {stats_staged_resolved['staged_letters_ready']}"
        )

        # Clean temp candidate
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM candidates WHERE id = ?", (temp_cid,))
        conn.commit()
        conn.close()

        print("  [5.3 & 5.4] Verified dynamic metric reactivity for pending welcome emails & staged letters.")
        print("  ✓ Flow 5 Passed successfully!")

        return True

    finally:
        # Cleanup created records and test files
        print("\n[Cleanup] Removing temporary test records and generated files...")
        if created_staging_id:
            try:
                db_manager.delete_staging_record(created_staging_id)
            except Exception:
                pass
        if created_candidate_id:
            try:
                conn = db_manager.get_connection()
                conn.execute("DELETE FROM email_log WHERE candidate_id = ?", (created_candidate_id,))
                conn.execute("DELETE FROM document_generation_log WHERE candidate_id = ?", (created_candidate_id,))
                conn.execute("DELETE FROM document_staging WHERE candidate_id = ?", (created_candidate_id,))
                conn.execute("DELETE FROM candidates WHERE id = ?", (created_candidate_id,))
                conn.commit()
                conn.close()
            except Exception:
                pass
        for fpath in generated_files:
            if fpath and os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass
        print("  ✓ Cleanup complete.")


def run_full_regression_suite() -> bool:
    """
    Executes the full suite of regression test scripts across all components.
    """
    print("\n" + "=" * 75)
    print("PART 2: COMPONENT REGRESSION SUITE (TASKS 1-8 + 74-COLUMN KEKA MASTER)")
    print("=" * 75)

    regression_scripts = [
        ("Task 1: Staging DB & Welcome Tracking", "test_task1_staging_db.py"),
        ("Task 2: Word COM & PDF Converter", "test_task2_pdf_converter.py"),
        ("Task 3: Smart Rule Detector Service", "test_task3_smart_rule_detector.py"),
        ("Task 4: Staging Service & Bulk Dispatch", "test_task4_staging_service.py"),
        ("Task 5: Welcome Email Staging UI", "test_task5_welcome_email_ui.py"),
        ("Task 6: Smart Document Pipeline & Hub UI", "test_task6_staging_hub_integration.py"),
        ("Task 7: Dashboard Live Action Cards & Metrics", "test_task7_dashboard_metrics.py"),
        ("Task 8: 1-Click Desktop Launcher (.bat)", "test_task8_launcher.py"),
        ("Keka Master: 74-Column Ingestion Engine", "test_74_column_keka_master.py"),
    ]

    results = []
    suite_start = time.time()

    for idx, (label, script_name) in enumerate(regression_scripts, 1):
        script_path = os.path.join(SCRIPT_DIR, script_name)
        assert os.path.exists(script_path), f"Regression script not found: {script_path}"

        print(f"\n[{idx}/{len(regression_scripts)}] Running {label} ({script_name})...")
        t0 = time.time()
        try:
            res = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120
            )
            elapsed = time.time() - t0
            passed = (res.returncode == 0)
            results.append((label, script_name, passed, elapsed, res.stdout, res.stderr))

            if passed:
                print(f"  PASS: {script_name} completed in {elapsed:.2f}s")
            else:
                print(f"  FAIL: {script_name} failed with exit code {res.returncode} in {elapsed:.2f}s")
                print("--- STDOUT ---")
                print(res.stdout)
                print("--- STDERR ---")
                print(res.stderr)
        except subprocess.TimeoutExpired:
            elapsed = time.time() - t0
            print(f"  TIMEOUT: {script_name} timed out after {elapsed:.2f}s")
            results.append((label, script_name, False, elapsed, "", "Process timed out after 120s"))
        except Exception as ex:
            elapsed = time.time() - t0
            print(f"  ERROR: {script_name} encountered exception: {ex}")
            results.append((label, script_name, False, elapsed, "", str(ex)))

    total_time = time.time() - suite_start
    total_count = len(results)
    pass_count = sum(1 for r in results if r[2])
    fail_count = total_count - pass_count

    print("\n" + "=" * 75)
    print("REGRESSION SUITE SCOREBOARD")
    print("=" * 75)
    for idx, (label, script_name, passed, elapsed, _, _) in enumerate(results, 1):
        mark = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {idx}. [{mark}] {label:<45} ({elapsed:5.2f}s)")
    print("-" * 75)
    print(f"Summary: {pass_count}/{total_count} Passed ({pass_count/total_count*100:.1f}%), {fail_count} Failed. Total Time: {total_time:.2f}s")
    print("=" * 75)

    return fail_count == 0


def main():
    start_time = time.time()
    print("=" * 75)
    print("STARTING TASK 9: END-TO-END PIPELINE VERIFICATION & FULL REGRESSION SUITE")
    print("=" * 75)

    # Part 1: End-to-End Integration Simulation
    e2e_ok = run_e2e_integration_flows()
    if not e2e_ok:
        print("\nFATAL: End-to-End integration flows failed! Aborting regression suite.")
        sys.exit(1)

    # Part 2: Component Regression Suite
    regression_ok = run_full_regression_suite()
    if not regression_ok:
        print("\nFATAL: One or more regression tests failed!")
        sys.exit(1)

    total_time = time.time() - start_time
    print("\n" + "=" * 75)
    print("🏆 ALL INTEGRATION FLOWS & REGRESSION TESTS PASSED WITH 100% SUCCESS!")
    print(f"Total Execution Time: {total_time:.2f}s | Exit Code: 0")
    print("=" * 75)
    sys.exit(0)


if __name__ == "__main__":
    main()
