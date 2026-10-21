import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db_manager

def test_migration():
    db_manager.init_db()
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(candidates)")
    cols = {row[1] for row in cur.fetchall()}
    conn.close()

    expected_cols = [
        "employee_number", "first_name", "last_name", "display_name",
        "work_email", "personal_email", "date_of_birth", "gender",
        "marital_status", "marriage_date", "current_address", "permanent_address",
        "father_name", "mother_name", "spouse_name", "department",
        "job_title", "reporting_to", "reporting_manager_emp_no", "date_joined",
        "employment_status", "worker_type", "time_type", "leave_plan",
        "shift_policy", "weekly_off_policy", "notice_period", "pan_number",
        "aadhaar_number", "pf_number", "uan_number", "exit_date",
        "exit_status", "termination_type", "termination_reason", "cost_center"
    ]
    missing = [c for c in expected_cols if c not in cols]
    if missing:
        print(f"FAILED: Missing columns in candidates table: {missing}")
        sys.exit(1)
    print("Schema migration verification: PASS")

if __name__ == "__main__":
    test_migration()
