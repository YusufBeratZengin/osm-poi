"""Quickstart demonstration of using osm-poi as a Python library.

This example runs offline without requiring network access, demonstrating:
1. Spatial boundary primitives (BBox, Polygon).
2. Category preset selection and custom presets.
3. Overpass QL query generation.
4. Normalizing raw OSM fixtures and deduplicating nearby elements.
5. Exporting records to CSV, GeoJSON, and JSONL formats.
6. The high-level fetch_pois() invocation pattern.
"""

from __future__ import annotations

from pathlib import Path

from osm_poi.areas import BBox, load_polygon_file
from osm_poi.dedupe import dedupe
from osm_poi.normalize import normalize_elements
from osm_poi.presets import load_presets, select_presets
from osm_poi.query import build_query
from osm_poi.writers import render


def main() -> None:
    print("--- 1. Bounding Box & Polygon ---")
    bbox = BBox(south=40.95, west=29.00, north=41.03, east=29.11)
    print(f"Bounding box area: {bbox.area_sq_degrees():.4f} sq degrees")

    polygon_file = Path(__file__).parent / "district_kadikoy.geojson"
    if polygon_file.exists():
        polygons = load_polygon_file(polygon_file)
        print(f"Loaded {len(polygons)} polygon ring(s) from {polygon_file.name}")
        print(f"Polygon ring area: {polygons[0].area_sq_degrees():.6f} sq degrees")

    print("\n--- 2. Category Presets ---")
    custom_presets_file = Path(__file__).parent / "custom_presets.json"
    all_presets = load_presets(custom_presets_file if custom_presets_file.exists() else None)
    selected = select_presets(all_presets, ["cafe", "restaurant", "bike_shop"])
    for p in selected:
        print(f" - {p.name:<12} ({p.label})")

    print("\n--- 3. Overpass QL Generation (Offline) ---")
    query = build_query([bbox], selected, timeout=60)
    print(query.strip())

    print("\n--- 4. Normalization, Deduplication & Export ---")
    raw_osm_elements = [
        {
            "type": "node",
            "id": 101,
            "lat": 40.9900,
            "lon": 29.0300,
            "tags": {
                "amenity": "cafe",
                "name": "Moda Kahvecisi",
                "addr:street": "Moda Caddesi",
                "addr:housenumber": "12",
                "addr:city": "Kadıköy",
                "phone": "+90 216 555 0101",
                "website": "https://example.org/moda",
                "opening_hours": "Mo-Su 08:00-22:00",
            },
        },
        {
            "type": "way",
            "id": 202,
            "center": {"lat": 40.9902, "lon": 29.0301},
            "tags": {"amenity": "cafe", "name": "moda kahvecisi"},
        },
    ]

    normalized = normalize_elements(raw_osm_elements, selected, include_unnamed=False)
    deduped = dedupe(normalized, radius_m=75.0)
    print(
        f"Raw elements: {len(raw_osm_elements)} -> "
        f"Normalized: {len(normalized)} -> Deduplicated: {len(deduped)}"
    )

    csv_excerpt = render(deduped, "csv")
    print("CSV Output:")
    print(csv_excerpt.strip())

    print("\n--- 5. Network fetch_pois() Usage Pattern ---")
    print(
        """To fetch live data from OpenStreetMap, provide a valid User-Agent:

    from osm_poi import fetch_pois

    pois = fetch_pois(
        bbox="40.95,29.00,41.03,29.11",
        categories=["cafe", "restaurant"],
        user_agent="my-application/1.0 (contact@example.org)",
    )
    for poi in pois:
        print(poi.name, poi.category, poi.phone)
"""
    )


if __name__ == "__main__":
    main()
