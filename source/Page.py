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

    # --- func for getting page coordinates, height, width ---
    def get_pg_coords(self,pg):
        coords = tuple(map(float, pg.attrib["bbox"].split(",")))
        height = abs(coords[1] - coords[3])
        width = abs(coords[2] - coords[0])
        return width,height

    # --- gather all textboxes of the page and store it in the list ---
    def process_textboxes(self,pg):
        textBoxes = pg.findall(".//textbox")
        for tb in textBoxes:
            self.all_tbs.append(TextBox(tb))

    # --- func for gathering the sidenotes textboxes ---
    def get_side_notes(self):
        if not hasattr(self, 'body_startX') or not hasattr(self, 'body_endX'):
            return  # Skip if body region not defined
        
        for tb in self.all_tbs:
            if (tb.coords[2]< self.body_startX or tb.coords[0] > self.body_endX ) and (tb not in self.header_tbs) and tb.height < 0.25 * self.pg_height and tb.width < 0.25 * self.pg_width:
                if  tb.extract_text_from_tb().strip():
                    self.side_notes.append(tb)
        
    def print_headers(self):
        for tb in self.header_tbs:
            print(tb.extract_text_from_tb())
    
    def print_footers(self):
        for tb in self.footer_tbs:
            print(tb.extract_text_from_tb())

    def print_sidenotes(self):
        for tb in self.side_notes:
            print(tb.extract_text_from_tb())

    #  --- func to find the tbs which has more than 50% of page width ---
    def  get_width_ofTB_moreThan_Half_of_pg(self):
        self.fiftyPercent_moreWidth_tbs = []
        for tb in self.all_tbs:
            if round(tb.width,2) >= 0.5 * self.pg_width :
                self.fiftyPercent_moreWidth_tbs.append(tb)

    # --- func to find the page is single column or not ---
    def is_single_column_page(self):
            sum_height_of_tbs = round(sum([tb.height for tb in self.fiftyPercent_moreWidth_tbs]),2)
            if sum_height_of_tbs > 0.4 * self.pg_height:
                return True 
            else:
                return False
    
    # --- cluster the textboxes which make max_height span --- 
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
    
    # --- func to find body width if fiftyPercent_moreWidth_tbs exists ---
    def get_body_width_by_binning(self):
        if self.fiftyPercent_moreWidth_tbs:
            self.body_width = self.cluster_coord_with_max_height_span(self.fiftyPercent_moreWidth_tbs)
        else:
            self.body_width = self.get_body_width()
        
    # --- func to find body width if fiftyPercent_moreWidth_tbs not exists ---
    def get_body_width(self):
        body_candidates = [
        tb for tb in self.all_tbs
        if tb not in self.header_tbs
        and tb.coords[0] > 0.125 * self.pg_width
        and tb.coords[2] < 0.875 * self.pg_width
        ]
        
        self.body_startX = min(tb.coords[0] for tb in body_candidates)
        self.body_endX = max(tb.coords[2] for tb in body_candidates)

        return round(self.body_endX - self.body_startX, 2)
