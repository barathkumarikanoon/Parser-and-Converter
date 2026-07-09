import xml.etree.ElementTree as ET
import subprocess
import logging

class ParserTool:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def add_opt(self, cmd, flag, value):
        if value is not None:
            cmd.extend([flag, str(value)])

    def convert_to_xml(self,pdf_path, xml_path, pdf_type, \
                       char_margin, word_margin, line_margin):
        cmd = [
            "pdf2txt.py",
            "-A",
            "-t", "xml",
            "-o", xml_path,
        ]

        if char_margin is None:
            if pdf_type not in {"acts"}:
                char_margin = "25.0"
        
        if line_margin is None:
            if pdf_type not in {"sebi", "sebi_circulars", "acts"}:
                line_margin = "0.3"

        
        self.add_opt(cmd, '--char-margin', char_margin)
        self.add_opt(cmd, '--word-margin', word_margin)
        self.add_opt(cmd, '--line-margin', line_margin)
        cmd.append(pdf_path)
            
        try:
            subprocess.run(cmd, check=True)
            self.logger.info(f"[✔] Parse completed: {xml_path}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"[✖] Parse failed: {e}")
    
    def get_pages_from_xml(self,xml_path,start_page,end_page):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            pages = root.findall(".//page")
            if not pages:
                self.logger.warning(f"No <page> elements found: {xml_path}")
                return []
            
            filtered = []
            if start_page and end_page and start_page > end_page:
                self.logger.warning(f"start_page ({start_page}) > end_page ({end_page}), swapping.")
                start_page, end_page = end_page, start_page

            for p in pages:
                num_attr = p.get("id")
                if num_attr is None:
                    continue  

                try:
                    num = int(num_attr)
                except ValueError:
                    continue 

                if (start_page is None or num >= start_page) and \
                            (end_page is None or num <= end_page):
                    filtered.append(p)

            self.logger.debug(
                f"Collected {len(filtered)} page(s) from XML: {xml_path} "
                f"(start={start_page}, end={end_page})"
            )

            if not self.is_scanned_pdf(filtered):
                return filtered
            else:
                return None
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error in file {xml_path}: {e}")
            raise
        except FileNotFoundError as e:
            self.logger.error(f"XML file not found: {xml_path}")
            raise
        except Exception as e:
            self.logger.exception(f"Unexpected error while parsing XML: {xml_path} -- {e}")
            raise
    
    def is_scanned_pdf(self, pages, threshold=0.2):
        total_pages = len(pages)

        if total_pages == 0:
            return True

        text_pages = 0

        for page in pages:
            has_text = False

            for textbox in page.findall(".//textbox"):
                texts = textbox.findall(".//text")

                for t in texts:
                    if t.text and t.text.strip():
                        has_text = True
                        break

                if has_text:
                    break

            if has_text:
                text_pages += 1

        ratio = text_pages / total_pages

        self.logger.info(
            f"PDF text coverage: {text_pages}/{total_pages} "
            f"({ratio:.2%})"
        )

        return ratio < threshold