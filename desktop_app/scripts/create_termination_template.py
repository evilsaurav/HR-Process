"""
Script: create_termination_template.py
Purpose: Generates a standardized, generic (designation-independent) Termination Letter
template for Doctors For You by inheriting the letterhead branding, margins, and header/footer
from an existing offer letter template, and maps it in document_templates database table.
"""

import os
import sys
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Ensure desktop_app root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from database.db_manager import init_db, add_document_template, get_template_path
from config import TEMPLATES_DIR


def create_termination_template():
    # Base template to inherit branding, header logo (image3.png), footer, and margins from
    base_template_path = os.path.join(TEMPLATES_DIR, "offer", "associate_district_coordinator.docx")
    if not os.path.exists(base_template_path):
        raise FileNotFoundError(f"Base template not found at {base_template_path}")

    output_dir = os.path.join(TEMPLATES_DIR, "termination")
    os.makedirs(output_dir, exist_ok=True)
    output_file_path = os.path.join(output_dir, "termination_letter.docx")

    print(f"Loading base branding template: {base_template_path}")
    doc = Document(base_template_path)

    # Paragraph 0 in the base template is reserved as the anchor for insert_reference_and_date()
    # which inserts the Reference No and Date line immediately after paragraph 0.
    # Remove all paragraphs after paragraph 0.
    for i in range(len(doc.paragraphs) - 1, 0, -1):
        p_elem = doc.paragraphs[i]._element
        p_elem.getparent().remove(p_elem)

    # Ensure paragraph 0 has Times New Roman style and appropriate spacing
    p0 = doc.paragraphs[0]
    p0.text = "   "
    p0.paragraph_format.space_after = Pt(2)

    def add_p(text="", bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=3, space_before=0):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.line_spacing = 1.15
        if text:
            run = p.add_run(text)
            run.font.name = "Times New Roman"
            run.font.size = Pt(11)
            run.bold = bold
        return p

    # Spacing after reference line
    add_p("", space_after=4)

    # Recipient details
    add_p("To,", space_after=1)
    add_p("{{TITLE}} {{Full Name}}", space_after=1)
    add_p("{{RELATION}} {{FATHER_TITLE}} {{Father Name}}", space_after=1)
    add_p("R/o {{Full Address}}", space_after=6)

    # Subject line
    add_p("Sub: Termination of Services", bold=True, space_after=8, space_before=4)

    # Salutation
    add_p("Dear {{TITLE}} {{Full Name}},", space_after=6)

    # Body Paragraph 1: Formal notification of termination with placeholders
    add_p(
        "This is to formally inform you that your contractual engagement as a (Consultant) "
        "{{Job Title}} with Doctors For You supported {{Department}}, {{Location}}, which commenced "
        "on {{Date Joined}}, stands terminated with effect from {{Termination Date}}.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=6
    )

    # Body Paragraph 2: Reason & Notice Period
    add_p(
        "This decision has been made due to {{Reason}}. In accordance with the terms and conditions "
        "of your appointment contract, a notice period of {{Notice Period}} is being observed.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=6
    )

    # Body Paragraph 3: Handover, assets return, and exit formalities
    add_p(
        "You are advised to hand over all organizational responsibilities, files, records, and any company "
        "property or assets in your possession to your designated supervisor on or before your last working day. "
        "Your final dues and clearance will be processed in accordance with the organization's policy upon completion "
        "of all handover formalities and receipt of the requisite clearance certificate.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=6
    )

    # Body Paragraph 4: Professional closing and well wishes
    add_p(
        "We appreciate the contributions made by you during your association with Doctors For You "
        "and wish you the very best in your future endeavors.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=16
    )

    # Signatory block
    add_p("For Doctors For You,", space_after=28)
    add_p("Authorized Signatory", bold=True, space_after=1)
    add_p("HR Department", space_after=16)

    # Employee acknowledgement block
    add_p("I acknowledge receipt of this letter and confirm adherence to all exit formalities.", space_after=18)
    add_p("(Signature)", space_after=0)

    # Save template
    doc.save(output_file_path)
    print(f"Termination template successfully created at:\n  {output_file_path}")

    # Register in database
    init_db()
    relative_mapping_path = "termination/termination_letter.docx"
    success = add_document_template("termination", "Generic", relative_mapping_path)
    if success:
        print(f"Registered template in database: ('termination', 'Generic') -> {relative_mapping_path}")
    else:
        print(f"Template mapping ('termination', 'Generic') already registered or updated.")

    resolved = get_template_path("termination", "Generic")
    print(f"Resolved DB template path: {resolved}")
    return output_file_path


if __name__ == "__main__":
    create_termination_template()
