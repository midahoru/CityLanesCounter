# 🛣️ CityLanesCounter

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
    ├── data/                         # Stores the resulting data
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

The yaml file has the information to frame the query. The boundingbox is used if available, otherwise
it will use the city, and if available, the country. If none if provided, an error is raised.

```bash
# Query Overpass API and export lane data for a given city.
python -m osm_pipeline.query_lanes # Gets the bbox or the city (and possibly the country) from the yaml file. 
python -m osm_pipeline.query_lanes --bbox 4.64 -74.09 4.69 -74.06 # Barrios Unidos district in Bogotá
python -m osm_pipeline.query_lanes --bbox 4.46 -74.22 4.84 -73.99 # City of Bogotá
python -m osm_pipeline.query_lanes --output path/for/the/results/name.gpkg
```

#### Find changes in lanes
```bash
# Use the data from OSM to find the points where the number of lanes change
python -m osm_pipeline.find_lanes_changes
```