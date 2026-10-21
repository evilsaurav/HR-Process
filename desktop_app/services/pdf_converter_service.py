"""
PDF Converter Service
Provides DOCX to PDF conversion using Microsoft Word COM automation (win32com)
with graceful fallback if Word or COM is unavailable.
"""

import os
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

try:
    import win32com.client
    import pythoncom
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False
    win32com = None
    pythoncom = None


def is_pdf_conversion_available() -> bool:
    """
    Check if Microsoft Word COM automation is available and responsive on the host.
    
    Returns:
        bool: True if Word COM is available, False otherwise.
    """
    if not HAS_WIN32COM:
        logger.warning("win32com or pythoncom is not installed.")
        return False

    word = None
    co_initialized = False
    try:
        if pythoncom:
            pythoncom.CoInitialize()
            co_initialized = True

        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        _ = word.Version
        return True
    except Exception as e:
        logger.warning("Word COM automation check failed: %s", e)
        return False
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception as e:
                logger.debug("Error quitting Word during availability check: %s", e)
        if co_initialized and pythoncom:
            try:
                pythoncom.CoUninitialize()
            except Exception as e:
                logger.debug("Error during CoUninitialize: %s", e)


def convert_docx_to_pdf(docx_path: str, pdf_path: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Convert a DOCX document to PDF format using Microsoft Word COM automation.

    Args:
        docx_path: Absolute or relative path to the input .docx file.
        pdf_path: Optional destination path for the output .pdf file.
                  If omitted, saved in the same directory with .pdf extension.

    Returns:
        Tuple[bool, Optional[str], Optional[str]]:
            - success: True if PDF was generated successfully, False otherwise.
            - output_path: Absolute path to the generated PDF (or None if failed).
            - error_message: Descriptive error message if conversion failed (None on success).
    """
    if not os.path.exists(docx_path):
        err = f"Source DOCX file not found: {docx_path}"
        logger.warning(err)
        return False, None, err

    if not HAS_WIN32COM:
        err = "win32com is not installed or available on this system."
        logger.warning(err)
        return False, None, err

    abs_docx = os.path.abspath(docx_path)
    if not pdf_path:
        base, _ = os.path.splitext(abs_docx)
        abs_pdf = base + ".pdf"
    else:
        abs_pdf = os.path.abspath(pdf_path)

    os.makedirs(os.path.dirname(abs_pdf), exist_ok=True)

    word = None
    doc = None
    co_initialized = False

    try:
        if pythoncom:
            pythoncom.CoInitialize()
            co_initialized = True

        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone

        # 17 is wdFormatPDF in Word COM
        doc = word.Documents.Open(abs_docx, ReadOnly=True)
        doc.SaveAs(abs_pdf, FileFormat=17)

        if os.path.exists(abs_pdf) and os.path.getsize(abs_pdf) > 0:
            logger.info("Successfully converted %s to %s", abs_docx, abs_pdf)
            return True, abs_pdf, None
        else:
            err = f"Conversion finished but output PDF file was not created or is empty: {abs_pdf}"
            logger.warning(err)
            return False, None, err

    except Exception as e:
        err = f"Word COM PDF conversion failed: {str(e)}"
        logger.warning(err)
        return False, None, err

    finally:
        if doc is not None:
            try:
                # 0 is wdDoNotSaveChanges
                doc.Close(SaveChanges=0)
            except Exception as e:
                logger.debug("Error closing document: %s", e)
        if word is not None:
            try:
                word.Quit()
            except Exception as e:
                logger.debug("Error quitting Word application: %s", e)
        if co_initialized and pythoncom:
            try:
                pythoncom.CoUninitialize()
            except Exception as e:
                logger.debug("Error during CoUninitialize: %s", e)
