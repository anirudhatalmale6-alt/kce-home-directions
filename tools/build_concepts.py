#!/usr/bin/env python3
"""Assemble the two home-page concepts into standalone files:
fonts embedded as base64, coverage map inlined with the served states switched on."""
import base64, pathlib, re

ROOT = pathlib.Path(__file__).parent
CON = ROOT / "concepts"

# Placeholder coverage until KCE sends the real list. Two of these are offices.
OFFICES = {"TX", "VA"}
SERVED = {
    "TX", "OK", "LA", "AR", "NM", "KS", "MO", "TN", "KY", "OH",
    "IN", "IL", "GA", "NC", "SC", "VA", "MD", "WV", "PA", "DE",
}
assert len(SERVED) == 20, len(SERVED)

RAW_MAP = (CON / "usmap.svg").read_text()


def map_svg(extra_class=""):
    """Stamp .hq / .on onto the right state paths."""
    def sub(m):
        code = m.group(1)
        cls = "hq" if code in OFFICES else ("on" if code in SERVED else "")
        return f'<path id="{code}" class="{cls}"' if cls else f'<path id="{code}"'

    svg = re.sub(r'<path id="([A-Z]{2})"', sub, RAW_MAP)
    if extra_class:
        svg = svg.replace('class="usmap"', f'class="usmap {extra_class}"', 1)
    return svg


def font_face(family, filename, weight):
    b64 = base64.b64encode((CON / "fonts" / filename).read_bytes()).decode()
    return (
        f"@font-face{{font-family:'{family}';font-style:normal;"
        f"font-weight:{weight};font-display:swap;"
        f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
    )


BUILDS = [
    ("a.html", "concept-a-the-record.html", font_face("Instrument Sans", "InstrumentSans.woff2", "400 700")),
    ("b.html", "concept-b-the-corridor.html", font_face("Manrope", "Manrope.woff2", "200 800")),
]

for src, out, face in BUILDS:
    html = (CON / "src" / src).read_text()
    html = html.replace("/*FONT*/", face)
    html = html.replace("<!--USMAP-->", map_svg())
    html = html.replace("<!--MAPBG-->", map_svg("mapbg"))
    (CON / out).write_text(html)
    print(f"{out}: {len(html)/1024:.0f} KB")
