import xml.etree.ElementTree as ET
import subprocess

class ParserTool:
    def convert_to_xml(self,pdf_path, base_name_of_file):
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
    
    def get_pages_from_xml(self,xml_path):
        tree = ET.parse(xml_path)
        root = tree.getroot()
        pages = root.findall(".//page")
        
        return pages