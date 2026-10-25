from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.make_example import generate_examples


def _extract_fenced_blocks(markdown_text: str, lang: str) -> list[str]:
    pattern = rf"```{lang}\r?\n(.*?)```"
    return [match.strip() for match in re.findall(pattern, markdown_text, re.DOTALL)]


def test_golden_sample_files_match_generation(tmp_path: Path) -> None:
    csv_gen, geojson_gen, jsonl_gen = generate_examples(tmp_path)
    root = Path(__file__).resolve().parent.parent

    csv_existing = (root / "examples" / "sample.csv").read_text(encoding="utf-8")
    geojson_existing = (root / "examples" / "sample.geojson").read_text(encoding="utf-8")
    jsonl_existing = (root / "examples" / "sample.jsonl").read_text(encoding="utf-8")

    assert csv_existing == csv_gen
    assert geojson_existing == geojson_gen
    assert jsonl_existing == jsonl_gen


def test_readme_examples_match_golden_files() -> None:
    root = Path(__file__).resolve().parent.parent
    sample_csv = (root / "examples" / "sample.csv").read_text(encoding="utf-8").strip()
    sample_geojson = (root / "examples" / "sample.geojson").read_text(encoding="utf-8")
    sample_jsonl_text = (root / "examples" / "sample.jsonl").read_text(encoding="utf-8").strip()
    first_jsonl_line = sample_jsonl_text.splitlines()[0]
    first_feature = json.loads(sample_geojson)["features"][0]

    for filename in ("README.md", "README.tr.md"):
        content = (root / filename).read_text(encoding="utf-8")

        # Verify CSV block
        csv_blocks = _extract_fenced_blocks(content, "csv")
        assert any(sample_csv == block for block in csv_blocks), (
            f"CSV sample in {filename} does not match examples/sample.csv"
        )

        # Verify GeoJSON excerpt block
        json_blocks = _extract_fenced_blocks(content, "json")
        matching_feature = False
        for b in json_blocks:
            try:
                parsed = json.loads(b)
                if parsed == first_feature:
                    matching_feature = True
                    break
            except json.JSONDecodeError:
                continue
        assert matching_feature, f"GeoJSON excerpt in {filename} does not match first feature"

        # Verify JSONL excerpt block
        jsonl_blocks = _extract_fenced_blocks(content, "jsonl")
        assert any(first_jsonl_line in block for block in jsonl_blocks), (
            f"JSONL excerpt in {filename} does not match first line of examples/sample.jsonl"
        )
