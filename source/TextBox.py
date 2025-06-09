import re

class TextBox:
    def __init__(self, tb):
        self.tbox = tb
        self.coords = tuple(map(float, tb.attrib["bbox"].split(",")))
        self.height = self.coords[3] - self.coords[1]
        self.width = self.coords[2] - self.coords[0]
        

    # --- get texts from the textbox ---
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
    
    def textFont_is_bold(self):
        bold_font_re = re.compile(r'bold', re.IGNORECASE)
        no_of_chars = 0
        no_of_bold_chars = 0

        for textline in self.tbox.findall(".//textline"):
            for text in textline.findall(".//text"):
                if text.text :
                    no_of_chars += 1
                    font_name = text.attrib.get("font", "")
                    if bold_font_re.search(font_name):
                        # print(text.text)
                        no_of_bold_chars += 1

        if no_of_chars == 0:
            return False  # Avoid division by zero
        
        # print((no_of_bold_chars / no_of_chars) > 0.6)
        return (no_of_bold_chars / no_of_chars) > 0.1
    

    def textFont_is_italic(self):
        italic_font_re = re.compile(r'italic', re.IGNORECASE)
        no_of_chars = 0
        no_of_italic_chars = 0

        for textline in self.tbox.findall(".//textline"):
            for text in textline.findall(".//text"):
                if text.text:
                    no_of_chars += 1
                    font_name = text.attrib.get("font", "")
                    if italic_font_re.search(font_name):
                        no_of_italic_chars += 1

        if no_of_chars == 0:
            return False  # Avoid division by zero

        return (no_of_italic_chars / no_of_chars) > 0.1
        
    
    def is_uppercase(self):
        total_letters = 0
        total_uppercase = 0

        for textline in self.tbox.findall(".//textline"):
            for text in textline.findall(".//text"):
                if text.text:
                    for char in text.text:
                        if char.isalpha():
                            total_letters += 1
                            if char.isupper():
                                total_uppercase += 1

        if total_letters == 0:
            return False  # Avoid division by zero

        return (total_uppercase / total_letters) >= 0.25  # 60% or more letters are uppercase
    

    def is_titlecase(self):
        words = []
        for textline in self.tbox.findall(".//textline"):
            for text in textline.findall(".//text"):
                if text.text and isinstance(text.text, str):
                    # Optional: strip brackets around the text
                    cleaned_text = re.sub(r'^[\[\(\{]+|[\]\)\}]+$', '', text.text.strip())
                    words.extend(cleaned_text.split())

        if not words:
            return False

        titlecase_count = 0
        valid_word_count = 0

        for word in words:
            # Check if the word contains at least one alphabetic character
            if any(c.isalpha() for c in word):
                valid_word_count += 1
                # Check if first letter uppercase and the rest lowercase
                if len(word) == 1:
                    # For single letter words, just check uppercase
                    if word[0].isupper():
                        titlecase_count += 1
                else:
                    if word[0].isupper() and word[1:].islower():
                        titlecase_count += 1

        if valid_word_count == 0:
            return False

        # Return True if at least 70% of words are titlecase
        return (titlecase_count / valid_word_count) >= 0.25





