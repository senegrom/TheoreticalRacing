#!/usr/bin/env python3
"""Stitch the OpenStreetMap ways for Circuit de la Sarthe into one clean loop.

The OSM data has the modern 13.6 km layout fragmented, and ~40% of the lap
(the public-road Mulsanne sections) is missing entirely. A greedy
nearest-endpoint stitch tangles on those gaps (it jumps to whatever way is
nearest, regardless of lap order, producing self-crossings).

Le Mans is roughly triangular -- star-shaped about its centroid -- so we order
the ways by the angle of their midpoint around the centroid. That gives a clean
monotonic angular sweep (a simple, non-self-crossing closed polygon), with
straight-line connectors bridging the missing sections.
"""

import json
import math
import sys

KEEP_NAMES = {
    'Tertre Rouge',
    'Ligne Droite des Hunaudières',
    'Virage de Mulsanne',
    'Virage du Pont',
    "Virage d'Arnage",
    'Virage Porsche',
    'Maison Blanche',
    'Chicane Ford',
    'Courbe Dunlop',
    'Chicane Dunlop',
    'Esses de la Forêt',
    'Le « S » du Garage Bleu',
    'Circuit des 24 Heures du Mans',
}

EARTH_R = 6371000.0


def to_m(lat, lon, lat0):
    x = math.radians(lon) * math.cos(math.radians(lat0)) * EARTH_R
    y = math.radians(lat) * EARTH_R
    return x, y


def main():
    in_path = sys.argv[1]
    out_path = sys.argv[2]
    with open(in_path, encoding='utf-8') as f:
        data = json.load(f)

    ways = []
    for e in data['elements']:
        if e['type'] != 'way':
            continue
        if e.get('tags', {}).get('name', '') not in KEEP_NAMES:
            continue
        ways.append(e['geometry'])
    print(f"Filtered {len(ways)} ways", file=sys.stderr)

    lat0 = sum(p['lat'] for w in ways for p in w) / sum(len(w) for w in ways)

    # Project every way's points to local meters once.
    proj = []
    for w in ways:
        proj.append([to_m(p['lat'], p['lon'], lat0) for p in w])

    # Overall centroid.
    allpts = [p for w in proj for p in w]
    cx = sum(p[0] for p in allpts) / len(allpts)
    cy = sum(p[1] for p in allpts) / len(allpts)

    # Order ways by the angle of their midpoint around the centroid.
    def midangle(w):
        mx = sum(p[0] for p in w) / len(w)
        my = sum(p[1] for p in w) / len(w)
        return math.atan2(my - cy, mx - cx)

    order = sorted(range(len(proj)), key=lambda i: midangle(proj[i]))

    # Walk the ordered ways, orienting each so its entry endpoint is the one
    # nearer to the running chain end. Straight connectors bridge gaps.
    chain = []
    cur = None
    for oi in order:
        w = proj[oi]
        if cur is None:
            chain.extend(w)
            cur = w[-1]
            continue
        d_fwd = math.dist(cur, w[0])
        d_rev = math.dist(cur, w[-1])
        seq = w if d_fwd <= d_rev else list(reversed(w))
        chain.extend(seq)
        cur = seq[-1]

    # Convert back to lon/lat and close the loop.
    def to_lonlat(x, y):
        lat = math.degrees(y / EARTH_R)
        lon = math.degrees(x / (EARTH_R * math.cos(math.radians(lat0))))
        return [lon, lat]

    coords = [to_lonlat(x, y) for x, y in chain]
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    out = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"Location": "Le Mans", "Name": "Circuit de la Sarthe", "length": 13600},
            "geometry": {"type": "LineString", "coordinates": coords},
        }],
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f)
    print(f"Wrote {out_path}: {len(coords)} centerline points", file=sys.stderr)


if __name__ == "__main__":
    main()
