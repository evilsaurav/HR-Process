"""
Service: candidate_outreach_service.py
Purpose: Generates instant 1-click personalized WhatsApp / SMS messages
and candidate interview bio-data summary slips for field HR teams.
"""

from typing import Dict, Any


def generate_whatsapp_outreach_text(candidate: Dict[str, Any], message_type: str = "selection") -> str:
    """
    Generates a personalized, professional Hinglish message for WhatsApp or SMS.
    Types: 'selection', 'interview', 'joining'.
    """
    name = candidate.get("candidate_name") or candidate.get("display_name") or "Candidate"
    desig = candidate.get("applied_designation") or candidate.get("job_title") or "the position"
    loc = candidate.get("contact_location") or "Designated Project Location"
    sal = candidate.get("negotiated_salary") or "As mutually agreed"
    email = candidate.get("email") or candidate.get("work_email") or "your registered email"
    doj = candidate.get("date_joined") or "shortly"

    msg_type = (message_type or "selection").lower().strip()

    if msg_type == "selection":
        return (
            f"Namaste {name},\n\n"
            f"Doctors For You (DFY) ki taraf se aapko '{desig}' post ({loc}) ke liye select kiya gaya hai. 🎉\n\n"
            f"Aapka formal Welcome Email aur selection details aapke registered email ({email}) par bhej di gayi hain. "
            f"Kripya apna email check karein aur confirmation bhejein.\n\n"
            f"Kisi bhi query ke liye aap is number par reply kar sakte hain.\n\n"
            f"Warm Regards,\n"
            f"HR Operations Team\n"
            f"Doctors For You"
        )
    elif msg_type == "interview":
        return (
            f"Namaste {name},\n\n"
            f"Doctors For You (DFY) me '{desig}' post ({loc}) ke liye aapka interview schedule kiya gaya hai.\n\n"
            f"Kripya apne original documents (Educational Certificates, Experience Letters, ID Proof) "
            f"aur updated resume ke sath samay par upasthit rahein.\n\n"
            f"Best wishes,\n"
            f"HR Recruitment Team\n"
            f"Doctors For You"
        )
    elif msg_type == "joining":
        return (
            f"Namaste {name},\n\n"
            f"Doctors For You family me aapka swagat hai!\n"
            f"Aapki joining date '{doj}' nirdharit ki gayi hai ({loc} office).\n\n"
            f"Joining ke samay PAN Card, Aadhaar Card, Bank Passbook aur 2 passport size photos lana anivarya hai.\n\n"
            f"Regards,\n"
            f"HR Operations Team\n"
            f"Doctors For You"
        )
    else:
        return (
            f"Namaste {name},\n\n"
            f"Doctors For You HR department ki taraf se yeh message hai. "
            f"Aapka record '{desig}' post ke liye review kiya gaya hai.\n\n"
            f"Regards,\n"
            f"Doctors For You HR Team"
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
