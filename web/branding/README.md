# Racing app identity

The authored `racing-icon.svg` is a red open-wheel racing car on an ivory game
tile, with a gold vector trail, chequered flag and green background. It shares
Mahjong’s game-tile visual language but uses racing-specific artwork.

The build generates opaque RGB PNG icons at 16, 32, 152, 167, 180, 192 and 512
pixels, an ICO with 16/32/48 entries, and a separate maskable 512 icon. The full
artwork fits inside the maskable icon’s safe circle. iOS supplies its own corner
mask; the source has a full-bleed opaque background.

```sh
python3 -m pip install -r web/requirements-icons.txt
python3 web/scripts/export_icons.py
```

Unlike Mahjong’s committed raster exports, this small static app generates the
raster assets during the build from one editable vector source. Neither the
Python renderer nor its dependencies are downloaded by players.

HTML explicitly links Apple 152/167/180 PNGs, classic PNG/ICO tab icons, Apple
standalone/title/status-bar metadata and the web manifest. All URLs are relative
to this project, not the shared github.io root. The manifest ID is explicitly
`/TheoreticalRacing/`, distinct from `/mahjong/` and the other apps. Distinct Racing-specific physical filenames with a revision, not only query
strings, avoid reusing previous icon requests. An existing Home Screen shortcut may need
to be removed and re-added on the device to refresh its cached icon.

The build records source/export SHA-256 hashes. CI validates PNG integrity,
dimensions and opacity, ICO resolutions, head/manifest declarations, actual
image decoding and HTTP paths on the deployed site.
