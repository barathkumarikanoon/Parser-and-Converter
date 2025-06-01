from source.TextBox import TextBox
from sklearn.cluster import DBSCAN
import numpy as np

class Page:
    def __init__(self,pg):
        self.pg_width, self.pg_height = self.get_pg_coords(pg)
        self.list_of_tbs = []

    def get_pg_coords(self,pg):
        coords = tuple(map(float, pg.attrib["bbox"].split(",")))
        height = abs(coords[1] - coords[3])
        width = abs(coords[2] - coords[0])
        return width,height

    def process_textboxes(self,pg):
        textBoxes = pg.findall(".//textbox")
        for tb in textBoxes:
            self.list_of_tbs.append(TextBox(tb))
    
    def  get_width_ofTB_moreThan_Half_of_pg(self):
        self.fiftyPercent_moreWidth_tbs = []
        for tb in self.list_of_tbs:
            if round(tb.width,2) >= 0.5 * self.pg_width :
                self.fiftyPercent_moreWidth_tbs.append(tb)
    
    def get_page_layout(self):
        try :
            sum_height_of_tbs = round(sum([tb.height for tb in self.fiftyPercent_moreWidth_tbs]),2)
            if sum_height_of_tbs > 0.4 * self.pg_height:
                return "single_column_page"
            else:
                return "page_may have mulitple columns"
        
        except Exception as e:
            return e

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
        min_x0 = min(tb.coords[0] for tb in best_cluster)
        max_x2 = max(tb.coords[2] for tb in best_cluster)

        return round((max_x2 - min_x0),2)
    

    def get_body_width_by_binning(self):
        self.body_width = self.cluster_coord_with_max_height_span(self.fiftyPercent_moreWidth_tbs)
