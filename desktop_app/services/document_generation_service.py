"""
Service: document_generation_service.py
Purpose: Complete document generation orchestrator for HR documents:
- Offer Letters, Extension Letters, Increment Letters, Termination Letters (placeholder-based)
- Experience and Salary Certificates (dynamic paragraph injection)
Provides preview generation (non-consuming reference sequence) and final document generation (consuming reference sequence + audit logging).
"""

import os
import re
import datetime
import docx
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from typing import Dict, Any, Optional, List

from config import DESKTOP_APP_DIR
from database import db_manager
from services.placeholder_engine import replace_placeholders_in_docx
from services.document_formatters import (
    get_title_and_relation,
    format_address_multiline,
    format_date_long,
    calculate_end_date,
    amount_to_indian_words,
    format_currency_inr,
)


def get_document_reference_date(candidate: dict, document_type: str, extra_fields: dict) -> str:
    """
    Determines the appropriate top/reference date according to document type rules.
    - Offer: date_joined (or today fallback)
    - Extension: extension_start_date (or today fallback)
    - Increment: effective_from (or today fallback)
    - Termination: termination_date (or today fallback)
    - Experience/Salary: today's date
    """
    doc_type_lower = (document_type or "").strip().lower()
    raw_date = None
    if doc_type_lower in ["offer", "offer_letter"]:
        raw_date = candidate.get("date_joined")
    elif doc_type_lower in ["extension", "extension_letter"]:
        raw_date = extra_fields.get("extension_start_date") or candidate.get("date_joined")
    elif doc_type_lower in ["increment", "increment_letter"]:
        raw_date = extra_fields.get("effective_from") or candidate.get("date_joined")
    elif doc_type_lower in ["termination", "termination_letter"]:
        raw_date = extra_fields.get("termination_date") or candidate.get("relieving_date")

    if not raw_date:
        raw_date = datetime.datetime.now()

    return format_date_long(raw_date)


