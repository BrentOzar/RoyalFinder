#!/usr/bin/env python3
"""Extract Club Royale offer PDFs into cruises.json for index.html.

Usage: python3 build.py [sources_dir]
Needs `pdftotext` (poppler). Reads the index PDF (e.g. 2611C.pdf) for the
points per offer code, then every <code>.pdf it lists.
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


def main():
    index = [p for p in glob.glob(os.path.join(SRC, "*.pdf"))
             if re.fullmatch(r"\d{4}C", os.path.basename(p)[:-4])]
    if len(index) != 1:
        sys.exit(f"Expected one index PDF like 2611C.pdf in {SRC}, found {index}")
    idx = text(index[0])
    codes = re.findall(r"\b(\d{4}C\w+)\b", idx)
    pts = [int(p.replace(",", "")) for p in re.findall(r"([\d,]+) Points", idx)]
    if not codes or len(codes) != len(pts):
        sys.exit(f"Index PDF: {len(codes)} codes vs {len(pts)} point values")
    points = dict(zip(codes, pts))

    ships, ports, rooms = [], [], []
    def ix(lst, v):
        if v not in lst: lst.append(v)
        return lst.index(v)

    sailings = {}
    offers = []
    for code in sorted(points, key=lambda c: -points[c]):
        path = os.path.join(SRC, code + ".pdf")
        if not os.path.exists(path):
            sys.exit(f"Missing {path}")
        t = text(path)
        fees = re.search(r"JUST PAY BETWEEN (\$[\d.,]+) AND (\$[\d.,]+)", t)
        offers.append({"code": code, "points": points[code],
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

    missing = [s for s in ships if s.split(" Of ")[0] not in CLASS_OF]
    if missing:
        sys.exit(f"Unknown ship class for: {missing} - add to SHIP_CLASS")

    out = {
        "generated": datetime.date.today().isoformat(),
        "source": os.path.basename(index[0]),
        "offers": offers,
        "ships": [{"name": s, "cls": CLASS_OF[s.split(" Of ")[0]]} for s in ships],
        "ports": ports,
        "rooms": [{"name": r, "cat": room_category(r), "gty": r.endswith("GTY")} for r in rooms],
        "sailings": sorted(sailings.values(), key=lambda s: (s["d"], ships[s["s"]])),
    }
    for s in out["sailings"]:
        s["o"].sort(key=lambda o: -offers[o[0]]["points"])
    with open(OUT, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print(f"{len(out['sailings'])} sailings, {sum(len(s['o']) for s in out['sailings'])} offers -> {OUT}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
