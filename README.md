# 🛣️ CityLaneCounter

Query OpenStreetMap via Overpass API, extract `lanes=*` tags to get the **lane counts for every street in a city**

---

## Project Structure

```
citylanescounter/
├── configs/
│   ├── constants.py                  # Global variables that should not be changed
│   ├── settings.yamls                # Query information (geographical location, timeout)
│
├── osm_pipeline/
│   ├── query_lanes.py                # Overpass API query. Returns a GeoJSON
│   ├── qa_lanes_info.py              # Improve lane data quality (#TODO)
│   ├── find_lanes_changes.py         # Find the points where there the number of lanes changes
│
├── requirements.txt
└── README.md                         # This file
```

---

## Quickstart

### 1. Setup environment

```python
pip install -r requirements.txt
```

### 2. Run OSM pipeline

#### Query OSM

The yaml file has the information to frame the query. If the city, the country and the boundig box define
and empty zone (e.g. a city in South America and a country name in North America), the query might return nothing.

```bash
# Query Overpass API and export lane data for a given city. Defaults to Bogotá, Colombia
python -m osm_pipeline.querylanes
python -m osm_pipeline.query_lanes --bbox 4.64 -74.09 4.69 -74.06 # Barrios Unidos district
python -m osm_pipeline.query_lanes --bbox 4.46 -74.22 4.84 -73.99 # City of Bogotá
python -m osm_pipeline.query_lanes   --output path/for/the/results/name.gpkg
```

#### Find changes in lanes
```bash
# Use the data from OSM to find the points where the number of lanes change
python -m osm_pipeline.find_lanes_changes
```