def build_placeholder_mapping(candidate: dict, document_type: str, extra_fields: dict) -> dict:
    """
    Builds the complete dictionary of placeholder keys and formatted values.
    Missing/None fields resolve to empty string "" (never crash, never insert 'None').
    """
    if candidate is None:
        candidate = {}
    if extra_fields is None:
        extra_fields = {}

    doc_type_lower = (document_type or "").strip().lower()

    # Base candidate attributes
    candidate_name = str(candidate.get("candidate_name") or "").strip()
    gender = str(candidate.get("gender") or "").strip()
    title, relation = get_title_and_relation(gender)
    father_title = "Mr."
    father_name = str(candidate.get("father_name") or "").strip()
    address_raw = str(candidate.get("full_address") or "").strip()
    full_address = format_address_multiline(address_raw)
    job_title = str(candidate.get("applied_designation") or "").strip()
    department = str(candidate.get("department") or "").strip()
    location = str(candidate.get("contact_location") or "").strip()

    date_joined_raw = candidate.get("date_joined")
    date_joined = format_date_long(date_joined_raw) if date_joined_raw else ""
    end_date = calculate_end_date(date_joined_raw) if date_joined_raw else ""

    salary_raw = extra_fields.get("monthly_gross_salary") or extra_fields.get("gross_salary") or candidate.get("negotiated_salary")
    pay_grade = format_currency_inr(salary_raw) if salary_raw else ""
    salary_words = amount_to_indian_words(salary_raw) if salary_raw else ""

    # Extra fields for extension
    ext_start_raw = extra_fields.get("extension_start_date")
    extension_start_date = format_date_long(ext_start_raw) if ext_start_raw else ""
    extension_end_date = calculate_end_date(ext_start_raw) if ext_start_raw else ""

    # Extra fields for termination
    term_date_raw = extra_fields.get("termination_date")
    termination_date = format_date_long(term_date_raw) if term_date_raw else ""
    reason = str(extra_fields.get("reason") or "").strip()
    notice_period = str(extra_fields.get("notice_period") or "").strip()

    # Extra fields for increment
    eff_from_raw = extra_fields.get("effective_from")
    effective_from = format_date_long(eff_from_raw) if eff_from_raw else ""
    revised_salary_raw = extra_fields.get("revised_pay_grade")
    revised_pay_grade = format_currency_inr(revised_salary_raw) if revised_salary_raw else ""
    revised_salary_words = amount_to_indian_words(revised_salary_raw) if revised_salary_raw else ""
    offer_doc_date_raw = extra_fields.get("offer_letter_document_date")
    offer_letter_document_date = format_date_long(offer_doc_date_raw) if offer_doc_date_raw else ""

    # Extra fields for certificate (experience / salary)
    if "exit_date" in extra_fields:
        exit_raw = extra_fields.get("exit_date")
    else:
        exit_raw = candidate.get("relieving_date")

    if exit_raw and str(exit_raw).strip() != "" and str(exit_raw).strip().lower() not in ["none", "nan", "null"]:
        exit_date = format_date_long(exit_raw)
        is_working = False
    else:
        exit_date = "Till Date"
        is_working = True

    # Gender-based pronouns for certificates
    g_lower = gender.lower()
    if g_lower in ["female", "f", "woman", "girl", "ms", "mrs"]:
        pronoun = "her"
        obj_pronoun = "her"
        subject_pronoun = "She"
    else:
        pronoun = "his"
        obj_pronoun = "him"
        subject_pronoun = "He"

    # Certificate narrative paragraphs
    if is_working:
        main_para = (
            f"This is to certify that {title} {candidate_name} "
            f"{relation} {father_title} {father_name} R/o {full_address} "
            f"is currently working in the capacity of a (Consultant) {job_title} "
            f"at DFY supported {department} {location} "
            f"from {date_joined} to {exit_date}."
        )
    else:
        main_para = (
            f"This is to certify that {title} {candidate_name} "
            f"{relation} {father_title} {father_name} R/o {full_address} "
            f"was working in the capacity of a (Consultant) {job_title} "
            f"at DFY supported {department} {location} "
            f"from {date_joined} to {exit_date}."
        )

    appreciation_para = (
        f"We highly acknowledged {pronoun} hard work, perseverance, and dedication. "
        f"In course of {pronoun} association with us we appreciated {pronoun} sincerity and professionalism."
    )

    future_line = f"We wish {obj_pronoun} success in all {pronoun} future endeavours."

    if is_working:
        salary_para = (
            f"{subject_pronoun} is drawing a total monthly payment of INR {pay_grade} "
            f"({salary_words}). "
            f"Tax deduction is applicable as per existing income tax guidelines. "
            f"We hereby confirm that all the above details are as per our records. "
            f"This letter is issued to {obj_pronoun} on {pronoun} request."
        )
    else:
        salary_para = (
            f"{subject_pronoun} was drawing a total monthly payment of INR {pay_grade} "
            f"({salary_words}). "
            f"Tax deduction was applicable as per existing income tax guidelines. "
            f"We hereby confirm that all the above details are as per our records. "
            f"This letter is issued to {obj_pronoun} on {pronoun} request."
        )

    # Keka Master Fields
    emp_no = str(candidate.get("employee_number") or "").strip()
    first_name = str(candidate.get("first_name") or "").strip()
    last_name = str(candidate.get("last_name") or "").strip()
    display_name = str(candidate.get("display_name") or candidate_name).strip()
    work_email = str(candidate.get("work_email") or "").strip()
    personal_email = str(candidate.get("personal_email") or "").strip()
    mobile_num = str(candidate.get("mobile") or "").strip()
    dob_raw = candidate.get("date_of_birth")
    dob = format_date_long(dob_raw) if dob_raw else ""
    marital_status = str(candidate.get("marital_status") or "").strip()
    marriage_date_raw = candidate.get("marriage_date")
    marriage_date = format_date_long(marriage_date_raw) if marriage_date_raw else ""
    current_addr = str(candidate.get("current_address") or "").strip()
    permanent_addr = str(candidate.get("permanent_address") or "").strip()
    mother_name = str(candidate.get("mother_name") or "").strip()
    spouse_name = str(candidate.get("spouse_name") or "").strip()
    reporting_to = str(candidate.get("reporting_to") or "").strip()
    reporting_mgr_emp_no = str(candidate.get("reporting_manager_emp_no") or "").strip()
    emp_status = str(candidate.get("employment_status") or "").strip()
    worker_type = str(candidate.get("worker_type") or "").strip()
    time_type = str(candidate.get("time_type") or "").strip()
    leave_plan = str(candidate.get("leave_plan") or "").strip()
    shift_policy = str(candidate.get("shift_policy") or "").strip()
    weekly_off_policy = str(candidate.get("weekly_off_policy") or "").strip()
    notice_period_val = str(candidate.get("notice_period") or notice_period or "").strip()
    pan_num = str(candidate.get("pan_number") or "").strip()
    aadhaar_num = str(candidate.get("aadhaar_number") or "").strip()
    pf_num = str(candidate.get("pf_number") or "").strip()
    uan_num = str(candidate.get("uan_number") or "").strip()
    cost_center = str(candidate.get("cost_center") or "").strip()
    exit_status = str(candidate.get("exit_status") or "").strip()
    term_type = str(candidate.get("termination_type") or "").strip()
    term_reason = str(candidate.get("termination_reason") or reason or "").strip()
    blood_group = str(candidate.get("blood_group") or "").strip()
    middle_name = str(candidate.get("middle_name") or "").strip()
    nationality = str(candidate.get("nationality") or "").strip()
    legal_entity = str(candidate.get("legal_entity") or "").strip()
    business_unit = str(candidate.get("business_unit") or "").strip()
    band = str(candidate.get("band") or "").strip()

    res = {
        # Recipient & Identity
        "TITLE": title,
        "Full Name": candidate_name,
        "Candidate Name": candidate_name,
        "candidate_name": candidate_name,
        "Display Name": display_name,
        "display_name": display_name,
        "First Name": first_name,
        "first_name": first_name,
        "Middle Name": middle_name,
        "middle_name": middle_name,
        "Blood Group": blood_group,
        "blood_group": blood_group,
        "Nationality": nationality,
        "nationality": nationality,
        "Legal Entity": legal_entity,
        "legal_entity": legal_entity,
        "Business Unit": business_unit,
        "business_unit": business_unit,
        "Band": band,
        "band": band,
        "Last Name": last_name,
        "last_name": last_name,
        "Employee Number": emp_no,
        "employee_number": emp_no,
        "RELATION": relation,
        "FATHER_TITLE": father_title,
        "Father Name": father_name,
        "father_name": father_name,
        "Mother Name": mother_name,
        "mother_name": mother_name,
        "Spouse Name": spouse_name,
        "spouse_name": spouse_name,
        "Full Address": full_address,
        "full_address": full_address,
        "Current Address": current_addr,
        "current_address": current_addr,
        "Permanent Address": permanent_addr,
        "permanent_address": permanent_addr,
        "Work Email": work_email,
        "work_email": work_email,
        "Personal Email": personal_email,
        "personal_email": personal_email,
        "Mobile": mobile_num,
        "mobile": mobile_num,
        "Date of Birth": dob,
        "date_of_birth": dob,
        "Marital Status": marital_status,
        "marital_status": marital_status,
        "Marriage Date": marriage_date,
        "marriage_date": marriage_date,
        # Position & Department
        "Job Title": job_title,
        "job_title": job_title,
        "Applied Designation": job_title,
        "applied_designation": job_title,
        "Department": department,
        "department": department,
        "Location": location,
        "location": location,
        "Reporting To": reporting_to,
        "reporting_to": reporting_to,
        "Reporting Manager Employee Number": reporting_mgr_emp_no,
        "reporting_manager_emp_no": reporting_mgr_emp_no,
        # Offer & Joining
        "Date Joined": date_joined,
        "date_joined": date_joined,
        "END DATE": end_date,
        "end_date": end_date,
        "Pay Grade": pay_grade,
        "pay_grade": pay_grade,
        "Gross Salary": pay_grade,
        "gross_salary": pay_grade,
        "Monthly Gross Salary": pay_grade,
        "monthly_gross_salary": pay_grade,
        "SALARY_WORDS": salary_words,
        "salary_words": salary_words,
        # Policy & Compliance
        "Employment Status": emp_status,
        "employment_status": emp_status,
        "Worker Type": worker_type,
        "worker_type": worker_type,
        "Time Type": time_type,
        "time_type": time_type,
        "Leave Plan": leave_plan,
        "leave_plan": leave_plan,
        "Shift Policy": shift_policy,
        "shift_policy": shift_policy,
        "Weekly Off Policy": weekly_off_policy,
        "weekly_off_policy": weekly_off_policy,
        "Notice Period": notice_period_val,
        "notice_period": notice_period_val,
        # Statutory & Accounts
        "PAN Number": pan_num,
        "pan_number": pan_num,
        "Aadhaar Number": aadhaar_num,
        "aadhaar_number": aadhaar_num,
        "PF Number": pf_num,
        "pf_number": pf_num,
        "UAN Number": uan_num,
        "uan_number": uan_num,
        "Cost Center": cost_center,
        "cost_center": cost_center,
        # Extension
        "Extension start date": extension_start_date,
        "extension_start_date": extension_start_date,
        "Extension end date": extension_end_date,
        "extension_end_date": extension_end_date,
        # Termination & Exit
        "Termination Date": termination_date,
        "termination_date": termination_date,
        "Exit Date": exit_date,
        "exit_date": exit_date,
        "Exit Status": exit_status,
        "exit_status": exit_status,
        "Termination Type": term_type,
        "termination_type": term_type,
        "Reason": term_reason,
        "reason": term_reason,
        "Termination Reason": term_reason,
        "termination_reason": term_reason,
        # Increment
        "Effective From": effective_from,
        "effective_from": effective_from,
        "Revised Pay Grade": revised_pay_grade,
        "revised_pay_grade": revised_pay_grade,
        "Revised Salary Words": revised_salary_words,
        "revised_salary_words": revised_salary_words,
        "Offer letter Document Date": offer_letter_document_date,
        "offer_letter_document_date": offer_letter_document_date,
        # Certificate specific
        "main_para": main_para,
        "salary_para": salary_para,
        "appreciation_para": appreciation_para,
        "future_line": future_line,
        "is_working": is_working,
        "pronoun": pronoun,
        "obj_pronoun": obj_pronoun,
        "subject_pronoun": subject_pronoun,
    }

    # Add underscore variants for all space-separated keys for template compatibility
    underscore_variants = {}
    for k, v in res.items():
        if " " in k:
            underscore_variants[k.replace(" ", "_")] = v
            underscore_variants[k.title().replace(" ", "_")] = v
    res.update(underscore_variants)

    return res


