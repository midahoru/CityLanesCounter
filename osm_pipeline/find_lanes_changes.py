"""
osm_pipeline/find_lanes_changes.py
---------------------
Use the information fetched from OMS to find the points in space
where the number of lanes changes for all the available streets.

It uses the information from settings.yaml to look for the input file.

Usage:
    python -m osm_pipeline.find_lanes_changes.py
"""

import json
import math

from unidecode import unidecode

from configs import get_settings
from configs.constants import TOLERANCE

# Getss input to frame the query
settings = get_settings()
CITY_NAME    = settings["city"]["name"]
CITY_COUNTRY = settings["city"]["country"]

INPUT_FILE  = f"./data/{unidecode(CITY_NAME).lower()}_{unidecode(CITY_COUNTRY).lower()}_lanes.geojson"
OUTPUT_FILE = f"./data/{unidecode(CITY_NAME).lower()}_{unidecode(CITY_COUNTRY).lower()}_lanes_changes.geojson"
OUTPUT_FILE_MISSING_LANES = f"./data/{unidecode(CITY_NAME).lower()}_{unidecode(CITY_COUNTRY).lower()}_missing_lanes.geojson"

# Loads json with lane counts per street segment
with open(INPUT_FILE, encoding="utf-8") as f:
    input_json = json.load(f)

# Groups by street name
streets = {}
for feat in input_json["features"]:
    name = feat["properties"].get("name")
    if name is None:
        continue
    streets.setdefault(name, []).append(feat)

# Euclidean distance (given the tolerance, it  is ok to assume a flat space)
def dist(a, b) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

# List to store points where changes are identified
change_points = []
# List for the segments with no lane info
missing_lanes_segments = []
no_lane_info = 0

# Iterates over all the segments related to the same street
for street_name, segments in streets.items():
    # Skeeps streets with just one segment
    if len(segments) < 2:
        continue

    # Collects all endpoints for this street
    # Each entry: (segment_index, coordinate, lane_count)
    endpoints = []
    for i, seg in enumerate(segments):
        coords = seg["geometry"]["coordinates"]
        lanes  = seg["properties"].get("lanes")
        if lanes is None or int(lanes) < 1:
            missing_lanes_segments.append(seg)
            continue
        endpoints.append((i, coords[0],  lanes))
        endpoints.append((i, coords[-1],  lanes))

    # To keep track of already considered points (to avoid duplicates)
    seen = set()
    # Compares every endpoint pair from DIFFERENT segments
    for idx_a, (id_a, coords_a, lanes_a) in enumerate(endpoints):

        for id_b, coords_b, lanes_b in endpoints[idx_a + 1:]:
            # Same segment, skip
            if id_a == id_b:
                continue
            
            # Not touching segments, skip
            if dist(coords_a, coords_b) > TOLERANCE:
                continue
            
            # No change in the number of lanes, skip
            if lanes_a == lanes_b:
                continue 

            # Point already considered for this street, skip
            # Use rounded coord as key
            key = (round(coords_a[0], 5), round(coords_a[1], 5))
            if key in seen:
                continue
            seen.add(key)

            # Include point with lane change info
            change_points.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": coords_a,   # use the first endpoint as the point
                },
                "properties": {
                    "street":        street_name,
                    "lanes_from":    lanes_a,
                    "lanes_to":      lanes_b,
                    "delta_lanes":   int(lanes_b) - int(lanes_a)
                },
            })

# Generates the outputs
output_lane_changes = {"type": "FeatureCollection", "features": change_points}
output_missing_lanes = {"type": "FeatureCollection", "features": missing_lanes_segments}

# Exports the outputs as a geojson
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output_lane_changes, f, ensure_ascii=False, indent=2)
with open(OUTPUT_FILE_MISSING_LANES, "w", encoding="utf-8") as f:
    json.dump(output_missing_lanes, f, ensure_ascii=False, indent=2)

print(f"Found {len(change_points)} lane-change points → {OUTPUT_FILE}")
print(f"No lane info for {len(missing_lanes_segments)} segments")