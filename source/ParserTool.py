import xml.etree.ElementTree as ET
import subprocess
import logging
import asyncio
import io
from html import escape

import pymupdf
from PIL import Image
from chrome_lens_py import LensAPI
from statistics import median

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
    
    def is_scanned_pdf(self, pages, threshold=0.95):
        total_pages = len(pages)

        if total_pages == 0:
            return True

        text_pages = 0

        for page in pages:
            has_text = False

            for textbox in page.findall(".//textbox"):
                for t in textbox.findall(".//text"):
                    if t.text and t.text.strip():
                        has_text = True
                        break

                if has_text:
                    break

            if has_text:
                text_pages += 1

        ratio = text_pages / total_pages

        self.logger.info(
            f"PDF text coverage: {text_pages}/{total_pages} ({ratio:.2%})"
        )

        return ratio < threshold

class ChromeLensParserTool:

    def __init__(self, pdf_path):
        self.logger = logging.getLogger(__name__)
        self.lens = LensAPI()
        self.pdf_path = pdf_path
        self.xml = []
        self.total_pages = 0

    def build_xml(self, start_page=None, end_page=None):

        self.xml.clear()

        doc = pymupdf.open(self.pdf_path)

        try:

            self.total_pages = len(doc)

            if start_page is None:
                start_page = 1

            if end_page is None:
                end_page = self.total_pages

            start_page = max(1, start_page)
            end_page = min(self.total_pages, end_page)

            asyncio.run(
                self._build_async(doc, start_page, end_page)
            )

            return self.xml

        finally:
            doc.close()

    async def process_page(self, page):

        pix = page.get_pixmap(dpi=300, alpha=False)

        image = Image.open(io.BytesIO(pix.tobytes("png")))

        result = await self.lens.process_image(
            image_path=image,
            output_format="detailed"
        )

        return result.get("detailed_blocks", [])

    async def _process_page_with_retry(self, page, retries=3):

        last_exception = None

        for attempt in range(retries):

            try:
                return await self.process_page(page)

            except Exception as e:

                last_exception = e

                self.logger.warning(
                    f"Page {page.number + 1} OCR failed "
                    f"(Attempt {attempt + 1}/{retries}): {e}"
                )

        raise last_exception

    async def _build_async(self, doc, start_page, end_page):

        for page_num in range(start_page, end_page + 1):

            page = doc[page_num - 1]

            detailed_blocks = await self._process_page_with_retry(page)

            page_xml = self.build_page_xml(
                detailed_blocks=detailed_blocks,
                page_number=page_num,
                page_width=page.rect.width,
                page_height=page.rect.height
            )

            self.xml.append(page_xml)

    @staticmethod
    def _bbox(geometry):

        left = geometry["center_x"] - geometry["width"] / 2
        right = geometry["center_x"] + geometry["width"] / 2
        top = geometry["center_y"] - geometry["height"] / 2
        bottom = geometry["center_y"] + geometry["height"] / 2

        return (left, top, right, bottom)

    @staticmethod
    def _flip_y(top, bottom, page_height):

        return page_height - bottom, page_height - top

    @staticmethod
    def _bbox_string(left, top, right, bottom):

        return (
            f"{left:.2f},"
            f"{top:.2f},"
            f"{right:.2f},"
            f"{bottom:.2f}"
        )

    @staticmethod
    def _union_bbox(words):

        left = float("inf")
        top = float("inf")
        right = float("-inf")
        bottom = float("-inf")

        for word in words:

            l, t, r, b = ChromeLensParserTool._bbox(word["geometry"])

            left = min(left, l)
            top = min(top, t)
            right = max(right, r)
            bottom = max(bottom, b)

        return (left, top, right, bottom)

    def build_page_xml(
        self,
        detailed_blocks,
        page_number,
        page_width=None,
        page_height=None
    ):

        page_attrs = {"id": str(page_number)}

        if page_width is not None and page_height is not None:
            page_attrs["bbox"] = self._bbox_string(0, 0, page_width, page_height)

        page_el = ET.Element("page", page_attrs)

        if page_height is None:
            self.logger.warning(
                f"Page {page_number} missing page_height; "
                f"bbox y-axis will not be flipped to pdfminer convention."
            )

        textbox_id = 0

        for block in detailed_blocks:

            lines = block.get("lines", [])

            if not lines:
                continue

            block_words = []

            for line in lines:
                block_words.extend(line.get("words", []))

            if not block_words:
                continue

            block_left, block_top, block_right, block_bottom = (
                self._union_bbox(block_words)
            )

            if page_height is not None:
                tb_y0, tb_y1 = self._flip_y(block_top, block_bottom, page_height)
            else:
                tb_y0, tb_y1 = block_top, block_bottom

            textbox = ET.SubElement(
                page_el,
                "textbox",
                {
                    "id": str(textbox_id),
                    "bbox": self._bbox_string(
                        block_left, tb_y0, block_right, tb_y1
                    )
                }
            )

            textbox_id += 1

            line_id = 0

            for line in lines:

                words = line.get("words", [])

                if not words:
                    continue

                line_left, line_top, line_right, line_bottom = (
                    self._union_bbox(words)
                )

                if page_height is not None:
                    ln_y0, ln_y1 = self._flip_y(line_top, line_bottom, page_height)
                else:
                    ln_y0, ln_y1 = line_top, line_bottom

                textline = ET.SubElement(
                    textbox,
                    "textline",
                    {
                        "id": str(line_id),
                        "bbox": self._bbox_string(
                            line_left, ln_y0, line_right, ln_y1
                        )
                    }
                )

                line_id += 1

                previous_word = None

                for word in words:

                    text = word.get("text", "").strip()

                    if not text:
                        continue

                    left, top, right, bottom = self._bbox(word["geometry"])

                    if previous_word is not None:

                        prev_left, prev_top, prev_right, prev_bottom = (
                            self._bbox(previous_word["geometry"])
                        )

                        if left > prev_right:

                            sp_top = min(top, prev_top)
                            sp_bottom = max(bottom, prev_bottom)

                            if page_height is not None:
                                sp_y0, sp_y1 = self._flip_y(
                                    sp_top, sp_bottom, page_height
                                )
                            else:
                                sp_y0, sp_y1 = sp_top, sp_bottom

                            space = ET.SubElement(
                                textline,
                                "text",
                                {
                                    "bbox": self._bbox_string(
                                        prev_right, sp_y0, left, sp_y1
                                    )
                                }
                            )

                            space.text = " "

                    n_chars = len(text)

                    if n_chars == 0:
                        previous_word = word
                        continue

                    word_width = max(right - left, 0.01)

                    char_width = word_width / n_chars

                    current_x = left

                    if page_height is not None:
                        ch_y0, ch_y1 = self._flip_y(top, bottom, page_height)
                    else:
                        ch_y0, ch_y1 = top, bottom

                    for ch in text:

                        char_left = current_x
                        char_right = current_x + char_width

                        char_node = ET.SubElement(
                            textline,
                            "text",
                            {
                                "bbox": self._bbox_string(
                                    char_left, ch_y0, char_right, ch_y1
                                )
                            }
                        )

                        char_node.text = ch

                        current_x = char_right

                    previous_word = word

        return page_el