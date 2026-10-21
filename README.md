# World Notebook

An interactive map that tracks my daily geography notebook pages. Countries I've covered are shaded green, the rest yellow, and chokepoints or other concepts show as red anchor pins. Hover over anything to see its name, plus the page number and date if I've written it up.

## Daily routine

1. Add a row to `notebook.csv`:

   ```
   Page,Date,Topic,Type
   5,2026-10-21,Portugal,Country
   ```

2. Rebuild the map:

   ```
   python build_map.py
   ```

3. Open `index.html` (or commit and push if it's hosted on GitHub Pages).

The script prints a warning for any row it couldn't place on the map.

## How rows are placed

| Type | Shown as |
| --- | --- |
| `Country` or `Territory` | Shape shaded green |
| `Territory` too small for a shape (Gibraltar, Ceuta, Melilla) | Green flag pin, located from `places.csv` |
| Anything else (`Chokepoint`, `Base`, `Region`...) | Red anchor pin, located from `places.csv` |

Names match loosely: case, accents and a leading "The" are ignored, and common alternates work (USA, UK, Burma, Türkiye, DRC, and so on).

## Adding a new place

If a chokepoint or concept isn't in `places.csv` yet, add one line with its coordinates:

```
Topic,Lat,Lon
Strait of Messina,38.25,15.63
```

`places.csv` already includes the major maritime chokepoints (Hormuz, Bab-el-Mandeb, Malacca, Suez, Panama, the Turkish and Danish Straits, GIUK Gap and more).

## Files

- `notebook.csv` — my page log (the only file I edit daily)
- `places.csv` — coordinates for pins
- `build_map.py` — reads the CSV, writes `index.html`
- `data/countries.geojson` — country borders from [Natural Earth](https://www.naturalearthdata.com/) (public domain)
- `index.html` — the generated map

## Setup

```
pip install -r requirements.txt
```

The country shapes and pins are embedded in `index.html`; the ocean background and map libraries load from the internet.
