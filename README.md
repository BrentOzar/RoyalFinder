# Club Royale Cruise Finder

Static, mobile-first filter page for Royal Caribbean Club Royale casino offer PDFs.

- `index.html` – the page (vanilla JS, no dependencies). Loads `cruises.json`.
- `build.py` – extracts `sources/*.pdf` into `cruises.json`. Needs `pdftotext` (`brew install poppler`).

## Monthly update

1. Drop the new index PDF (e.g. `2612C.pdf`) and every per-code PDF it lists into `sources/` (remove last month's).
2. `python3 build.py`
3. Upload `index.html` + `cruises.json` to the same folder on the web host.

New ship? `build.py` fails loudly; add it to `SHIP_CLASS`.

Filters persist in the URL, so filtered views are shareable links.
