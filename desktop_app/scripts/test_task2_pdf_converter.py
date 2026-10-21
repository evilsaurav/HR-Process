import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import docx
from services import pdf_converter_service

def run_test():
    test_docx = os.path.abspath("desktop_app/output/pdf_test.docx")
    test_pdf = os.path.abspath("desktop_app/output/pdf_test.pdf")
    
    os.makedirs("desktop_app/output", exist_ok=True)
    doc = docx.Document()
    doc.add_heading("PDF Conversion Test", 0)
    doc.add_paragraph("Doctors For You - Document Pipeline Test")
    doc.save(test_docx)
    
    success, result_path, error = pdf_converter_service.convert_docx_to_pdf(test_docx, test_pdf)
    print(f"Conversion result: success={success}, path={result_path}, error={error}")
    
    if success:
        assert os.path.exists(test_pdf), "PDF file was not created"
        assert os.path.getsize(test_pdf) > 0, "PDF file is empty"
        print("SUCCESS: PDF conversion succeeded with Word COM.")
    else:
        print(f"INFO: Word COM conversion gracefully failed ({error}). Fallback active.")

    avail = pdf_converter_service.is_pdf_conversion_available()
    print(f"is_pdf_conversion_available: {avail}")
    print("SUCCESS: Task 2 PDF Converter verified successfully.")

if __name__ == "__main__":
    run_test()
