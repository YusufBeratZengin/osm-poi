"""High-level Python API for fetching points of interest."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from osm_poi.areas import Area, BBox, OsmArea, Polygon, load_polygon_file, parse_bbox
from osm_poi.cache import DiskCache
from osm_poi.config import Config, load_config
from osm_poi.dedupe import DEFAULT_RADIUS_M, dedupe
from osm_poi.errors import AreaError
from osm_poi.http import HttpClient
from osm_poi.models import Poi
from osm_poi.nominatim import NominatimClient
from osm_poi.normalize import normalize_elements
from osm_poi.overpass import OverpassClient
from osm_poi.presets import Preset, load_presets, select_presets
from osm_poi.query import build_query


def _parse_area_inputs(
    bbox: str | tuple[float, float, float, float] | BBox | None,
    area_name: str | None,
    polygon_input: str | Path | Sequence[tuple[float, float]] | Polygon | None,
    split_count: int,
    nominatim: NominatimClient | None,
) -> tuple[list[BBox], list[Polygon], list[OsmArea]]:
    bboxes: list[BBox] = []
    if bbox is not None:
        if isinstance(bbox, BBox):
            b = bbox
        elif isinstance(bbox, str):
            b = parse_bbox(bbox)
        else:
            b = BBox(*bbox)
        bboxes.extend(b.split(split_count) if split_count > 1 else [b])

    polygons: list[Polygon] = []
    if polygon_input is not None:
        if isinstance(polygon_input, Polygon):
            polygons.append(polygon_input)
        elif isinstance(polygon_input, (str, Path)):
            path = Path(polygon_input)
            polygons.extend(load_polygon_file(path))
        else:
            polygons.append(Polygon(tuple(polygon_input)))

    osm_areas: list[OsmArea] = []
    if area_name is not None and nominatim is not None:
        resolved = nominatim.resolve(area_name)
        if isinstance(resolved, BBox):
            bboxes.extend(resolved.split(split_count) if split_count > 1 else [resolved])
        elif isinstance(resolved, Polygon):
            polygons.append(resolved)
        elif isinstance(resolved, OsmArea):
            osm_areas.append(resolved)

    return bboxes, polygons, osm_areas


def fetch_pois(
    *,
    bbox: str | tuple[float, float, float, float] | BBox | None = None,
    area: str | None = None,
    polygon: str | Path | Sequence[tuple[float, float]] | Polygon | None = None,
    categories: Sequence[str] | str,
    user_agent: str | None = None,
    overpass_url: str | None = None,
    nominatim_url: str | None = None,
    timeout: float | None = None,
    retries: int | None = None,
    presets_file: Path | None = None,
    dedupe_radius: float = DEFAULT_RADIUS_M,
    include_unnamed: bool = False,
    query_timeout: int = 90,
    allow_large: bool = False,
    split: int = 1,
    cache_dir: Path | None = None,
    cache_ttl_hours: float | None = None,
    use_cache: bool = True,
    config: Config | None = None,
) -> list[Poi]:
    """Fetch and return normalized, deduplicated POI records from OpenStreetMap."""
    if not (bbox or area or polygon):
        raise AreaError("Provide at least one area via bbox, area, or polygon.")

    if split < 1:
        raise AreaError(f"Split must be at least 1, got {split}.")
    if split > 1 and bbox is None and area is None:
        raise AreaError("--split can only be used with bbox.")

    overrides = {
        "user_agent": user_agent,
        "overpass_url": overpass_url,
        "nominatim_url": nominatim_url,
        "timeout": timeout,
        "retries": retries,
        "cache_dir": cache_dir,
        "cache_ttl_hours": cache_ttl_hours,
        "use_cache": use_cache,
    }
    cfg = load_config(overrides={k: v for k, v in overrides.items() if v is not None})
    if config is not None:
        cfg = load_config(
            overrides={
                **{
                    k: getattr(config, k)
                    for k in (
                        "user_agent",
                        "overpass_url",
                        "nominatim_url",
                        "timeout",
                        "retries",
                        "backoff",
                        "overpass_interval",
                        "nominatim_interval",
                        "cache_dir",
                        "cache_ttl_hours",
                        "use_cache",
                        "max_area",
                    )
                    if getattr(config, k) is not None
                },
                **{k: v for k, v in overrides.items() if v is not None},
            }
        )

    agent = cfg.require_user_agent()
    disk_cache = DiskCache(
        cfg.resolved_cache_dir(),
        ttl_seconds=cfg.cache_ttl_hours * 3600,
        enabled=cfg.use_cache,
    )

    nominatim_client = None
    if area:
        nominatim_client = NominatimClient(
            cfg.nominatim_url,
            HttpClient(agent, cfg.timeout, cfg.retries, cfg.backoff, cfg.nominatim_interval),
            disk_cache,
        )

    bboxes, polygons, osm_areas = _parse_area_inputs(bbox, area, polygon, split, nominatim_client)

    if not allow_large:
        for b in bboxes:
            if b.area_sq_degrees() > cfg.max_area:
                raise AreaError(
                    f"Bounding box area {b.area_sq_degrees():.4f} sq deg exceeds the limit "
                    f"of {cfg.max_area:.4f} sq deg. Use allow_large=True or split into tiles."
                )
        for p in polygons:
            if p.area_sq_degrees() > cfg.max_area:
                raise AreaError(
                    f"Polygon area {p.area_sq_degrees():.4f} sq deg exceeds the limit "
                    f"of {cfg.max_area:.4f} sq deg. Use allow_large=True to proceed."
                )

    cat_list = [categories] if isinstance(categories, str) else list(categories)
    presets_all = load_presets(presets_file)
    selected_presets: list[Preset] = select_presets(presets_all, cat_list)

    queries: list[str] = []
    if split > 1 and bboxes:
        for b in bboxes:
            queries.append(build_query([b], selected_presets, timeout=query_timeout))
        for poly in polygons:
            queries.append(build_query([poly], selected_presets, timeout=query_timeout))
        for o_area in osm_areas:
            queries.append(build_query([o_area], selected_presets, timeout=query_timeout))
    else:
        all_areas: list[Area] = []
        all_areas.extend(bboxes)
        all_areas.extend(polygons)
        all_areas.extend(osm_areas)
        queries.append(build_query(all_areas, selected_presets, timeout=query_timeout))

    overpass_client = OverpassClient(
        cfg.overpass_url,
        HttpClient(agent, cfg.timeout, cfg.retries, cfg.backoff, cfg.overpass_interval),
        disk_cache,
    )

    all_elements: list[dict[str, Any]] = []
    for query in queries:
        all_elements.extend(overpass_client.run(query))

    pois = normalize_elements(all_elements, selected_presets, include_unnamed=include_unnamed)
    return dedupe(pois, radius_m=dedupe_radius)
