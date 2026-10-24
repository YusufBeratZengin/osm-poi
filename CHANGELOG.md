# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-23

### Added

- `osm-poi fetch` CLI command with flexible area inputs: bounding box (`--bbox`), Nominatim administrative name resolution (`--area`), or GeoJSON polygon files (`--polygon`).
- High-level Python API (`fetch_pois`, `Poi`, `BBox`, `Polygon`, `Config`, `load_config`) exporting typed data records directly into Python code.
- Overpass QL query builder querying nodes, ways, and relations with center points.
- Normalized POI data model: name, category, address parts, phone, website, email, opening hours, and OSM metadata.
- Spatial deduplication engine: resolves identical OSM elements and merges proximate building polygon outlines with point nodes within configurable distance (default 75 m).
- Multi-format exporters: CSV (with spreadsheet formula injection protection), GeoJSON FeatureCollections, and JSONL.
- Built-in category presets (44 business and amenity types) with custom preset file extension support (`--presets-file`).
- Area size safety guards: default 0.25 sq deg safety ceiling and `--split N` bounding box tiling for polite querying.
- Privacy controls: `--no-contact` flag dropping phone, website, and email columns, plus `--fields` for column-level selection.
- Polite HTTP client: compulsory User-Agent identification, automatic request spacing, exponential backoff on 429/5xx, `Retry-After` header support, and disk caching (`osm-poi cache path|clear`).
- Automatic ODbL compliance: generates `<file>.ATTRIBUTION.txt` alongside exports and embeds attribution into GeoJSON metadata.
- Terminal demo image generator (`scripts/make-demo.py`) producing reproducible SVG previews (`docs/demo.svg`).
- Release and CI workflows on GitHub Actions across Ubuntu, Windows, and macOS matrices with Python 3.10 and 3.13.

### Fixed

- HTTP client resilience: automatic redirect handling (301, 302, 307, 308) preserving POST payloads, transparent gzip/deflate response decompression, and graceful Overpass timeout handling.
- Normalization edge cases: support for `addr:full` fallback, `name:tr` and `name:en` language fallbacks, scheme addition for bare website domains, and clean semicolon-separated multiple phone numbers.

[Unreleased]: https://github.com/YusufBeratZengin/osm-poi/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YusufBeratZengin/osm-poi/releases/tag/v0.1.0
