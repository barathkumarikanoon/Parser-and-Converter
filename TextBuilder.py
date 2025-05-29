import xml.etree.ElementTree as ET
import statistics, math

class TextBuilder:
    # the below variable value changes per page
    page_coords = (0, 0, 0, 0)  # for pg_width = page_coords[2] , page_height = page_coords[3]

    # the below variable values are common across all pages in pdf
    body_starts_x = 0
    body_starts_y = 0
    body_ends_x = 0
    body_ends_y = 0

    @staticmethod
    def reset_static_var():
        #at end of each page reset the coords of page
        TextBuilder.page_coords = (0,0,0,0)

    @staticmethod
    def get_page_coords(page):
        TextBuilder.page_coords = tuple(map(float, page.attrib["bbox"].split(",")))
    
    @staticmethod
    def extract_text_from_each_lines(textbox_element):
        all_text = []
        for textline in textbox_element.findall('.//textline'):
            line_texts = []
            for text in textline.findall('.//text'):
                if text.text:
                    line_texts.append(text.text)
            
            line = ''.join(line_texts).replace("\n", " ").strip()
            if line:
                all_text.append(line)
        
        # Join all lines with space (or newline if you want separation)
        return '\n'.join(all_text)
    
    @staticmethod
    def is_heading(box_coords, tolerance=5):  # you can tune this tolerance
        def distance(p1, p2):
            x1, y1 = p1
            x2, y2 = p2
            return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        d_start = distance((TextBuilder.body_starts_x, TextBuilder.body_starts_y),
                           (box_coords[0], box_coords[1]))
        d_end = distance((TextBuilder.body_ends_x, TextBuilder.body_ends_y),
                         (box_coords[2], box_coords[3]))

        return abs(d_start - d_end) <= tolerance

        # left_margin = box_coords[0] - TextBuilder.body_starts_x 
        # right_margin = TextBuilder.body_ends_x - box_coords[2]
        # return abs(left_margin - right_margin) <= tolerance
    
    # getting sorted textboxes to extract text in the order of arrangement
    @staticmethod
    def get_sorted_textboxes(page):
        def parse_bbox(textbox):
            x0, y0, x1, y1 = map(float, textbox.attrib["bbox"].split(","))
            return x0, y0, x1, y1
        
        return    sorted(page.findall(".//textbox"),
            key=lambda tb: (
                -float(parse_bbox(tb)[1]),  # y0: top to bottom (higher y lower)
            float(parse_bbox(tb)[0]), #,   # x0: left to right
                -float(parse_bbox(tb)[3]),  # y1: optional secondary vertical order
                float(parse_bbox(tb)[2])    # x1: optional secondary horizontal order
            )
        )           
               
    
    @staticmethod
    def get_textBox_coords(box):
        return tuple(map(float,box.attrib["bbox"].split(",")))
    @staticmethod
    def process_tags(tags):
        text_boxes = TextBuilder.get_sorted_textboxes(tags)
        for box in text_boxes:
            texts = TextBuilder.extract_text_from_each_lines(box)
            if TextBuilder.is_heading(TextBuilder.get_textBox_coords(box)):
                print(texts)

    @staticmethod
    def get_stats_of_textbox(pages):
        x0_forMean = []
        y0_forMean = []
        x1_forMean = []
        y1_forMean = []
        for page in pages:
            textboxes = page.findall(".//textbox")

            x0_list = [float(tb.attrib["bbox"].split(",")[0]) for tb in textboxes]
            y0_list = [float(tb.attrib["bbox"].split(",")[1]) for tb in textboxes]
            x1_list = [float(tb.attrib["bbox"].split(",")[2]) for tb in textboxes]
            y1_list = [float(tb.attrib["bbox"].split(",")[3]) for tb in textboxes]

            x0_forMean.append(round(statistics.median(x0_list),2))
            y0_forMean.append(round(statistics.median(y0_list),2))
            x1_forMean.append(round(statistics.median(x1_list),2))
            y1_forMean.append(round(statistics.median(y1_list),2))

        return round(statistics.mean(x0_forMean),2), round(statistics.mean(y0_forMean),2), round(statistics.mean(x1_forMean),2), round(statistics.mean(y1_forMean),2)


    # @staticmethod
    # def dfs_of_tags(page):
    #     for  tags in  page:
    #         TextBuilder.process_tags(tags)

    @staticmethod
    def process_pages(pages):
        TextBuilder.body_starts_x , TextBuilder.body_starts_y, TextBuilder.body_ends_x, TextBuilder.body_ends_y = TextBuilder.get_stats_of_textbox(pages)

        print(TextBuilder.body_starts_x , TextBuilder.body_starts_y, TextBuilder.body_ends_x, TextBuilder.body_ends_y)
        for page in pages:
            TextBuilder.get_page_coords(page)
            # TextBuilder.dfs_of_tags(page)
            TextBuilder.process_tags(page)
        
            TextBuilder.reset_static_var()


