"""
Unit Test: test_dfy_policy_service.py
Verifies DFY HR Manual 2025 knowledge ingestion, search relevance,
Article citations, and quick-rule lookup for non-technical HR users.
"""

import os
import sys

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from services import dfy_policy_service


def run_tests():
    print("=" * 70)
    print("RUNNING TASK 1 TESTS: DFY HR MANUAL 2025 POLICY SERVICE")
    print("=" * 70)

    # 1. Test knowledge JSON file existence and article count
    print("\n[TEST 1] Verifying policy knowledge base structure...")
    articles = dfy_policy_service.get_all_policy_articles()
    assert len(articles) == 10, f"Expected 10 Articles in DFY HR Manual, got {len(articles)}"
    print(f"  ✓ Successfully loaded {len(articles)} official DFY HR Articles.")

    for art in articles:
        assert "article_num" in art, "Missing article_num"
        assert "title" in art, "Missing title"
        assert "summary" in art, "Missing summary"
        assert "full_text" in art, "Missing full_text"
        assert len(art["summary"]) > 20, f"Summary too short for Article {art['article_num']}"

    # 2. Test specific keyword and natural query searches
    print("\n[TEST 2] Testing policy search queries...")

    # Query 1: Probation
    prob_res = dfy_policy_service.search_dfy_policy("probation period kitne din ka hota hai")
    assert len(prob_res) > 0, "No results for probation query"
    top_prob = prob_res[0]
    print(f"  ✓ Probation Query matched: Article {top_prob['article_num']} - '{top_prob['title']}'")
    assert top_prob["article_num"] in (2, 3), f"Expected Article 2 or 3 for probation, got {top_prob['article_num']}"
    assert "probation" in top_prob["full_text"].lower()

    # Query 2: Casual / Sick Leaves
    leave_res = dfy_policy_service.search_dfy_policy("casual leave sick leave rules")
    assert len(leave_res) > 0, "No results for leave query"
    top_leave = leave_res[0]
    print(f"  ✓ Leave Query matched: Article {top_leave['article_num']} - '{top_leave['title']}'")
    assert top_leave["article_num"] == 4, f"Expected Article 4 for leaves, got {top_leave['article_num']}"

    # Query 3: Working Hours 9:30 AM to 5:30 PM
    hours_res = dfy_policy_service.search_dfy_policy("office working hours time")
    assert len(hours_res) > 0, "No results for working hours query"
    top_hours = hours_res[0]
    print(f"  ✓ Working Hours Query matched: Article {top_hours['article_num']} - '{top_hours['title']}'")
    assert "9:30" in top_hours["full_text"] or "hours" in top_hours["full_text"].lower()

    # Query 4: Resignation & Notice Period
    notice_res = dfy_policy_service.search_dfy_policy("resignation notice period relieving letter")
    assert len(notice_res) > 0, "No results for notice query"
    top_notice = notice_res[0]
    print(f"  ✓ Notice Query matched: Article {top_notice['article_num']} - '{top_notice['title']}'")
    assert top_notice["article_num"] == 5, f"Expected Article 5 for termination/resignation, got {top_notice['article_num']}"

    # Query 5: Medical Insurance & Benefits
    ins_res = dfy_policy_service.search_dfy_policy("medical insurance group benefits")
    assert len(ins_res) > 0, "No results for insurance query"
    top_ins = ins_res[0]
    print(f"  ✓ Insurance Query matched: Article {top_ins['article_num']} - '{top_ins['title']}'")
    assert top_ins["article_num"] == 6, f"Expected Article 6 for benefits, got {top_ins['article_num']}"

    # 3. Test Top 5 Pinned Quick-Rule Lookups
    print("\n[TEST 3] Testing Pinned Quick-Rules...")
    pinned_keys = ["probation", "leaves", "working_hours", "notice_period", "insurance"]
    for k in pinned_keys:
        rule = dfy_policy_service.get_quick_rule(k)
        assert rule is not None, f"Quick rule for '{k}' returned None"
        assert "headline" in rule and "article_ref" in rule and "plain_hinglish" in rule
        print(f"  ✓ Quick Rule [{k}]: Article {rule['article_ref']} -> {rule['headline']}")

    print("\n" + "=" * 70)
    print("ALL TASK 1 TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
