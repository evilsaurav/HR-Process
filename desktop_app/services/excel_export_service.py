"""
Service: excel_export_service.py
Purpose: Reusable Excel (.xlsx) export utility for data reports and audit logs.
Includes automated column width auto-adjustment for clean HR readability.
"""

import os
from typing import List, Dict, Any
import pandas as pd


def export_to_excel(data: List[Dict[str, Any]], output_path: str, sheet_name: str = "Report") -> str:
    """
    Exports a list of dictionaries to an Excel (.xlsx) file using openpyxl.
    Automatically formats column widths based on content length for readability.
    Handles empty data gracefully without crashing.

    Arguments:
        data: List of dictionaries representing table rows.
        output_path: Absolute or relative destination file path.
        sheet_name: Name of the worksheet tab.

    Returns:
        output_path on success.
    """
    # Ensure parent directory exists
    parent_dir = os.path.dirname(os.path.abspath(output_path))
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    df = pd.DataFrame(data if data else [])

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        worksheet = writer.sheets[sheet_name]

        # Auto-adjust column widths based on header and cell content length
        for col in worksheet.columns:
            col_letter = col[0].column_letter
            max_len = 0
            for cell in col:
                val_str = str(cell.value or "")
                max_len = max(max_len, len(val_str))
            # Set width with extra padding, constrained between min 12 and max 60
            calculated_width = max(max_len + 4, 12)
            worksheet.column_dimensions[col_letter].width = min(calculated_width, 60)

    return output_path
