#!/usr/bin/env python3
"""Bake catalog.json (the regular-lineup gallery) into index.html as plain HTML.

WRITES TO : index.html, only between <!--CATALOG:START--> and <!--CATALOG:END-->
READS     : catalog.json (photos live in assets/inventory/catalog/)
DOES NOT TOUCH: inventory.json, master.db, MASTERPRICE.xlsx

Why: AI crawlers don't run JavaScript. The list is real page text they can read;
in a browser the page's script turns the same list into gallery cards via card().
Run after editing catalog.json:  python3 generate_catalog.py
"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "catalog.json")
INDEX = os.path.join(HERE, "index.html")
START, END = "<!--CATALOG:START-->", "<!--CATALOG:END-->"


def build():
    with open(CATALOG, encoding="utf-8") as f:
        items = json.load(f)
    rows = []
    for it in items:
        if it.get("hidden"):
            continue
        a = lambda k: html.escape(str(it.get(k) or ""), quote=True)
        label = f"{a('make')} {a('model')}"
        link = f'<a href="{a("info")}" rel="noopener">{label}</a>' if it.get("info") else label
        tag = f" — {a('tagline')}" if it.get("tagline") else ""
        rows.append(
            f'<li data-cat="{a("cat")}" data-make="{a("make")}" data-model="{a("model")}" '
            f'data-zoom="{a("photoZoom")}" data-position="{a("photoPosition")}" data-tag="{a("tagline")}" data-photo="{a("photo")}" data-info="{a("info")}">{link}{tag}</li>'
        )
    block = f'{START}\n<ul class="catalog-list" id="catalogList">\n' + "\n".join(rows) + f"\n</ul>\n{END}"
    with open(INDEX, encoding="utf-8") as f:
        page = f.read()
    i, j = page.find(START), page.find(END)
    if i < 0 or j < i or page.count(START) != 1 or page.count(END) != 1:
        raise SystemExit("catalog markers missing or duplicated in index.html")
    page = page[:i] + block + page[j + len(END):]
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"catalog: {len(rows)} items baked into index.html")


if __name__ == "__main__":
    build()
    import generate_inventory_static
    print(f"inventory-static.html written ({generate_inventory_static.build()} items)")
