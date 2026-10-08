#!/usr/bin/env python3
"""Turn us-atlas states-10m TopoJSON into a lower-48 Albers SVG, one path per state,
keyed by USPS code so KCE can switch a state on or off by editing one class."""
import json, math

FIPS = {
 "01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE",
 "11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA",
 "20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN",
 "28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM",
 "36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI",
 "45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA",
 "54":"WV","55":"WI","56":"WY",
}
SKIP = {"AK", "HI"}  # plus every territory, which has no FIPS entry above

topo = json.load(open("us10m.json"))
tr = topo["transform"]
sx, sy = tr["scale"]
tx, ty = tr["translate"]


def decode(arc):
    """Undo topojson delta+quantization encoding -> list of (lon, lat)."""
    out, x, y = [], 0, 0
    for dx, dy in arc:
        x += dx
        y += dy
        out.append((x * sx + tx, y * sy + ty))
    return out


ARCS = [decode(a) for a in topo["arcs"]]


def ring(idxs):
    """Stitch an arc-index list into one closed ring, honouring ~i reversal."""
    pts = []
    for i in idxs:
        a = ARCS[~i][::-1] if i < 0 else ARCS[i]
        pts.extend(a[1:] if pts else a)
    return pts


# Albers equal-area conic, the standard US parameters.
LAT0, LON0 = math.radians(37.5), math.radians(-96.0)
P1, P2 = math.radians(29.5), math.radians(45.5)
N = 0.5 * (math.sin(P1) + math.sin(P2))
C = math.cos(P1) ** 2 + 2 * N * math.sin(P1)
RHO0 = math.sqrt(C - 2 * N * math.sin(LAT0)) / N


def albers(lon, lat):
    lam, phi = math.radians(lon), math.radians(lat)
    rho = math.sqrt(C - 2 * N * math.sin(phi)) / N
    th = N * (lam - LON0)
    # Negate y: the conic formula grows northward, SVG's y axis grows downward.
    return rho * math.sin(th), -(RHO0 - rho * math.cos(th))


# Project everything first so we can fit one shared viewBox.
shapes = {}
for g in topo["objects"]["states"]["geometries"]:
    code = FIPS.get(g["id"])
    if not code or code in SKIP:
        continue
    polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
    rings = []
    for poly in polys:
        for r in poly:
            pts = [albers(lon, lat) for lon, lat in ring(r)]
            if len(pts) > 2:
                rings.append(pts)
    if rings:
        shapes[code] = (g["properties"]["name"], rings)

xs = [p[0] for _, rs in shapes.values() for r in rs for p in r]
ys = [p[1] for _, rs in shapes.values() for r in rs for p in r]
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)

W, H, PAD = 1000.0, 620.0, 8.0
k = min((W - 2 * PAD) / (maxx - minx), (H - 2 * PAD) / (maxy - miny))
ox = (W - k * (maxx - minx)) / 2 - k * minx
oy = (H - k * (maxy - miny)) / 2 - k * miny


def fmt(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


out = []
for code in sorted(shapes):
    name, rings = shapes[code]
    d = []
    for r in rings:
        # Drop slivers: tiny offshore islands only add bytes.
        px = [(p[0] * k + ox, p[1] * k + oy) for p in r]
        bw = max(q[0] for q in px) - min(q[0] for q in px)
        bh = max(q[1] for q in px) - min(q[1] for q in px)
        if bw < 1.5 and bh < 1.5:
            continue
        # Douglas-Peucker is overkill; a distance filter is enough at this scale.
        keep = [px[0]]
        for q in px[1:]:
            if abs(q[0] - keep[-1][0]) + abs(q[1] - keep[-1][1]) > 0.6:
                keep.append(q)
        if len(keep) < 3:
            continue
        d.append("M" + "L".join(f"{fmt(a)} {fmt(b)}" for a, b in keep) + "Z")
    if d:
        out.append(f'<path id="{code}" data-name="{name}" d="{"".join(d)}"/>')

svg = (
    f'<svg class="usmap" viewBox="0 0 {fmt(W)} {fmt(H)}" '
    f'role="img" aria-label="KCE service coverage by state" '
    f'xmlns="http://www.w3.org/2000/svg">\n'
    + "\n".join(out)
    + "\n</svg>\n"
)
open("concepts/usmap.svg", "w").write(svg)
print("states:", len(out), "bytes:", len(svg))
