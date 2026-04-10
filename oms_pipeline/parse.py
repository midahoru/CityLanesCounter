"""
osm_pipeline/parse.py
---------------------
Clean and enrich raw OSM GeoJSON.
- Standardize lane counts (handle bidirectional roads)
- Flag missing data
- Export to GeoPackage for use in QGIS / GeoPandas

Usage:
    python osm_pipeline/parse.py \
        --input data/bogota_lanes.geojson \
        --output data/bogota_lanes_clean.gpkg
"""

import argparse
from pathlib import Path
from unidecode import unidecode

import geopandas as gpd
import pandas as pd


# OSM highway types → rough road category
HIGHWAY_CATEGORIES = {
    "motorway": "highway",
    "motorway_link": "highway",
    "trunk": "arterial",
    "trunk_link": "arterial",
    "primary": "arterial",
    "primary_link": "arterial",
    "secondary": "collector",
    "secondary_link": "collector",
    "tertiary": "local",
    "tertiary_link": "local",
    "residential": "local",
    "living_street": "local",
    "unclassified": "local",
}

# Default lane assumptions when OSM tag is missing (used as fallback, flagged)
DEFAULT_LANES = {
    "highway": 4,
    "arterial": 3,
    "collector": 2,
    "local": 2,
}


def parse_int(value) -> int | None:
    """Safely parse an integer from an OSM tag value."""
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def infer_total_lanes(row: pd.Series) -> tuple[int | None, str]:
    """
    Determine the best lane count estimate for a road segment.

    Returns:
        (lane_count, source) where source explains where the value came from.
    """
    # Direct tag
    if (n := parse_int(row.get("lanes"))) is not None:
        return n, "osm:lanes"

    # Sum forward + backward
    fwd = parse_int(row.get("lanes_forward"))
    bwd = parse_int(row.get("lanes_backward"))
    if fwd is not None and bwd is not None:
        return fwd + bwd, "osm:lanes_forward+backward"
    if fwd is not None and row.get("oneway") in ("yes", "1", "true"):
        return fwd, "osm:lanes_forward (oneway)"
    if bwd is not None:
        return bwd, "osm:lanes_backward"

    # No tag — return None (will be flagged as missing)
    return None, "missing"


def clean(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Apply all cleaning and enrichment steps."""

    # Add road category
    gdf["road_category"] = gdf["highway"].map(HIGHWAY_CATEGORIES).fillna("other")

    # Infer lane counts
    results = gdf.apply(infer_total_lanes, axis=1, result_type="expand")
    gdf["lanes_count"] = results[0]
    gdf["lanes_source"] = results[1]

    # Flag missing lane data
    gdf["has_lane_data"] = gdf["lanes_count"].notna()
    gdf["lanes_missing"] = ~gdf["has_lane_data"]

    # Fallback estimate (flagged separately — do NOT use as ground truth)
    gdf["lanes_estimate"] = gdf.apply(
        lambda row: row["lanes_count"]
        if row["lanes_count"] is not None
        else DEFAULT_LANES.get(row["road_category"], 2),
        axis=1,
    )
    gdf["estimate_is_fallback"] = gdf["lanes_missing"]

    # Sanity checks
    gdf["lanes_count"] = gdf["lanes_count"].clip(lower=1, upper=20)
    gdf["lanes_estimate"] = gdf["lanes_estimate"].clip(lower=1, upper=20)

    # Oneway normalization
    gdf["is_oneway"] = gdf["oneway"].isin(["yes", "1", "true"])

    return gdf


def print_summary(gdf: gpd.GeoDataFrame):
    total = len(gdf)
    with_data = gdf["has_lane_data"].sum()
    print(f"\n{'='*50}")
    print(f"  Total road segments : {total:,}")
    print(f"  With lane data      : {with_data:,} ({100*with_data/total:.1f}%)")
    print(f"  Missing lane data   : {total-with_data:,} ({100*(total-with_data)/total:.1f}%)")
    print(f"\n  Lane source breakdown:")
    for src, count in gdf["lanes_source"].value_counts().items():
        print(f"    {src:<35} {count:>6,}")
    print(f"\n  Road categories:")
    for cat, count in gdf["road_category"].value_counts().items():
        print(f"    {cat:<20} {count:>6,} segments")
    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/bogota_colombia_lanes.geojson")
    parser.add_argument("--output", default="data/bogota_colombia_lanes_clean.gpkg")
    args = parser.parse_args()

    print(f"[parse] Loading {args.input}...")
    gdf = gpd.read_file(args.input)
    print(f"[parse] Loaded {len(gdf):,} features")

    # Set CRS (OSM uses WGS84)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    # Reproject to Colombia's local CRS for metric measurements
    gdf = gdf.to_crs("EPSG:3116")  # MAGNA-SIRGAS / Colombia Bogota zone

    gdf = clean(gdf)
    print_summary(gdf)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Drop raw _all_tags before saving (too large for GeoPackage column)
    if "_all_tags" in gdf.columns:
        gdf = gdf.drop(columns=["_all_tags"])

    gdf.to_file(output_path, driver="GPKG", layer="roads")
    print(f"[parse] Saved → {output_path}")

    # Also export CSV summary (without geometry)
    csv_path = output_path.with_suffix(".csv")
    gdf.drop(columns=["geometry"]).to_csv(csv_path, index=False)
    print(f"[parse] CSV summary → {csv_path}")


if __name__ == "__main__":
    main()
