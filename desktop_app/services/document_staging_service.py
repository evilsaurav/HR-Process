"""
Service: document_staging_service.py
Purpose: Backend staging engine for HR document generation, inline corrections,
and atomic bulk dispatch.

Features:
- Draft generation to staging queue without consuming sequence numbers
- DOCX generation + optional PDF conversion
- Personalized AI email cover generation & data completeness auditing
- Instant inline corrections with automated document regeneration
- Sequence-safe atomic bulk dispatch ("Final Go") with reference stamping and email transmission
"""

import os
import re
import datetime
import logging
import threading
from typing import Dict, Any, Optional, List, Callable, Tuple

import docx
from docx.shared import Pt

from config import DESKTOP_APP_DIR
from database import db_manager
from services import (
    document_generation_service,
    pdf_converter_service,
    ai_service,
    email_service,
)
from services.placeholder_engine import replace_placeholders_in_docx

logger = logging.getLogger(__name__)

# Base output paths
OUTPUT_DIR = os.path.join(DESKTOP_APP_DIR, "output")
STAGED_DIR = os.path.join(OUTPUT_DIR, "staged_documents")
os.makedirs(STAGED_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _generate_staged_filename(candidate: dict, candidate_id: int, document_type: str, ext: str = ".docx") -> str:
    """Generates a clean, unique file path for staged draft documents."""
    cand_name_raw = str(candidate.get("candidate_name") or f"cand_{candidate_id}").strip()
    emp_prefix_raw = str(candidate.get("employee_number") or candidate_id).strip()
    cand_name_safe = re.sub(r'[\\/*?:"<>|\s]+', '_', cand_name_raw).strip('_')
    emp_prefix = re.sub(r'[\\/*?:"<>|]+', '-', emp_prefix_raw).strip('-')
    doc_type_clean = re.sub(r'[\\/*?:"<>|\s]+', '_', str(document_type).lower()).strip('_')
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"staged_{emp_prefix}_{cand_name_safe}_{doc_type_clean}_{timestamp}{ext}"
    return os.path.join(STAGED_DIR, filename)


def _get_draft_reference_placeholder(candidate_id: int) -> str:
    """
    Returns a non-consuming reference placeholder for drafts.
    Uses preview_next_reference if available without advancing the counter.
    """
    try:
        preview_info = db_manager.preview_next_reference("hr_reference")
        if preview_info and not preview_info.get("exhausted"):
            formatted = preview_info.get("formatted", f"DFY/HR/DRAFT/{candidate_id}")
            return f"DRAFT/{formatted}"
    except Exception as ex:
        logger.debug(f"Could not preview reference sequence: {ex}")
    return f"DFY/HR/DRAFT/{candidate_id}"


def _resolve_template_for_staging(
    document_type: str,
    candidate: dict,
    manual_designation_override: Optional[str] = None
) -> Tuple[bool, Optional[str], List[str], Optional[str]]:
    """
    Resolves the template path for a given document type and candidate.
    Provides intelligent fallback to available templates if candidate's designation
    lacks an exact template match.
    """
    res = document_generation_service.resolve_template(
        document_type=document_type,
        candidate=candidate,
        manual_designation_override=manual_designation_override
    )
    if res.get("found"):
        return True, res.get("template_path"), res.get("available_designations", []), res.get("matched_designation")

    avail = res.get("available_designations", [])
    if avail:
        # Check partial word match against candidate designation
        cand_desig = str(candidate.get("applied_designation") or "").lower()
        best_match = None
        for label in avail:
            words = [w for w in re.split(r'\W+', label.lower()) if len(w) > 3]
            if any(w in cand_desig for w in words):
                best_match = label
                break
        fallback_choice = best_match or avail[0]
        fb_res = document_generation_service.resolve_template(
            document_type=document_type,
            candidate=candidate,
            manual_designation_override=fallback_choice
        )
        if fb_res.get("found"):
            return True, fb_res.get("template_path"), avail, fallback_choice

    return False, None, avail, None


def _render_document_to_file(
    template_path: str,
    candidate: dict,
    document_type: str,
    extra_fields: dict,
    reference_text: str,
    dest_docx_path: str
) -> None:
    """Renders placeholders and stamps reference into docx and saves to destination."""
    doc = docx.Document(template_path)
    mapping = document_generation_service.build_placeholder_mapping(candidate, document_type, extra_fields)
    norm_type = document_generation_service.normalize_document_type(document_type)

    if norm_type in ["experience_certificate", "salary_certificate"]:
        document_generation_service.inject_certificate_paragraphs(doc, mapping, document_type)
    else:
        replace_placeholders_in_docx(doc, mapping)

    date_text = document_generation_service.get_document_reference_date(candidate, document_type, extra_fields)
    document_generation_service.insert_reference_and_date(doc, reference_text, date_text, document_type)
    doc.save(dest_docx_path)


def _restamp_docx_with_official_reference(
    docx_path: str,
    candidate: dict,
    document_type: str,
    extra_fields: dict,
    official_reference: str
) -> bool:
    """
    Replaces the placeholder reference number in an existing DOCX with the official reference.
    If no reference line is found, inserts it cleanly.
    """
    if not os.path.exists(docx_path):
        return False
    try:
        doc = docx.Document(docx_path)
        date_text = document_generation_service.get_document_reference_date(candidate, document_type, extra_fields)
        norm_type = document_generation_service.normalize_document_type(document_type)

        stamped = False
        for para in doc.paragraphs:
            if "Reference No:" in para.text:
                para.text = ""
                if norm_type in ["experience_certificate", "salary_certificate"]:
                    text = f"Reference No: {official_reference}" + (" " * 69) + f"Date: {date_text}"
                    run = para.add_run(text)
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(12)
                    run.bold = True
                else:
                    text = f"Reference No: {official_reference}" + (" " * 81) + f"Dated: {date_text}"
                    run = para.add_run(text)
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(11)
                    run.bold = True
                stamped = True
                break

        if not stamped:
            document_generation_service.insert_reference_and_date(doc, official_reference, date_text, document_type)

        doc.save(docx_path)
        return True
    except Exception as ex:
        logger.error(f"Error restamping document {docx_path}: {ex}")
        return False


def _safe_call_callback(
    callback: Optional[Callable],
    idx: int,
    total: int,
    status: str,
    staging_id: Optional[int] = None,
    error: Optional[str] = None
) -> None:
    """Safely dispatches progress callback supporting multiple caller signatures."""
    if not callback:
        return
    try:
        callback(idx, total, status, staging_id, error)
    except TypeError:
        try:
            callback(idx, total, status)
        except Exception as e:
            logger.debug(f"Progress callback error: {e}")
    except Exception as e:
        logger.debug(f"Progress callback error: {e}")


# ---------------------------------------------------------------------------
# Core Public API
# ---------------------------------------------------------------------------

def generate_draft_to_staging(
    candidate_id: int,
    document_type: str,
    extra_fields: Optional[dict] = None,
    preferred_format: str = "pdf",
    manual_designation_override: Optional[str] = None
) -> dict:
    """
    Validates candidate, generates a non-consuming draft DOCX and optional PDF,
    generates personalized email draft, audits candidate completeness, and inserts
    record into document_staging with status 'Staged'.

    Returns:
        {"success": True, "staging_id": id, "doc_file_path": path, "pdf_file_path": pdf_path, "warnings": warnings}
        OR
        {"success": False, "error": msg}
    """
    extra_fields = extra_fields or {}
    preferred_format = (preferred_format or "pdf").lower()

    # 1. Validate candidate exists
    candidate = db_manager.get_candidate_by_id(candidate_id)
    if not candidate:
        return {"success": False, "error": f"Candidate with ID {candidate_id} not found."}

    # 2. Resolve template
    found, template_path, avail_labels, matched_desig = _resolve_template_for_staging(
        document_type=document_type,
        candidate=candidate,
        manual_designation_override=manual_designation_override
    )
    if not found or not template_path:
        return {
            "success": False,
            "error": f"We could not find a matching template for document type '{document_type}'.",
            "available_designations": avail_labels
        }

    # 3. Generate draft reference placeholder (non-consuming)
    draft_ref = _get_draft_reference_placeholder(candidate_id)

    # 4. Render DOCX into staged output directory
    docx_path = _generate_staged_filename(candidate, candidate_id, document_type, ".docx")
    try:
        _render_document_to_file(
            template_path=template_path,
            candidate=candidate,
            document_type=document_type,
            extra_fields=extra_fields,
            reference_text=draft_ref,
            dest_docx_path=docx_path
        )
    except Exception as ex:
        logger.error(f"Failed to generate draft document: {ex}", exc_info=True)
        return {"success": False, "error": f"Failed to generate draft document: {ex}"}

    # 5. Convert to PDF if preferred_format is pdf
    pdf_file_path = None
    if preferred_format == "pdf":
        pdf_dest = os.path.splitext(docx_path)[0] + ".pdf"
        try:
            conv_ok, conv_path, _ = pdf_converter_service.convert_docx_to_pdf(docx_path, pdf_dest)
            if conv_ok and conv_path and os.path.exists(conv_path):
                pdf_file_path = conv_path
        except Exception as ex:
            logger.warning(f"PDF conversion failed (draft will remain docx): {ex}")

    # 6. Generate email draft using AI service
    email_draft = ai_service.generate_email_cover(candidate, document_type)
    subject = email_draft.get("subject", f"{document_type} - Doctors For You")
    body = email_draft.get("body", "")

    # 7. Audit completeness
    warnings = ai_service.audit_candidate_data_completeness(candidate, document_type)
    if matched_desig and candidate.get("applied_designation") and matched_desig.lower() != candidate.get("applied_designation", "").lower():
        warnings.append(f"Template fallback used: '{matched_desig}' for candidate designation '{candidate.get('applied_designation')}'.")

    recipient_email = candidate.get("email") or candidate.get("work_email") or candidate.get("personal_email") or ""
    recipient_name = candidate.get("candidate_name") or candidate.get("display_name") or ""

    # 8. Insert into document_staging table
    try:
        staging_id = db_manager.create_staging_record(
            candidate_id=candidate_id,
            document_type=document_type,
            status="Staged",
            doc_file_path=docx_path,
            pdf_file_path=pdf_file_path,
            preferred_format=preferred_format,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            email_subject=subject,
            email_body=body,
            reference_number=draft_ref,
            extra_fields=extra_fields,
            discrepancy_warnings=warnings
        )
    except Exception as ex:
        logger.error(f"Failed to create staging record: {ex}", exc_info=True)
        return {"success": False, "error": f"Failed to record draft in staging database: {ex}"}

    return {
        "success": True,
        "staging_id": staging_id,
        "doc_file_path": docx_path,
        "pdf_file_path": pdf_file_path,
        "warnings": warnings
    }


def inline_fix_and_regenerate(
    staging_id: int,
    updated_candidate_fields: dict,
    updated_extra_fields: Optional[dict] = None
) -> dict:
    """
    Updates candidate record with corrected fields, re-generates draft DOCX & PDF,
    re-runs data completeness check, and updates document_staging record.

    Returns:
        {"success": True, "staging_id": staging_id, "doc_file_path": path, "pdf_file_path": pdf_path, "warnings": warnings}
        OR
        {"success": False, "error": msg}
    """
    staging_rec = db_manager.get_staging_record_by_id(staging_id)
    if not staging_rec:
        return {"success": False, "error": f"Staging record with ID {staging_id} not found."}

    candidate_id = staging_rec["candidate_id"]

    # 1. Update candidate record in candidates table
    if updated_candidate_fields:
        update_ok = db_manager.update_candidate(candidate_id, updated_candidate_fields)
        if not update_ok:
            logger.warning(f"Could not update candidate {candidate_id} via update_candidate, trying direct sync.")

    # Refresh candidate record
    candidate = db_manager.get_candidate_by_id(candidate_id)
    if not candidate:
        return {"success": False, "error": f"Candidate with ID {candidate_id} not found after update."}

    # 2. Merge extra fields
    extra_fields = dict(staging_rec.get("extra_fields") or {})
    if updated_extra_fields:
        extra_fields.update(updated_extra_fields)

    document_type = staging_rec["document_type"]
    preferred_format = (staging_rec.get("preferred_format") or "pdf").lower()

    # 3. Re-resolve template (in case designation changed)
    found, template_path, avail_labels, matched_desig = _resolve_template_for_staging(
        document_type=document_type,
        candidate=candidate
    )
    if not found or not template_path:
        return {
            "success": False,
            "error": f"No template found for document type '{document_type}'.",
            "available_designations": avail_labels
        }

    # 4. Re-render draft DOCX
    doc_file_path = staging_rec.get("doc_file_path")
    if not doc_file_path or not os.path.exists(os.path.dirname(doc_file_path)):
        doc_file_path = _generate_staged_filename(candidate, candidate_id, document_type, ".docx")

    draft_ref = staging_rec.get("reference_number") or _get_draft_reference_placeholder(candidate_id)
    try:
        _render_document_to_file(
            template_path=template_path,
            candidate=candidate,
            document_type=document_type,
            extra_fields=extra_fields,
            reference_text=draft_ref,
            dest_docx_path=doc_file_path
        )
    except Exception as ex:
        logger.error(f"Failed to re-generate document during inline fix: {ex}", exc_info=True)
        return {"success": False, "error": f"Failed to re-generate document: {ex}"}

    # 5. Convert to PDF if preferred_format is pdf
    pdf_file_path = staging_rec.get("pdf_file_path")
    if preferred_format == "pdf":
        if not pdf_file_path:
            pdf_file_path = os.path.splitext(doc_file_path)[0] + ".pdf"
        try:
            conv_ok, conv_path, _ = pdf_converter_service.convert_docx_to_pdf(doc_file_path, pdf_file_path)
            if conv_ok and conv_path and os.path.exists(conv_path):
                pdf_file_path = conv_path
            else:
                pdf_file_path = None
        except Exception as ex:
            logger.warning(f"PDF re-conversion failed: {ex}")
            pdf_file_path = None
    else:
        pdf_file_path = None

    # 6. Re-run data completeness check
    warnings = ai_service.audit_candidate_data_completeness(candidate, document_type)
    if matched_desig and candidate.get("applied_designation") and matched_desig.lower() != candidate.get("applied_designation", "").lower():
        warnings.append(f"Template fallback used: '{matched_desig}' for candidate designation '{candidate.get('applied_designation')}'.")

    # 7. Refresh recipient email & email cover
    email_draft = ai_service.generate_email_cover(candidate, document_type)
    recipient_email = candidate.get("email") or candidate.get("work_email") or candidate.get("personal_email") or staging_rec.get("recipient_email", "")
    recipient_name = candidate.get("candidate_name") or candidate.get("display_name") or staging_rec.get("recipient_name", "")

    # 8. Update staging record
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db_manager.update_staging_record(
        staging_id,
        doc_file_path=doc_file_path,
        pdf_file_path=pdf_file_path,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        email_subject=email_draft.get("subject", staging_rec.get("email_subject")),
        email_body=email_draft.get("body", staging_rec.get("email_body")),
        extra_fields=extra_fields,
        discrepancy_warnings=warnings,
        updated_at=now_str
    )

    return {
        "success": True,
        "staging_id": staging_id,
        "doc_file_path": doc_file_path,
        "pdf_file_path": pdf_file_path,
        "warnings": warnings
    }


def _execute_bulk_dispatch(
    staging_ids: List[int],
    on_progress_callback: Optional[Callable] = None
) -> dict:
    """
    Synchronous worker that iterates over staging items, atomically consumes sequence
    numbers, re-stamps documents, sends emails, and logs dispatches.
    """
    count_sent = 0
    count_failed = 0
    errors = []
    total = len(staging_ids)

    for idx, staging_id in enumerate(staging_ids):
        staging_rec = db_manager.get_staging_record_by_id(staging_id)
        if not staging_rec:
            count_failed += 1
            err_msg = f"Staging record with ID {staging_id} not found."
            errors.append(err_msg)
            _safe_call_callback(on_progress_callback, idx + 1, total, "Failed", staging_id, err_msg)
            continue

        cand_id = staging_rec.get("candidate_id")
        candidate = db_manager.get_candidate_by_id(cand_id) if cand_id else None
        doc_type = staging_rec.get("document_type")
        extra_fields = staging_rec.get("extra_fields") or {}
        preferred_format = (staging_rec.get("preferred_format") or "pdf").lower()
        recipient_email = staging_rec.get("recipient_email") or (candidate.get("email") if candidate else "")
        recipient_name = staging_rec.get("recipient_name") or (candidate.get("candidate_name") if candidate else "")
        subject = staging_rec.get("email_subject") or f"{doc_type} - Doctors For You"
        body = staging_rec.get("email_body") or ""
        doc_file_path = staging_rec.get("doc_file_path")
        pdf_file_path = staging_rec.get("pdf_file_path")

        # 1. Recipient email validation
        if not recipient_email:
            count_failed += 1
            err_msg = f"Candidate (ID {cand_id}) has no recipient email address."
            errors.append(err_msg)
            db_manager.update_staging_record(staging_id, status="Failed")
            _safe_call_callback(on_progress_callback, idx + 1, total, "Failed", staging_id, err_msg)
            continue

        # 2. Atomically consume official reference number sequence
        official_ref, ref_err = db_manager.consume_next_reference("hr_reference")
        if ref_err or not official_ref:
            count_failed += 1
            err_msg = f"Failed to allocate official reference number for ID {staging_id}: {ref_err or 'Sequence exhausted'}"
            errors.append(err_msg)
            db_manager.update_staging_record(staging_id, status="Failed")
            _safe_call_callback(on_progress_callback, idx + 1, total, "Failed", staging_id, err_msg)
            continue

        # 3. Re-stamp the DOCX with the official reference number
        restamped = False
        if doc_file_path and os.path.exists(doc_file_path):
            restamped = _restamp_docx_with_official_reference(
                docx_path=doc_file_path,
                candidate=candidate or {},
                document_type=doc_type,
                extra_fields=extra_fields,
                official_reference=official_ref
            )

        if not restamped:
            # Fallback: re-render cleanly
            found, t_path, _, _ = _resolve_template_for_staging(doc_type, candidate or {})
            if found and t_path:
                if not doc_file_path:
                    doc_file_path = _generate_staged_filename(candidate or {}, cand_id, doc_type, ".docx")
                _render_document_to_file(t_path, candidate or {}, doc_type, extra_fields, official_ref, doc_file_path)

        # 4. Re-export PDF if format is PDF
        if preferred_format == "pdf" and doc_file_path and os.path.exists(doc_file_path):
            if not pdf_file_path:
                pdf_file_path = os.path.splitext(doc_file_path)[0] + ".pdf"
            try:
                conv_ok, conv_path, _ = pdf_converter_service.convert_docx_to_pdf(doc_file_path, pdf_file_path)
                if conv_ok and conv_path and os.path.exists(conv_path):
                    pdf_file_path = conv_path
                else:
                    pdf_file_path = None
            except Exception as ex:
                logger.warning(f"Re-exporting PDF failed during dispatch: {ex}")
                pdf_file_path = None
        else:
            pdf_file_path = None

        # 5. Choose attachment based on preferred_format
        attachment_to_send = None
        if preferred_format == "pdf" and pdf_file_path and os.path.exists(pdf_file_path):
            attachment_to_send = pdf_file_path
        elif doc_file_path and os.path.exists(doc_file_path):
            attachment_to_send = doc_file_path

        # 6. Send email using email_service
        send_ok, send_msg = email_service.send_email_smtp(
            to_addr=recipient_email,
            subject=subject,
            body=body,
            attachment_path=attachment_to_send,
            candidate_id=cand_id,
            document_type=doc_type,
            recipient_name=recipient_name,
            sent_by="HR Desktop (Final Go)"
        )

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 7. Update status and audit logs
        if send_ok:
            count_sent += 1
            db_manager.update_staging_record(
                staging_id,
                status="Dispatched",
                reference_number=official_ref,
                doc_file_path=doc_file_path,
                pdf_file_path=pdf_file_path,
                dispatched_at=now_str
            )
            db_manager.log_document_generation(
                candidate_id=cand_id,
                document_type=doc_type,
                reference_number=official_ref,
                extra_fields_dict=extra_fields,
                file_path=attachment_to_send or doc_file_path,
                generated_by="HR Desktop (Final Go)"
            )
            _safe_call_callback(on_progress_callback, idx + 1, total, "Dispatched", staging_id, None)
        else:
            count_failed += 1
            err_msg = f"Failed to dispatch email to {recipient_email}: {send_msg}"
            errors.append(err_msg)
            db_manager.update_staging_record(
                staging_id,
                status="Failed",
                reference_number=official_ref,
                doc_file_path=doc_file_path,
                pdf_file_path=pdf_file_path
            )
            _safe_call_callback(on_progress_callback, idx + 1, total, "Failed", staging_id, err_msg)

    return {
        "total": total,
        "sent": count_sent,
        "failed": count_failed,
        "errors": errors
    }


def final_go_dispatch(
    staging_ids: List[int],
    send_async: bool = False,
    on_progress_callback: Optional[Callable] = None
) -> dict:
    """
    Executes sequence-safe bulk dispatch for selected staged documents:
    - Atomically consumes official reference numbers via db_manager.consume_next_reference
    - Re-stamps documents with official Reference Number and re-converts PDF if requested
    - Sends personalized emails with attachments via email_service
    - Updates staging records to 'Dispatched' (or 'Failed') and writes audit logs
    - Supports synchronous execution or asynchronous execution via background thread

    Returns summary:
        {"total": int, "sent": int, "failed": int, "errors": list}
        OR if async:
        {"started": True, "total": int, "status": "processing"}
    """
    if not staging_ids:
        return {"total": 0, "sent": 0, "failed": 0, "errors": []}

    if send_async:
        def _worker():
            _execute_bulk_dispatch(staging_ids, on_progress_callback)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return {"started": True, "total": len(staging_ids), "status": "processing"}

    return _execute_bulk_dispatch(staging_ids, on_progress_callback)
