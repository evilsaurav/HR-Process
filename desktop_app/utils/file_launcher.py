"""
File Launcher Utility: file_launcher.py
Purpose: Provides native OS integration to launch exported files or reveal
their containing folders directly from the DFY HRMS desktop application.
"""

import os
import subprocess
import sys
from typing import Tuple


def open_file_externally(file_path: str) -> Tuple[bool, str]:
    """
    Opens the target file in the host OS default associated application
    (e.g., Microsoft Excel, WPS Office, Acrobat Reader).

    Args:
        file_path: Path to the target file.

    Returns:
        (success: bool, message: str)
    """
    if not file_path or not os.path.exists(file_path):
        return False, "File does not exist."

    try:
        abs_path = os.path.abspath(file_path)
        if hasattr(os, "startfile"):
            os.startfile(abs_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", abs_path])
        else:
            subprocess.Popen(["xdg-open", abs_path])
        return True, "File opened successfully."
    except Exception as e:
        return False, str(e)


def open_folder_and_select(file_path: str) -> Tuple[bool, str]:
    """
    Opens Windows Explorer (or OS file manager) and selects / highlights
    the target file within its parent directory.

    Args:
        file_path: Path to the target file or directory.

    Returns:
        (success: bool, message: str)
    """
    if not file_path or not os.path.exists(file_path):
        return False, "File does not exist."

    try:
        abs_path = os.path.abspath(file_path)
        if sys.platform == "win32" or hasattr(os, "startfile"):
            subprocess.Popen(f'explorer /select,"{abs_path}"')
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", abs_path])
        else:
            folder = os.path.dirname(abs_path) if os.path.isfile(abs_path) else abs_path
            subprocess.Popen(["xdg-open", folder])
        return True, "Folder opened successfully."
    except Exception as e:
        return False, str(e)