def resolve_template(document_type: str, candidate: dict, manual_designation_override: str = None) -> dict:
    """
    Resolves the template file path for the requested document type and candidate.
    Returns:
        {
            "found": bool,
            "template_path": str or None,
            "available_designations": list[str],
            "matched_designation": str or None
        }
    """
    doc_type_lower = (document_type or "").strip().lower()

    # 1. Termination: Always single generic template
    if doc_type_lower in ["termination", "termination_letter"]:
        path = db_manager.get_template_path("termination", "Generic")
        if not path:
            path = db_manager.resolve_template_path("termination/termination_letter.docx")
        if path and os.path.exists(path):
            return {
                "found": True,
                "template_path": path,
                "available_designations": ["Generic"],
                "matched_designation": "Generic"
            }
        return {
            "found": False,
            "template_path": None,
            "available_designations": ["Generic"],
            "matched_designation": None
        }

    # 2. Experience / Salary Certificates: Always standard certificate template
    if doc_type_lower in ["experience", "experience_certificate", "salary", "salary_certificate"]:
        # Check database mappings for certificate
        path = (
            db_manager.get_template_path(doc_type_lower, "Standard Experience Certificate")
            or db_manager.get_template_path("experience_certificate", "Standard Experience Certificate")
            or db_manager.get_template_path("salary_certificate", "Standard Salary Certificate")
            or db_manager.resolve_template_path("templates/certificate/experience_salary.docx")
        )
        if path and os.path.exists(path):
            return {
                "found": True,
                "template_path": path,
                "available_designations": ["Standard Certificate"],
                "matched_designation": "Standard Certificate"
            }
        return {
            "found": False,
            "template_path": None,
            "available_designations": ["Standard Certificate"],
            "matched_designation": None
        }

    # 3. Designation-dependent types: Offer, Extension, Increment
    available_templates = db_manager.get_templates_by_type(doc_type_lower)
    available_labels = [t["designation_label"] for t in available_templates]

    # Manual designation override provided by user
    if manual_designation_override:
        path = db_manager.get_template_path(doc_type_lower, manual_designation_override)
        if path and os.path.exists(path):
            return {
                "found": True,
                "template_path": path,
                "available_designations": available_labels,
                "matched_designation": manual_designation_override
            }

    # Automatic matching from candidate's applied designation
    candidate_desig = str((candidate or {}).get("applied_designation") or "").strip()

    # Exact case-sensitive match
    if candidate_desig:
        path = db_manager.get_template_path(doc_type_lower, candidate_desig)
        if path and os.path.exists(path):
            return {
                "found": True,
                "template_path": path,
                "available_designations": available_labels,
                "matched_designation": candidate_desig
            }

        # Case-insensitive match against available designations
        norm_cand = candidate_desig.lower()
        for t in available_templates:
            label = t["designation_label"]
            if label.lower() == norm_cand:
                resolved = db_manager.resolve_template_path(t["template_file_path"])
                if os.path.exists(resolved):
                    return {
                        "found": True,
                        "template_path": resolved,
                        "available_designations": available_labels,
                        "matched_designation": label
                    }

    # No template matched
    return {
        "found": False,
        "template_path": None,
        "available_designations": available_labels,
        "matched_designation": None
    }


