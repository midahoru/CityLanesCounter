"""
osm_pipeline/export.py
-----------------------
Export cleaned OSM lane data to multiple formats for use in QGIS,
notebooks, or other tools.

Outputs:
  - GeoJSON  (web-friendly)
  - GeoPackage (QGIS-native, single file)
  - CSV      (tabular, no geometry)
  - Shapefile (legacy GIS)
  - GeoParquet (fast analytics, optional)

Usage:
    python osm_pipeline/export.py \
        --input data/osm/bogota_lanes_clean.gpkg \
        --output-dir data/osm/exports/ \
        --formats geojson csv gpkg
"""

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd


SUPPORTED_FORMATS = ["geojson", "gpkg", "csv", "shp", "parquet"]


def export_geojson(gdf: gpd.GeoDataFrame, path: Path):
    gdf_wgs = gdf.to_crs("EPSG:4326")
    gdf_wgs.to_file(path, driver="GeoJSON")
    print(f"  ✓ GeoJSON      → {path}  ({path.stat().st_size // 1024:,} KB)")


def export_gpkg(gdf: gpd.GeoDataFrame, path: Path):
    gdf.to_file(path, driver="GPKG", layer="roads")
    print(f"  ✓ GeoPackage   → {path}  ({path.stat().st_size // 1024:,} KB)")


def export_csv(gdf: gpd.GeoDataFrame, path: Path):
    """Export without geometry, adding centroid lat/lon columns."""
    df = gdf.copy()
    centroids = gdf.to_crs("EPSG:4326").geometry.centroid
    df["centroid_lon"] = centroids.x
    df["centroid_lat"] = centroids.y
    df = df.drop(columns=["geometry"])
    df.to_csv(path, index=False)
    print(f"  ✓ CSV          → {path}  ({path.stat().st_size // 1024:,} KB)")


def export_shapefile(gdf: gpd.GeoDataFrame, path: Path):
    path.mkdir(parents=True, exist_ok=True)
    shp_path = path / "bogota_lanes.shp"
    # Shapefile has 10-char column name limit
    gdf_shp = gdf.rename(columns={
        "lanes_count": "lanes_cnt",
        "lanes_source": "lanes_src",
        "lanes_estimate": "lanes_est",
        "lanes_missing": "lanes_mis",
        "has_lane_data": "has_lanes",
        "estimate_is_fallback": "est_fallbk",
        "road_category": "road_cat",
        "lanes_forward": "lanes_fwd",
        "lanes_backward": "lanes_bwd",
    })
    gdf_shp.to_file(shp_path, driver="ESRI Shapefile")
    print(f"  ✓ Shapefile    → {shp_path}")


def export_parquet(gdf: gpd.GeoDataFrame, path: Path):
    try:
        gdf.to_parquet(path)
        print(f"  ✓ GeoParquet   → {path}  ({path.stat().st_size // 1024:,} KB)")
    except Exception as e:
        print(f"  ⚠ GeoParquet failed: {e}  (pip install pyarrow)")


def print_summary(gdf: gpd.GeoDataFrame):
    """Print a compact summary of the dataset being exported."""
    total = len(gdf)
    with_lanes = gdf["lanes_count"].notna().sum()
    print(f"\n  Dataset: {total:,} road segments")
    print(f"  CRS: {gdf.crs}")
    print(f"  OSM lane data: {with_lanes:,} ({100*with_lanes/total:.1f}%) of segments")
    print(f"  Columns: {', '.join(gdf.columns.tolist())}")
    if "road_category" in gdf.columns:
        print(f"  Road categories: {', '.join(gdf['road_category'].value_counts().index[:5])}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Export OSM lane data to multiple formats")
    parser.add_argument("--input", default="data/osm/bogota_lanes_clean.gpkg")
    parser.add_argument("--output-dir", default="data/osm/exports/")
    parser.add_argument("--formats", nargs="+", default=["geojson", "csv", "gpkg"],
                        choices=SUPPORTED_FORMATS,
                        help="Which formats to export")
    args = parser.parse_args()

    print(f"[export] Loading {args.input}...")
    gdf = gpd.read_file(args.input)
    print_summary(gdf)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[export] Exporting to: {output_dir}")

    for fmt in args.formats:
        if fmt == "geojson":
            export_geojson(gdf, output_dir / "bogota_lanes.geojson")
        elif fmt == "gpkg":
            export_gpkg(gdf, output_dir / "bogota_lanes.gpkg")
        elif fmt == "csv":
            export_csv(gdf, output_dir / "bogota_lanes.csv")
        elif fmt == "shp":
            export_shapefile(gdf, output_dir / "shapefile/")
        elif fmt == "parquet":
            export_parquet(gdf, output_dir / "bogota_lanes.parquet")

    print(f"\n[export] Done. All files in {output_dir}")
    print(f"[export] Tip: Load bogota_lanes.gpkg in QGIS → style by 'lanes_count' column")


if __name__ == "__main__":
    main()
