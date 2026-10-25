# osm-poi Examples

This directory provides sample data, input files, and runnable code examples demonstrating how to use `osm-poi` via both the command line interface (CLI) and the Python API.

## File Overview

| File | Type | Description |
|---|---|---|
| [`sample.csv`](sample.csv) | Output Sample | Normalized and deduplicated CSV export matching the Kadıköy worked example. Protected against spreadsheet formula injection. |
| [`sample.geojson`](sample.geojson) | Output Sample | GeoJSON `FeatureCollection` with embedded point geometries and full POI property records. |
| [`sample.jsonl`](sample.jsonl) | Output Sample | Line-delimited JSONL format containing one JSON POI object per line, ideal for streaming or big data pipelines. |
| [`custom_presets.json`](custom_presets.json) | Input Preset | Custom category configuration adding `bike_shop`, `bar`, and `organic_food` presets with Overpass tag mappings. |
| [`district_kadikoy.geojson`](district_kadikoy.geojson) | Input Geometry | GeoJSON `Polygon` covering the Moda neighborhood of Kadıköy, Istanbul, ready for `--polygon` queries. |
| [`python_api_quickstart.py`](python_api_quickstart.py) | Python Script | Executable Python script demonstrating bounding box math, preset resolution, Overpass QL generation, and normalization. |

---

## 1. Using Custom Presets

Pass `--presets-file` to list or fetch categories defined in an external JSON file:

```bash
# List all built-in and custom presets
osm-poi presets --presets-file examples/custom_presets.json

# Preview an Overpass query for bicycle shops
osm-poi fetch --bbox 40.95,29.00,41.03,29.11 --category bike_shop --presets-file examples/custom_presets.json --dry-run
```

---

## 2. Querying by GeoJSON Polygon

Use `--polygon` to query features inside arbitrary spatial boundaries rather than rectangular bounding boxes:

```bash
# Preview query for cafes inside the Kadikoy polygon boundary
osm-poi fetch --polygon examples/district_kadikoy.geojson -c cafe --dry-run

# Live fetch to CSV with privacy protection
osm-poi fetch --polygon examples/district_kadikoy.geojson -c cafe --no-contact -o cafes_moda.csv
```

---

## 3. Multi-Format Output Options

Output formats are automatically inferred from file extensions or can be forced with `--format`:

```bash
# CSV export (default protection against CSV formula injection)
osm-poi fetch --bbox 40.95,29.00,41.03,29.11 -c pharmacy -o pharmacies.csv

# GeoJSON FeatureCollection
osm-poi fetch --bbox 40.95,29.00,41.03,29.11 -c pharmacy -o pharmacies.geojson

# Line-delimited JSONL (streamable)
osm-poi fetch --bbox 40.95,29.00,41.03,29.11 -c pharmacy -f jsonl -o pharmacies.jsonl
```

---

## 4. Running the Python API Quickstart

Run the offline Python API example directly from the repository root:

```bash
python examples/python_api_quickstart.py
```
