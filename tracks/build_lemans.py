#!/usr/bin/env python3
"""Stitch the OpenStreetMap ways for Circuit de la Sarthe into one closed loop.

The OSM data has the modern 13.6 km layout fragmented and the public-road
sections (Mulsanne straight etc.) often missing entirely. We pick the
named-corner ways + the main "Circuit des 24 Heures du Mans" connectors,
then greedily stitch by nearest unused endpoint, filling gaps with straight
line segments where OSM data is missing.
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


def dist_m(a, b, lat0):
    ax, ay = to_m(a['lat'], a['lon'], lat0)
    bx, by = to_m(b['lat'], b['lon'], lat0)
    return math.hypot(ax - bx, ay - by)


def main():
    in_path = sys.argv[1]
    out_path = sys.argv[2]
    with open(in_path, encoding='utf-8') as f:
        data = json.load(f)

    ways = []
    for e in data['elements']:
        if e['type'] != 'way':
            continue
        name = e.get('tags', {}).get('name', '')
        if name not in KEEP_NAMES:
            continue
        g = e['geometry']
        ways.append({'id': e['id'], 'name': name, 'geom': g})

    print(f"Filtered {len(ways)} ways", file=sys.stderr)

    lat0 = sum(p['lat'] for w in ways for p in w['geom']) / sum(len(w['geom']) for w in ways)

    # Start from Tertre Rouge (well-known starting reference) so the loop ordering
    # comes out the right way.
    start = next(w for w in ways if w['name'] == 'Tertre Rouge')
    used = {start['id']}
    chain = [start]

    while True:
        cur_end = chain[-1]['geom'][-1]
        best = None
        best_d = math.inf
        for w in ways:
            if w['id'] in used:
                continue
            for ep_idx, ep in [(0, w['geom'][0]), (-1, w['geom'][-1])]:
                d = dist_m(cur_end, ep, lat0)
                if d < best_d:
                    best_d = d
                    best = (w, ep_idx == -1)  # reverse if matching the END
        if best is None:
            break
        w, reverse = best
        used.add(w['id'])
        wcopy = {**w}
        if reverse:
            wcopy['geom'] = list(reversed(w['geom']))
        chain.append(wcopy)
        print(f"  next: {w['name']!r:55} gap={best_d:6.1f}m  reverse={reverse}", file=sys.stderr)

    # Collect points, deduplicating shared endpoints
    pts = list(chain[0]['geom'])
    for w in chain[1:]:
        # Skip first point if it matches previous last (within 1m)
        last = pts[-1]
        first = w['geom'][0]
        if dist_m(last, first, lat0) < 1.0:
            pts.extend(w['geom'][1:])
        else:
            pts.extend(w['geom'])
    print(f"Total centerline points: {len(pts)}", file=sys.stderr)

    coords = [[p['lon'], p['lat']] for p in pts]
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
    print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
