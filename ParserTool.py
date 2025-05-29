import os
import xml.etree.ElementTree as ET
import re
import subprocess
from TextBuilder import TextBuilder


class PdfMiner:
    def convert_to_xml(pdf_path, base_name_of_file):
        output_xml_path = f"{base_name_of_file}.xml"
        cmd = [
            "pdf2txt.py",
            "-A",
            "-t", "xml",
            "-o", output_xml_path,
            pdf_path
        ]
        try:
            subprocess.run(cmd, check=True)
            print(f"[✔] Parse completed: {output_xml_path}")
        except subprocess.CalledProcessError as e:
            print(f"[✖] Parse failed: {e}")
    
    def extract_text_from_xml(xml_path):
        tree = ET.parse(xml_path)
        root = tree.getroot()
        TextBuilder.process_pages(root.findall(".//page"))



# --- Main --- #

if __name__ == "__main__":
    pdf_path = r'in-union-act-ministryofcivilaviation-2025-04-16-17-publication-document.pdf'  # 👈 Replace with your PDF path
    base_name_of_file = os.path.splitext(os.path.basename(pdf_path))[0]
    PdfMiner.convert_to_xml(pdf_path,base_name_of_file)

    xml_path = f"{base_name_of_file}.xml"
    PdfMiner.extract_text_from_xml(xml_path)