"""Command line interface: ``osm-poi fetch | presets | cache``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from osm_poi import __version__
from osm_poi.areas import Area, BBox, OsmArea, Polygon, load_polygon_file, parse_bbox
from osm_poi.cache import DiskCache
from osm_poi.config import Config, load_config
from osm_poi.dedupe import DEFAULT_RADIUS_M, dedupe
from osm_poi.errors import AreaError, ConfigError, OsmPoiError
from osm_poi.http import HttpClient
from osm_poi.models import FIELDS
from osm_poi.nominatim import NominatimClient
from osm_poi.normalize import normalize_elements
from osm_poi.overpass import OverpassClient
from osm_poi.presets import Preset, load_presets, select_presets
from osm_poi.query import build_query
from osm_poi.writers import FORMATS, guess_format, write_output

CONTACT_FIELDS = frozenset({"phone", "website", "email"})


def resolve_fields(fields_arg: str | None, no_contact: bool) -> tuple[str, ...]:
    if fields_arg:
        chosen = [f.strip() for f in fields_arg.split(",") if f.strip()]
        for f in chosen:
            if f not in FIELDS:
                raise ConfigError(
                    f"Unknown field {f!r}. Available fields: {', '.join(FIELDS)}"
                )
    else:
        chosen = list(FIELDS)

    if no_contact:
        chosen = [f for f in chosen if f not in CONTACT_FIELDS]

    if not chosen:
        raise ConfigError("No fields selected for export.")
    return tuple(chosen)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="osm-poi",
        description="Export OpenStreetMap points of interest to CSV, GeoJSON or JSONL.",
    )
    parser.add_argument("--version", action="version", version=f"osm-poi {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="query Overpass and write the results")
    area = fetch.add_argument_group("area (give at least one)")
    area.add_argument(
        "--area",
        action="append",
        default=[],
        metavar="NAME",
        help='place name resolved with Nominatim, e.g. "Kadikoy, Istanbul"',
    )
    area.add_argument(
        "--bbox",
        action="append",
        default=[],
        metavar="S,W,N,E",
        help="bounding box: south,west,north,east",
    )
    area.add_argument(
        "--polygon",
        action="append",
        default=[],
        metavar="FILE",
        help="GeoJSON file with Polygon or MultiPolygon geometry",
    )
    fetch.add_argument(
        "-c",
        "--category",
        action="append",
        default=[],
        metavar="LIST",
        help="comma separated preset names (see 'osm-poi presets')",
    )
    fetch.add_argument(
        "-o", "--output", default="-", metavar="FILE", help="output file, or - for stdout (default)"
    )
    fetch.add_argument(
        "-f", "--format", choices=FORMATS, help="output format (default: from file extension)"
    )
    fetch.add_argument(
        "--presets-file",
        type=Path,
        metavar="FILE",
        help="JSON file with extra or overriding presets",
    )
    fetch.add_argument(
        "--include-unnamed", action="store_true", help="keep features without a name"
    )
    fetch.add_argument(
        "--no-contact",
        action="store_true",
        help="drop phone, website and email columns from the output",
    )
    fetch.add_argument(
        "--fields",
        metavar="LIST",
        help="comma-separated list of output columns (default: all)",
    )
    fetch.add_argument(
        "--allow-large",
        action="store_true",
        help="allow search areas larger than the maximum area limit",
    )
    fetch.add_argument(
        "--max-area",
        type=float,
        metavar="DEG2",
        help="maximum area in square degrees allowed without --allow-large (default: 0.25)",
    )
    fetch.add_argument(
        "--split",
        type=int,
        default=1,
        metavar="N",
        help="tile each bounding box into N x N sub-queries",
    )
    fetch.add_argument(
        "--dedupe-radius",
        type=float,
        default=DEFAULT_RADIUS_M,
        metavar="METERS",
        help="merge same-name duplicates closer than this; 0 disables "
        f"(default {DEFAULT_RADIUS_M:g})",
    )
    fetch.add_argument(
        "--dry-run",
        action="store_true",
        help="print the Overpass query and exit without querying Overpass",
    )
    fetch.add_argument(
        "--query-timeout",
        type=int,
        default=90,
        metavar="SECONDS",
        help="timeout written into the Overpass query (default 90)",
    )
    _add_network_options(fetch)

    listing = sub.add_parser("presets", help="list available category presets")
    listing.add_argument("--presets-file", type=Path, metavar="FILE")

    cache = sub.add_parser("cache", help="inspect or clear the on-disk cache")
    cache.add_argument("action", choices=("path", "clear"))
    cache.add_argument("--cache-dir", type=Path)
    cache.add_argument("--config", type=Path)
    return parser


def _add_network_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("network and cache")
    group.add_argument("--config", type=Path, metavar="FILE", help="JSON config file")
    group.add_argument(
        "--user-agent", help="identifies you to Overpass and Nominatim (or set OSM_POI_USER_AGENT)"
    )
    group.add_argument("--overpass-url", help="Overpass interpreter endpoint")
    group.add_argument("--nominatim-url", help="Nominatim base URL")
    group.add_argument("--timeout", type=float, help="HTTP timeout in seconds")
    group.add_argument("--retries", type=int, help="retries on 429/5xx and network errors")
    group.add_argument("--cache-dir", type=Path, help="cache directory")
    group.add_argument("--cache-ttl-hours", type=float, help="cache lifetime in hours")
    group.add_argument("--no-cache", action="store_true", help="do not read or write the cache")


def _config_from_args(args: argparse.Namespace) -> Config:
    overrides = {
        "user_agent": getattr(args, "user_agent", None),
        "overpass_url": getattr(args, "overpass_url", None),
        "nominatim_url": getattr(args, "nominatim_url", None),
        "timeout": getattr(args, "timeout", None),
        "retries": getattr(args, "retries", None),
        "cache_dir": getattr(args, "cache_dir", None),
        "cache_ttl_hours": getattr(args, "cache_ttl_hours", None),
        "use_cache": False if getattr(args, "no_cache", False) else None,
        "max_area": getattr(args, "max_area", None),
    }
    return load_config(path=getattr(args, "config", None), overrides=overrides)


def _make_cache(config: Config) -> DiskCache:
    return DiskCache(
        config.resolved_cache_dir(),
        ttl_seconds=config.cache_ttl_hours * 3600,
        enabled=config.use_cache,
    )


def _split_categories(values: Sequence[str]) -> list[str]:
    return [part.strip() for value in values for part in value.split(",") if part.strip()]


def _log(message: str) -> None:
    print(message, file=sys.stderr)


def _cmd_fetch(args: argparse.Namespace) -> int:
    presets_all = load_presets(args.presets_file)
    presets: list[Preset] = select_presets(presets_all, _split_categories(args.category))
    if not (args.area or args.bbox or args.polygon):
        raise AreaError("Give an area with --area, --bbox or --polygon.")

    fmt = args.format or ("csv" if args.output == "-" else guess_format(args.output))
    selected_fields = resolve_fields(args.fields, args.no_contact)

    config = _config_from_args(args)
    cache = _make_cache(config)

    if not args.dry_run:
        agent = config.require_user_agent()
    else:
        agent = config.user_agent or "osm-poi/dry-run"

    if args.split < 1:
        raise AreaError(f"Split must be at least 1, got {args.split}.")
    if args.split > 1 and not args.bbox and not args.area:
        raise AreaError("--split can only be used with --bbox or bounding areas.")

    bboxes: list[BBox] = []
    for text in args.bbox:
        b = parse_bbox(text)
        bboxes.extend(b.split(args.split) if args.split > 1 else [b])

    polygons: list[Polygon] = []
    for path in args.polygon:
        polygons.extend(load_polygon_file(Path(path)))

    osm_areas: list[OsmArea] = []
    if args.area:
        agent = config.require_user_agent()
        nominatim = NominatimClient(
            config.nominatim_url,
            HttpClient(
                agent, config.timeout, config.retries, config.backoff, config.nominatim_interval
            ),
            cache,
        )
        for name in args.area:
            resolved = nominatim.resolve(name)
            if isinstance(resolved, BBox):
                bboxes.extend(resolved.split(args.split) if args.split > 1 else [resolved])
            elif isinstance(resolved, Polygon):
                polygons.append(resolved)
            elif isinstance(resolved, OsmArea):
                osm_areas.append(resolved)

    if not args.allow_large:
        for b in bboxes:
            if b.area_sq_degrees() > config.max_area:
                raise AreaError(
                    f"Bounding box area {b.area_sq_degrees():.4f} sq deg exceeds the limit "
                    f"of {config.max_area:.4f} sq deg. Use --allow-large to proceed or "
                    f"--split to tile the bounding box into smaller queries."
                )
        for p in polygons:
            if p.area_sq_degrees() > config.max_area:
                raise AreaError(
                    f"Polygon area {p.area_sq_degrees():.4f} sq deg exceeds the limit "
                    f"of {config.max_area:.4f} sq deg. Use --allow-large to proceed."
                )

    queries: list[str] = []
    if args.split > 1 and bboxes:
        for b in bboxes:
            queries.append(build_query([b], presets, timeout=args.query_timeout))
        for other in (*polygons, *osm_areas):
            queries.append(build_query([other], presets, timeout=args.query_timeout))
    else:
        all_areas: list[Area] = [*bboxes, *polygons, *osm_areas]
        queries.append(build_query(all_areas, presets, timeout=args.query_timeout))

    if args.dry_run:
        for q in queries:
            sys.stdout.write(q)
        return 0

    overpass = OverpassClient(
        config.overpass_url,
        HttpClient(agent, config.timeout, config.retries, config.backoff, config.overpass_interval),
        cache,
    )
    elements: list[dict[str, Any]] = []
    for q in queries:
        elements.extend(overpass.run(q))

    pois = normalize_elements(elements, presets, include_unnamed=args.include_unnamed)
    unique = dedupe(pois, radius_m=args.dedupe_radius)
    notice = write_output(unique, args.output, fmt, fields=selected_fields)

    _log(f"{len(elements)} elements, {len(pois)} usable, {len(unique)} after deduplication.")
    if notice is not None:
        _log(f"Wrote {args.output} and {notice}")
    _log("Data (c) OpenStreetMap contributors, ODbL 1.0. https://www.openstreetmap.org/copyright")
    return 0


def _cmd_presets(args: argparse.Namespace) -> int:
    for name, preset in sorted(load_presets(args.presets_file).items()):
        print(f"{name:<20} {preset.label}")
    return 0


def _cmd_cache(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    cache = _make_cache(config)
    if args.action == "path":
        print(cache.directory)
    else:
        print(f"Removed {cache.clear()} cache entries from {cache.directory}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "fetch":
            return _cmd_fetch(args)
        if args.command == "presets":
            return _cmd_presets(args)
        return _cmd_cache(args)
    except OsmPoiError as exc:
        print(f"osm-poi: error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("osm-poi: interrupted", file=sys.stderr)
        return 130
