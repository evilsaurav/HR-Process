"""
Script: create_test_keka_sheet.py
Purpose: Generates a sample Keka HRMS export sheet (.xlsx) for testing Keka Sync.
Includes:
- Row 1: Matched active employee with blank relieving date (for data-preservation testing)
- Row 2: Matched resigned employee with date (2024-11-30)
- Row 3: Unmatched candidate with dummy name ('Rohit Deshmukh')
- Row 4: Matched resigned employee with alternative date format (15/12/2024)
"""

import os
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(DESKTOP_APP_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

test_file_path = os.path.join(OUTPUT_DIR, "test_keka_export.xlsx")

data = [
    {
        "Employee Code": "DFY-1001",
        "Employee Name": "Test Kumar",
        "Contact Number": "+91 98765 43210",  # Matches Test Kumar (9876543210)
        "Relieving Date": ""                  # Blank -> Tests that existing DB relieving_date is preserved
    },
    {
        "Employee Code": "DFY-1002",
        "Employee Name": "Priya Sharma",
        "Contact Number": "9123456789",       # Matches Priya Sharma (9123456789)
        "Relieving Date": "2024-11-30"        # Resigned employee with ISO date
    },
    {
        "Employee Code": "DFY-9999",
        "Employee Name": "Rohit Deshmukh",    # Unmatched candidate
        "Contact Number": "9998887776",       # Mobile not in DB
        "Relieving Date": ""
    },
    {
        "Employee Code": "DFY-1006",
        "Employee Name": "Anjali Singh",
        "Contact Number": "9822334455",       # Matches Anjali Singh (9822334455)
        "Relieving Date": "15/12/2024"        # Resigned employee with DD/MM/YYYY date
    }
]

df = pd.DataFrame(data)
df.to_excel(test_file_path, index=False)
print(f"Test Keka export sheet created at:\n  {test_file_path}")
print("\nSheet content:")
print(df)
