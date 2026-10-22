# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Release workflow (`.github/workflows/release.yml`) for publishing to PyPI with trusted publishing (OIDC) and GitHub releases on `v*` tags.
- High-level Python API: `fetch_pois` exporting normalized `Poi` records, with public exports in `osm_poi.__all__`.
- Search area safety guard: refuses queries exceeding a configurable limit (default 0.25 sq deg) without `--allow-large`, with `--split N` to tile bounding boxes into $N \times N$ sequential sub-queries.
- Privacy controls: `--no-contact` flag to omit phone, website, and email columns from export, and `--fields` to select specific columns.
- Category presets useful for local agencies: `estate_agent` alias, `stationery`, `notary`, `car_wash`, `butcher`, `dry_cleaning`, and `driving_school`.
- Preset schema and uniqueness test validating preset JSON specifications.
- Community guidelines: Contributor Covenant 2.1 `CODE_OF_CONDUCT.md`, GitHub issue templates (`bug_report.md`, `feature_request.md`, `preset_request.md`), and pull request template.
- Example generator `scripts/make_example.py` creating `examples/sample.csv` and `examples/sample.geojson`, verified by golden tests.
- Worked Kadıköy example and Responsible Use (KVKK/GDPR and commercial electronic message compliance) documentation in English and Turkish READMEs.

### Changed

- CI workflow expanded to include Python 3.11 and 3.12 on Ubuntu, distribution package building, twine verification, and an isolated venv smoke test.
- Packaging metadata: added `Source` repository URL, SPDX license expression (`license = "MIT"` and `license-files = ["LICENSE"]`), `Operating System :: OS Independent` and Python 3.14 classifiers, expanded keywords, and added `build` and `twine` to `dev` dependencies.

### Fixed

- HTTP client resilience: automatic redirect following (301, 302, 307, 308) preserving POST bodies, transparent gzip/deflate response decompression, and graceful handling of Overpass runtime errors and timeouts.
- Normalization edge cases: support for `addr:full` fallback, `name:tr` and `name:en` language fallbacks, scheme addition for bare website domains, and clean semicolon-separated multiple phone numbers.

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

[Unreleased]: https://github.com/YusufBeratZengin/osm-poi/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YusufBeratZengin/osm-poi/releases/tag/v0.1.0
