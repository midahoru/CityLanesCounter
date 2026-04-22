"""
osm_pipeline/query_lanes.py
---------------------
Query the Overpass API for all roads with lane data in a city or a bounding box.
Saves result as GeoJSON.
Receives as arguments:
    - output: the output path
    - city: the city to query, 
    - country: the country the city belongs to
    - bbox: bounding box of the area of interest
    - timeout: timeout for the query
If no arguments are provided, it gets the inputs defined in the configs/settings.yaml file.
A missmatch between the city name, the country and the bounding box can lead to an empty query.   

Usage:
    python -m osm_pipeline.query_lanes.py --city Bogota --country Colombia 
    python -m osm_pipeline.query_lanes.py --bbox 4.64 -74.09 4.69 -74.06
"""

import argparse
import json
import time
from pathlib import Path

import requests
from unidecode import unidecode

from configs import get_settings
from configs.constants import OVERPASS_URL

# Getss input to frame the query
settings = get_settings()
CITY_NAME    = settings["city"]["name"]
CITY_COUNTRY = settings["city"]["country"]
CITY_BBOX    = (
    settings["city"]["bbox"]["south"],
    settings["city"]["bbox"]["west"],
    settings["city"]["bbox"]["north"],
    settings["city"]["bbox"]["east"],
)
QUERY_TIME_OUT = settings["query"]["timeout"]
HEADERS = {
    "User-Agent": "CityLanesCounter/1.0 (public-street-network-research; https://github.com/midahoru/CityLanesCounter.git)",
    "Accept": "application/json",
}

def build_query(city: str | None = None, country: str | None = None,
    bbox: tuple[float, float, float, float] | None = None, time_out: int = 600) -> str:
    """
    Build an Overpass query based on available location inputs.
    Priority: bbox > city (+ optional country)
    """
    if bbox:
        south, west, north, east = bbox
        spatial_filter = f"({south},{west},{north},{east})"
        area_setup = ""
    elif city:
        area_name = f"{city},{country}" if country else city
        area_setup = f'{{{{geocodeArea:{area_name}}}}}->.searchArea;\n'
        spatial_filter = "(area.searchArea)"
    else:
        raise ValueError("Must provide either bbox or city.")

    return f"""
    [out:json][timeout:{time_out}];
    {area_setup}(
        way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential)$"]{spatial_filter};
    );
    out body geom;
    """


def run_query(query: str, time_out: int = 600, header: str=None, retries: int = 3) -> dict:
    """POST query to Overpass API with retry logic."""
    for attempt in range(retries):
        try:
            print(f"[query] Sending Overpass query (attempt {attempt + 1}/{retries})...")
            response = requests.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=time_out,
                headers=header if header else None
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


def main():
    # Argument parser
    parser = argparse.ArgumentParser(description=f"Query OSM lane data for {CITY_NAME}, {CITY_COUNTRY}")
    parser.add_argument("--output", 
                        default=f"./data/{unidecode(CITY_NAME).lower()}_{unidecode(CITY_COUNTRY).lower()}_lanes.geojson",
                        help="Output file path for GeoJSON")
    parser.add_argument("--city",
                        type=str,
                        default=CITY_NAME,
                        help="City name for query")
    parser.add_argument("--country",
                        type=str,
                        default=CITY_COUNTRY,
                        help="Country name for query")
    parser.add_argument("--bbox",
                        nargs=4,
                        type=float,
                        metavar=("SOUTH", "WEST", "NORTH", "EAST"),
                        default=list(CITY_BBOX),
                        help="Bounding box to query")
    parser.add_argument("--timeout",
                        type=int,
                        default=QUERY_TIME_OUT,
                        help="Overpass query timeout in seconds")
    args = parser.parse_args()

    # Create dir if it doesn't exist
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Normalize city and country names to ASCII for consistent querying
    city = unidecode(args.city) if args.city else None
    country = unidecode(args.country) if args.country else None

    # Bounding box for the query
    bbox = tuple(args.bbox) if args.bbox else None

    # Timeout
    tout = args.timeout

    # Creates the query
    query = build_query(city, country, bbox, tout)
    print(f"[query] City: {city}, Country: {country}, Bounding box: {bbox}")

    # Runs the query
    data = run_query(query, tout, HEADERS)
    total = len([e for e in data["elements"] if e["type"] == "way"])
    print(f"[query] Retrieved {total} road segments from OSM")

    # Create the result as geojson
    geojson = overpass_to_geojson(data)
    with_lanes = sum(1 for f in geojson["features"] if f["properties"]["lanes"])
    print(f"[query] {with_lanes}/{total} segments have 'lanes' tag "
          f"({100 * with_lanes / total:.1f}%)")

    # Saves geojson
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    print(f"[query] Saved → {output_path}")


if __name__ == "__main__":
    main()