"""
add_products.py
---------------
Reads a pubmed_<toxicant>.csv, detects which cosmetic product types are mentioned
in each paper's title + abstract, and adds a "products" column.

Usage:
    python tools/add_products.py --toxicant parabens
    python tools/add_products.py --toxicant phthalates

Multiple products are separated by " | " in the column.
If no product is detected, the value is "unspecified".
"""

import os
import argparse
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
DATABASE_PATH = os.getenv("DATABASE_PATH")

parser = argparse.ArgumentParser()
parser.add_argument("--toxicant", required=True, help="e.g. parabens, phthalates")
args = parser.parse_args()
CSV_FILE = os.path.join(DATABASE_PATH, f"pubmed_{args.toxicant}.csv")

# ── Product keyword map ───────────────────────────────────────────────────────

PRODUCT_KEYWORDS = {
    "face wash":    ["face wash", "facial cleanser", "facial wash", "face cleanser", "cleansing foam"],
    "moisturizer":  ["moisturizer", "moisturiser", "moisturizing cream", "moisturising cream",
                     "day cream", "night cream", "face cream", "facial cream", "skin cream"],
    "sunscreen":    ["sunscreen", "sunblock", "sun protection", "sun cream", "spf ", "uv filter",
                     "uv protection", "photoprotection"],
    "foundation":   ["foundation", "bb cream", "cc cream", "face powder", "concealer"],
    "shampoo":      ["shampoo"],
    "conditioner":  ["hair conditioner", "conditioner"],
    "hair dye":     ["hair dye", "hair color", "hair colour", "hair coloring", "hair colouring",
                     "hair bleach", "hair bleaching"],
    "lipstick":     ["lipstick", "lip gloss", "lip balm", "lip liner", "lip product"],
    "nail polish":  ["nail polish", "nail lacquer", "nail varnish", "nail product"],
    "deodorant":    ["deodorant", "antiperspirant"],
    "body wash":    ["body wash", "shower gel", "bath gel", "bath product"],
    "lotion":       ["body lotion", "hand cream", "hand lotion", "body cream", "skin lotion"],
    "soap":         ["soap", "bar soap", "liquid soap", "hand soap"],
    "perfume":      ["perfume", "cologne", "eau de toilette", "eau de parfum", "fragrance product"],
    "serum":        ["face serum", "skin serum", "facial serum"],
    "toothpaste":   ["toothpaste", "dentifrice", "tooth paste"],
    "baby product": ["baby shampoo", "baby lotion", "baby cream", "baby product", "baby wash",
                     "baby powder", "diaper cream"],
    "tanning product": ["self-tanner", "self tanner", "tanning lotion", "tanning product",
                        "bronzer", "fake tan"],
    "eye product":  ["eye cream", "eye shadow", "eyeshadow", "mascara", "eyeliner", "eye liner"],
}

# ── Detection function ────────────────────────────────────────────────────────

def detect_products(title: str, abstract: str) -> str:
    text = (title + " " + abstract).lower()
    found = []
    for product, keywords in PRODUCT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            found.append(product)
    return " | ".join(found) if found else "unspecified"

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(CSV_FILE):
        print(f"File not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE, dtype=str).fillna("")
    print(f"Loaded {len(df)} records from {CSV_FILE}")

    df["products"] = df.apply(
        lambda row: detect_products(row["title"], row["abstract"]), axis=1
    )

    unspecified = (df["products"] == "unspecified").sum()
    print(f"  Products detected in {len(df) - unspecified} papers")
    print(f"  Unspecified: {unspecified} papers")

    from collections import Counter
    counter = Counter()
    for val in df["products"]:
        if val != "unspecified":
            for p in val.split(" | "):
                counter[p.strip()] += 1
    print("\n  Breakdown by product:")
    for product, count in counter.most_common():
        print(f"    {product}: {count}")

    df.to_csv(CSV_FILE, index=False)
    print(f"\nDone. Saved to:\n  {CSV_FILE}")

if __name__ == "__main__":
    main()
