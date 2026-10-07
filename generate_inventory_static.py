#!/usr/bin/env python3
"""Generate inventory-static.html from catalog.json + inventory.json (same items as the homepage gallery).

WRITES TO : inventory-static.html (this repo only — never pricing data)
TRIGGER   : run by price_compare_server.py /api/commit before each inventory
            git commit, or manually: python3 generate_inventory_static.py
            and by generate_catalog.py after a catalog change
Stock/sold status is never published; trailers are hidden (matches index.html).
DOES NOT TOUCH: inventory.json, catalog.json, index.html, master.db, MASTERPRICE.xlsx

Purpose: the homepage gallery is rendered by JavaScript. This is a standalone,
search-landing page with the same items as plain HTML (grouped by category,
styled like the site) so Google and AI crawlers can read and link to it.
"""
import html
import json
import os
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "catalog.json")
INVENTORY = os.path.join(HERE, "inventory.json")
OUT = os.path.join(HERE, "inventory-static.html")
SUBDIR = "equipment"   # brand + category landing pages: equipment/<slug>.html
SITE = "https://mauipowerequipment.com"

# Same categories, labels and order as the homepage filters (index.html FILTERS / cat()).
CATS = [("zt", "Zero-Turn Mowers"), ("mower", "Lawn Mowers"), ("chainsaw", "Chainsaws"),
        ("trimmer", "String Trimmers & Weedeaters"), ("blower", "Leaf Blowers"),
        ("hedge", "Hedge Trimmers & Pole Saws"), ("multi", "Multi-Task Tools"),
        ("generator", "Generators"), ("pump", "Water Pumps & Sprayers"),
        ("battery", "Batteries & Chargers"), ("other", "More Equipment")]
SLUG = {"zt": "zero-turn-mowers", "mower": "lawn-mowers", "chainsaw": "chainsaws", "trimmer": "string-trimmers",
        "blower": "leaf-blowers", "hedge": "hedge-trimmers-pole-saws", "multi": "multi-task-tools",
        "generator": "generators", "pump": "water-pumps-sprayers", "battery": "batteries-chargers"}
# Brand pages only for dealer brands with enough models to be a useful page.
BRANDS = [("STIHL", "stihl"), ("Honda", "honda"), ("SCAG", "scag"), ("Maruyama", "maruyama"),
          ("ECHO", "echo"), ("Shindaiwa", "shindaiwa")]
SAMPLE = ("This is a sample of what we carry, not the full list. We often have other models in the shop "
          "and can order most others, so call to check on anything you don't see.")


def cat(t):
    t = (t or "").lower()
    for word, c in (("trailer", "trailer"), ("zero turn", "zt"), ("mower", "mower"), ("chainsaw", "chainsaw"),
                    ("weedeater", "trimmer"), ("trimmer", "trimmer"), ("brushcutter", "trimmer"),
                    ("blower", "blower"), ("generator", "generator"), ("sprayer", "pump"), ("pump", "pump")):
        if word in t:
            return c
    return "other"


def load():
    with open(CATALOG, encoding="utf-8") as f:
        items = [c for c in json.load(f) if not c.get("hidden")]
    with open(INVENTORY, encoding="utf-8") as f:
        floor = [x for x in json.load(f) if cat(x.get("type")) != "trailer" and x.get("photo")]
    key = lambda x: f"{x.get('make') or ''} {x.get('model') or ''}".strip().lower()
    seen = {key(c) for c in items} | {c.get("info") for c in items if c.get("info")}
    for x in floor:  # same product as a lineup card = one entry, like the homepage
        if key(x) not in seen and x.get("info") not in seen:
            seen.add(key(x))
            items.append(x)
    return [it for it in items if key(it)]


def and_list(xs):
    return xs[0] if len(xs) < 2 else ", ".join(xs[:-1]) + " and " + xs[-1]


def e(s):
    return html.escape(str(s or "").strip(), quote=True)


def catof(it):
    return it.get("cat") or cat(it.get("type"))


