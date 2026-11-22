# Club Royale Cruise Finder

Static, mobile-first filter page for Royal Caribbean Club Royale casino offer PDFs.

- `index.html` – the page (vanilla JS, no dependencies). Loads `cruises.json`.
- `build.py` – extracts `sources/*.pdf` into `cruises.json`. Needs `pdftotext` (`brew install poppler`).

## Offer sets

The certificate you're offered depends on the cruise you earn it on: the month you sail and its length (1–5 vs 6+ nights). Each combination is its own offer set: tier PDFs named `<set><tier>.pdf`, where the set is `YYMM` + one letter (e.g. `2612A01.pdf` … `2612A10.pdf`). So far Royal uses **A = current cruise under 6 nights, C = 6+ nights**. The overview PDF (`2612A.pdf`) is optional: if present it supplies the points per tier, otherwise `build.py` uses its `TIER_POINTS` table. The page opens with a "Which cruise are you on?" banner that picks the set.

`sources/sets.json` says which cruise length each set covers (the PDFs don't say):

```json
{ "2611C": {"nights": "6+"}, "2611A": {"nights": "1-5"} }
```

A set missing from `sets.json` is treated as "any length" and the build prints a warning.

## Update

1. Drop each set's tier PDFs (and overview PDF, if you have it) into `sources/` (remove expired months), and add each set to `sources/sets.json`.
2. `python3 build.py`
3. Upload `index.html` + `cruises.json` to the same folder on the web host.

New ship? `build.py` fails loudly; add it to `SHIP_CLASS`.

Filters persist in the URL, so filtered views are shareable links.
