# osm-poi

[![CI](https://github.com/YusufBeratZengin/osm-poi/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/osm-poi/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/osm-poi.svg)](https://pypi.org/project/osm-poi/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Export points of interest (businesses, amenities, shops) from OpenStreetMap to CSV, GeoJSON or JSONL with category presets, polite rate-limiting, and automatic deduplication.

<p align="center">
  <img src="docs/demo.svg" alt="osm-poi terminal demo" width="820">
</p>

## Why osm-poi?

- **Zero paid API keys or vendor lock-in**: No costly Google Places or Mapbox bills. Queries OpenStreetMap's Overpass API and Nominatim directly and legally with zero runtime dependencies beyond Python's standard library.
- **Production-grade hygiene and deduplication**: Queries nodes, ways, and relations; cleans CSV formula-injection risks; standardizes phone and website formats; and intelligently merges building outline polygons with point nodes within 75 meters.
- **Polite and compliant by design**: Protects public servers with request spacing, exponential backoff, area safety limits (`--max-area`), and bounding box tiling (`--split`). Generates ODbL attributions automatically and includes privacy flags (`--no-contact`) for GDPR/KVKK compliance.

## Features

- **Flexible area inputs**: Bounding box (`--bbox`), administrative area name resolved via Nominatim (`--area`), or GeoJSON polygon files (`--polygon`). Multiple areas can be queried in a single run.
- **Rich category presets**: Over 40 built-in presets (`cafe`, `restaurant`, `pharmacy`, `dentist`, `real_estate_agent`, `estate_agent`, `hairdresser`, `hotel`, `stationery`, `notary`, `car_repair`, `supermarket`, etc.) defined in plain JSON.
- **Full geometry support**: Queries nodes, ways, and relations; ways and relations calculate their center points.
- **Normalized output schema**: `osm_type, osm_id, osm_url, name, category, lat, lon, street, housenumber, postcode, city, country, phone, website, email, opening_hours`.
- **Proximity deduplication**: Merges duplicate records sharing the same name and category within 75 meters (configurable via `--dedupe-radius`).
- **Server safety guards**: Rejects queries exceeding 0.25 sq degrees by default unless `--allow-large` is supplied, with `--split N` to tile large areas into polite sub-queries.
- **Privacy controls**: `--no-contact` strips phone, website, and email columns; `--fields` allows picking exact columns.
- **Multi-format output**: Clean CSV (protected against spreadsheet formula injection), GeoJSON FeatureCollections, or line-delimited JSONL.
- **Polite networking**: Enforced User-Agent identification, automatic pacing between calls, exponential retry backoff on 429/5xx, and local disk caching.
- **Dry-run inspection**: `--dry-run` outputs generated Overpass QL without querying the server.
- **Automated ODbL attribution**: Creates an attribution file next to each output file.

## Quick start

### Installation

```bash
pip install osm-poi
```

Python 3.10 or newer is required.

### Identification

Overpass and Nominatim require you to identify your application. Set a `User-Agent` with contact information:

```bash
# Linux / macOS
export OSM_POI_USER_AGENT="my-project/1.0 (contact@example.org)"

# PowerShell
$env:OSM_POI_USER_AGENT = "my-project/1.0 (contact@example.org)"
```

### Basic Commands

```bash
# Fetch cafes and restaurants in Kadikoy to CSV
osm-poi fetch --area "Kadikoy, Istanbul" --category cafe,restaurant -o out.csv

# Fetch pharmacies by bounding box to GeoJSON
osm-poi fetch --bbox 40.95,29.00,41.03,29.11 -c pharmacy -o pharmacies.geojson

# Fetch dentists inside a polygon to JSONL
osm-poi fetch --polygon district.geojson -c dentist -f jsonl -o dentists.jsonl

# Preview the generated Overpass query without network calls
osm-poi fetch --bbox 40.95,29.00,41.03,29.11 -c cafe --dry-run

# List all available presets
osm-poi presets
```

`--bbox` follows the standard Overpass coordinate order: `south,west,north,east`. The output format is automatically inferred from the file extension (`.csv`, `.geojson`/`.json`, `.jsonl`) or overridden with `--format`. When using `-o -` (the default), output streams to standard output.

### Output Columns

`osm_type, osm_id, osm_url, name, category, lat, lon, street, housenumber, postcode, city, country, phone, website, email, opening_hours`

Features without a name are skipped unless `--include-unnamed` is supplied. Missing attributes are represented by empty strings.

## Usage examples

### Worked Example: Kadıköy

In this Kadıköy worked example, querying cafes and restaurants returns 5 raw elements from OpenStreetMap: a node and a way outline for "Moda Kahvecisi" located 25 metres apart, a seafood restaurant ("Kadıköy Balıkçısı"), a book cafe ("Bahariye Kitap Kafe"), and an unnamed cafe node.

1. **Unnamed filtering**: Features without a name are skipped by default, dropping the unnamed node.
2. **Deduplication**: Deduplication identifies that the building way and the node share the same normalized name ("moda kahvecisi") within 75 metres. The pass merges them into a single record, retaining the node because it contains richer contact details (street address, phone number, website, and opening hours).
3. **Clean output**: The final result yields exactly 3 deduplicated business records.

### CSV Output Excerpt

```csv
osm_type,osm_id,osm_url,name,category,lat,lon,street,housenumber,postcode,city,country,phone,website,email,opening_hours
node,101,https://www.openstreetmap.org/node/101,Moda Kahvecisi,cafe,40.99,29.03,Moda Caddesi,12,,Kadıköy,TR,+90 216 555 0101,https://example.org/moda,,Mo-Su 08:00-22:00
node,303,https://www.openstreetmap.org/node/303,Kadıköy Balıkçısı,restaurant,40.985,29.025,Balıkçı Sokak,5,,Kadıköy,TR,+90 216 555 0102,https://example.org/balik,,Tu-Su 12:00-23:00
node,404,https://www.openstreetmap.org/node/404,Bahariye Kitap Kafe,cafe,40.982,29.028,Bahariye Caddesi,42,,Kadıköy,TR,+90 216 555 0103,https://example.org/kitap,,Mo-Sa 09:00-21:00
```

### GeoJSON Feature Excerpt

```json
{
  "type": "Feature",
  "id": "node/101",
  "geometry": {
    "type": "Point",
    "coordinates": [
      29.03,
      40.99
    ]
  },
  "properties": {
    "osm_type": "node",
    "osm_id": 101,
    "osm_url": "https://www.openstreetmap.org/node/101",
    "name": "Moda Kahvecisi",
    "category": "cafe",
    "street": "Moda Caddesi",
    "housenumber": "12",
    "postcode": "",
    "city": "Kadıköy",
    "country": "TR",
    "phone": "+90 216 555 0101",
    "website": "https://example.org/moda",
    "email": "",
    "opening_hours": "Mo-Su 08:00-22:00"
  }
}
```

### Python API

You can use `osm-poi` directly as a Python library:

```python
from osm_poi import Poi, fetch_pois

pois = fetch_pois(
    bbox="40.95,29.00,41.03,29.11",
    categories=["cafe", "restaurant"],
    user_agent="my-app/1.0 (contact@example.org)",
)

for poi in pois:
    print(f"{poi.name} ({poi.category}) - {poi.lat}, {poi.lon} - {poi.phone or 'no phone'}")
```

Public classes and functions exported in `__all__`:
- `fetch_pois`: Fetch, normalize, and deduplicate POIs in a single call.
- `Poi`: Strongly-typed dataclass representing normalized POI records.
- `BBox`, `Polygon`: Spatial boundary primitives.
- `Config`, `load_config`: Configuration management.

## Presets

List all presets with `osm-poi presets`. To define custom presets or override built-in ones, pass `--presets-file my_presets.json`:

```json
{
  "bike_shop": {
    "label": "Bicycle shops",
    "tags": [{"shop": "bicycle"}]
  },
  "bar": {
    "label": "Bars and pubs",
    "tags": [{"amenity": ["bar", "pub", "biergarten"]}]
  }
}
```

`tags` is a list of tag sets. A feature matches a preset if it satisfies any tag set; within a tag set, all key-value constraints must match. Values can be exact strings, lists of alternatives, or `"*"` to test key existence.

## Configuration

Precedence (lowest to highest): defaults, JSON config file, environment variables, command-line flags.

| Setting | Environment variable | Flag | Default |
|---|---|---|---|
| `user_agent` | `OSM_POI_USER_AGENT` | `--user-agent` | none (required) |
| `overpass_url` | `OSM_POI_OVERPASS_URL` | `--overpass-url` | `https://overpass-api.de/api/interpreter` |
| `nominatim_url` | `OSM_POI_NOMINATIM_URL` | `--nominatim-url` | `https://nominatim.openstreetmap.org` |
| `timeout` | `OSM_POI_TIMEOUT` | `--timeout` | 90 seconds |
| `retries` | `OSM_POI_RETRIES` | `--retries` | 3 |
| `backoff` | `OSM_POI_BACKOFF` | | 2 seconds, doubled per attempt |
| `overpass_interval` | `OSM_POI_OVERPASS_INTERVAL` | | 1 second between requests |
| `nominatim_interval` | `OSM_POI_NOMINATIM_INTERVAL` | | 1 second between requests |
| `cache_dir` | `OSM_POI_CACHE_DIR` | `--cache-dir` | user cache directory |
| `cache_ttl_hours` | `OSM_POI_CACHE_TTL_HOURS` | `--cache-ttl-hours` | 168 |
| `use_cache` | `OSM_POI_USE_CACHE` | `--no-cache` | true |
| `max_area` | `OSM_POI_MAX_AREA` | `--max-area` | 0.25 square degrees |

### CLI Options

- `--no-contact`: Drop phone, website, and email columns from exported data.
- `--fields LIST`: Comma-separated column list to export (e.g. `--fields name,category,lat,lon`).
- `--allow-large`: Bypass the area size safety limit.
- `--split N`: Tile a bounding box into $N \times N$ sequential sub-queries with polite pacing.

Config files are resolved in order: `--config`, `OSM_POI_CONFIG`, or `~/.config/osm-poi/config.json` (`%APPDATA%\osm-poi\config.json` on Windows).
Inspect or purge cache entries with `osm-poi cache path` and `osm-poi cache clear`.

## Responsible use

OpenStreetMap data is entered and maintained by community volunteers. While business entries often contain publicly displayed contact tags, please keep the following in mind:

- **Privacy flags**: Pass `--no-contact` to omit `phone`, `website`, and `email` columns entirely, or use `--fields name,category,lat,lon` to select specific columns.
- **Data protection (KVKK / GDPR)**: Contact information associated with sole proprietors, freelancers, or individual professionals may constitute personal data under the Turkish Personal Data Protection Law (KVKK No. 6698), the European General Data Protection Regulation (GDPR), and similar international frameworks.
- **Anti-spam and marketing regulations**: Unsolicited commercial communications (cold email, automated calling, or commercial SMS) are strictly regulated by law (such as the Turkish Law on the Regulation of Electronic Commerce No. 6563 and the Commercial Electronic Message Management System / İYS).
- **Disclaimer**: This documentation does not constitute legal advice. You are responsible for evaluating the legal compliance of your own data collection and communication workflows.

## Usage policies

- [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/): At most one request per second, a valid User-Agent, cached results, and no bulk geocoding. osm-poi sends one lookup per `--area` and caches it. Do not point it at the public instance for large batch jobs.
- [Overpass API policy](https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances): Public servers are shared community infrastructure. Keep search areas reasonable, and use `--overpass-url` to target your own instance for heavy usage.

## FAQ & Limitations

### What is the maximum search area I can query?
By default, osm-poi enforces a safety limit of 0.25 square degrees (roughly $50 \times 50\text{ km}$ at mid-latitudes) to prevent overburdening public Overpass servers. If you need larger areas, pass `--split 2` (or higher) to tile the bounding box into smaller polite sub-queries, or pass `--allow-large` if targeting a private Overpass mirror.

### Are phone numbers and opening hours guaranteed to exist?
No. OpenStreetMap data is crowd-sourced. While many business records include full contact information and opening hours, coverage varies by geographic region and mapping activity. Missing attributes are represented by empty strings.

### How does the ODbL license affect my use of exported data?
Data from OpenStreetMap is licensed under the Open Database License (ODbL) 1.0. You must credit `(c) OpenStreetMap contributors`. If you publicly distribute an altered derivative database, that database must also be shared under ODbL. Internal analyses and proprietary applications that merely query or display the data generally do not require open-sourcing internal code. See [OSM Copyright](https://www.openstreetmap.org/copyright) for details.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork and clone the repository.
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run test, lint, and typecheck suites:
   ```bash
   python -m pytest
   python -m ruff check .
   python -m ruff format --check .
   python -m mypy src
   ```
4. Read our [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md).
5. Open a pull request using our PR template.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
Data (c) [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL 1.0.
