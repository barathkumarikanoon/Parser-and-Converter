import camelot
import logging 
import statistics
import numpy as np
import pandas as pd

class TableExtraction:
    def __init__(self,pdf_path,pg_num, pdf_type, scanned_copy):
        self.logger = logging.getLogger(__name__)
        self.pdf_type = pdf_type
        self.tables, self.table_bbox = self.get_table_and_bbox(pdf_path,pg_num, scanned_copy)
    
    # --- func to find the table contents and their coordinates ---
    def get_table_and_bbox(self,pdf_path,page_num, scanned_copy):
        table = {}
        bbox = {}
        if scanned_copy:
            return table, bbox
        try:
            tables_and_bbox = camelot.read_pdf(pdf_path, pages=page_num, flavor='lattice')
            for idx,tab in enumerate(tables_and_bbox):
                table[idx] = tab.df
                bbox[idx] = tab._bbox
        except Exception as e:
            self.logger.error("Exception occurred while checking for table contents: %s" % (str(e)))

        return table,bbox

    def get_table_width(self, idx):
        if idx not in self.table_bbox:
            return None
        x1, y1, x2, y2 = self.table_bbox[idx]
        width = abs(x2 - x1)
        return width
    
    def get_table_height(self, idx):
        if idx not in self.table_bbox:
            return None
        x1, y1, x2, y2 = self.table_bbox[idx]
        height = abs(y2 - y1)
        return height

class TBItem:
    def __init__(self, tb_obj, x0, y0, x1, y1, text,
                 n_textlines=1, line_height_est=10.0, is_split_child=False):
        self.tb_obj = tb_obj
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.text = text
        self.n_textlines = n_textlines
        self.line_height_est = line_height_est
        self.is_split_child = is_split_child

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0


class PenalizedLogisticClassifier:
    FEATURE_ORDER = ()

    def __init__(self, weights=None, bias=0.0):
        self.weights = dict(weights) if weights else {f: 0.0 for f in self.FEATURE_ORDER}
        self.bias = bias

    @staticmethod
    def _sigmoid(z):
        z = max(-60.0, min(60.0, z))
        return 1.0 / (1.0 + np.exp(-z))

    def _vectorize(self, features):
        return np.array([features.get(f, 0.0) for f in self.FEATURE_ORDER], dtype=float)

    def predict_proba(self, features):
        x = self._vectorize(features)
        w = np.array([self.weights.get(f, 0.0) for f in self.FEATURE_ORDER], dtype=float)
        z = float(np.dot(w, x)) + self.bias
        return self._sigmoid(z)

    def predict(self, features, threshold=0.5):
        return self.predict_proba(features) >= threshold

    def fit(self, X, y, l2=0.05, lr=0.5, epochs=300):
        if not X or not y or len(X) != len(y):
            raise ValueError("X and y must be non-empty and the same length")

        n = len(X)
        feat_matrix = np.array([[fd.get(f, 0.0) for f in self.FEATURE_ORDER] for fd in X], dtype=float)
        labels = np.array(y, dtype=float)

        w = np.array([self.weights.get(f, 0.0) for f in self.FEATURE_ORDER], dtype=float)
        b = self.bias

        for _ in range(epochs):
            z = feat_matrix.dot(w) + b
            preds = 1.0 / (1.0 + np.exp(-np.clip(z, -60.0, 60.0)))
            error = preds - labels

            grad_w = feat_matrix.T.dot(error) / n + 2.0 * l2 * w
            grad_b = error.mean()

            w -= lr * grad_w
            b -= lr * grad_b

        self.weights = {f: float(w[i]) for i, f in enumerate(self.FEATURE_ORDER)}
        self.bias = float(b)
        return self

    def update_online(self, features, label, lr=0.15, l2=0.02, reward=1.0):
        x = self._vectorize(features)
        w = np.array([self.weights.get(f, 0.0) for f in self.FEATURE_ORDER], dtype=float)
        z = float(np.dot(w, x)) + self.bias
        pred = self._sigmoid(z)

        error = (pred - float(label)) * float(reward)
        grad_w = error * x + 2.0 * l2 * w
        grad_b = error

        w = w - lr * grad_w
        b = self.bias - lr * grad_b

        self.weights = {f: float(w[i]) for i, f in enumerate(self.FEATURE_ORDER)}
        self.bias = float(b)
        return pred

    def to_dict(self):
        return {"weights": self.weights, "bias": self.bias}

    @classmethod
    def from_dict(cls, data):
        return cls(weights=data.get("weights"), bias=data.get("bias", 0.0))

    def save(self, path):
        import json
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path):
        import json
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)


