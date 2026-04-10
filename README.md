# 🛣️ CityLaneCounter

Pipeline project to extract **lane counts for every street in a city** from OMS:

1. **OSM Pipeline** — Query OpenStreetMap via Overpass API, extract `lanes=*` tags

---

## Project Structure

```
citylanescounter/
├── osm_pipeline/
│   ├── query.py                # Overpass API query → GeoJSON
│   ├── parse.py                # Extract & clean lane attributes
│   ├── export.py               # Export to GeoPackage / CSV / GeoJSON
│
├── scripts/
│   ├── setup_env.sh            # Install all dependencies
│   └── run_all.sh              # End-to-end pipeline runner
├── requirements.txt
└── README.md                   # This file
```

---

## Quickstart

### 1. Setup environment

```bash
bash scripts/setup_env.sh
conda activate bogota-lanes
# or: pip install -r requirements.txt
```

### 2. Run OSM pipeline

```bash
# Query Overpass API and export lane data for Bogotá
python osm_pipeline/query.py --output data/osm/bogota_lanes.geojson
python osm_pipeline/parse.py --input data/osm/bogota_lanes.geojson --output data/osm/bogota_lanes_clean.gpkg
```