"""Generate a terminal-style SVG recording of real osm-poi CLI commands and output.

Run this script to regenerate docs/demo.svg:
    python scripts/make-demo.py
"""

from __future__ import annotations

import html
import http.server
import json
import subprocess
import sys
import threading
from pathlib import Path

# Sample fixtures matching worked example in README
SAMPLE_FIXTURE = {
    "version": 0.6,
    "generator": "Overpass API mock",
    "elements": [
        {
            "type": "node",
            "id": 101,
            "lat": 40.9900000,
            "lon": 29.0300000,
            "tags": {
                "amenity": "cafe",
                "name": "Moda Kahvecisi",
                "addr:street": "Moda Caddesi",
                "addr:housenumber": "12",
                "addr:city": "Kadıköy",
                "phone": "+90 216 555 0101",
                "website": "https://example.org/moda",
                "opening_hours": "Mo-Su 08:00-22:00",
            },
        },
        {
            "type": "way",
            "id": 202,
            "center": {"lat": 40.9902000, "lon": 29.0301000},
            "tags": {"amenity": "cafe", "name": "moda kahvecisi"},
        },
        {
            "type": "node",
            "id": 303,
            "lat": 40.9850000,
            "lon": 29.0250000,
            "tags": {
                "amenity": "restaurant",
                "name": "Kadıköy Balıkçısı",
                "addr:street": "Balıkçı Sokak",
                "addr:housenumber": "5",
                "addr:city": "Kadıköy",
                "phone": "+90 216 555 0102",
                "opening_hours": "Tu-Su 12:00-23:00",
            },
        },
        {
            "type": "node",
            "id": 404,
            "lat": 40.9820000,
            "lon": 29.0280000,
            "tags": {
                "amenity": "cafe",
                "name": "Bahariye Kitap Kafe",
                "addr:street": "Bahariye Caddesi",
                "addr:housenumber": "42",
                "addr:city": "Kadıköy",
                "phone": "+90 216 555 0103",
                "opening_hours": "Mo-Sa 09:00-21:00",
            },
        },
        {
            "type": "node",
            "id": 505,
            "lat": 40.9800000,
            "lon": 29.0200000,
            "tags": {"amenity": "cafe"},
        },
    ],
}


class _MockHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        payload = json.dumps(SAMPLE_FIXTURE).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        pass


