from TextBox import TextBox
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
    
    def  cluster_coord(self,data):
        X = np.array(data).reshape(-1, 1)
        db = DBSCAN(eps=5, min_samples=2)  # You can tune `eps`
        labels = db.fit_predict(X)

        # Group by labels
        clusters = {}
        for tb, label in zip(data, labels):
            clusters.setdefault(label, []).append(tb)
        
        return clusters

    def width_binning(self):
        # Filter and round the widths
        bigger_width_tb  = [tb for tb in self.list_of_tbs if tb.width > 0.5 * self.pg_width]
        if not bigger_width_tb:
            return {}
        
        for_body_startX = [tb.coords[0] for tb in bigger_width_tb]
        for_body_endX   = [tb.coords[2] for tb in bigger_width_tb]

        print(self.cluster_coord(for_body_startX))
        print(self.cluster_coord(for_body_endX))
        
        
    # def find_optimal_k(self,data):
    #     data = np.array(data).reshape(-1, 1)
    #     # Determine max_k dynamically based on data distribution
    #     max_k = min(int(np.sqrt(len(data))), len(data) // 2)  # Adaptive upper bound
    #     wcss = []
    #     for k in range(1, max_k + 1):
    #         kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
    #         kmeans.fit(data)
    #         wcss.append(kmeans.inertia_)

    #     # Heuristic: pick the point where the decrease slows down (second derivative method)
    #     deltas = np.diff(wcss)
    #     double_deltas = np.diff(deltas)
    #     if len(double_deltas) > 0:
    #         optimal_k = np.argmin(double_deltas) + 2  # +2 due to double diff
    #     else:
    #         optimal_k = 1
        
    #     return optimal_k

            
    # def width_binning(self):
    #     bigger_width_tb = [round(tb.width,2) for tb in self.list_of_tbs if tb.width> 0.5 * self.pg_width]
    #     optimal_k = self.find_optimal_k(bigger_width_tb)
    #     print(optimal_k)
    #     kmeans = KMeans(n_clusters=optimal_k)
    #     kmeans.fit(np.array(bigger_width_tb).reshape(-1, 1))
    #     clusters = {i: [] for i in range(optimal_k)}
    #     for i, label in enumerate(kmeans.labels_):
    #         clusters[label].append(bigger_width_tb[i])
    #     return clusters


