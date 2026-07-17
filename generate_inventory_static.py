#!/usr/bin/env python3
"""Generate inventory-static.html from inventory.json.

WRITES TO : inventory-static.html (this repo only — never pricing data)
TRIGGER   : run by price_compare_server.py /api/commit before each inventory
            git commit, or manually: python3 generate_inventory_static.py
DOES NOT TOUCH: inventory.json, index.html, master.db, MASTERPRICE.xlsx

Purpose: the main site injects inventory client-side from inventory.json,
which is invisible to non-JS crawlers (GPTBot, ClaudeBot, PerplexityBot,
common-crawl). This bakes the same data into plain HTML + schema.org
Product JSON-LD so AI crawlers can see what's actually in stock.
"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
INVENTORY = os.path.join(HERE, "inventory.json")
OUT = os.path.join(HERE, "inventory-static.html")
SITE = "https://mauipowerequipment.com"


def build():
    with open(INVENTORY, encoding="utf-8") as f:
        items = json.load(f)

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
        sold = (it.get("status") or "").lower() == "sold"
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
                "availability": "https://schema.org/SoldOut" if sold
                                else "https://schema.org/InStock",
                "seller": {"@type": "Store", "name": "Maui Power Equipment",
                           "url": SITE},
            },
        }
        products.append({k: v for k, v in p.items() if v is not None})

        status = " — SOLD" if sold else " — in stock now"
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
            f" — {html.escape(tagline)}{status}"
            f"{(' · ' + bits) if bits else ''}</li>"
        )

    ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Maui Power Equipment — Current Floor Inventory",
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
<title>Current Inventory — Maui Power Equipment | Wailuku, HI</title>
<meta name="description" content="Outdoor power equipment in stock now at Maui Power Equipment, 970 Lower Main St, Wailuku, Maui. STIHL, Honda, SCAG, Wright, Hustler mowers, chainsaws, generators, and trailers.">
<link rel="canonical" href="{SITE}/inventory-static.html">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script type="application/ld+json">
{json.dumps(ld, indent=1)}
</script>
<style>body{{font-family:system-ui,sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;line-height:1.6}}li{{margin:.4rem 0}}</style>
</head>
<body>
<h1>Maui Power Equipment — Current Floor Inventory</h1>
<p>Locally owned outdoor power equipment dealer at 970 Lower Main St, Wailuku, HI 96793 — (808) 249-2730.
Sales, service, and parts. Walk-in service, no appointment needed.
This list updates whenever the showroom floor changes; see the
<a href="{SITE}/">main site</a> for photos and details.</p>
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