def insert_reference_and_date(doc, reference_number: str, date_text: str, document_type: str) -> None:
    """
    Inserts Reference Number and Dated line after the anchor paragraph (doc.paragraphs[0]).
    - Offer, extension, increment, termination: 81 spaces, bold, Times New Roman, 11pt, 'Dated: ...'
    - Experience, salary: 69 spaces, bold, Times New Roman, 12pt, 'Date: ...'
    """
    if not doc or not doc.paragraphs:
        return

    doc_type_lower = (document_type or "").strip().lower()
    first_para_element = doc.paragraphs[0]._element
    p_element = OxmlElement("w:p")
    first_para_element.addnext(p_element)
    p = Paragraph(p_element, doc.paragraphs[0]._parent)

    clean_ref = str(reference_number).strip() if reference_number else ""
    clean_date = str(date_text).strip() if date_text else ""

    if doc_type_lower in ["experience", "experience_certificate", "salary", "salary_certificate"]:
        text = f"Reference No: {clean_ref}" + (" " * 69) + f"Date: {clean_date}"
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.bold = True
    else:
        text = f"Reference No: {clean_ref}" + (" " * 81) + f"Dated: {clean_date}"
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(11)
        run.bold = True


def inject_certificate_paragraphs(doc, mapping: dict, document_type: str) -> None:
    """
    Dynamically injects certificate body paragraphs into docx templates
    following the 'To whomsoever this may concern' header paragraph.
    """
    doc_type_lower = (document_type or "").strip().lower()
    is_salary = doc_type_lower in ["salary", "salary_certificate"]

    main_para = mapping.get("main_para", "")
    salary_para = mapping.get("salary_para", "")
    appreciation_para = mapping.get("appreciation_para", "")
    future_line = mapping.get("future_line", "")

    for para in doc.paragraphs:
        if "to whomsoever this may concern" in para.text.lower():
            p = para._element

            blank1 = OxmlElement("w:p")
            p.addnext(blank1)

            new_p1 = OxmlElement("w:p")
            blank1.addnext(new_p1)

            para1 = Paragraph(new_p1, para._parent)
            run1 = para1.add_run(main_para)
            run1.font.name = "Times New Roman"
            run1.font.size = Pt(12)
            para1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            blank2 = OxmlElement("w:p")
            new_p1.addnext(blank2)

            if is_salary:
                new_p2 = OxmlElement("w:p")
                blank2.addnext(new_p2)

                para2 = Paragraph(new_p2, para._parent)
                run2 = para2.add_run(salary_para)
                run2.font.name = "Times New Roman"
                run2.font.size = Pt(12)
                para2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            else:
                new_p2 = OxmlElement("w:p")
                blank2.addnext(new_p2)

                para2 = Paragraph(new_p2, para._parent)
                run2 = para2.add_run(appreciation_para)
                run2.font.name = "Times New Roman"
                run2.font.size = Pt(12)
                para2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

                blank3 = OxmlElement("w:p")
                new_p2.addnext(blank3)

                new_p3 = OxmlElement("w:p")
                blank3.addnext(new_p3)

                para3 = Paragraph(new_p3, para._parent)
                run3 = para3.add_run(future_line)
                run3.font.name = "Times New Roman"
                run3.font.size = Pt(12)
                para3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            break


