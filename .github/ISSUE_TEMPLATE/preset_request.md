---
name: Preset request
about: Suggest a new category preset or tag matching rule
title: '[PRESET] '
labels: ['presets']
assignees: ''
---

**Category name**
Short identifier in snake_case (e.g. `veterinary`, `notary`).

**User-facing label**
Human-readable label (e.g. "Notary offices").

**OpenStreetMap tags**
Which OSM tags define this category?
Example:
```json
{
  "tags": [
    {"amenity": "notary"}
  ]
}
```

**Common use case**
Describe the business type or agency use case that benefits from this preset.
