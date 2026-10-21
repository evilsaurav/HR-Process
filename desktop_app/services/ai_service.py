import requests

def test_connection(provider: str, api_key: str):
    """Returns (success: bool, message: str)"""
    try:
        if provider == "Gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            list(genai.list_models())
            return True, "Gemini connected successfully"

        elif provider == "Groq":
            r = requests.get("https://api.groq.com/openai/v1/models",
                              headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            if r.status_code == 200:
                return True, "Groq connected successfully"
            print(f"Groq connection error ({r.status_code}):", r.text[:200])
            return False, "We couldn't connect using this API key. Please check that the key is correct and that you have an internet connection, then try again."

        elif provider == "NVIDIA":
            r = requests.get("https://integrate.api.nvidia.com/v1/models",
                              headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            if r.status_code == 200:
                return True, "NVIDIA connected successfully"
            print(f"NVIDIA connection error ({r.status_code}):", r.text[:200])
            return False, "We couldn't connect using this API key. Please check that the key is correct and that you have an internet connection, then try again."

        elif provider == "OpenRouter":
            r = requests.get("https://openrouter.ai/api/v1/models",
                              headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            if r.status_code == 200:
                return True, "OpenRouter connected successfully"
            print(f"OpenRouter connection error ({r.status_code}):", r.text[:200])
            return False, "We couldn't connect using this API key. Please check that the key is correct and that you have an internet connection, then try again."

        elif provider == "Together AI":
            r = requests.get("https://api.together.xyz/v1/models",
                              headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            if r.status_code == 200:
                return True, "Together AI connected successfully"
            print(f"Together AI connection error ({r.status_code}):", r.text[:200])
            return False, "We couldn't connect using this API key. Please check that the key is correct and that you have an internet connection, then try again."

        elif provider == "OpenAI":
            r = requests.get("https://api.openai.com/v1/models",
                              headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            if r.status_code == 200:
                return True, "OpenAI connected successfully"
            print(f"OpenAI connection error ({r.status_code}):", r.text[:200])
            return False, "We couldn't connect using this API key. Please check that the key is correct and that you have an internet connection, then try again."

        return False, "Unknown provider - cannot verify"
    except Exception as e:
        print(f"AI test connection error ({provider}):", e)
        return False, "We couldn't connect using this API key. Please check that the key is correct and that you have an internet connection, then try again."


import re
from typing import List, Dict, Any


def audit_candidate_data_completeness(candidate: Dict[str, Any], doc_type: str = "") -> List[str]:
    """
    Audits a candidate's data for missing or inconsistent fields before document generation / emailing.
    Returns a list of plain-language warning messages.
    """
    warnings = []
    if not candidate:
        return ["Candidate record is empty."]

    cand_name = candidate.get("candidate_name") or candidate.get("display_name") or "Candidate"
    email = candidate.get("work_email") or candidate.get("email") or candidate.get("personal_email")
    mobile = candidate.get("mobile")

    # Email check
    if not email:
        warnings.append(f"No email address found for {cand_name}. An email address is required before sending.")
    elif not re.match(r"[^@]+@[^@]+\.[^@]+", str(email).strip()):
        warnings.append(f"Email address '{email}' does not appear to be in a valid format.")

    # Mobile check
    if not mobile or len(re.sub(r"[^\d]", "", str(mobile))) < 10:
        warnings.append("Mobile number is missing or less than 10 digits.")

    # Document type specific checks
    doc_type_clean = (doc_type or "").lower().strip()
    if any(k in doc_type_clean for k in ["offer", "appointment"]):
        if not candidate.get("applied_designation") and not candidate.get("job_title"):
            warnings.append("Designation / Job Title is missing.")
        if not candidate.get("department"):
            warnings.append("Department is not specified.")
        if not candidate.get("contact_location"):
            warnings.append("Posting location is not specified.")
        if not candidate.get("negotiated_salary"):
            warnings.append("Salary / pay grade is missing.")
        if not candidate.get("full_address") and not candidate.get("permanent_address") and not candidate.get("current_address"):
            warnings.append("Residential address is missing.")

    if any(k in doc_type_clean for k in ["relieving", "experience", "termination"]):
        if not candidate.get("relieving_date") and not candidate.get("exit_date"):
            warnings.append("Relieving / Exit date is missing.")

    # Statutory advisory
    if not candidate.get("pan_number"):
        warnings.append("Notice: PAN Number is not on file (recommended for statutory records).")
    if not candidate.get("aadhaar_number"):
        warnings.append("Notice: Aadhaar Number is not on file.")

    return warnings


def generate_email_cover(candidate: Dict[str, Any], doc_type: str = "offer", extra_notes: str = "") -> Dict[str, str]:
    """
    Generates professional email subject and body for a candidate document dispatch.
    Works 100% offline using tailored corporate templates.
    """
    cand_name = candidate.get("candidate_name") or candidate.get("display_name") or "Candidate"
    job_title = candidate.get("applied_designation") or candidate.get("job_title") or "the position"
    dept = candidate.get("department") or "our organization"
    loc = candidate.get("contact_location") or "our office"
    doj = candidate.get("date_joined") or "as mutually agreed"

    doc_type_clean = (doc_type or "offer").lower().strip()

    if "offer" in doc_type_clean:
        subject = f"Offer Letter: {job_title} - Doctors For You | {cand_name}"
        body = (
            f"Dear {cand_name},\n\n"
            f"We are pleased to extend an offer of engagement for the position of {job_title} "
            f"with Doctors For You ({dept}), based at {loc}.\n\n"
            f"Please find your formal Offer Letter attached with this email, detailing your compensation structure, "
            f"terms of engagement, and reporting schedule.\n\n"
            f"Kindly review the attached letter and reply to confirm your acceptance by returning a signed copy, "
            f"or confirming via reply email by your earliest convenience.\n\n"
            f"{extra_notes.strip() + chr(10) + chr(10) if extra_notes.strip() else ''}"
            f"We look forward to welcoming you to the Doctors For You team!\n\n"
            f"Warm regards,\n"
            f"Human Resources Team\n"
            f"Doctors For You"
        )
    elif "appointment" in doc_type_clean:
        subject = f"Appointment Letter - {cand_name} | Doctors For You"
        body = (
            f"Dear {cand_name},\n\n"
            f"Welcome to Doctors For You!\n\n"
            f"Please find your formal Appointment Letter attached for the position of {job_title} "
            f"in the {dept} department.\n\n"
            f"This letter contains your appointment terms, job responsibilities, and official policies.\n\n"
            f"{extra_notes.strip() + chr(10) + chr(10) if extra_notes.strip() else ''}"
            f"Wishing you a rewarding and successful tenure with us.\n\n"
            f"Warm regards,\n"
            f"Human Resources Team\n"
            f"Doctors For You"
        )
    elif "extension" in doc_type_clean:
        subject = f"Contract Extension Letter - {cand_name} | Doctors For You"
        body = (
            f"Dear {cand_name},\n\n"
            f"We are pleased to inform you that your engagement as {job_title} with Doctors For You "
            f"has been extended as detailed in the attached Extension Letter.\n\n"
            f"Thank you for your dedicated service and valuable contributions to the project.\n\n"
            f"{extra_notes.strip() + chr(10) + chr(10) if extra_notes.strip() else ''}"
            f"Best wishes,\n"
            f"Human Resources Team\n"
            f"Doctors For You"
        )
    elif "increment" in doc_type_clean:
        subject = f"Annual Performance Increment Notice - {cand_name} | Doctors For You"
        body = (
            f"Dear {cand_name},\n\n"
            f"In recognition of your performance and valuable service with Doctors For You, "
            f"we are pleased to share your revised compensation details in the attached Annual Increment Letter.\n\n"
            f"{extra_notes.strip() + chr(10) + chr(10) if extra_notes.strip() else ''}"
            f"We look forward to your continued dedication and excellence.\n\n"
            f"Warm regards,\n"
            f"Human Resources Team\n"
            f"Doctors For You"
        )
    elif any(k in doc_type_clean for k in ["experience", "relieving", "salary"]):
        subject = f"Experience & Relieving Certificate - {cand_name} | Doctors For You"
        body = (
            f"Dear {cand_name},\n\n"
            f"As requested, please find attached your official Certificate from Doctors For You "
            f"verifying your service tenure and association with the organization.\n\n"
            f"{extra_notes.strip() + chr(10) + chr(10) if extra_notes.strip() else ''}"
            f"We wish you the very best in all your future professional endeavours.\n\n"
            f"Warm regards,\n"
            f"Human Resources Team\n"
            f"Doctors For You"
        )
    else:
        subject = f"Official Communication - {cand_name} | Doctors For You"
        body = (
            f"Dear {cand_name},\n\n"
            f"Please find the relevant official document attached for your records.\n\n"
            f"{extra_notes.strip() + chr(10) + chr(10) if extra_notes.strip() else ''}"
            f"Warm regards,\n"
            f"Human Resources Team\n"
            f"Doctors For You"
        )

    return {"subject": subject, "body": body}
