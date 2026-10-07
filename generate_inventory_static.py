#!/usr/bin/env python3
"""Generate inventory-static.html from catalog.json + inventory.json (same items as the homepage gallery).

WRITES TO : inventory-static.html (this repo only — never pricing data)
TRIGGER   : run by price_compare_server.py /api/commit before each inventory
            git commit, or manually: python3 generate_inventory_static.py
            and by generate_catalog.py after a catalog change
Stock/sold status is never published; trailers are hidden (matches index.html).
DOES NOT TOUCH: inventory.json, catalog.json, index.html, master.db, MASTERPRICE.xlsx

Purpose: the main site injects inventory client-side from inventory.json,
which is invisible to non-JS crawlers (GPTBot, ClaudeBot, PerplexityBot,
common-crawl). This bakes the same data into plain HTML + schema.org
Product JSON-LD so AI crawlers can see what's actually in stock.
"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "catalog.json")
INVENTORY = os.path.join(HERE, "inventory.json")
OUT = os.path.join(HERE, "inventory-static.html")
SITE = "https://mauipowerequipment.com"


def build():
    with open(CATALOG, encoding="utf-8") as f:
        items = [c for c in json.load(f) if not c.get("hidden")]
    with open(INVENTORY, encoding="utf-8") as f:
        floor = [x for x in json.load(f) if "trailer" not in (x.get("type") or "").lower()]
    key = lambda x: f"{x.get('make') or ''} {x.get('model') or ''}".strip().lower()
    seen = {key(c) for c in items} | {c.get("info") for c in items if c.get("info")}
    items += [x for x in floor if key(x) not in seen and x.get("info") not in seen]  # same product as a lineup card = one entry, like the homepage

    products = []
    rows = []
    for it in items:
        make = (it.get("make") or "").strip()
        model = (it.get("model") or "").strip()
        if not (make or model):
            continue
        name = f"{make} {model}".strip()
        tagline = (it.get("tagline") or "").strip()
        itype = (it.get("type") or "").strip()
        photo = (it.get("photo") or "").strip()
        img = None
        if photo and os.path.exists(os.path.join(HERE, "assets", "inventory", photo)):
            img = f"{SITE}/assets/inventory/{photo}"

        p = {
            "@type": "Product",
            "name": name,
            "description": tagline or itype,
            "brand": {"@type": "Brand", "name": make} if make else None,
            "category": itype or None,
            "image": img,
            "offers": {
                "@type": "Offer",
                "seller": {"@type": "Store", "name": "Maui Power Equipment",
                           "url": SITE},
            },
        }
        products.append({k: v for k, v in p.items() if v is not None})

        stat_strs = []
        for s in (it.get("stats") or []):
            if isinstance(s, dict):
                lab, val = (s.get("label") or "").strip(), (s.get("value") or "").strip()
                if lab and val:
                    stat_strs.append(f"{lab}: {val}")
            elif isinstance(s, str) and s.strip():
                stat_strs.append(s.strip())
        bits = " · ".join(html.escape(b) for b in stat_strs)
        rows.append(
            f"<li><strong>{html.escape(name)}</strong>"
            f"{(' (' + html.escape(itype) + ')') if itype else ''}"
            f"{(' — ' + html.escape(tagline)) if tagline else ''}"
            f"{(' · ' + bits) if bits else ''}</li>"
        )

    ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Equipment at Maui Power Equipment",
        "url": f"{SITE}/inventory-static.html",
        "numberOfItems": len(products),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "item": p}
            for i, p in enumerate(products)
        ],
    }

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Equipment We Carry — Maui Power Equipment | Wailuku, HI</title>
<meta name="description" content="Outdoor power equipment carried at Maui Power Equipment, 970 Lower Main St, Wailuku, Maui. STIHL, Honda, SCAG, Wright, ECHO, Hustler mowers, chainsaws, trimmers, blowers, generators, and pumps.">
<link rel="canonical" href="{SITE}/inventory-static.html">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script type="application/ld+json">
{json.dumps(ld, indent=1)}
</script>
<style>body{{font-family:system-ui,sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;line-height:1.6}}li{{margin:.4rem 0}}</style>
</head>
<body>
<h1>Equipment We Carry — Maui Power Equipment</h1>
<p>Locally owned outdoor power equipment dealer at 970 Lower Main St, Wailuku, HI 96793 — (808) 249-2730.
Sales, service, and parts. Walk-in service, no appointment needed.
Call to check availability. See the <a href="{SITE}/#stock">main site</a> for photos and details.</p>
<ul>
{chr(10).join(rows)}
</ul>
<p>Don't see what you're looking for? We can order it — call or text (808) 249-2730.</p>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    return len(products)


if __name__ == "__main__":
    n = build()
    print(f"inventory-static.html written ({n} items)")
