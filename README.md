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
- Category presets (`cafe`, `restaurant`, `pharmacy`, `dentist`, `real_estate_agent`, `estate_agent`,
  `hairdresser`, `hotel`, `stationery`, `notary`, `car_repair`, and more) defined in plain JSON.
- Nodes, ways and relations are all queried; ways and relations use their centre point.
- Normalized fields: name, category, address parts, phone, website, email, opening hours,
  OSM id and URL.
- Deduplication of identical OSM objects and near-duplicates (same name and category within
  75 m by default, for example a building outline plus a node).
- Area size safety: protects Overpass servers by enforcing a default 0.25 sq deg area limit
  unless `--allow-large` is given, with `--split N` to tile large bounding boxes.
- Privacy-conscious: `--no-contact` drops phone, website, and email columns, while `--fields`
  allows selecting exact columns.
- Output as CSV, GeoJSON or JSONL. CSV cells are protected against spreadsheet formula injection.
- Polite by default: configurable User-Agent (required), spacing between requests, retries with
  exponential backoff on 429 and 5xx (honouring `Retry-After`), and on-disk caching.
- `--dry-run` prints the Overpass query without sending it.
- ODbL attribution is written next to every output file.

## Install

```
pip install .
```

Python 3.10 or newer is required. From a checkout, `pip install -e ".[dev]"` adds test and
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

## Example output

### Worked example: Kadıköy

In this Kadıköy worked example, querying cafes and restaurants returns 5 raw elements from
OpenStreetMap: a node and a way outline for "Moda Kahvecisi" located 25 metres apart, a seafood
restaurant ("Kadıköy Balıkçısı"), a book cafe ("Bahariye Kitap Kafe"), and an unnamed cafe node.
During processing:

1. **Unnamed filtering**: Features without a name are skipped by default, dropping the unnamed node.
2. **Deduplication**: Deduplication identifies that the building way and the node share the same
   normalized name ("moda kahvecisi") within 75 metres. The pass merges them into a single record,
   retaining the node because it contains richer contact details (street address, phone number,
   website, and opening hours).
3. **Clean output**: The final result yields exactly 3 deduplicated business records.

### CSV output excerpt

```csv
osm_type,osm_id,osm_url,name,category,lat,lon,street,housenumber,postcode,city,country,phone,website,email,opening_hours
node,101,https://www.openstreetmap.org/node/101,Moda Kahvecisi,cafe,40.99,29.03,Moda Caddesi,12,,Kadıköy,TR,+90 216 555 0101,https://example.org/moda,,Mo-Su 08:00-22:00
node,303,https://www.openstreetmap.org/node/303,Kadıköy Balıkçısı,restaurant,40.985,29.025,Balıkçı Sokak,5,,Kadıköy,TR,+90 216 555 0102,https://example.org/balik,,Tu-Su 12:00-23:00
node,404,https://www.openstreetmap.org/node/404,Bahariye Kitap Kafe,cafe,40.982,29.028,Bahariye Caddesi,42,,Kadıköy,TR,+90 216 555 0103,https://example.org/kitap,,Mo-Sa 09:00-21:00
```

### GeoJSON feature excerpt

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

## Python API

You can use `osm-poi` as a Python library:

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

The returned objects are instances of [`Poi`](src/osm_poi/models.py). The public functions and
classes are exported in `__all__`: `fetch_pois`, `Poi`, `BBox`, `Polygon`, `Config`, and `load_config`.

## Responsible use

OpenStreetMap data is entered and maintained by community volunteers. While business entries often
contain publicly displayed contact tags, please keep the following in mind:

- **Privacy flags**: You can pass `--no-contact` to omit `phone`, `website`, and `email` columns
  from the output entirely, or use `--fields name,category,lat,lon` to select specific columns.
- **Data protection (KVKK / GDPR)**: Contact information associated with sole proprietors,
  freelancers, or individual professionals may constitute personal data under the Turkish Personal
  Data Protection Law (KVKK No. 6698), the European General Data Protection Regulation (GDPR),
  and similar international frameworks.
- **Anti-spam and marketing regulations**: Unsolicited commercial communications (cold email,
  automated calling, or commercial SMS) are strictly regulated by law (such as the Turkish Law on
  the Regulation of Electronic Commerce No. 6563 and the Commercial Electronic Message Management
  System / İYS).
- **Disclaimer**: This documentation does not constitute legal advice. You are responsible for
  evaluating the legal compliance of your own data collection and communication workflows.

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
| `max_area` | `OSM_POI_MAX_AREA` | `--max-area` | 0.25 square degrees |

Additional command line options:
- `--no-contact`: drop phone, website, and email columns from exported data.
- `--fields LIST`: comma-separated column list to export (e.g. `--fields name,category,lat,lon`).
- `--allow-large`: bypass the area size safety limit.
- `--split N`: tile a bounding box into $N \times N$ sequential sub-queries with polite pacing.

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
