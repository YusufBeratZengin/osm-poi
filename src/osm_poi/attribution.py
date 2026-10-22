"""ODbL attribution text that must accompany exported data."""

from __future__ import annotations

from datetime import datetime, timezone

COPYRIGHT_URL = "https://www.openstreetmap.org/copyright"
LICENSE_URL = "https://opendatacommons.org/licenses/odbl/1-0/"

SHORT = f"Data (c) OpenStreetMap contributors, ODbL 1.0. {COPYRIGHT_URL}"


def attribution_text(generated: datetime | None = None) -> str:
    """Return the attribution notice written next to every output file."""
    when = (generated or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    return (
        "Data attribution\n"
        "================\n"
        "\n"
        "This file contains data from OpenStreetMap.\n"
        "\n"
        "(c) OpenStreetMap contributors\n"
        "The data is available under the Open Database License (ODbL) 1.0.\n"
        f"Copyright and license: {COPYRIGHT_URL}\n"
        f"License text: {LICENSE_URL}\n"
        "\n"
        "If you publish this data or a database derived from it, you must credit\n"
        "OpenStreetMap contributors and keep the derived database under the ODbL\n"
        "(share-alike). Read the ODbL and the OSM attribution guidelines for the\n"
        "exact obligations of your use case.\n"
        "\n"
        f"Exported on {when} with osm-poi.\n"
    )
