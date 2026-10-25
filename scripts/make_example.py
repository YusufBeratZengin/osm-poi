"""Generate example outputs (examples/sample.csv, examples/sample.geojson) from test fixtures."""

from __future__ import annotations

from pathlib import Path

from osm_poi.dedupe import dedupe
from osm_poi.normalize import normalize_elements
from osm_poi.presets import load_builtin_presets, select_presets
from osm_poi.writers import render

SAMPLE_FIXTURE_ELEMENTS = [
    {
        "type": "node",
        "id": 101,
        "lat": 40.9900000,
        "lon": 29.0300000,
        "tags": {
            "amenity": "cafe",
            "name": "Moda Kahvecisi",
            "addr:street": "Moda Caddesi",
            "addr:housenumber": "12",
            "addr:city": "Kadıköy",
            "addr:country": "TR",
            "phone": "+90 216 555 0101",
            "website": "https://example.org/moda",
            "opening_hours": "Mo-Su 08:00-22:00",
        },
    },
    {
        "type": "way",
        "id": 202,
        "center": {"lat": 40.9902000, "lon": 29.0301000},
        "tags": {"amenity": "cafe", "name": "moda kahvecisi"},
    },
    {
        "type": "node",
        "id": 303,
        "lat": 40.9850000,
        "lon": 29.0250000,
        "tags": {
            "amenity": "restaurant",
            "name": "Kadıköy Balıkçısı",
            "addr:street": "Balıkçı Sokak",
            "addr:housenumber": "5",
            "addr:city": "Kadıköy",
            "addr:country": "TR",
            "phone": "+90 216 555 0102",
            "website": "https://example.org/balik",
            "opening_hours": "Tu-Su 12:00-23:00",
        },
    },
    {
        "type": "node",
        "id": 404,
        "lat": 40.9820000,
        "lon": 29.0280000,
        "tags": {
            "amenity": "cafe",
            "name": "Bahariye Kitap Kafe",
            "addr:street": "Bahariye Caddesi",
            "addr:housenumber": "42",
            "addr:city": "Kadıköy",
            "addr:country": "TR",
            "phone": "+90 216 555 0103",
            "website": "https://example.org/kitap",
            "opening_hours": "Mo-Sa 09:00-21:00",
        },
    },
    {
        "type": "node",
        "id": 505,
        "lat": 40.9800000,
        "lon": 29.0200000,
        "tags": {"amenity": "cafe"},
    },
]


def generate_examples(output_dir: Path | None = None) -> tuple[str, str, str]:
    target_dir = output_dir or Path(__file__).resolve().parent.parent / "examples"
    target_dir.mkdir(parents=True, exist_ok=True)

    presets = select_presets(load_builtin_presets(), ["cafe", "restaurant"])
    pois = normalize_elements(SAMPLE_FIXTURE_ELEMENTS, presets, include_unnamed=False)
    unique = dedupe(pois, radius_m=75.0)

    csv_text = render(unique, "csv")
    geojson_text = render(unique, "geojson")
    jsonl_text = render(unique, "jsonl")

    (target_dir / "sample.csv").write_text(csv_text, encoding="utf-8", newline="")
    (target_dir / "sample.geojson").write_text(geojson_text, encoding="utf-8", newline="")
    (target_dir / "sample.jsonl").write_text(jsonl_text, encoding="utf-8", newline="")
    return csv_text, geojson_text, jsonl_text


if __name__ == "__main__":
    generate_examples()