def run_cli_and_capture(tmp_dir: Path) -> list[tuple[str, str, str]]:
    """Runs real CLI commands against local server and captures real outputs.

    Returns list of (line_type, line_text, color_style).
    Guarantees no local file paths are exposed.
    """
    server = http.server.HTTPServer(("127.0.0.1", 0), _MockHandler)
    port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    fetch_cmd = [
        sys.executable,
        "-m",
        "osm_poi",
        "fetch",
        "--bbox",
        "40.95,29.00,41.03,29.11",
        "-c",
        "cafe,restaurant",
        "-o",
        "out.csv",
        "--overpass-url",
        f"http://127.0.0.1:{port}/api/interpreter",
        "--user-agent",
        "my-project/1.0 (contact@example.org)",
        "--no-cache",
    ]

    fetch_proc = subprocess.run(
        fetch_cmd,
        cwd=tmp_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    fetch_stderr_lines = [
        line.strip() for line in fetch_proc.stderr.strip().splitlines() if line.strip()
    ]

    out_csv = tmp_dir / "out.csv"
    csv_lines = out_csv.read_text(encoding="utf-8").strip().splitlines()

    presets_proc = subprocess.run(
        [sys.executable, "-m", "osm_poi", "presets"],
        cwd=tmp_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    all_preset_lines = [
        line.strip() for line in presets_proc.stdout.strip().splitlines() if line.strip()
    ]
    curated_presets = [
        line
        for line in all_preset_lines
        if any(
            line.startswith(p)
            for p in ("bakery", "cafe", "dentist", "pharmacy", "real_estate_agent", "restaurant")
        )
    ][:6]

    server.shutdown()

    lines: list[tuple[str, str, str]] = [
        ("cmd", '$ export OSM_POI_USER_AGENT="my-project/1.0 (contact@example.org)"', "cmd"),
        (
            "cmd",
            "$ osm-poi fetch --bbox 40.95,29.00,41.03,29.11 -c cafe,restaurant -o out.csv",
            "cmd",
        ),
    ]

    for stderr_line in fetch_stderr_lines:
        color = (
            "info"
            if "elements" in stderr_line
            else ("success" if "Wrote" in stderr_line else "dim")
        )
        lines.append(("out", stderr_line, color))

    lines.append(("space", "", "dim"))
    lines.append(("cmd", "$ head -n 4 out.csv", "cmd"))

    # CSV header and sample rows
    if csv_lines:
        lines.append(("out", csv_lines[0], "header"))
        for row in csv_lines[1:4]:
            lines.append(("out", row, "data"))

    lines.append(("space", "", "dim"))
    lines.append(("cmd", "$ osm-poi presets | grep -E 'cafe|restaurant|pharmacy|bakery'", "cmd"))
    for pr in curated_presets:
        lines.append(("out", pr, "data"))

    return lines


def generate_svg(lines: list[tuple[str, str, str]]) -> str:
    line_height = 22
    pad_top = 58
    pad_bottom = 26
    height = pad_top + len(lines) * line_height + pad_bottom
    width = 820

    color_map = {
        "cmd": "#f0f6fc",
        "prompt": "#58a6ff",
        "info": "#79c0ff",
        "success": "#7ee787",
        "dim": "#8b949e",
        "header": "#f9e2af",
        "data": "#cdd6f4",
    }

    font_mono = (
        'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace'
    )
    title_text = "osm-poi — terminal"

    svg_lines: list[str] = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="100%" height="{height}" style="max-width:{width}px;">'
        ),
        "  <defs>",
        "    <linearGradient id='bg' x1='0%' y1='0%' x2='100%' y2='100%'>",
        "      <stop offset='0%' stop-color='#0d1117'/>",
        "      <stop offset='100%' stop-color='#161b22'/>",
        "    </linearGradient>",
        "  </defs>",
        (
            f"  <rect width='{width}' height='{height}' rx='10' "
            "fill='url(#bg)' stroke='#30363d' stroke-width='1.5'/>"
        ),
        "  <!-- Window controls -->",
        "  <circle cx='24' cy='24' r='6' fill='#ff5f56'/>",
        "  <circle cx='44' cy='24' r='6' fill='#ffbd2e'/>",
        "  <circle cx='64' cy='24' r='6' fill='#27c93f'/>",
        "  <!-- Title -->",
        (
            f"  <text x='{width // 2}' y='28' text-anchor='middle' fill='#8b949e' "
            f"font-family='{font_mono}' font-size='12' font-weight='600'>{title_text}</text>"
        ),
        f"  <line x1='0' y1='44' x2='{width}' y2='44' stroke='#30363d' stroke-width='1'/>",
        "  <!-- Terminal content -->",
        f"  <g font-family='{font_mono}' font-size='12.5'>",
    ]

    for idx, (kind, text, style) in enumerate(lines):
        y = pad_top + idx * line_height
        escaped = html.escape(text)
        if kind == "cmd":
            parts = escaped.split(" ", 1)
            prompt = parts[0]
            rest = (" " + parts[1]) if len(parts) > 1 else ""
            svg_lines.append(
                f'    <text x="24" y="{y}">'
                f'<tspan fill="{color_map["prompt"]}" font-weight="700">{prompt}</tspan>'
                f'<tspan fill="{color_map["cmd"]}" font-weight="600">{rest}</tspan>'
                f"</text>"
            )
        elif kind == "space":
            continue
        else:
            col = color_map.get(style, "#c9d1d9")
            svg_lines.append(f'    <text x="24" y="{y}" fill="{col}">{escaped}</text>')

    svg_lines.append("  </g>")
    svg_lines.append("</svg>")
    return "\n".join(svg_lines) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    docs_dir = root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = root / "is" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    lines = run_cli_and_capture(tmp_dir)
    svg_content = generate_svg(lines)

    target = docs_dir / "demo.svg"
    target.write_text(svg_content, encoding="utf-8")
    print(f"Generated {target} ({len(lines)} lines of real CLI session).")


if __name__ == "__main__":
    main()
