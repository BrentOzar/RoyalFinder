# Club Royale Cruise Finder

Static, mobile-first filter page for Royal Caribbean Club Royale casino offer PDFs.

- `index.html` – the page (vanilla JS, no dependencies). Loads `cruises.json`.
- `build.py` – extracts `sources/*.pdf` into `cruises.json`. Needs `pdftotext` (`brew install poppler`).

## Offer sets

The certificate you're offered depends on the cruise you earn it on: the month you sail and its length (1–5 vs 6+ nights). Each combination is its own offer set: an index PDF named `YYMM<letters>.pdf` (e.g. `2612A.pdf`) plus the tier PDFs it lists (`2612A01.pdf` …). The page opens with a "Which cruise are you on?" banner that picks the set.

`sources/sets.json` says which cruise length each set covers (the PDFs don't say):

```json
{ "2611C": {"nights": "6+"}, "2611A": {"nights": "1-5"} }
```

A set missing from `sets.json` is treated as "any length" and the build prints a warning.

## Update

1. Drop each index PDF and all of its tier PDFs into `sources/` (remove expired months), and add each set to `sources/sets.json`.
2. `python3 build.py`
3. Upload `index.html` + `cruises.json` to the same folder on the web host.

New ship? `build.py` fails loudly; add it to `SHIP_CLASS`.

Filters persist in the URL, so filtered views are shareable links.
