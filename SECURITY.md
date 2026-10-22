# Security Policy

## Supported versions

Only the latest released version receives security fixes.

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub's private vulnerability
reporting on the repository
(<https://github.com/YusufBeratZengin/osm-poi/security/advisories/new>) and include steps to
reproduce, the affected version and the impact you see.

You can expect an acknowledgement within a week. Fixes are released as soon as they are ready and
credited in the changelog unless you prefer otherwise.

## Scope notes

osm-poi sends HTTP requests to the Overpass and Nominatim endpoints you configure. It only
accepts `http` and `https` URLs, builds Overpass queries from validated presets with escaped
values, and neutralizes spreadsheet formulas in CSV output. It stores no credentials; the
User-Agent is the only identifying value it sends.
