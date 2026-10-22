# osm-poi

[![CI](https://github.com/YusufBeratZengin/osm-poi/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/osm-poi/actions/workflows/ci.yml)

Export points of interest (businesses, amenities, shops) from OpenStreetMap to CSV, GeoJSON or
JSONL. It talks to the public Overpass API and Nominatim, follows their usage policies and has
no runtime dependencies beyond the Python standard library.

It is meant for small agencies, researchers and civic projects that need a free and legal way to
list businesses in an area without a paid Places API.

## Features

- Area input: bounding box, administrative area name (resolved through Nominatim) or a GeoJSON
  polygon. Several areas can be combined.
- Category presets (`cafe`, `restaurant`, `pharmacy`, `dentist`, `real_estate_agent`,
  `hairdresser`, `hotel`, and more) defined in a plain JSON file you can extend.
- Nodes, ways and relations are all queried; ways and relations use their centre point.
- Normalized fields: name, category, address parts, phone, website, email, opening hours,
  OSM id and URL.
- Deduplication of identical OSM objects and of near-duplicates (same name and category within
  75 m by default, for example a building outline plus a node).
- Output as CSV, GeoJSON or JSONL. CSV cells are protected against spreadsheet formula injection.
- Polite by default: configurable User-Agent (required), spacing between requests, retries with
  exponential backoff on 429 and 5xx (honouring `Retry-After`), and an on-disk cache keyed by the
  hash of each request.
- `--dry-run` prints the Overpass query without sending it.
- ODbL attribution is written next to every output file.

## Install

```
pip install .
```

Python 3.10 or newer is required. From a checkout, `pip install -e ".[dev]"` adds the test and
lint tools.

## Quick start

Overpass and Nominatim require you to identify your application. Set a User-Agent with a way to
contact you:

```
export OSM_POI_USER_AGENT="my-project/1.0 (me@example.org)"      # Linux, macOS
$env:OSM_POI_USER_AGENT = "my-project/1.0 (me@example.org)"      # PowerShell
```

Then:

```
osm-poi fetch --area "Kadikoy, Istanbul" --category cafe,restaurant -o out.csv
osm-poi fetch --bbox 40.95,29.00,41.03,29.11 -c pharmacy -o pharmacies.geojson
osm-poi fetch --polygon district.geojson -c dentist -f jsonl -o dentists.jsonl
osm-poi fetch --bbox 40.95,29.00,41.03,29.11 -c cafe --dry-run
osm-poi presets
```

`--bbox` uses the Overpass order: `south,west,north,east`. The output format comes from the file
extension (`.csv`, `.geojson`/`.json`, `.jsonl`) or from `--format`. With `-o -` (the default) the
result goes to standard output.

### Output columns

`osm_type, osm_id, osm_url, name, category, lat, lon, street, housenumber, postcode, city,
country, phone, website, email, opening_hours`

Features without a name are skipped unless you pass `--include-unnamed`. Missing values are empty
strings.

## Presets

List them with `osm-poi presets`. To add or override presets, pass `--presets-file my.json`:

```json
{
  "bike_shop": {
    "label": "Bicycle shops",
    "tags": [{"shop": "bicycle"}]
  },
  "bar": {
    "tags": [{"amenity": ["bar", "pub", "biergarten"]}]
  }
}
```

`tags` is a list of tag sets. A feature matches a preset if it matches any tag set; inside a tag
set all keys must match. A value is a string, a list of alternatives, or `"*"` for "key exists".

## Configuration

Precedence, lowest to highest: defaults, JSON config file, environment variables, command-line
flags.

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

The config file is JSON with the same keys. Its location is `--config`, `OSM_POI_CONFIG`, or
`~/.config/osm-poi/config.json` (`%APPDATA%\osm-poi\config.json` on Windows). `osm-poi cache path`
shows the cache directory and `osm-poi cache clear` empties it.

## Usage policies

- [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/): at most one
  request per second, a real User-Agent, cached results, no bulk geocoding. osm-poi sends one
  lookup per `--area` and caches it. Do not point it at the public instance for large batch jobs.
- [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances):
  the public servers are shared. Keep areas and categories reasonable, and use `--overpass-url` to
  target your own instance for heavy use.

## Attribution and license of the data

The data comes from OpenStreetMap and is licensed under the
[Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
You must credit "(c) OpenStreetMap contributors", and a database derived from this data must be
shared under the same license. osm-poi writes `<output>.ATTRIBUTION.txt` next to each file and
adds `attribution` and `license` members to GeoJSON output. See the
[OSM copyright page](https://www.openstreetmap.org/copyright). This is not legal advice.

OpenStreetMap contains data entered by volunteers, which can include phone numbers and addresses
of businesses. Check the privacy and marketing laws that apply to your use, for example GDPR and
anti-spam rules, before contacting anyone.

## Development

```
pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m mypy src
```

Tests never touch the real network: HTTP behaviour is tested against a local fake server.

## License

MIT, see [LICENSE](LICENSE). Copyright (c) 2026 Yusuf Berat Zengin.
