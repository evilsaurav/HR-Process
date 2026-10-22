"""
Service: zip_export_service.py
Purpose: Packages multiple staged or dispatched documents into an organized
ZIP archive for Accounts, Management, and Donor/Auditor review.
"""

import os
import zipfile
import datetime
from typing import List, Tuple
from config import DESKTOP_APP_DIR


def create_bulk_document_zip(
    file_paths: List[str],
    zip_filename: str = "",
    target_zip_path: str = ""
) -> Tuple[bool, str, str]:
    """
    Creates a ZIP archive containing all valid files from `file_paths`.
    Returns (success: bool, zip_path: str, error_message: str).
    """
    valid_files = [f for f in file_paths if f and os.path.exists(f)]
    if not valid_files:
        return False, "", "No valid document files found to package."

    try:
        if not target_zip_path:
            out_dir = os.path.join(DESKTOP_APP_DIR, "output")
            os.makedirs(out_dir, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = zip_filename or f"DFY_Documents_Package_{ts}.zip"
            if not fname.endswith(".zip"):
                fname += ".zip"
            target_zip_path = os.path.join(out_dir, fname)
        else:
            os.makedirs(os.path.dirname(os.path.abspath(target_zip_path)), exist_ok=True)

        with zipfile.ZipFile(target_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            added_names = set()
            for path in valid_files:
                base = os.path.basename(path)
                # Ensure unique arcnames in zip
                arcname = base
                counter = 1
                while arcname in added_names:
                    root, ext = os.path.splitext(base)
                    arcname = f"{root}_{counter}{ext}"
                    counter += 1
                added_names.add(arcname)
                zf.write(path, arcname=arcname)

        return True, target_zip_path, ""
    except Exception as e:
        return False, "", f"Failed to create ZIP package: {str(e)}"
