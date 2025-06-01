class TextBox:
    def __init__(self, tb):
        self.tbox = tb
        self.coords = tuple(map(float, tb.attrib["bbox"].split(",")))
        self.height = abs(self.coords[3] - self.coords[1])
        self.width = abs(self.coords[2] - self.coords[0])