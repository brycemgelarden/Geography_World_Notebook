"""
Build the world notebook map.

    python build_map.py                       # reads notebook.csv, writes index.html
    python build_map.py my.csv out.html       # custom input / output

notebook.csv columns: Page, Date (YYYY-MM-DD), Topic, Type
  - Type "Country" or "Territory"  -> the shape is shaded green
  - Any other Type (Chokepoint, Base, Region...) -> red pin, located via places.csv
  - Territories too small to have a shape (e.g. Gibraltar) fall back to a green pin
"""

import csv
import json
import sys
import unicodedata
from datetime import date
from pathlib import Path

import folium

ROOT = Path(__file__).parent
BORDERS = ROOT / "data" / "countries.geojson"
PLACES = ROOT / "places.csv"

DONE_COLOR = "#3a9d5d"     # green  – covered
TODO_COLOR = "#f1d36b"     # yellow – not yet
PIN_COLOR = "red"          # chokepoints and other concepts
SHAPE_TYPES = {"country", "territory"}

# "Back" button in the top-left corner. Set BACK_URL = "" to hide it.
BACK_URL = "/Pages/projects.html"
BACK_LABEL = "Back to Research / Projects"

# Common alternate spellings -> the name used in the borders file
ALIASES = {
    "usa": "United States of America", "us": "United States of America",
    "united states": "United States of America", "america": "United States of America",
    "uk": "United Kingdom", "great britain": "United Kingdom", "britain": "United Kingdom",
    "czech republic": "Czechia", "turkiye": "Turkey", "burma": "Myanmar",
    "swaziland": "eSwatini", "eswatini": "eSwatini", "ivory coast": "Ivory Coast",
    "cote d'ivoire": "Ivory Coast", "drc": "Democratic Republic of the Congo",
    "dr congo": "Democratic Republic of the Congo",
    "congo-kinshasa": "Democratic Republic of the Congo",
    "congo-brazzaville": "Republic of the Congo", "congo": "Republic of the Congo",
    "north korea": "North Korea", "dprk": "North Korea",
    "south korea": "South Korea", "rok": "South Korea", "korea": "South Korea",
    "east timor": "East Timor", "timor-leste": "East Timor",
    "vatican": "Vatican", "holy see": "Vatican", "uae": "United Arab Emirates",
    "cabo verde": "Cape Verde", "north macedonia": "North Macedonia",
    "macedonia": "North Macedonia", "taiwan": "Taiwan", "palestine": "Palestine",
    "hong kong": "Hong Kong S.A.R.", "macau": "Macao S.A.R", "macao": "Macao S.A.R",
    "serbia": "Republic of Serbia", "bahamas": "The Bahamas",
    "tanzania": "United Republic of Tanzania",
}


def norm(text):
    """Lowercase, strip accents and a leading 'the' so names match loosely."""
    text = text.replace("\u2019", "'")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.strip().lower()
    return text[4:] if text.startswith("the ") else text


def pretty_date(iso):
    try:
        d = date.fromisoformat(iso.strip())
        return d.strftime("%a, %Y-%m-%d")
    except ValueError:
        return iso.strip()


