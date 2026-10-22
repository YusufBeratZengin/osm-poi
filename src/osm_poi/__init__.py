"""osm-poi: export points of interest from OpenStreetMap via the Overpass API."""

from osm_poi.api import fetch_pois
from osm_poi.areas import BBox, Polygon
from osm_poi.config import Config, load_config
from osm_poi.models import Poi

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "fetch_pois",
    "Poi",
    "BBox",
    "Polygon",
    "Config",
    "load_config",
]
