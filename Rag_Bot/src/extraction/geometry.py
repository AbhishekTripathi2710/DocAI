"""
src/extraction/geometry.py
--------------------------
Geometric primitives and grouping logic for PDF layout analysis.
Ported from 'bbox-align' concepts for slope-aware text grouping.
"""

import math
from collections import defaultdict

class BBoxPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        
    def __add__(self, other):
        return BBoxPoint(self.x + other.x, self.y + other.y)
        
    def __sub__(self, other):
        return BBoxPoint(self.x - other.x, self.y - other.y)
        
    def __truediv__(self, scalar):
        return BBoxPoint(self.x / scalar, self.y / scalar)
        
    def distance_to_line(self, line):
        A, B, C = line.coeffs
        # distance = |Ax + By + C| / sqrt(A^2 + B^2)
        denom = math.sqrt(A**2 + B**2)
        if denom == 0: return 0
        return abs(A * self.x + B * self.y + C) / denom

class BBoxLine:
    def __init__(self, p, m):
        self.m = m  # slope
        self.c = p.y - (p.x * m)  # intercept
        
    @property
    def coeffs(self):
        """Returns (A, B, C) for Ax + By + C = 0 -> mx - y + c = 0"""
        return (self.m, -1, self.c)

class BBox:
    def __init__(self, word_dict):
        # Coordinates from pdfplumber word (x0, top, x1, bottom)
        self.p1 = BBoxPoint(word_dict["x0"], word_dict["top"])
        self.p2 = BBoxPoint(word_dict["x1"], word_dict["top"])
        self.p3 = BBoxPoint(word_dict["x1"], word_dict["bottom"])
        self.p4 = BBoxPoint(word_dict["x0"], word_dict["bottom"])
        
        # Precompute midpoint and average height
        self.midpoint = (self.p1 + self.p3) / 2
        self.height = abs(self.p1.y - self.p4.y)
        
        # Calculate approximate orientation (slope)
        dx = self.p2.x - self.p1.x
        dy = self.p2.y - self.p1.y
        self.slope = dy / dx if dx != 0 else 0
        
        self.text = word_dict.get("text", "")
        self.raw = word_dict

def is_inline(b1, b2, slope_threshold=3, y_ratio=0.5):
    """Checks if b2 is in-line with the flow of b1."""
    line = BBoxLine(b1.midpoint, b1.slope)
    dist = b2.midpoint.distance_to_line(line)
    
    # Slope difference check (in degrees)
    angle1 = math.degrees(math.atan(b1.slope))
    angle2 = math.degrees(math.atan(b2.slope))
    slope_diff = abs(angle1 - angle2)
    
    # Tolerance: distance should be within a fraction of height
    return dist <= b2.height * y_ratio and slope_diff < slope_threshold

def group_words_geometrically(words):
    """
    Groups a list of pdfplumber word dictionaries into lines using geometric slope-aware logic.
    Returns a list of rows, where each row is a list of word dictionaries sorted left-to-right.
    """
    if not words:
        return []
        
    # 1. Convert words to BBox objects
    bboxes = [BBox(w) for w in words]
    n = len(bboxes)
    
    # 2. Build Adjacency List (Graph)
    adj = defaultdict(list)
    for i in range(n):
        for j in range(i + 1, n):
            # Mutual check for better robustness
            if is_inline(bboxes[i], bboxes[j]) or is_inline(bboxes[j], bboxes[i]):
                adj[i].append(j)
                adj[j].append(i)
                
    # 3. Find Connected Components using DFS
    visited = set()
    rows_bboxes = []
    for i in range(n):
        if i not in visited:
            component = []
            stack = [i]
            while stack:
                curr = stack.pop()
                if curr not in visited:
                    visited.add(curr)
                    component.append(bboxes[curr])
                    stack.extend(adj[curr])
            
            # Sort words within the component by X position
            component.sort(key=lambda b: b.midpoint.x)
            rows_bboxes.append(component)
            
    # 4. Sort rows vertically (Top to Bottom)
    def get_vertical_score(row):
        """Combined score of average Y and flow intercept."""
        avg_y = sum(b.midpoint.y for b in row) / len(row)
        avg_slope = sum(b.slope for b in row) / len(row)
        avg_x = sum(b.midpoint.x for b in row) / len(row)
        intercept = avg_y - (avg_x * avg_slope)
        return (avg_y + intercept) / 2

    rows_bboxes.sort(key=get_vertical_score)
    
    # 5. Convert back to raw word dictionaries
    final_rows = []
    for row in rows_bboxes:
        final_rows.append([b.raw for b in row])
        
    return final_rows
