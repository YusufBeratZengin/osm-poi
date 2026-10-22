# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-22

### Added

- `osm-poi fetch` command with area input by bounding box, Nominatim area name or GeoJSON polygon.
- Built-in category presets in JSON, extendable with `--presets-file`.
- Overpass QL builder for nodes, ways and relations with centre points.
- Normalized POI fields, deduplication by OSM id and by name and proximity.
- CSV, GeoJSON and JSONL writers; CSV formula-injection protection.
- Polite HTTP client: required User-Agent, request spacing, retries with backoff on 429 and 5xx,
  `Retry-After` support.
- On-disk cache keyed by request hash, `osm-poi cache path|clear`.
- `--dry-run` to print the Overpass query.
- ODbL attribution file written next to each output.
- Configuration through JSON file, environment variables and flags.
