"""
osm_pipeline/query_lines.py
---------------------
Query the Overpass API for all roads with lane data in a city or a bounding box.
Saves result as GeoJSON.
If no arguments are provided, defaults to Bogotá's bounding box.

Usage:
    python osm_pipeline/query_lines.py --city Bogotá --country Colombia 
    python osm_pipeline/query_lines.py --bbox 40.4774,-74.2591,40.9176,-73.7004
"""

import argparse
import json
import time
from pathlib import Path
from unidecode import unidecode

import requests

def build_query(city: str, country: str, bbox: tuple[float, float, float, float], time_out: int=600) -> str:
    """Insert city,country and bounding box into Overpass query template."""
    south, west, north, east = bbox
    return f"""
            [out:json][timeout:{time_out}];
            (
                // Query all highways within {city},{country}
                way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential)$"]
                ({south},{west},{north},{east});
            );
            out body geom;
            """


def run_query(query: str, time_out: int = 600, retries: int = 3) -> dict:
    """POST query to Overpass API with retry logic."""
    for attempt in range(retries):
        try:
            print(f"[query] Sending Overpass query (attempt {attempt + 1}/{retries})...")
            response = requests.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=time_out,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print(f"[query] Timeout — retrying in 10s...")
            time.sleep(10)
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                print(f"[query] Bad request — check your query syntax.")
                raise e
            elif response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 60))
                print(f"[query] Rate limited — waiting {wait}s...")
                time.sleep(wait)
            else:
                raise e

    raise RuntimeError("Overpass query failed after all retries.")


def overpass_to_geojson(data: dict) -> dict:
    """
    Convert Overpass JSON response to GeoJSON FeatureCollection.
    Each OSM way becomes a LineString Feature with all tags as properties.
    """
    features = []

    for element in data.get("elements", []):
        # Security check
        if element["type"] != "way":
            continue

        # Build geometry from node coordinates
        coords = [
            [node["lon"], node["lat"]]
            for node in element.get("geometry", [])
        ]

        # Skip features without valid geometry (a node or an element with missing geometry)
        if len(coords) < 2:
            continue

        tags = element.get("tags", {})

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
            "properties": {
                "osm_id": element["id"],
                "highway": tags.get("highway"),
                "name": tags.get("name"),
                "name_es": tags.get("name:es"),
                # Lane-related tags
                "lanes": tags.get("lanes"),
                "lanes_forward": tags.get("lanes:forward"),
                "lanes_backward": tags.get("lanes:backward"),
                "turn_lanes": tags.get("turn:lanes"),
                # Road characteristics
                "oneway": tags.get("oneway"),
                "maxspeed": tags.get("maxspeed"),
                "surface": tags.get("surface"),
                "width": tags.get("width"),
                # Raw tags for reference
                "_all_tags": json.dumps(tags, ensure_ascii=False),
            },
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    return geojson

# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Build query
# City's bounding box (extreme points defining a circumscribed rectangle): 
# south, west, north, east
# CITY_BBOX = (4.46, -74.22, 4.84, -73.99) # Bogotá's bounding box
CITY_BBOX = (4.64, -74.09, 4.69, -74.06) # Test with Barrios Unidos district
CITY_NAME = "Bogotá"
CITY_COUNTRY = "Colombia"

def main():
    # TODO: extend to other cities or bboxes
    parser = argparse.ArgumentParser(description="Query OSM lane data for Bogotá")
    parser.add_argument("--output", default=f"./data/{unidecode(CITY_NAME).lower()}_{unidecode(CITY_COUNTRY).lower()}_lanes.geojson")
    parser.add_argument("--city", default=CITY_NAME, help="City name for query")
    parser.add_argument("--country", default=CITY_COUNTRY, help="Country name for query")
    parser.add_argument("--bbox", nargs=4, type=float,
                        metavar=("SOUTH", "WEST", "NORTH", "EAST"),
                        default=list(CITY_BBOX),
                        help="Bounding box to query")
    parser.add_argument("--timeout", type=int, default=600, help="Overpass query timeout in seconds")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    city = unidecode(args.city)
    country = unidecode(args.country)

    bbox = tuple(args.bbox)
    query = build_query(city, country, bbox)

    print(f"[query] City: {city}, Country: {country}, Bounding box: {bbox}")
    data = run_query(query)

    total = len([e for e in data["elements"] if e["type"] == "way"])
    print(f"[query] Retrieved {total} road segments from OSM")

    geojson = overpass_to_geojson(data)
    with_lanes = sum(1 for f in geojson["features"] if f["properties"]["lanes"])
    print(f"[query] {with_lanes}/{total} segments have 'lanes' tag "
          f"({100 * with_lanes / total:.1f}%)")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"[query] Saved → {output_path}")


if __name__ == "__main__":
    main()
