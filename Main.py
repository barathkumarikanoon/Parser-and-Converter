import os
from ParserTool import ParserTool
from Page import Page
class Main:
    def __init__(self):
        self.parserTool = ParserTool()

    def process_pages(self,pages):
        for pg in pages:
            page = Page(pg)
            page.process_textboxes(pg)
            print(page.width_binning())

    def parsePDF(self,pdf_path):
        base_name_of_file = os.path.splitext(os.path.basename(pdf_path))[0]
        self.parserTool.convert_to_xml(pdf_path,base_name_of_file)
        xml_path = f"{base_name_of_file}.xml"
        pages = self.parserTool.get_pages_from_xml(xml_path)

        self.process_pages(pages)


if __name__ == "__main__":
    pdf_path = r'in-union-act-ministryofcivilaviation-2025-04-16-17-publication-document.pdf'  # 👈 Replace with your PDF path
    main = Main()
    main.parsePDF(pdf_path)



    
    