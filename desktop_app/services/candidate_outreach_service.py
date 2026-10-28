"""
Service: candidate_outreach_service.py
Purpose: Generates instant 1-click personalized WhatsApp / SMS messages
and candidate interview bio-data summary slips for field HR teams.
"""

import re
import urllib.parse
from typing import Dict, Any, Optional


def clean_indian_mobile(mobile_str: Optional[str]) -> Optional[str]:
    """
    Cleans and standardizes an Indian mobile number into international WhatsApp format '91XXXXXXXXXX'.
    Handles inputs like '+91 98765 43210', '09876543210', '9876543210', '91-9876543210'.
    Returns a 12-digit string starting with 91, or None if invalid.
    """
    if not mobile_str:
        return None

    digits = re.sub(r"\D", "", str(mobile_str))
    if not digits:
        return None

    # Already has 91 country code and 10 digits
    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        return digits

    # 10 digits starting with valid mobile prefix
    if len(digits) == 10 and digits[0] in "6789":
        return f"91{digits}"

    # 11 digits starting with 0
    if len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
        return f"91{digits[1:]}"

    # Fallback if 10 digits regardless of first digit
    if len(digits) == 10:
        return f"91{digits}"

    if len(digits) == 12 and digits.startswith("91"):
        return digits

    return None


def build_whatsapp_web_url(clean_mobile: str, message_text: str) -> str:
    """
    Builds a direct wa.me link with URL-encoded message text for opening in WhatsApp Web or WhatsApp Desktop.
    """
    quoted_text = urllib.parse.quote(message_text)
    return f"https://wa.me/{clean_mobile}?text={quoted_text}"


DOC_TYPE_LABELS = {
    "offer": "Offer Letter",
    "appointment": "Appointment Letter",
    "extension": "Service Extension Letter",
    "increment": "Salary Increment Letter",
    "termination": "Relieving & Service Letter",
    "experience_certificate": "Experience Certificate",
    "salary_certificate": "Salary Certificate",
}


def generate_document_release_whatsapp_text(
    candidate: Dict[str, Any],
    document_type: str = "offer",
    reference_number: str = ""
) -> str:
    """
    Generates a personalized WhatsApp outreach message when an official HR document has been issued/staged.
    """
    name = candidate.get("candidate_name") or candidate.get("display_name") or "Candidate"
    desig = candidate.get("applied_designation") or candidate.get("job_title") or "Designated Position"
    email = candidate.get("email") or candidate.get("work_email") or "your registered email"
    doc_label = DOC_TYPE_LABELS.get(str(document_type).lower(), "Official HR Document")
    ref_part = f"Ref No: *{reference_number}*\n" if reference_number else ""

    return (
        f"Namaste {name},\n\n"
        f"Greetings from *Doctors For You (DFY)*!\n\n"
        f"Aapka *{doc_label}* ({desig}) DFY HR Operations portal se release kar diya gaya hai. 📄✨\n\n"
        f"{ref_part}"
        f"Kripya apna registered email ({email}) check karein jahan document ki official copy bhej di gayi hai.\n\n"
        f"Yadi aapko koi clarification chahiye, to aap is number par sampark kar sakte hain.\n\n"
        f"Warm Regards,\n"
        f"*HR Operations Team*\n"
        f"Doctors For You (DFY)\n"
        f"https://doctorsforyou.org"
    )


