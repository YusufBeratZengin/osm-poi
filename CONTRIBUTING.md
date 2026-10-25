# Contributing to osm-poi

Thank you for your interest in contributing to `osm-poi`! We welcome bug reports, new category presets, documentation enhancements, and focused code improvements.

## Code of Conduct

All contributors and participants are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

## Development Setup

`osm-poi` requires Python 3.10+ and maintains zero runtime dependencies outside Python's standard library. Development tools are installed as optional extras:

```bash
git clone https://github.com/YusufBeratZengin/osm-poi.git
cd osm-poi
python -m pip install -e ".[dev]"
```

## Quality Standards

Before opening a pull request, ensure all tests, linters, and type checkers pass cleanly:

```bash
# 1. Run unit tests with branch coverage
python -m pytest -q --cov=osm_poi --cov-report=term-missing

# 2. Run Ruff linter
python -m ruff check .

# 3. Check code formatting
python -m ruff format --check .

# 4. Run Mypy strict type checker
python -m mypy src
```

All four checks are enforced by continuous integration across Linux, Windows, and macOS matrices on Python 3.10 and 3.13.

## Architectural Overview

`osm-poi` follows a linear, decoupled pipeline:

```
Inputs (CLI / API)
   │
   ├──> Areas (BBox / Polygon / OsmArea via Nominatim)
   ├──> Presets (Built-in JSON or custom JSON file)
   │
   └──> Query Builder (Builds deterministic Overpass QL)
           │
           └──> HTTP Client (User-Agent, rate limiting, retry backoff, disk cache)
                   │
                   └──> Normalize (Schema mapping, address parts, sanitization)
                           │
                           └──> Deduplicate (Proximity deduplication within 75 m)
                                   │
                                   └──> Writers (CSV safe from injection, GeoJSON, JSONL)
```

## Guidelines for Contributions

- **Zero runtime dependencies**: Keep production dependencies at zero. Python's standard library (`urllib`, `dataclasses`, `json`, `csv`, `math`, etc.) is sufficient.
- **Offline testing**: Unit tests must never contact real network endpoints. Use mocked HTTP fixtures or the local server in `tests/conftest.py`.
- **Category presets**: New built-in presets belong in `src/osm_poi/data/presets.json`. Use well-established OpenStreetMap tag keys verified on the [OSM Map Features Wiki](https://wiki.openstreetmap.org/wiki/Map_features).
- **Synchronized documentation**: When changing user-facing features or CLI options, keep `README.md` and `README.tr.md` in sync. Verify that examples remain golden using `python scripts/make_example.py` and `pytest tests/test_golden_examples.py`.
- **Conventional Commits**: Format commit messages according to [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- **Privacy and security**: Never commit real personal data, API keys, tokens, or private credentials.

## Pull Request Checklist

1. Fork the repository and create your branch from `main`.
2. Add or update tests covering your changes.
3. Update `CHANGELOG.md` under the `## [Unreleased]` section.
4. Verify all tests, linting, formatting, and typing checks pass locally.
5. Submit your pull request following the provided PR template.

## Reporting Bugs and Security Vulnerabilities

- **Bug reports**: Open an issue using the [Bug Report Template](https://github.com/YusufBeratZengin/osm-poi/issues/new?template=bug_report.yml).
- **Preset suggestions**: Propose new categories using the [Preset Request Template](https://github.com/YusufBeratZengin/osm-poi/issues/new?template=preset_request.yml).
- **Security vulnerabilities**: Do not open public issues. Follow [SECURITY.md](SECURITY.md) to disclose vulnerabilities privately via GitHub Security Advisories.
