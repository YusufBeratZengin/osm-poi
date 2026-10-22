# Contributing

Thanks for your interest in osm-poi. Bug reports, presets for new categories and small focused
pull requests are welcome.

## Setup

```
git clone https://github.com/YusufBeratZengin/osm-poi.git
cd osm-poi
python -m pip install -e ".[dev]"
```

## Before opening a pull request

```
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

All four must pass. CI runs them on Linux and Windows with Python 3.10 and 3.13.

## Guidelines

- Tests must not use the real network. Use the local fake server in `tests/conftest.py`.
- Keep runtime dependencies at zero. The standard library is enough for this project.
- Add or update tests with every behaviour change, and mention user-visible changes in
  `CHANGELOG.md`.
- Use Conventional Commits for messages (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- New presets go in `src/osm_poi/data/presets.json`. Use well-established OSM tags and check
  them on the [OSM wiki](https://wiki.openstreetmap.org/wiki/Map_features).
- Never commit real personal data, API keys or tokens.

## Reporting bugs

Open an issue with the command you ran (without secrets), the output, your Python version and
operating system. For security problems, see [SECURITY.md](SECURITY.md) instead.
