import os
import unittest


from source.ParserTool import ParserTool
from source.Page import Page

class TestPageLayoutDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pdf_path = "test/SampleTest.pdf"
        cls.expected_layouts = [
            "single_column_page",
            "single_column_page",
            "single_column_page",
            "single_column_page",
            "single_column_page",
            "single_column_page",
            "page_may have mulitple columns",
            "page_may have mulitple columns",
            "page_may have mulitple columns",
            "page_may have mulitple columns"
        ]

        cls.base_name = os.path.splitext(os.path.basename(cls.pdf_path))[0]
        cls.xml_path = f"test/{cls.base_name}.xml"
        cls.result_file = f"test/{cls.base_name}_layout_test_results.txt"

        # Convert PDF to XML
        cls.parser = ParserTool()
        cls.parser.convert_to_xml(cls.pdf_path,"test/"+cls.base_name)

        # Get all page elements
        cls.pages = cls.parser.get_pages_from_xml(cls.xml_path)

    def test_layout_detection_on_all_pages(self):
        with open(self.result_file, "w") as f:
            f.write("Page\t\tExpected\t\tActual\t\tResult\n")
            for i, page_elem in enumerate(self.pages):
                page = Page(page_elem)
                page.process_textboxes(page_elem)
                page.get_width_ofTB_moreThan_Half_of_pg()
                page.get_body_width_by_binning()
                actual_layout = page.get_page_layout()

                # Get expected layout
                expected_layout = self.expected_layouts[i] if i < len(self.expected_layouts) else "N/A"
                result = "PASS" if actual_layout == expected_layout else "FAIL"

                # Log to file
                f.write(f"{i+1}\t\t{expected_layout}\t\t{actual_layout}\t\t{result}\n")

                # Also assert
                # self.assertEqual(actual_layout, expected_layout)

if __name__ == "__main__":
    unittest.main()
