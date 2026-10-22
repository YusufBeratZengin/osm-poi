"""Data model for a normalized point of interest."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass(frozen=True)
class Poi:
    """One normalized OpenStreetMap feature.

    ``lat``/``lon`` are the node position, or the centre for ways and relations.
    """

    osm_type: str
    osm_id: int
    osm_url: str
    name: str
    category: str
    lat: float
    lon: float
    street: str = ""
    housenumber: str = ""
    postcode: str = ""
    city: str = ""
    country: str = ""
    phone: str = ""
    website: str = ""
    email: str = ""
    opening_hours: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def completeness(self) -> int:
        """Number of optional text fields that are filled in."""
        optional = (
            self.street,
            self.housenumber,
            self.postcode,
            self.city,
            self.country,
            self.phone,
            self.website,
            self.email,
            self.opening_hours,
        )
        return sum(1 for value in optional if value)


FIELDS: tuple[str, ...] = tuple(f.name for f in fields(Poi))
