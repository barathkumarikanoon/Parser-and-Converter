class TextBox:
    def __init__(self, tb):
        self.tbox = tb
        self.coords = tuple(map(float, tb.attrib["bbox"].split(",")))
        self.height = self.coords[3] - self.coords[1]
        self.width = self.coords[2] - self.coords[0]
        

    
    def extract_text_from_tb(self):
        all_text = []
        for textline in self.tbox.findall('.//textline'):
            line_texts = []
            for text in textline.findall('.//text'):
                if text.text:
                    line_texts.append(text.text)
            
            line = ''.join(line_texts).replace("\n", " ").strip()
            if line:
                all_text.append(line)
        
        # Join all lines with space (or newline if you want separation)
        return ' '.join(all_text)