def read_notebook(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [
            {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
            for r in csv.DictReader(f)
        ]
    return [r for r in rows if r.get("topic")]


def read_places(path):
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        return {norm(r["Topic"]): (float(r["Lat"]), float(r["Lon"])) for r in csv.DictReader(f)}


def load_borders():
    """Load country shapes, trimming coordinate precision to keep the HTML small."""
    geo = json.loads(BORDERS.read_text(encoding="utf-8"))

    def trim(coords):
        if isinstance(coords[0], (int, float)):
            return [round(coords[0], 3), round(coords[1], 3)]
        return [trim(c) for c in coords]

    index = {}
    for feat in geo["features"]:
        p = feat["properties"]
        feat["geometry"]["coordinates"] = trim(feat["geometry"]["coordinates"])
        name = p["ADMIN"]
        feat["properties"] = {"name": p["NAME_LONG"] or name, "admin": name}
        for key in (name, p.get("NAME"), p.get("NAME_LONG"), p.get("NAME_EN"),
                    p.get("FORMAL_EN"), p.get("ISO_A3"), p.get("ADM0_A3")):
            if key and key != "-99":
                index.setdefault(norm(key), feat)
    return geo, index


def find_shape(topic, index):
    key = norm(topic)
    if key in ALIASES:
        key = norm(ALIASES[key])
    return index.get(key)


def entry_line(r):
    return f"Page {r.get('page', '?')} &middot; {pretty_date(r.get('date', ''))}"


def build(csv_path="notebook.csv", out_path="index.html"):
    rows = read_notebook(ROOT / csv_path)
    places = read_places(PLACES)
    geo, index = load_borders()

    # Every country starts yellow with just its name on hover
    for feat in geo["features"]:
        feat["properties"].update(status="todo", info="")

    shaded, pins, missing = {}, [], []
    for r in rows:
        kind = r.get("type", "").lower()
        topic = r["topic"]
        if kind in SHAPE_TYPES:
            feat = find_shape(topic, index)
            if feat is not None:
                shaded.setdefault(feat["properties"]["admin"], (feat, []))[1].append(r)
                continue
            # Too small to have a shape – drop a green pin instead
            if norm(topic) in places:
                pins.append((r, places[norm(topic)], "green"))
                continue
        else:
            if norm(topic) in places:
                pins.append((r, places[norm(topic)], PIN_COLOR))
                continue
        missing.append(r)

    for feat, entries in shaded.values():
        feat["properties"]["status"] = "done"
        feat["properties"]["info"] = "<br>".join(entry_line(e) for e in entries)

    # ---- map ---------------------------------------------------------------
    m = folium.Map(location=[25, 10], zoom_start=2, min_zoom=2,
                   tiles=None, world_copy_jump=True)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, GEBCO, NOAA, Garmin", name="Ocean", max_zoom=13,
    ).add_to(m)

    folium.GeoJson(
        geo,
        name="Countries",
        style_function=lambda f: {
            "fillColor": DONE_COLOR if f["properties"]["status"] == "done" else TODO_COLOR,
            "fillOpacity": 0.75 if f["properties"]["status"] == "done" else 0.45,
            "color": "#6b6b6b", "weight": 0.5,
        },
        highlight_function=lambda f: {"weight": 2, "color": "#1f2a44", "fillOpacity": 0.9},
        tooltip=folium.GeoJsonTooltip(fields=["name", "info"], labels=False, sticky=True),
    ).add_to(m)

    pin_layer = folium.FeatureGroup(name="Chokepoints & other topics").add_to(m)
    for r, (lat, lon), color in pins:
        label = (f"<b>{r['topic']}</b><br>{r.get('type', '')}<br>{entry_line(r)}")
        folium.Marker(
            [lat, lon],
            tooltip=label,
            icon=folium.Icon(color=color, icon="anchor" if color == PIN_COLOR else "flag",
                             prefix="fa"),
        ).add_to(pin_layer)

    folium.LayerControl(collapsed=True).add_to(m)

    # Legend / tally box
    pages = len(rows)
    last = max((r.get("date", "") for r in rows), default="")
    legend = f"""
    <div style="position:fixed;bottom:24px;left:16px;z-index:9999;background:#fff;
         padding:10px 14px;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.25);
         font:13px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#1f2a44">
      <div style="font-weight:600;font-size:14px;margin-bottom:4px">World Notebook</div>
      <div><span style="display:inline-block;width:12px;height:12px;background:{DONE_COLOR};
           border-radius:2px;margin-right:6px"></span>Covered ({len(shaded)})</div>
      <div><span style="display:inline-block;width:12px;height:12px;background:{TODO_COLOR};
           border-radius:2px;margin-right:6px"></span>Not yet</div>
      <div><span style="display:inline-block;width:12px;height:12px;background:#d33d29;
           border-radius:50%;margin-right:6px"></span>Chokepoints &amp; concepts
           ({sum(1 for p in pins if p[2] == PIN_COLOR)})</div>
      <div style="margin-top:6px;color:#666">{pages} pages &middot; last entry {pretty_date(last)}</div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend))
    m.get_root().header.add_child(folium.Element("<title>World Notebook</title>"))

    if BACK_URL:
        back = f"""
        <a href="{BACK_URL}" style="position:fixed;top:12px;left:56px;z-index:9999;
           background:#1f2a44;color:#fff;text-decoration:none;padding:14px 28px;
           border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.3);
           font:600 24px -apple-system,Segoe UI,Helvetica,Arial,sans-serif">&larr; {BACK_LABEL}</a>"""
        m.get_root().html.add_child(folium.Element(back))

    m.save(ROOT / out_path)

    print(f"Wrote {out_path}: {len(shaded)} shaded, {len(pins)} pins, {pages} pages.")
    for r in missing:
        print(f"  ! Not placed: page {r.get('page')} '{r['topic']}' ({r.get('type')}). "
              f"Add it to places.csv with Lat,Lon (or check the spelling).")


if __name__ == "__main__":
    build(*sys.argv[1:3])