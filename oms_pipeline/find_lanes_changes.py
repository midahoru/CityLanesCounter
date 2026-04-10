import json
import math

# ── Config ────────────────────────────────────────────────────────────────────
INPUT_FILE  = "data/bogota_colombia_lanes.geojson"
OUTPUT_FILE = "data/lane_change_points.geojson"
TOLERANCE   = 3e-4   # ~30 meters in degrees — adjust if needed

# ── Load ──────────────────────────────────────────────────────────────────────
with open(INPUT_FILE, encoding="utf-8") as f:
    features = json.load(f)

# ── Group by street name ──────────────────────────────────────────────────────
streets = {}
for feat in features:
    name = feat["properties"].get("name")
    if name is None:
        continue
    streets.setdefault(name, []).append(feat)

# ── Find lane-change contact points ──────────────────────────────────────────
def dist(a, b) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

change_points = []

for street_name, segments in streets.items():
    if len(segments) < 2:
        continue

    # Collect all endpoints for this street
    # Each entry: (segment_index, role, coordinate, lane_count)
    endpoints = []
    for i, seg in enumerate(segments):
        coords = seg["geometry"]["coordinates"]
        lanes  = seg["properties"].get("lanes")
        endpoints.append((i, "start", coords[0],  lanes))
        endpoints.append((i, "end",   coords[-1],  lanes))

    # Compare every endpoint pair from DIFFERENT segments
    seen = set()  # avoid duplicate points

    for idx_a, (si, role_a, pt_a, lanes_a) in enumerate(endpoints):
        for si2, role_b, pt_b, lanes_b in endpoints[idx_a + 1:]:
            if si == si2:
                continue  # same segment, skip

            if dist(pt_a, pt_b) > TOLERANCE:
                continue  # not touching

            if lanes_a == lanes_b:
                continue  # touching but same lane count — not interesting

            # De-duplicate: use rounded coord as key
            key = (round(pt_a[0], 5), round(pt_a[1], 5))
            if key in seen:
                continue
            seen.add(key)

            change_points.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": pt_a,   # use the first endpoint as the point
                },
                "properties": {
                    "street":        street_name,
                    "lanes_from":    lanes_a,
                    "lanes_to":      lanes_b,
                    "delta_lanes":   int(lanes_b) - int(lanes_a),
                    "segment_a":     si,
                    "segment_b":     si2,
                    "role_a":        role_a,
                    "role_b":        role_b,
                },
            })

# ── Save ──────────────────────────────────────────────────────────────────────
output = {"type": "FeatureCollection", "features": change_points}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Found {len(change_points)} lane-change points → {OUTPUT_FILE}")
for pt in change_points:
    p = pt["properties"]
    print(f"  {p['street']}: {p['lanes_from']} → {p['lanes_to']} lanes  "
          f"at {pt['geometry']['coordinates']}")