def generate_preview_document(
    candidate_id: int,
    document_type: str,
    extra_fields: dict = None,
    manual_designation_override: str = None
) -> dict:
    """
    Generates a temporary preview document without consuming the reference number sequence.
    Returns:
        {"success": True, "preview_file_path": str, "previewed_reference_number": str}
        OR
        {"success": False, "needs_template_selection": bool, "available_designations": list, "error": str}
    """
    extra_fields = extra_fields or {}

    candidate = db_manager.get_candidate_by_id(candidate_id)
    if not candidate:
        return {
            "success": False,
            "error": f"Candidate with ID {candidate_id} not found."
        }

    template_res = resolve_template(document_type, candidate, manual_designation_override)
    if not template_res.get("found"):
        return {
            "success": False,
            "needs_template_selection": True,
            "available_designations": template_res.get("available_designations", []),
            "error": "We could not find a matching template for this designation. Please select one manually."
        }

    # Build placeholders
    mapping = build_placeholder_mapping(candidate, document_type, extra_fields)

    # Load template
    template_path = template_res["template_path"]
    try:
        doc = docx.Document(template_path)
    except Exception as ex:
        print("Template open error (preview):", ex)
        return {
            "success": False,
            "error": "We couldn't open the document template. Please make sure the template file exists and is not currently open in another program, then try again."
        }

    doc_type_lower = (document_type or "").strip().lower()
    if doc_type_lower in ["experience", "experience_certificate", "salary", "salary_certificate"]:
        inject_certificate_paragraphs(doc, mapping, document_type)
    else:
        replace_placeholders_in_docx(doc, mapping)

    # Preview next reference number without consuming it
    ref_preview_info = db_manager.preview_next_reference("hr_reference")
    if not ref_preview_info or ref_preview_info.get("exhausted"):
        previewed_ref = "DFY/HR/XXXX/PREVIEW"
    else:
        previewed_ref = ref_preview_info.get("formatted", "DFY/HR/PREVIEW")

    date_text = get_document_reference_date(candidate, document_type, extra_fields)
    insert_reference_and_date(doc, previewed_ref, date_text, document_type)

    # Save to temp preview folder
    previews_dir = os.path.join(DESKTOP_APP_DIR, "output", "previews")
    os.makedirs(previews_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    preview_filename = f"preview_{candidate_id}_{doc_type_lower}_{timestamp}.docx"
    preview_file_path = os.path.join(previews_dir, preview_filename)

    try:
        doc.save(preview_file_path)
    except PermissionError as ex:
        print("Preview document save permission error:", ex)
        return {
            "success": False,
            "error": "We couldn't save the document because it may be open in Microsoft Word or another program. Please close it and try again."
        }
    except Exception as ex:
        print("Preview document save error:", ex)
        return {
            "success": False,
            "error": "We couldn't save the document. Please check the destination folder and try again."
        }

    return {
        "success": True,
        "preview_file_path": preview_file_path,
        "previewed_reference_number": previewed_ref
    }


def finalize_document(
    candidate_id: int,
    document_type: str,
    extra_fields: dict = None,
    manual_designation_override: str = None
) -> dict:
    """
    Generates and saves the final document, consuming the next reference number sequence
    and creating an audit log entry in document_generation_log.
    Returns:
        {"success": True, "file_path": str, "reference_number": str, "log_id": int}
        OR
        {"success": False, "error": str}
    """
    extra_fields = extra_fields or {}

    candidate = db_manager.get_candidate_by_id(candidate_id)
    if not candidate:
        return {
            "success": False,
            "error": f"Candidate with ID {candidate_id} not found."
        }

    template_res = resolve_template(document_type, candidate, manual_designation_override)
    if not template_res.get("found"):
        return {
            "success": False,
            "needs_template_selection": True,
            "available_designations": template_res.get("available_designations", []),
            "error": "We could not find a matching template for this designation. Please select one manually."
        }

    # Consume next reference number atomically
    ref_num, ref_err = db_manager.consume_next_reference("hr_reference")
    if ref_err or not ref_num:
        friendly_error = ref_err or "Reference number range is exhausted. Please configure a new range in Settings."
        return {
            "success": False,
            "error": friendly_error
        }

    # Build placeholders
    mapping = build_placeholder_mapping(candidate, document_type, extra_fields)

    # Load template
    template_path = template_res["template_path"]
    try:
        doc = docx.Document(template_path)
    except Exception as ex:
        print("Template open error (final):", ex)
        return {
            "success": False,
            "error": "We couldn't open the document template. Please make sure the template file exists and is not currently open in another program, then try again."
        }

    doc_type_lower = (document_type or "").strip().lower()
    if doc_type_lower in ["experience", "experience_certificate", "salary", "salary_certificate"]:
        inject_certificate_paragraphs(doc, mapping, document_type)
    else:
        replace_placeholders_in_docx(doc, mapping)

    date_text = get_document_reference_date(candidate, document_type, extra_fields)
    insert_reference_and_date(doc, ref_num, date_text, document_type)

    # Save to generated_documents folder
    gen_dir = os.path.join(DESKTOP_APP_DIR, "output", "generated_documents")
    os.makedirs(gen_dir, exist_ok=True)

    cand_name_raw = str(candidate.get("candidate_name") or f"cand_{candidate_id}").strip()
    emp_prefix_raw = str(candidate.get("employee_number") or candidate_id).strip()

    # Sanitize filename-unsafe characters for Windows filesystem (\ / : * ? " < > |)
    cand_name_safe = re.sub(r'[\\/*?:"<>|\s]+', '_', cand_name_raw).strip('_')
    emp_prefix = re.sub(r'[\\/*?:"<>|]+', '-', emp_prefix_raw).strip('-')
    filename = f"{emp_prefix}_{cand_name_safe}_{doc_type_lower}_letter.docx"
    final_file_path = os.path.join(gen_dir, filename)

    try:
        doc.save(final_file_path)
    except PermissionError as ex:
        print("Final document save permission error:", ex)
        return {
            "success": False,
            "error": "We couldn't save the document because it may be open in Microsoft Word or another program. Please close it and try again."
        }
    except Exception as ex:
        print("Final document save error:", ex)
        return {
            "success": False,
            "error": "We couldn't save the document. Please check the destination folder and try again."
        }

    # Record audit log
    log_id = db_manager.log_document_generation(
        candidate_id=candidate_id,
        document_type=doc_type_lower,
        reference_number=ref_num,
        extra_fields_dict=extra_fields,
        file_path=final_file_path,
        generated_by="HR Desktop"
    )

    return {
        "success": True,
        "file_path": final_file_path,
        "reference_number": ref_num,
        "log_id": log_id
    }
