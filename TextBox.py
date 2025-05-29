class TextBox:
    def __init__(self, tb):
        self.tbox = tb
        self.coords = tuple(map(float, tb.attrib["bbox"].split(",")))
        self.height = self.coords[1] - self.coords[3]
        self.width = self.coords[2] - self.coords[0]