from TextBox import TextBox
from sklearn.cluster import DBSCAN
import numpy as np

class Page:
    def __init__(self,pg):
        self.pg_width, self.pg_height = self.get_pg_coords(pg)
        self.pg_num = pg.attrib["id"]
        self.all_tbs = []
        self.header_tbs = []
        self.footer_tbs = []
        self.side_notes = []

    def get_pg_coords(self,pg):
        coords = tuple(map(float, pg.attrib["bbox"].split(",")))
        height = abs(coords[1] - coords[3])
        width = abs(coords[2] - coords[0])
        return width,height

    def process_textboxes(self,pg):
        textBoxes = pg.findall(".//textbox")
        for tb in textBoxes:
            self.all_tbs.append(TextBox(tb))

    def get_side_notes(self):
        if not hasattr(self, 'body_startX') or not hasattr(self, 'body_endX'):
            return  # Skip if body region not defined
        
        for tb in self.all_tbs:
            if (tb.coords[2]< self.body_startX or tb.coords[0] > self.body_endX ) and (tb not in self.header_tbs) and tb.height < 0.25 * self.pg_height and tb.width < 0.25 * self.pg_width:
                if  tb.extract_text_from_tb().strip():
                    self.side_notes.append(tb)
        
    # def print_headers(self):
    #     for tb in self.header_tbs:
    #         print(tb.extract_text_from_tb())
    
    # def print_footers(self):
    #     for tb in self.footer_tbs:
    #         print(tb.extract_text_from_tb())

    # def print_sidenotes(self):
    #     for tb in self.side_notes:
    #         print(tb.extract_text_from_tb())

    
    def  get_width_ofTB_moreThan_Half_of_pg(self):
        self.fiftyPercent_moreWidth_tbs = []
        for tb in self.all_tbs:
            if round(tb.width,2) >= 0.5 * self.pg_width :
                self.fiftyPercent_moreWidth_tbs.append(tb)
    
    def is_single_column_page(self):
            sum_height_of_tbs = round(sum([tb.height for tb in self.fiftyPercent_moreWidth_tbs]),2)
            if sum_height_of_tbs > 0.4 * self.pg_height:
                return True 
            else:
                return False

    def cluster_coord_with_max_height_span(self, textboxes, eps=8, min_samples=2):
        if not textboxes:
            return None

        # Cluster based on x0
        x_coords = np.array([tb.coords[0] for tb in textboxes]).reshape(-1, 1)
        db = DBSCAN(eps=eps, min_samples=min_samples)
        labels = db.fit_predict(x_coords)

        # Group textboxes into clusters
        clusters = {}
        for tb, label in zip(textboxes, labels):
            clusters.setdefault(label, []).append(tb)

        # Calculate total height for each cluster
        max_height_sum = 0
        best_cluster = []

        for label, group in clusters.items():
            total_height = sum(tb.height for tb in group)
            if total_height > max_height_sum:
                max_height_sum = total_height
                best_cluster = group

        if not best_cluster:
            return None

        # Calculate bounding box of best cluster
        self.body_startX = min(tb.coords[0] for tb in best_cluster)
        self.body_endX = max(tb.coords[2] for tb in best_cluster)

        return round((self.body_endX - self.body_startX),2)
    
    
    def get_body_width_by_binning(self):
        if self.fiftyPercent_moreWidth_tbs:
            self.body_width = self.cluster_coord_with_max_height_span(self.fiftyPercent_moreWidth_tbs)
        else:
            self.body_width = self.cluster_coord_with_max_height_span_v1(self.all_tbs) - self.cluster_coord_with_max_height_span_v2(self.all_tbs) 
        
    
    # def get_body_width(self):
    #     def findStartX():
    #         minVal = float("inf")
    #         for tb in self.fiftyPercent_moreWidth_tbs:
    #             minVal = min(tb.coords[0],minVal)
    #         return minVal
        
    #     def findEndX():
    #         maxVal = float("-inf")
    #         for tb in self.fiftyPercent_moreWidth_tbs:
    #             maxVal = max(tb.coords[2],maxVal)
    #         return maxVal

    #     self.body_startX = findStartX()   
    #     self.body_endX = findEndX() 
    #     self.body_width = self.body_endX - self.body_startX
    #     print("Body start and end:",self.body_startX,self.body_endX)
