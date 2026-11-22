#!/usr/bin/env python3
"""Extract Club Royale offer PDFs into cruises.json for index.html.

Usage: python3 build.py [sources_dir]
Needs `pdftotext` (poppler).

The certificate you're offered depends on the cruise you're on (month and
length), so sources/ can hold several offer sets. A set is the tier PDFs named
<set><tier>.pdf, e.g. 2611C01.pdf ... 2611C10.pdf, 2611CVIP1.pdf, where the set
code is YYMM + one letter. The optional index PDF (2611C.pdf) supplies points
per tier; without it, points come from TIER_POINTS. The month comes from the
code; the cruise length comes from sources/sets.json, e.g.
  {"2611A": {"nights": "1-5"}, "2611C": {"nights": "6+"}}
(Royal's letters so far: A = current cruise under 6 nights, C = 6+ nights.)
A set missing from sets.json gets nights = null (shown as "any length").
"""
import glob, json, os, re, subprocess, sys, datetime

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "sources")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cruises.json")

SHIP_CLASS = {
    "Icon": ["Icon", "Star", "Legend"],
    "Oasis": ["Oasis", "Allure", "Harmony", "Symphony", "Wonder", "Utopia"],
    "Quantum": ["Quantum", "Anthem", "Ovation", "Spectrum", "Odyssey"],
    "Freedom": ["Freedom", "Liberty", "Independence"],
    "Voyager": ["Voyager", "Explorer", "Adventure", "Navigator", "Mariner"],
    "Radiance": ["Radiance", "Brilliance", "Serenade", "Jewel"],
    "Vision": ["Grandeur", "Rhapsody", "Enchantment", "Vision"],
}
CLASS_OF = {s: c for c, ships in SHIP_CLASS.items() for s in ships}


def text(path):
    return subprocess.run(["pdftotext", "-layout", path, "-"], check=True,
                          capture_output=True, text=True).stdout


def room_category(room):
    r = room.lower()
    if "interior" in r: return "Interior"
    if "balcony" in r: return "Balcony"
    if "ocean view" in r and "suite" not in r: return "Ocean View"
    return "Suite"


def clean_itin(s):
    s = re.sub(r"^(\d+)\s*n\b", r"\1 Night", s.strip())
    s = re.sub(r"Transatlanigh\w*", "Transatlantic", s)
    return s


ONE_WAY_WORDS = re.compile(r"Transatlantic|Transpacific|Reposition|Northbound|Southbound|Pacific Coastal|\bTo\b")


def mark_one_way(sailings):
    """Flag sailings that end somewhere other than where they start.

    The PDFs only give a departure port, so: if the same ship's next listed
    sailing departs from a different port the day this one ends (or a day
    early, for date-line crossings), this sailing ends there. Otherwise fall
    back to itinerary keywords (Transatlantic, "Miami To Cape Liberty", ...),
    where the end port is unknown. Sets s["e"] = end port index, or -1 if
    one-way with unknown end. Absent = round trip (or no evidence otherwise).
    """
    by_ship = {}
    for s in sailings.values():
        by_ship.setdefault(s["s"], []).append(s)
    for lst in by_ship.values():
        lst.sort(key=lambda s: s["d"])
        for a, b in zip(lst, lst[1:]):
            gap = (datetime.date.fromisoformat(b["d"]) - datetime.date.fromisoformat(a["d"])).days - a["n"]
            if gap in (-1, 0) and b["p"] != a["p"]:
                a["e"] = b["p"]
    for s in sailings.values():
        if "e" not in s and ONE_WAY_WORDS.search(s["i"]):
            s["e"] = -1


NIGHTS = {None, "1-5", "6+"}
TIER_FILE = re.compile(r"(\d{4}[A-Z])(\d\d[A-Z]?|VIP\d+)")
# Points per tier suffix, as published in the Nov/Dec 2026 offer tables and 2611C.pdf.
TIER_POINTS = {"VIP1": 70000, "VIP2": 40000, "01": 25000, "02": 15000, "02A": 9000, "03": 6500,
               "03A": 4000, "04": 3000, "05": 2000, "06": 1500, "07": 1200, "08": 800,
               "09": 600, "10": 400}


