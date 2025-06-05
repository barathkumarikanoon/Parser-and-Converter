import os
from difflib import SequenceMatcher
from ParserTool import ParserTool
from Page import Page
class Main:
    def __init__(self):
        self.parserTool = ParserTool()
        self.total_pgs = 0

    def process_pages(self,pages):
        self.sorted_footer_units = []
        self.sorted_header_units = []
        self.headers_footers = []
        self.headers = []
        self.footers = []
        for pg in pages:
            page = Page(pg)
            self.total_pgs +=1
            page.process_textboxes(pg)
            page.get_width_ofTB_moreThan_Half_of_pg()
            self.contour_header_footer_of_page(page)
            page.get_body_width_by_binning()
            page.is_single_column_page()
        
        self.process_footer_and_header()


    def contour_header_footer_of_page(self,pg):
        units = []
        for tb in pg.all_tbs:
            paragraph = tb.extract_text_from_tb()
            if not paragraph.isspace():
                units.append({'pg_num':pg.pg_num,'tb':tb,'para':paragraph,'x0':tb.coords[0],'y0':tb.coords[1]})
            else:
                pass
        if not units:
            return
        
        most_bottom_unit = sorted(units, key= lambda d: d['y0'], reverse=False)
        footer_area_units = []
        header_area_units = []

        headers = [most_bottom_unit[-1]]
        footers = [most_bottom_unit[0]]

        for ele in most_bottom_unit:
            smallest = most_bottom_unit[0]['y0']
            largest = most_bottom_unit[-1]['y0']
            if (ele['y0']-smallest) >= 0 and (ele['y0']- smallest) < 0.025 * pg.pg_height:
                if ele['para'] != most_bottom_unit[0]['para']:
                    footers.append(ele)
                    continue
                else:
                    continue
            if (largest - ele['y0']) >= 0 and (largest - ele['y0']) < 0.025* pg.pg_height:
                if ele['para'] != most_bottom_unit[-1]['para']:
                    headers.append(ele)
                    continue
                else:
                    continue
            
            if ele['y0'] - pg.pg_height/2 >= 0:
                header_area_units.append(ele)
            if ele['y0'] - pg.pg_height/2 < 0:
                footer_area_units.append(ele)
            
        header_area_units = sorted(header_area_units, key=lambda d: d['y0'], reverse=True)
        self.sorted_footer_units.append(footer_area_units)
        self.sorted_header_units.append(header_area_units)
        headers = sorted(headers, key=lambda d: d['x0'], reverse=False )
        headers = (el['para'] for el in headers if el['para'].strip())
        footers = sorted(footers, key=lambda d: d['x0'], reverse=False)
        footers = (el['para'] for el in footers if el['para'].strip())
        header = '!!??!!'.join(headers)
        footer = '!!??!!'.join(footers)
        # print({'page':pg.pg_num,'header':" ".join(header.split()),'footer':" ".join(footer.split())})
        self.headers_footers.append({'page':pg.pg_num,'header':" ".join(header.split()),'footer':" ".join(footer.split())})

    def process_footer_and_header(self):
        def similar(table, miner):
            return SequenceMatcher(None, table, miner).ratio()
        
        counter_in_loop_hf = 0
        while True:
            units_with_same_index = []
            i_break = False
            for el in self.sorted_footer_units:
                try:
                    units_with_same_index.append(el[counter_in_loop_hf])
                except Exception as e:
                    pass
            for unitt in units_with_same_index:
                similar_counter = 0
                for rest in units_with_same_index:
                    if similar(unitt['para'],rest['para']) > 0.4:
                        similar_counter += 1
                if similar_counter > 0.05 * self.total_pgs:
                    a = " ".join(unitt['para'].split())
                    for el in self.headers_footers:
                        if el['page'] == unitt['pg_num']:
                            el['footer'] = str(el['footer']+'!!??!!'+a)
                            
                else:
                    i_break = True
            if i_break:
                break
            counter_in_loop_hf +=1
        #_____________
        counter_in_loop_hf = 0
        while True:
            units_with_same_index = []
            i_break = False
            for el in self.sorted_header_units:
                try:
                    units_with_same_index.append(el[counter_in_loop_hf])
                except Exception as e:
                    pass
            for unitt in units_with_same_index:
                similar_counter = 0
                for rest in units_with_same_index:
                    if similar(unitt['para'],rest['para']) > 0.4:
                        similar_counter += 1
                if similar_counter > 0.05 * self.total_pgs:
                    a = " ".join(unitt['para'].split())
                    for el in self.headers_footers:
                        if el['page'] == unitt['pg_num']:
                            el['header'] = str(el['header']+'!!??!!'+a)
                else:
                    i_break = True
            if i_break:
                break
            counter_in_loop_hf +=1
        #------------------------------------------------------
        for el in self.headers_footers:
            counter_f = 0
            counter_h = 0
            for rest in self.headers_footers:
                if similar(el['footer'],rest['footer']) > 0.4:
                    counter_f +=1
            for rest in self.headers_footers:
                if similar(el['header'],rest['header']) > 0.4:
                    counter_h +=1

            if counter_f >= 0.05 * self.total_pgs :
                self.footers.append({'page':el['page'],'footers':el['footer'].split(sep='!!??!!')})
            if counter_h >= 0.05 * self.total_pgs:
                self.headers.append({'page':el['page'],'headers':el['header'].split(sep='!!??!!')})


        

            
    def parsePDF(self,pdf_path):
        base_name_of_file = os.path.splitext(os.path.basename(pdf_path))[0]
        self.parserTool.convert_to_xml(pdf_path,base_name_of_file)
        xml_path = f"{base_name_of_file}.xml"
        pages = self.parserTool.get_pages_from_xml(xml_path)

        self.process_pages(pages)


if __name__ == "__main__":
    pdf_path = r'/home/barath-kumar/Documents/IKanoon/Parser-and-Converter/in-union-act-ministryofcivilaviation-2025-04-16-17-publication-document.pdf'  # 👈 Replace with your PDF path
    main = Main()
    main.parsePDF(pdf_path)