def generate_whatsapp_outreach_text(
    candidate: Dict[str, Any],
    message_type: str = "selection",
    document_type: str = "offer",
    reference_number: str = ""
) -> str:
    """
    Generates a personalized, professional Hinglish message for WhatsApp or SMS.
    Types: 'document_release', 'selection', 'interview', 'joining'.
    """
    msg_type = (message_type or "selection").lower().strip()
    if msg_type in ["document_release", "document", "release"]:
        return generate_document_release_whatsapp_text(candidate, document_type, reference_number)

    name = candidate.get("candidate_name") or candidate.get("display_name") or "Candidate"
    desig = candidate.get("applied_designation") or candidate.get("job_title") or "the position"
    loc = candidate.get("contact_location") or "Designated Project Location"
    sal = candidate.get("negotiated_salary") or "As mutually agreed"
    email = candidate.get("email") or candidate.get("work_email") or "your registered email"
    doj = candidate.get("date_joined") or "shortly"

    if msg_type == "selection":
        return (
            f"Namaste {name},\n\n"
            f"Doctors For You (DFY) ki taraf se aapko '{desig}' post ({loc}) ke liye select kiya gaya hai. 🎉\n\n"
            f"Aapka formal Welcome Email aur selection details aapke registered email ({email}) par bhej di gayi hain. "
            f"Kripya apna email check karein aur confirmation bhejein.\n\n"
            f"Kisi bhi query ke liye aap is number par reply kar sakte hain.\n\n"
            f"Warm Regards,\n"
            f"HR Operations Team\n"
            f"Doctors For You\n"
            f"https://doctorsforyou.org"
        )
    elif msg_type == "interview":
        return (
            f"Namaste {name},\n\n"
            f"Doctors For You (DFY) me '{desig}' post ({loc}) ke liye aapka interview schedule kiya gaya hai. 📅\n\n"
            f"Kripya apne original documents (Educational Certificates, Experience Letters, ID Proof) "
            f"aur updated resume ke sath samay par upasthit rahein.\n\n"
            f"Best wishes,\n"
            f"HR Recruitment Team\n"
            f"Doctors For You\n"
            f"https://doctorsforyou.org"
        )
    elif msg_type == "joining":
        return (
            f"Namaste {name},\n\n"
            f"Doctors For You family me aapka swagat hai! 🏥🤝\n"
            f"Aapki joining date '{doj}' nirdharit ki gayi hai ({loc} office).\n\n"
            f"Joining ke samay PAN Card, Aadhaar Card, Bank Passbook aur 2 passport size photos lana anivarya hai.\n\n"
            f"Regards,\n"
            f"HR Operations Team\n"
            f"Doctors For You\n"
            f"https://doctorsforyou.org"
        )
    else:
        return (
            f"Namaste {name},\n\n"
            f"Doctors For You HR department ki taraf se yeh message hai. "
            f"Aapka record '{desig}' post ke liye review kiya gaya hai.\n\n"
            f"Regards,\n"
            f"Doctors For You HR Team\n"
            f"https://doctorsforyou.org"
        )


def generate_candidate_bio_data_slip(candidate: Dict[str, Any]) -> str:
    """
    Generates a clean text slip summarizing candidate credentials for the interview panel or project director.
    """
    name = candidate.get("candidate_name") or "N/A"
    mobile = candidate.get("mobile") or "N/A"
    email = candidate.get("email") or "N/A"
    desig = candidate.get("applied_designation") or "N/A"
    sal = candidate.get("negotiated_salary") or "N/A"
    if sal != "N/A" and str(sal).isdigit():
        sal_fmt = f"₹{int(sal):,}"
    else:
        sal_fmt = str(sal)

    edu = candidate.get("highest_education") or "N/A"
    exp = candidate.get("total_experience") or "N/A"
    loc = candidate.get("contact_location") or "N/A"
    dept = candidate.get("department") or candidate.get("source_sheet_name") or "General"
    status = candidate.get("status") or "Applied"
    skills = candidate.get("core_technical_skills") or "N/A"

    return (
        f"====================================================\n"
        f"       DOCTORS FOR YOU — CANDIDATE BIO-DATA SLIP    \n"
        f"====================================================\n"
        f"Candidate Name       : {name}\n"
        f"Mobile Number        : {mobile}\n"
        f"Email Address        : {email}\n"
        f"Applied Designation  : {desig}\n"
        f"Proposed Pay / Sal   : {sal_fmt}\n"
        f"Location / State     : {loc}\n"
        f"Project / Department : {dept}\n"
        f"Highest Education    : {edu}\n"
        f"Total Experience     : {exp} Years\n"
        f"Current Pipeline St. : {status}\n"
        f"Core Technical Skills: {skills}\n"
        f"====================================================\n"
    )