def main():
    tier_files = {}
    for p in glob.glob(os.path.join(SRC, "*.pdf")):
        m = TIER_FILE.fullmatch(os.path.basename(p)[:-4])
        if m: tier_files.setdefault(m.group(1), []).append(m.group(2))
    set_codes = sorted(tier_files)
    if not set_codes:
        sys.exit(f"No tier PDFs like 2611C01.pdf in {SRC}")
    cfg_path = os.path.join(SRC, "sets.json")
    cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
    for sc in sorted(set(cfg) - set(set_codes)):
        print(f"NOTE: {sc} is in sets.json but has no PDFs in {SRC}; skipped", file=sys.stderr)

    ships, ports, rooms = [], [], []
    def ix(lst, v):
        if v not in lst: lst.append(v)
        return lst.index(v)

    sets = []
    for sc in set_codes:
        nights = cfg.get(sc, {}).get("nights")
        if nights not in NIGHTS:
            sys.exit(f"sets.json: {sc} nights must be one of {NIGHTS}, got {nights!r}")
        if nights is None:
            print(f"WARNING: {sc} has no nights in sets.json; shown as any cruise length", file=sys.stderr)
        print(f"== {sc}", file=sys.stderr)
        offers, sailings = build_set(sc, tier_files[sc], ships, ports, rooms, ix)
        sets.append({"code": sc, "source": sc + ".pdf", "month": f"20{sc[:2]}-{sc[2:4]}", "nights": nights,
                     "offers": offers,
                     "sailings": sorted(sailings.values(), key=lambda s: (s["d"], ships[s["s"]]))})

    missing = [s for s in ships if s.split(" Of ")[0] not in CLASS_OF]
    if missing:
        sys.exit(f"Unknown ship class for: {missing} - add to SHIP_CLASS")

    out = {
        "generated": datetime.date.today().isoformat(),
        "ships": [{"name": s, "cls": CLASS_OF[s.split(" Of ")[0]]} for s in ships],
        "ports": ports,
        "rooms": [{"name": r, "cat": room_category(r), "gty": r.endswith("GTY")} for r in rooms],
        "sets": sorted(sets, key=lambda x: (x["month"], x["nights"] or "", x["code"])),
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print(f"{len(sets)} offer set(s) -> {OUT}", file=sys.stderr)


def build_set(sc, tiers, ships, ports, rooms, ix):
    index = os.path.join(SRC, sc + ".pdf")
    if os.path.exists(index):
        idx = text(index)
        codes = re.findall(rf"\b({re.escape(sc)}\w+)\b", idx)
        pts = [int(p.replace(",", "")) for p in re.findall(r"([\d,]+) Points", idx)]
        if not codes or len(codes) != len(pts):
            sys.exit(f"{sc}.pdf: {len(codes)} codes vs {len(pts)} point values")
        points = dict(zip(codes, pts))
        extra = sorted(set(sc + t for t in tiers) - set(points))
        if extra:
            sys.exit(f"{sc}.pdf doesn't list {extra}")
    else:
        unknown = [t for t in tiers if t not in TIER_POINTS]
        if unknown:
            sys.exit(f"No {sc}.pdf and no default points for tiers {unknown}; add them to TIER_POINTS")
        points = {sc + t: TIER_POINTS[t] for t in tiers}

    sailings = {}
    offers = []
    for code in sorted(points, key=lambda c: -points[c]):
        path = os.path.join(SRC, code + ".pdf")
        if not os.path.exists(path):
            sys.exit(f"Missing {path}")
        t = text(path)
        fees = re.search(r"JUST PAY BETWEEN (\$[\d.,]+) AND (\$[\d.,]+)", t)
        offers.append({"code": code, "tier": code[len(sc):], "points": points[code],
                       "fees": [fees.group(1), fees.group(2)] if fees else None})
        oi = len(offers) - 1
        n = 0
        for line in t.splitlines():
            if not re.match(rf"\s*{code}\s", line): continue
            f = re.split(r"\s{2,}", line.strip())
            if len(f) not in (8, 9) or f[0] != code:
                sys.exit(f"Unparseable row in {code}: {f}")
            _, ship, port, date, itin, room, otype, *rest = f
            bonus, obc = (rest if len(rest) == 2 else [None, rest[0]])
            ship = ship.replace("®", "").strip()
            iso = datetime.datetime.strptime(date, "%B %d, %Y").date().isoformat()
            itin = clean_itin(itin)
            nights = int(re.match(r"(\d+)", itin).group(1))
            key = (ship, iso)
            s = sailings.setdefault(key, {
                "s": ix(ships, ship), "d": iso, "p": ix(ports, port),
                "n": nights, "i": itin, "o": []})
            s["o"].append([oi, ix(rooms, room), 2 if "2" in otype else 1,
                           int(bonus.split()[0].strip("$").replace(",", "")) if bonus else 0,
                           int(obc.strip("$").replace(",", ""))])
            n += 1
        if n == 0:
            sys.exit(f"No rows parsed from {code}")
        offers[oi]["rows"] = n
        print(f"{code:>12} {points[code]:>7,} pts  {n:>5} rows", file=sys.stderr)

    mark_one_way(sailings)
    for s in sailings.values():
        s["o"].sort(key=lambda o: -offers[o[0]]["points"])
    ow = [s for s in sailings.values() if "e" in s]
    print(f"{len(sailings)} sailings, {len(ow)} one-way ({sum(1 for s in ow if s['e'] < 0)} with unknown end port)",
          file=sys.stderr)
    return offers, sailings


if __name__ == "__main__":
    main()
