import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import smart_rule_detector

def run_test():
    # Case 1: Active joinee -> Offer Letter
    c1 = {"id": 101, "candidate_name": "Aarav Patel", "status": "Joined", "employment_status": "Active"}
    res1 = smart_rule_detector.classify_candidate_document_need(c1, history=[])
    assert res1["suggested_doc_type"] == "offer_letter", f"Expected offer_letter, got {res1['suggested_doc_type']}"
    assert res1["priority"] == "High"
    assert res1["trigger_reason"] == "Active joinee without prior offer letter on file"
    assert "missing_fields" in res1
    assert isinstance(res1["missing_fields"], list)

    # Case 2: Extension till -> Extension Letter
    c2 = {"id": 102, "candidate_name": "Pooja Shah", "extension_of_service_till": "2026-12-31"}
    res2 = smart_rule_detector.classify_candidate_document_need(c2)
    assert res2["suggested_doc_type"] == "extension_letter", f"Expected extension_letter, got {res2['suggested_doc_type']}"
    assert res2["priority"] == "Normal"
    assert res2["trigger_reason"] == "Service extension date or tenure recorded"

    # Case 3: Exit date -> Experience Certificate
    c3 = {"id": 103, "candidate_name": "Rahul Verma", "exit_date": "2026-09-30", "exit_status": "Resigned"}
    res3 = smart_rule_detector.classify_candidate_document_need(c3)
    assert res3["suggested_doc_type"] == "experience_certificate", f"Expected experience_certificate, got {res3['suggested_doc_type']}"
    assert res3["priority"] == "Normal"
    assert res3["trigger_reason"] == "Employee separation / Exit date recorded"

    # Case 4: Termination reason -> Termination Letter
    c4 = {"id": 104, "candidate_name": "Karan Mehra", "termination_reason": "Performance shortfall"}
    res4 = smart_rule_detector.classify_candidate_document_need(c4)
    assert res4["suggested_doc_type"] == "termination_letter", f"Expected termination_letter, got {res4['suggested_doc_type']}"
    assert res4["priority"] == "High"
    assert res4["trigger_reason"] == "Involuntary separation / Termination recorded"

    # Case 5: Increment detection -> Increment Letter
    c5 = {"id": 105, "candidate_name": "Meera Joshi", "pay_grade_changed": True}
    res5 = smart_rule_detector.classify_candidate_document_need(c5)
    assert res5["suggested_doc_type"] == "increment_letter", f"Expected increment_letter, got {res5['suggested_doc_type']}"
    assert res5["priority"] == "Normal"
    assert res5["trigger_reason"] == "Salary/Pay Grade revision detected"

    # Case 6: Active joinee WITH prior offer letter on file -> None
    c6 = {"id": 106, "candidate_name": "Sneha Roy", "status": "Joined", "employment_status": "Active"}
    res6 = smart_rule_detector.classify_candidate_document_need(c6, history=[{"document_type": "offer_letter"}])
    assert res6["suggested_doc_type"] == "none", f"Expected none, got {res6['suggested_doc_type']}"
    assert res6["priority"] == "Normal"
    assert res6["trigger_reason"] == "Profile up to date / No document triggered"

    # Case 7: Test batch scanner does not crash and returns well-formed items
    batch_res = smart_rule_detector.scan_all_candidates_for_document_needs()
    assert isinstance(batch_res, list)
    for item in batch_res[:5]:
        assert "candidate_id" in item
        assert "suggested_doc_type" in item
        assert "trigger_reason" in item
        assert "priority" in item
        assert "missing_fields" in item
        assert item["suggested_doc_type"] != "none"

    print("SUCCESS: Task 3 Smart Rule Detector classified all scenarios accurately.")

if __name__ == "__main__":
    run_test()
