"""
Verification Script: test_duplicate_actions.py
Step 3 Test Suite for Safe Candidate Updates, Additions, and Single-Candidate Actions.

Tests:
1. "Replace with New" action updates modified fields.
2. "Replace with New" action strictly PRESERVES existing data when uploaded cells are blank.
3. "Replace with New" action strictly PRESERVES lifecycle fields (father_name, date_joined, status).
4. "Keep Existing" action leaves the candidate record 100% untouched.
5. Genuinely new candidates are added fresh into the database.
6. Summary reporting returns accurate counts (added, updated, kept).
7. Regression verification for single-candidate operations on the Joining Process page
   (update status, delete candidate, query with filters).
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
from services.sheet_processor import (
    apply_joining_decisions,
    safe_update_candidate,
    insert_new_candidate,
)


def run_tests():
    print("=" * 70)
    print("RUNNING STEP 3 TESTS: ACTION WIRING & DATA SAFETY")
    print("=" * 70)

    db_manager.init_db()

    # Unique test mobiles to avoid collision
    mob_alpha = "9000000001"
    mob_beta = "9000000002"
    mob_gamma = "9000000003"

    # Clean up any leftover test data first
    conn = db_manager.get_connection()
    conn.execute("DELETE FROM candidates WHERE mobile IN (?, ?, ?)", (mob_alpha, mob_beta, mob_gamma))
    conn.commit()
    conn.close()

    try:
        # 1. Setup Test Candidate Alpha
        ok1 = insert_new_candidate({
            "candidate_name": "Test Person Alpha",
            "mobile": mob_alpha,
            "email": "alpha.orig@dfy.org",
            "applied_designation": "Coordinator",
            "negotiated_salary": "30000",
            "contact_location": "Patna",
            "recent_designation": "Field Worker",
            "highest_education": "B.Sc",
            "total_experience": "3",
            "core_technical_skills": "Coordination",
            "key_responsibilities": "Field Ops",
        }, source_sheet_name="TestInit")
        assert ok1, "Failed to insert Test Person Alpha"

        # Add extra details & custom status to Alpha to test preservation
        c_alpha = db_manager.get_candidate_by_mobile(mob_alpha)
        assert c_alpha is not None
        db_manager.update_candidate_status(c_alpha["id"], "Shortlisted")
        db_manager.update_candidate_extra_details(
            c_alpha["id"],
            father_name="Shri Ram Alpha",
            full_address="Ward 4, Patna",
            gender="Male",
            department="Health Services",
            date_joined="2024-01-15",
            employee_number="EMP_ALPHA",
        )

        # 2. Setup Test Candidate Beta
        ok2 = insert_new_candidate({
            "candidate_name": "Test Person Beta",
            "mobile": mob_beta,
            "email": "beta.orig@dfy.org",
            "applied_designation": "Manager",
            "negotiated_salary": "45000",
            "contact_location": "Gaya",
            "recent_designation": "Deputy Manager",
            "highest_education": "MBA",
            "total_experience": "7",
            "core_technical_skills": "HR & Admin",
            "key_responsibilities": "Operations",
        }, source_sheet_name="TestInit")
        assert ok2, "Failed to insert Test Person Beta"

        c_beta = db_manager.get_candidate_by_mobile(mob_beta)
        assert c_beta is not None
        db_manager.update_candidate_status(c_beta["id"], "Joined")

        # -------------------------------------------------------------
        # TEST 1 & 2: Prepare decision batch
        # -------------------------------------------------------------
        print("\n[TEST 1] Testing apply_joining_decisions with Replace, Keep, and New...")

        # Duplicate 1: Alpha -> REPLACE with new data, but with BLANK email to test non-overwrite
        dup_alpha = {
            "existing_record": c_alpha,
            "uploaded_row": {
                "candidate_name": "Test Person Alpha",
                "mobile": mob_alpha,
                "email": "",  # BLANK! Must NOT overwrite existing 'alpha.orig@dfy.org'
                "applied_designation": "Lead Project Coordinator",  # MODIFIED
                "negotiated_salary": "38000",  # MODIFIED
                "recent_designation": "Senior Field Worker",  # MODIFIED
                "highest_education": "",  # BLANK! Must NOT overwrite existing 'B.Sc'
                "total_experience": "4",  # MODIFIED
                "core_technical_skills": "Advanced Project Management",  # MODIFIED
                "key_responsibilities": "Project Leadership",  # MODIFIED
                "contact_location": "Patna Urban",  # MODIFIED
            },
            "action": "replace",
        }

        # Duplicate 2: Beta -> KEEP existing (user decided to reject changes)
        dup_beta = {
            "existing_record": c_beta,
            "uploaded_row": {
                "candidate_name": "Test Person Beta",
                "mobile": mob_beta,
                "email": "beta.new@dfy.org",
                "applied_designation": "Director",
                "negotiated_salary": "99999",  # MUST NOT be applied
                "contact_location": "Delhi",
            },
            "action": "keep",
        }

        # Genuinely new candidate: Gamma
        new_gamma = {
            "candidate_name": "Test Person Gamma",
            "mobile": mob_gamma,
            "email": "gamma@dfy.org",
            "applied_designation": "MIS Specialist",
            "negotiated_salary": "50000",
            "recent_designation": "Data Analyst",
            "highest_education": "M.Tech",
            "total_experience": "5",
            "core_technical_skills": "Python, SQL",
            "key_responsibilities": "MIS Dashboard",
            "contact_location": "Ranchi",
        }

        summary = apply_joining_decisions(
            duplicates=[dup_alpha, dup_beta],
            new_rows=[new_gamma],
            source_sheet_name="BatchUpload2026.xlsx",
        )

        assert summary["success"] is True, f"Expected success=True, got {summary}"
        assert summary["added_count"] == 1, f"Expected added=1, got {summary['added_count']}"
        assert summary["updated_count"] == 1, f"Expected updated=1, got {summary['updated_count']}"
        assert summary["kept_count"] == 1, f"Expected kept=1, got {summary['kept_count']}"
        assert summary["total_processed"] == 3, f"Expected total=3, got {summary['total_processed']}"
        print(f"  ✓ Summary metrics verified: Added={summary['added_count']}, Updated={summary['updated_count']}, Kept={summary['kept_count']}")

        # -------------------------------------------------------------
        # VERIFY DATABASE STATE AFTER APPLYING
        # -------------------------------------------------------------
        print("\n[TEST 2] Verifying database state for replaced candidate (Alpha)...")
        alpha_after = db_manager.get_candidate_by_id(c_alpha["id"])
        assert alpha_after["applied_designation"] == "Lead Project Coordinator", "Designation was not updated"
        assert alpha_after["negotiated_salary"] == "38000", "Salary was not updated"
        assert alpha_after["total_experience"] == "4", "Experience was not updated"
        assert alpha_after["contact_location"] == "Patna Urban", "Location was not updated"
        # STRICT DATA PRESERVATION CHECKS:
        assert alpha_after["email"] == "alpha.orig@dfy.org", f"Blank email overwrote existing email! Got: {alpha_after['email']}"
        assert alpha_after["highest_education"] == "B.Sc", f"Blank education overwrote existing education! Got: {alpha_after['highest_education']}"
        assert alpha_after["father_name"] == "Shri Ram Alpha", f"Father name was wiped! Got: {alpha_after['father_name']}"
        assert alpha_after["employee_number"] == "EMP_ALPHA", "Employee number was wiped!"
        assert alpha_after["date_joined"] == "2024-01-15", "Date joined was wiped!"
        assert alpha_after["status"] == "Shortlisted", "Status was changed unexpectedly!"
        print("  ✓ Replace candidate updated modified fields and strictly preserved blank & lifecycle fields!")

        print("\n[TEST 3] Verifying database state for kept candidate (Beta)...")
        beta_after = db_manager.get_candidate_by_id(c_beta["id"])
        assert beta_after["negotiated_salary"] == "45000", f"Kept candidate salary changed! Got: {beta_after['negotiated_salary']}"
        assert beta_after["applied_designation"] == "Manager", f"Kept candidate designation changed! Got: {beta_after['applied_designation']}"
        assert beta_after["email"] == "beta.orig@dfy.org", "Kept candidate email changed!"
        assert beta_after["status"] == "Joined", "Kept candidate status changed!"
        print("  ✓ Kept candidate was 100% untouched in the database!")

        print("\n[TEST 4] Verifying database state for new candidate (Gamma)...")
        gamma_after = db_manager.get_candidate_by_mobile(mob_gamma)
        assert gamma_after is not None, "Gamma was not inserted"
        assert gamma_after["candidate_name"] == "Test Person Gamma"
        assert gamma_after["applied_designation"] == "MIS Specialist"
        assert gamma_after["negotiated_salary"] == "50000"
        assert gamma_after["status"] == "Applied", "New candidate status should default to 'Applied'"
        print("  ✓ Genuinely new candidate inserted properly with status 'Applied'!")

        # -------------------------------------------------------------
        # TEST 5: Regression test on single-candidate operations
        # -------------------------------------------------------------
        print("\n[TEST 5] Testing existing single-candidate operations for zero regressions...")
        # Status update
        db_manager.update_candidate_status(gamma_after["id"], "Interview")
        gamma_updated = db_manager.get_candidate_by_id(gamma_after["id"])
        assert gamma_updated["status"] == "Interview", "Failed to update single candidate status"
        print("  ✓ Single-candidate inline status change works correctly.")

        # Candidate search / filtering
        candidates_filtered = db_manager.get_all_candidates(search_term="MIS Specialist", status_filter="Interview")
        assert any(c["id"] == gamma_after["id"] for c in candidates_filtered), "Candidate search/filter failed"
        print("  ✓ Single-candidate search and status filter works correctly.")

        # Candidate deletion
        db_manager.delete_candidate(gamma_after["id"])
        gamma_deleted = db_manager.get_candidate_by_id(gamma_after["id"])
        assert gamma_deleted is None, "Failed to delete candidate"
        print("  ✓ Single-candidate deletion works correctly.")

        print("\n" + "=" * 70)
        print("ALL STEP 3 TESTS PASSED SUCCESSFULLY! ✅")
        print("=" * 70)

    finally:
        # Cleanup test records
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM candidates WHERE mobile IN (?, ?, ?)", (mob_alpha, mob_beta, mob_gamma))
        conn.commit()
        conn.close()


if __name__ == "__main__":
    run_tests()