class HeaderRowClassifier(PenalizedLogisticClassifier):
    FEATURE_ORDER = ("fill_diff", "len_ratio", "lines_diff", "gap_ratio")

    @classmethod
    def default(cls):
        return cls(
            weights={
                "fill_diff": 3.2,
                "len_ratio": 2.6,
                "lines_diff": 1.6,
                "gap_ratio": 1.1,
            },
            bias=-1.6,
        )


class RegionMergeClassifier(PenalizedLogisticClassifier):
    FEATURE_ORDER = ("col_overlap_ratio", "gap_norm", "xspan_overlap", "col_count_diff")

    @classmethod
    def default(cls):
        return cls(
            weights={
                "col_overlap_ratio": 3.0,
                "gap_norm": -1.3,
                "xspan_overlap": 2.0,
                "col_count_diff": -2.2,
            },
            bias=-0.6,
        )


class BorderlessTableExtraction:
    def __init__(self, all_tbs, pdf_type,
                 page_width, page_height, adaptive_ratio=0.02,
                 min_col_support=3, min_narrow_col_support=2,
                 min_rows=3, min_cols=2, min_fill_ratio=0.4,
                 max_col_width_ratio=0.6,
                 min_col_row_support_ratio=0.34,
                 min_multi_col_row_ratio=0.5,
                 header_classifier=None,
                 header_probability_threshold=0.5,
                 region_merge_classifier=None,
                 region_merge_probability_threshold=0.5):
        self.logger = logging.getLogger(__name__)
        self.pdf_type = pdf_type
        self.all_tbs = all_tbs

        self.page_width = page_width
        self.page_height = page_height
        self.adaptive_ratio = adaptive_ratio

        self.min_col_support = min_col_support
        self.min_narrow_col_support = min_narrow_col_support
        self.min_rows = min_rows
        self.min_cols = min_cols
        self.min_fill_ratio = min_fill_ratio
        self.max_col_width_ratio = max_col_width_ratio

        self.min_col_row_support_ratio = min_col_row_support_ratio
        self.min_multi_col_row_ratio = min_multi_col_row_ratio

        self.header_classifier = self._resolve_classifier(header_classifier, HeaderRowClassifier)
        self.header_probability_threshold = header_probability_threshold

        self.region_merge_classifier = self._resolve_classifier(region_merge_classifier, RegionMergeClassifier)
        self.region_merge_probability_threshold = region_merge_probability_threshold

        self.table_headers = {}
        self.table_header_scores = {}
        self.table_header_features = {}
        self.region_merge_events = []

        self.tables, self.table_bbox = self.get_table_and_bbox()

    @staticmethod
    def _resolve_classifier(classifier, classifier_cls):
        if classifier is None:
            return classifier_cls.default()
        if isinstance(classifier, str):
            return classifier_cls.load(classifier)
        return classifier

    def px(self, ratio=None):
        ratio = self.adaptive_ratio if ratio is None else ratio
        return self.page_width * ratio

    def py(self, ratio=None):
        ratio = self.adaptive_ratio if ratio is None else ratio
        return self.page_height * ratio

    def box_x(self, item, ratio=0.10):
        return item.width * ratio

    def box_y(self, item, ratio=0.10):
        return item.height * ratio

    def get_table_and_bbox(self):
        table, bbox = {}, {}
        try:
            items = self._collect_candidate_items()
            if len(items) < self.min_rows:
                return table, bbox

            line_height = self._estimate_line_height(items)

            column_clusters = self._cluster_columns(items)
            table_items, item_col_id = self._flag_table_items(items, column_clusters)
            if len(table_items) < self.min_rows:
                return table, bbox

            row_groups = self._cluster_rows(table_items, line_height)
            regions = self._segment_rows_into_regions(row_groups, line_height)
            regions = self._merge_related_regions(regions, item_col_id, line_height)

            idx = 0
            for region_rows in regions:
                if len(region_rows) < self.min_rows:
                    continue

                region_rows = self._prune_weak_columns(region_rows, item_col_id)
                if len(region_rows) < self.min_rows:
                    continue

                if not self._passes_multi_col_row_check(region_rows, item_col_id):
                    self.logger.debug(
                        "Rejected borderless region: not enough multi-column rows "
                        "(likely not a real table)"
                    )
                    continue

                df, region_bbox, fill_ratio, n_cols, has_header, header_prob, header_features = self._build_table(
                    region_rows, item_col_id
                )
                if df is None:
                    continue

                n_rows = df.shape[0]
                if n_rows >= self.min_rows and n_cols >= self.min_cols and fill_ratio >= self.min_fill_ratio:
                    table[idx] = df
                    bbox[idx] = region_bbox
                    self.table_headers[idx] = has_header
                    self.table_header_scores[idx] = header_prob
                    if header_features is not None:
                        self.table_header_features[idx] = header_features
                    self.logger.debug(
                        f"Accepted borderless table idx={idx} rows={n_rows} cols={n_cols} "
                        f"fill_ratio={round(fill_ratio, 2)} header={has_header} "
                        f"header_p={round(header_prob, 3)} bbox={region_bbox}"
                    )
                    idx += 1
        except Exception as e:
            self.logger.error(
                "Exception occurred while checking for borderless table contents: %s" % (str(e))
            )

        return table, bbox

    def _collect_candidate_items(self):
        items = []
        for tb_obj, label in self.all_tbs.items():
            if label is not None:
                continue

            x0, y0, x1, y1 = tb_obj.coords
            text = None
            if hasattr(tb_obj, "extract_text_from_tb"):
                text = tb_obj.extract_text_from_tb()
            if not text or not text.strip():
                continue
            text = text.strip()

            textlines = tb_obj.tbox.findall("textline")
            n_lines = max(1, len(textlines))
            line_height_est = (y1 - y0) / n_lines if n_lines else (y1 - y0)

            split_items = self._try_split_multi_column_box(
                tb_obj, x0, y0, x1, y1, textlines, line_height_est
            )
            if split_items:
                items.extend(split_items)
            else:
                items.append(TBItem(tb_obj, x0, y0, x1, y1, text, n_lines, line_height_est))

        return items

    def _try_split_multi_column_box(self, tb_obj, x0, y0, x1, y1, textlines, line_height_est):
        if not textlines:
            return None
        try:
            first_line = textlines[0]
            fl_bbox = first_line.attrib.get("bbox")
            if not fl_bbox:
                return None
            fl_x0, fl_y0, fl_x1, fl_y1 = [float(v) for v in fl_bbox.split(",")]

            runs = first_line.findall("text")
            spans = []
            for r in runs:
                rb = r.attrib.get("bbox")
                if not rb:
                    return None
                rx0, ry0, rx1, ry1 = [float(v) for v in rb.split(",")]
                spans.append((rx0, rx1, r.text or ""))

            if len(spans) < 3:
                return None

            gaps = []
            for i in range(len(spans) - 1):
                gap = spans[i + 1][0] - spans[i][1]
                if gap > 0:
                    gaps.append(gap)
            if len(gaps) < 3:
                return None

            median_gap = statistics.median(gaps)
            mad = statistics.median([abs(g - median_gap) for g in gaps]) or self.px(0.002)

            split_indices = []
            for i in range(len(spans) - 1):
                gap = spans[i + 1][0] - spans[i][1]
                if (
                    gap > median_gap + 6 * mad
                    and gap > max(
                        line_height_est * 0.5,
                        self.box_x(TBItem(tb_obj, x0, y0, x1, y1, ""), 0.08)
                    )
                ):
                    split_indices.append(i)

            if not split_indices:
                return None

            boundaries = [0] + [i + 1 for i in split_indices] + [len(spans)]
            segments = []
            for s, e in zip(boundaries[:-1], boundaries[1:]):
                seg_spans = spans[s:e]
                if not seg_spans:
                    continue
                seg_x0 = seg_spans[0][0]
                seg_x1 = seg_spans[-1][1]
                seg_text = "".join(sp[2] for sp in seg_spans).strip()
                segments.append([seg_x0, seg_x1, seg_text])

            if len(segments) < 2:
                return None

            rest_text_parts = []
            rest_x1 = segments[-1][1]
            for tl in textlines[1:]:
                tb2 = tl.attrib.get("bbox")
                if tb2:
                    _, _, tlx1, _ = [float(v) for v in tb2.split(",")]
                    rest_x1 = max(rest_x1, tlx1)
                line_text = "".join((t.text or "") for t in tl.findall("text")).strip()
                if line_text:
                    rest_text_parts.append(line_text)

            items_out = []
            for idx, (seg_x0, seg_x1, seg_text) in enumerate(segments):
                is_last = (idx == len(segments) - 1)
                if not seg_text:
                    continue
                if is_last:
                    full_text = " ".join([seg_text] + rest_text_parts).strip()
                    items_out.append(TBItem(
                        tb_obj, seg_x0, y0, max(seg_x1, rest_x1), y1, full_text,
                        n_textlines=len(textlines), line_height_est=line_height_est,
                        is_split_child=True
                    ))
                else:
                    items_out.append(TBItem(
                        tb_obj, seg_x0, fl_y0, seg_x1, fl_y1, seg_text,
                        n_textlines=1, line_height_est=line_height_est,
                        is_split_child=True
                    ))

            return items_out if len(items_out) >= 2 else None
        except Exception:
            return None

    def _estimate_line_height(self, items):
        heights = [it.line_height_est for it in items if it.line_height_est > 0]
        if not heights:
            return self.py(0.01)
        return statistics.median(heights)

    @staticmethod
    def _auto_eps(sorted_values, k=2, *, fallback):
        n = len(sorted_values)
        if n < k + 2:
            return fallback
        k_dists = []
        for i in range(n):
            lo, hi = max(0, i - k), min(n, i + k + 1)
            neighbours = sorted(abs(sorted_values[i] - sorted_values[j]) for j in range(lo, hi) if j != i)
            if len(neighbours) >= k:
                k_dists.append(neighbours[k - 1])
        if not k_dists:
            return fallback
        k_dists.sort()
        y = np.array(k_dists, dtype=float)
        x = np.arange(len(y), dtype=float)
        x_range = x.max() - x.min() if x.max() > x.min() else 1.0
        y_range = y.max() - y.min() if y.max() > y.min() else 1.0
        x_norm = (x - x.min()) / x_range
        y_norm = (y - y.min()) / y_range
        diff = y_norm - x_norm
        knee_idx = int(np.argmax(diff))
        return max(k_dists[knee_idx], fallback * 0.25)

    @staticmethod
    def _sequential_cluster_1d(values_with_ref, eps):
        if not values_with_ref:
            return []
        clusters = [[values_with_ref[0][1]]]
        cluster_vals = [[values_with_ref[0][0]]]
        for val, ref in values_with_ref[1:]:
            if val - cluster_vals[-1][-1] <= eps:
                clusters[-1].append(ref)
                cluster_vals[-1].append(val)
            else:
                clusters.append([ref])
                cluster_vals.append([val])
        return clusters

    def _cluster_columns(self, items):
        sorted_items = sorted(items, key=lambda it: it.x0)
        xs = [it.x0 for it in sorted_items]
        eps_x = self._auto_eps(xs, k=2, fallback=self.px(0.015))

        raw_clusters = self._sequential_cluster_1d(list(zip(xs, sorted_items)), eps_x)

        median_item_width = statistics.median([it.width for it in items]) if items else self.px(0.01)

        column_clusters = []
        for cluster_items in raw_clusters:
            widths = [it.width for it in cluster_items]
            median_width = statistics.median(widths)

            is_narrow = median_width < median_item_width * 0.5
            required_support = self.min_narrow_col_support if is_narrow else self.min_col_support

            if len(cluster_items) < required_support:
                continue

            xs_i = [it.x0 for it in cluster_items]
            column_clusters.append({
                "items": cluster_items,
                "left": statistics.mean(xs_i),
                "median_width": median_width,
                "is_narrow": is_narrow,
            })

        column_clusters.sort(key=lambda c: c["left"])
        return column_clusters

    def _dynamic_max_col_width_ratio(self, n_columns_detected):
        if n_columns_detected <= self.min_cols:
            reserved_ratio = 0.10
        else:
            reserved_ratio = 0.10 * (n_columns_detected - 1)
        dynamic_cap = 1.0 - min(reserved_ratio, 0.55)
        return max(self.max_col_width_ratio, dynamic_cap)

    def _flag_table_items(self, items, column_clusters):
        if not items or len(column_clusters) < self.min_cols:
            return [], {}

        x_min = min(it.x0 for it in items)
        x_max = max(it.x1 for it in items)
        total_span = max(x_max - x_min, 1.0)

        dynamic_ratio = self._dynamic_max_col_width_ratio(len(column_clusters))

        valid_clusters = [
            c for c in column_clusters
            if (c["median_width"] / total_span) <= dynamic_ratio
        ]

        if len(valid_clusters) < self.min_cols:
            return [], {}

        item_col_id = {}
        table_items = []
        for col_id, cluster in enumerate(valid_clusters):
            for it in cluster["items"]:
                item_col_id[id(it)] = col_id
                table_items.append(it)

        return table_items, item_col_id

    def _cluster_rows(self, table_items, line_height):
        fallback_eps_row = max(self.py(0.003), line_height * 0.6)

        sorted_items = sorted(table_items, key=lambda it: it.y1)
        ys = [it.y1 for it in sorted_items]

        eps_row = self._auto_eps(ys, k=2, fallback=fallback_eps_row)
        eps_row = max(eps_row, self.py(0.0015))
        eps_row = min(eps_row, line_height * 2.5)

        raw_row_clusters = self._sequential_cluster_1d(list(zip(ys, sorted_items)), eps_row)

        raw_row_clusters.sort(key=lambda cluster: -statistics.mean(it.y1 for it in cluster))
        return raw_row_clusters

    def _segment_rows_into_regions(self, row_groups, line_height):
        if not row_groups:
            return []

        gaps = []
        for i in range(len(row_groups) - 1):
            cur_bottom = min(it.y0 for it in row_groups[i])
            nxt_top = max(it.y1 for it in row_groups[i + 1])
            gaps.append(cur_bottom - nxt_top)

        baseline = statistics.median([g for g in gaps if g > -line_height]) if gaps else line_height
        region_gap_threshold = max(
            self.py(0.015),
            line_height * 1.8,
            baseline * 2.2 if baseline > 0 else line_height * 1.8
        )

        regions = []
        current = [row_groups[0]]
        for i in range(1, len(row_groups)):
            cur_bottom = min(it.y0 for it in row_groups[i - 1])
            nxt_top = max(it.y1 for it in row_groups[i])
            gap = cur_bottom - nxt_top
            if gap > region_gap_threshold:
                regions.append(current)
                current = []
            current.append(row_groups[i])
        if current:
            regions.append(current)

        return regions

    @staticmethod
    def _compute_region_merge_features(region_a, region_b, item_col_id, line_height):
        items_a = [it for row in region_a for it in row]
        items_b = [it for row in region_b for it in row]
        if not items_a or not items_b:
            return None

        cols_a = set(item_col_id[id(it)] for it in items_a)
        cols_b = set(item_col_id[id(it)] for it in items_b)
        union_cols = cols_a | cols_b
        col_overlap_ratio = len(cols_a & cols_b) / len(union_cols) if union_cols else 0.0
        max_col_count = max(len(cols_a), len(cols_b), 1)
        col_count_diff = abs(len(cols_a) - len(cols_b)) / max_col_count

        a_bottom = min(it.y0 for it in items_a)
        b_top = max(it.y1 for it in items_b)
        gap = a_bottom - b_top
        gap_norm = gap / line_height if line_height else gap

        a_x0, a_x1 = min(it.x0 for it in items_a), max(it.x1 for it in items_a)
        b_x0, b_x1 = min(it.x0 for it in items_b), max(it.x1 for it in items_b)
        overlap = max(0.0, min(a_x1, b_x1) - max(a_x0, b_x0))
        union_span = max(a_x1, b_x1) - min(a_x0, b_x0)
        xspan_overlap = overlap / union_span if union_span > 0 else 0.0

        return {
            "col_overlap_ratio": col_overlap_ratio,
            "gap_norm": max(-5.0, min(5.0, gap_norm)),
            "xspan_overlap": xspan_overlap,
            "col_count_diff": col_count_diff,
        }

    def _merge_related_regions(self, regions, item_col_id, line_height):
        if len(regions) < 2:
            return regions

        merged_regions = [regions[0]]
        for region in regions[1:]:
            prev_region = merged_regions[-1]
            features = self._compute_region_merge_features(prev_region, region, item_col_id, line_height)
            prob = self.region_merge_classifier.predict_proba(features) if features else 0.0
            should_merge = features is not None and prob >= self.region_merge_probability_threshold

            if features is not None:
                self.region_merge_events.append((features, should_merge, prob))

            if should_merge:
                merged_regions[-1] = prev_region + region
                self.logger.debug(f"Merged two borderless regions into one table (p={round(prob, 3)})")
            else:
                merged_regions.append(region)

        return merged_regions

    def _prune_weak_columns(self, region_rows, item_col_id):
        n_rows = len(region_rows)
        if n_rows == 0:
            return region_rows

        col_row_counts = {}
        for row_items in region_rows:
            cols_in_row = set(item_col_id[id(it)] for it in row_items)
            for c in cols_in_row:
                col_row_counts[c] = col_row_counts.get(c, 0) + 1

        min_row_floor = max(1, int(round(self.min_rows * 0.5)))
        min_support = max(min_row_floor, int(round(n_rows * self.min_col_row_support_ratio)))
        keep_cols = {c for c, cnt in col_row_counts.items() if cnt >= min_support}

        if len(keep_cols) < self.min_cols:
            return []

        pruned_rows = []
        for row_items in region_rows:
            kept_items = [it for it in row_items if item_col_id[id(it)] in keep_cols]
            if kept_items:
                pruned_rows.append(kept_items)

        return pruned_rows

    def _passes_multi_col_row_check(self, region_rows, item_col_id):
        if not region_rows:
            return False

        multi_col_rows = 0
        for row_items in region_rows:
            cols_in_row = set(item_col_id[id(it)] for it in row_items)
            if len(cols_in_row) >= 2:
                multi_col_rows += 1

        ratio = multi_col_rows / len(region_rows)
        return ratio >= self.min_multi_col_row_ratio

    @staticmethod
    def _compute_header_features(region_rows, item_col_id, n_cols):
        if len(region_rows) < 2:
            return None

        header_items = region_rows[0]
        body_rows = region_rows[1:]
        if not header_items or not body_rows or n_cols == 0:
            return None

        header_cols = set(item_col_id[id(it)] for it in header_items)
        header_fill = len(header_cols) / n_cols
        header_avg_len = statistics.mean(len(it.text) for it in header_items)
        header_avg_lines = statistics.mean(it.n_textlines for it in header_items)

        body_fills, body_lens, body_lines = [], [], []
        for row_items in body_rows:
            cols = set(item_col_id[id(it)] for it in row_items)
            body_fills.append(len(cols) / n_cols)
            body_lens.extend(len(it.text) for it in row_items)
            body_lines.extend(it.n_textlines for it in row_items)

        if not body_fills or not body_lens or not body_lines:
            return None

        body_fill_median = statistics.median(body_fills)
        body_len_mean = statistics.mean(body_lens)
        body_lines_mean = statistics.mean(body_lines)

        fill_diff = header_fill - body_fill_median
        len_ratio = 1.0 - (header_avg_len / body_len_mean if body_len_mean else 1.0)
        lines_diff = body_lines_mean - header_avg_lines

        header_bottom = min(it.y0 for it in header_items)
        first_body_top = max(it.y1 for it in body_rows[0])
        header_to_body_gap = header_bottom - first_body_top

        body_gaps = []
        for i in range(len(body_rows) - 1):
            cur_bottom = min(it.y0 for it in body_rows[i])
            nxt_top = max(it.y1 for it in body_rows[i + 1])
            body_gaps.append(cur_bottom - nxt_top)

        if body_gaps:
            median_body_gap = statistics.median(body_gaps)
            gap_ratio = (header_to_body_gap - median_body_gap) / (abs(median_body_gap) + 1e-6)
        else:
            gap_ratio = 0.0
        gap_ratio = max(-5.0, min(5.0, gap_ratio))

        return {
            "fill_diff": fill_diff,
            "len_ratio": len_ratio,
            "lines_diff": lines_diff,
            "gap_ratio": gap_ratio,
        }

    def _detect_header_row(self, region_rows, item_col_id, n_cols):
        if len(region_rows) <= self.min_rows:
            return False, 0.0, None

        features = self._compute_header_features(region_rows, item_col_id, n_cols)
        if features is None:
            return False, 0.0, None

        prob = self.header_classifier.predict_proba(features)
        return prob >= self.header_probability_threshold, prob, features

    @staticmethod
    def _dedupe_header_names(raw_names):
        seen = {}
        final_names = []
        for i, name in enumerate(raw_names):
            name = name if name else f"col_{i + 1}"
            if name in seen:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            else:
                seen[name] = 0
            final_names.append(name)
        return final_names

    def _build_table(self, region_rows, item_col_id):
        all_items = [it for row in region_rows for it in row]
        col_ids_present = sorted(set(item_col_id[id(it)] for it in all_items))
        col_index_map = {col_id: i for i, col_id in enumerate(col_ids_present)}
        n_cols = len(col_index_map)
        if n_cols == 0:
            return None, None, 0.0, 0, False, 0.0, None

        has_header, header_prob, header_features = self._detect_header_row(region_rows, item_col_id, n_cols)
        header_items = region_rows[0] if has_header else None
        data_rows = region_rows[1:] if has_header else region_rows

        def build_row_cells(row_items):
            cells = [""] * n_cols
            occupied = [False] * n_cols
            for it in sorted(row_items, key=lambda x: x.x0):
                col_id = item_col_id[id(it)]
                c_idx = col_index_map[col_id]
                if occupied[c_idx]:
                    cells[c_idx] = (cells[c_idx] + " " + it.text).strip()
                else:
                    cells[c_idx] = it.text
                    occupied[c_idx] = True
            return cells

        rows_out = []
        filled = 0
        total_cells = 0
        for row_items in data_rows:
            cells = build_row_cells(row_items)
            rows_out.append(cells)
            filled += sum(1 for c in cells if c)
            total_cells += n_cols

        if not rows_out:
            return None, None, 0.0, 0, False, 0.0, None

        df = pd.DataFrame(rows_out)
        fill_ratio = filled / total_cells if total_cells else 0.0

        if has_header:
            header_cells = build_row_cells(header_items)
            df.columns = self._dedupe_header_names(header_cells)

        x0 = min(it.x0 for it in all_items)
        x1 = max(it.x1 for it in all_items)
        y0 = min(it.y0 for it in all_items)
        y1 = max(it.y1 for it in all_items)

        return df, (x0, y0, x1, y1), fill_ratio, n_cols, has_header, header_prob, header_features

    def reinforce_header_row(self, idx, actual_is_header, lr=0.15, l2=0.02, reward=1.0):
        features = self.table_header_features.get(idx)
        if features is None:
            return False
        label = 1.0 if actual_is_header else 0.0
        self.header_classifier.update_online(features, label, lr=lr, l2=l2, reward=reward)
        return True

    def reinforce_region_merge(self, event_index, actual_should_merge, lr=0.15, l2=0.02, reward=1.0):
        if event_index < 0 or event_index >= len(self.region_merge_events):
            return False
        features, _, _ = self.region_merge_events[event_index]
        label = 1.0 if actual_should_merge else 0.0
        self.region_merge_classifier.update_online(features, label, lr=lr, l2=l2, reward=reward)
        return True

    def persist_learned_weights(self, header_path=None, region_merge_path=None):
        if header_path:
            self.header_classifier.save(header_path)
        if region_merge_path:
            self.region_merge_classifier.save(region_merge_path)

    def get_table_width(self, idx):
        if idx not in self.table_bbox:
            return None
        x1, y1, x2, y2 = self.table_bbox[idx]
        return abs(x2 - x1)

    def get_table_height(self, idx):
        if idx not in self.table_bbox:
            return None
        x1, y1, x2, y2 = self.table_bbox[idx]
        return abs(y2 - y1)

    def get_table_has_header(self, idx):
        return self.table_headers.get(idx, False)

    def get_table_header_confidence(self, idx):
        return self.table_header_scores.get(idx, 0.0)