def page(items, path, title, desc, h1, intro):
    """Render one landing page of items grouped by category; returns item count."""
    groups = {c: [] for c, _ in CATS}
    for it in items:
        groups.get(catof(it), groups["other"]).append(it)

    ld_items, sections = [], []
    for c, label in CATS:
        if not groups[c]:
            continue
        cards = []
        for it in groups[c]:
            name = f"{(it.get('make') or '').strip()} {(it.get('model') or '').strip()}".strip()
            photo = (it.get("photo") or "").strip()
            src = f"/assets/inventory/{quote(photo)}" if photo and os.path.exists(
                os.path.join(HERE, "assets", "inventory", photo)) else ""
            info = (it.get("info") or "").strip() if str(it.get("info") or "").startswith("http") else ""
            ld = {"@type": "ListItem", "position": len(ld_items) + 1, "name": name}
            if src:
                ld["image"] = f"{SITE}{src}"
            if info:
                ld["url"] = info
            ld_items.append(ld)
            img = f'<img loading="lazy" src="{src}" alt="{e(name)}">' if src else ""
            more = f'<a class="info" href="{e(info)}" rel="noopener" target="_blank">Specs ›</a>' if info else ""
            tag = f'<p class="tag">{e(it.get("tagline"))}</p>' if it.get("tagline") else ""
            cards.append(f'<li class="card"><div class="ph">{img}</div><div class="cb">'
                         f'<div class="k">{e(it.get("make"))}</div><h3>{e(it.get("model"))}</h3>{tag}{more}</div></li>')
        sections.append(f'<section id="{c}"><h2>{e(label)} <span>{len(cards)}</span></h2>'
                        f'<ul class="grid">{"".join(cards)}</ul></section>')

    here = f"/{path}"
    pill = lambda href, label: f'<a href="{href}"{" aria-current=\"page\"" if href == here else ""}>{e(label)}</a>'
    jump = (pill("/inventory-static.html", "All equipment")
            + "".join(pill(f"/{SUBDIR}/{SLUG[c]}.html", l) for c, l in CATS if c in SLUG)
            + "".join(pill(f"/{SUBDIR}/{s}.html", b) for b, s in BRANDS))
    ld = {"@context": "https://schema.org", "@type": "ItemList",
          "name": h1 + " — Maui Power Equipment, Wailuku, Maui",
          "url": f"{SITE}/{path}", "numberOfItems": len(ld_items),
          "itemListElement": ld_items}

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{SITE}/{path}">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/logos/favicon.png">
<meta property="og:title" content="{e(title)}">
<meta property="og:image" content="{SITE}/assets/og-image.jpg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@600&family=Inter:wght@400;500;600&family=Barlow+Semi+Condensed:wght@700;800&display=swap" rel="stylesheet">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False)}
</script>
<style>
:root{{--paper:#f7f4ee;--ink:#1d2722;--muted:#6a736d;--green:#2f4339;--green-dark:#202d27;--gold:#FFAD00;--gold-deep:#D99300;--line:#e6e1d6}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;color:var(--ink);background:var(--paper);line-height:1.55;-webkit-font-smoothing:antialiased}}
a{{color:inherit;text-decoration:none}}
.wrap{{max-width:1200px;margin:0 auto;padding:0 clamp(16px,5vw,56px)}}
header{{background:linear-gradient(rgba(32,45,39,.93),rgba(32,45,39,.96)),url('/assets/lauhala.jpg') center/cover;color:#fff;padding:18px 0 34px}}
.top{{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:13px;color:#d7ddd4}}
.top img{{height:40px;width:auto}}
.top a:hover{{color:var(--gold)}}
h1{{font-family:'Barlow Semi Condensed',sans-serif;font-weight:800;text-transform:uppercase;font-size:clamp(34px,6vw,60px);line-height:1;margin:26px 0 10px}}
.lead{{max-width:680px;color:#d7ddd4}}
.cta{{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}}
.btn{{font-family:'Oswald',sans-serif;font-weight:600;font-size:14px;letter-spacing:1.2px;text-transform:uppercase;padding:12px 22px;border-radius:999px;background:var(--gold);color:var(--ink)}}
.btn:hover{{background:var(--gold-deep)}}
.btn.ghost{{background:transparent;color:#fff;border:1.5px solid rgba(255,255,255,.35)}}
nav{{position:sticky;top:0;z-index:5;background:var(--paper);border-bottom:1px solid var(--line)}}
nav .wrap{{display:flex;gap:8px;overflow-x:auto;padding-top:10px;padding-bottom:10px}}
nav a{{flex:none;font-family:'Oswald',sans-serif;font-weight:600;font-size:12.5px;letter-spacing:1px;text-transform:uppercase;padding:7px 14px;border-radius:999px;border:1px solid var(--line);background:#fff}}
nav a:hover,nav a[aria-current]{{border-color:var(--green)}}
nav a[aria-current]{{background:var(--green);color:#fff}}
section{{padding:34px 0 8px;scroll-margin-top:60px}}
h2{{font-family:'Barlow Semi Condensed',sans-serif;font-weight:800;text-transform:uppercase;font-size:28px;margin-bottom:14px}}
h2 span{{font-family:'Inter';font-weight:500;font-size:14px;color:var(--muted)}}
.grid{{list-style:none;display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:14px}}
.card{{background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}}
.ph{{height:170px;display:flex;align-items:center;justify-content:center}}
.ph img{{width:100%;height:100%;object-fit:contain;padding:12px}}
.cb{{padding:10px 12px 12px;border-top:1px solid var(--line);flex:1;display:flex;flex-direction:column}}
.k{{font-family:'Oswald',sans-serif;font-weight:600;font-size:12px;letter-spacing:1.4px;text-transform:uppercase;color:var(--green)}}
h3{{font-family:'Barlow Semi Condensed',sans-serif;font-weight:700;text-transform:uppercase;font-size:18px;line-height:1.1;margin:1px 0 4px}}
.tag{{font-size:13px;color:var(--muted);flex:1}}
.info{{font-size:12.5px;font-weight:600;color:var(--gold-deep);margin-top:6px}}
.order{{margin:34px 0 0;padding:22px;border-radius:14px;background:#fff;border:1px solid var(--line)}}
.order h2{{font-size:22px;margin-bottom:6px}}
footer{{background:var(--green-dark);color:rgba(255,255,255,.82);font-size:13px;margin-top:40px;padding:26px 0}}
footer .wrap{{display:flex;flex-wrap:wrap;justify-content:space-between;gap:16px}}
footer a:hover{{color:var(--gold)}}
@media(max-width:520px){{.grid{{grid-template-columns:1fr 1fr;gap:10px}}.ph{{height:130px}}h3{{font-size:16px}}.top .addr{{display:none}}}}
</style>
</head>
<body>
<header><div class="wrap">
  <div class="top"><a href="{SITE}/"><img src="/assets/logos/mpe-hero.png" alt="Maui Power Equipment home"></a>
    <span class="addr">970 Lower Main St, Wailuku · <a href="tel:8082492730">(808) 249-2730</a></span></div>
  <h1>{e(h1)}</h1>
  <p class="lead">{e(intro)} {e(SAMPLE)}</p>
  <div class="cta"><a class="btn" href="tel:8082492730">Call (808) 249-2730</a>
    <a class="btn ghost" href="https://maps.google.com/?q=970+Lower+Main+St+Wailuku+HI+96793" target="_blank" rel="noopener">Directions</a>
    <a class="btn ghost" href="{SITE}/#contact">Send a message</a></div>
</div></header>
<nav aria-label="Equipment categories and brands"><div class="wrap">{jump}</div></nav>
<main class="wrap">
{chr(10).join(sections)}
<div class="order"><h2>Don't see it?</h2><p>This page shows some of what we carry. We often have other models in the shop, and we can order most equipment and parts. Call or text (808) 249-2730, or email <a href="mailto:Info@mauipowerequipment.com">Info@mauipowerequipment.com</a>.</p></div>
</main>
<footer><div class="wrap">
  <span>Maui Power Equipment · <a href="https://maps.google.com/?q=970+Lower+Main+St+Wailuku+HI+96793" target="_blank" rel="noopener">970 Lower Main St, Wailuku, HI 96793</a></span>
  <span>Mon–Fri 7:30am–4:30pm · Sat 7:30am–2:00pm · Sun closed</span>
  <a href="{SITE}/">Home</a>
</div></footer>
</body>
</html>
"""
    out = os.path.join(HERE, path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    return len(ld_items)


SHOP = "Sales, walk-in service (no appointment needed), and parts at our locally owned shop on Lower Main St in Wailuku."


def build():
    """Write inventory-static.html plus equipment/<category>.html and equipment/<brand>.html.
    Returns the main page's item count. Pages for categories/brands with no items are removed."""
    items = load()
    n = page(items, "inventory-static.html",
             "Equipment We Carry — Maui Power Equipment | Wailuku, HI",
             "STIHL, Honda, SCAG, ECHO, Maruyama and more at Maui Power Equipment in Wailuku: zero-turn mowers, "
             "chainsaws, trimmers, blowers, generators and pumps. Walk-in service and parts. Call (808) 249-2730.",
             "Equipment We Carry", "STIHL, Honda, SCAG, ECHO, Maruyama and more. " + SHOP)
    written = set()
    for c, label in CATS:
        sub = [it for it in items if catof(it) == c]
        if c not in SLUG or not sub:
            continue
        makes = []
        for it in sub:
            m = (it.get("make") or "").strip()
            if m and m.lower() not in [x.lower() for x in makes]:
                makes.append(m)
        path = f"{SUBDIR}/{SLUG[c]}.html"
        page(sub, path, f"{label} on Maui | Maui Power Equipment, Wailuku",
             f"{label} from {', '.join(makes[:4])} at Maui Power Equipment in Wailuku, Maui. "
             f"Walk-in service and parts. Call (808) 249-2730.",
             f"{label} on Maui", f"{label} from {and_list(makes)}. " + SHOP)
        written.add(path)
    for brand, slug in BRANDS:
        sub = [it for it in items if (it.get("make") or "").strip().lower() == brand.lower()]
        if not sub:
            continue
        kinds = [l.lower() for c, l in CATS if c in SLUG and any(catof(it) == c for it in sub)]
        path = f"{SUBDIR}/{slug}.html"
        page(sub, path, f"{brand} on Maui | Sales, Service & Parts — Maui Power Equipment",
             f"{brand} {', '.join(kinds[:4])} at Maui Power Equipment in Wailuku, Maui. "
             f"{brand} service and parts, walk-in. Call (808) 249-2730.",
             f"{brand} on Maui", f"{brand} {and_list(kinds)}. " + SHOP)
        written.add(path)
    for f in os.listdir(os.path.join(HERE, SUBDIR)):  # drop pages for categories/brands that emptied out
        if f.endswith(".html") and f"{SUBDIR}/{f}" not in written:
            os.remove(os.path.join(HERE, SUBDIR, f))
    return n


if __name__ == "__main__":
    n = build()
    print(f"inventory-static.html written ({n} items)")
