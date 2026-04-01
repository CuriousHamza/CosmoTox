"""
add_inference.py
----------------
Reads a pubmed_<toxicant>.csv, classifies each paper into one or more context
categories based on title + abstract keywords, and adds an "inference" column.

The inference label helps identify papers that were pulled in by a toxicant keyword
but are not actually relevant to cosmetics (e.g. industrial/environmental studies).

Usage:
    python tools/add_inference.py --toxicant parabens
    python tools/add_inference.py --toxicant heavy_metals

Multiple categories are separated by " | ".
Papers with no cosmetic signals are flagged with "no cosmetics context".
"""

import os
import argparse
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
DATABASE_PATH = os.getenv("DATABASE_PATH")

parser = argparse.ArgumentParser()
parser.add_argument("--toxicant", required=True, help="e.g. parabens, heavy_metals")
args = parser.parse_args()
CSV_FILE = os.path.join(DATABASE_PATH, f"pubmed_{args.toxicant}.csv")

# ── Context category keyword map ──────────────────────────────────────────────
# Format: "category label": [keywords to scan for]

CONTEXT_CATEGORIES = {
    "cosmetics product study": [
        "cosmetic", "cosmetics", "makeup", "make-up", "personal care product",
        "beauty product", "toiletry", "toiletries",
    ],
    "sunscreen/UV filter study": [
        "sunscreen", "sunblock", "sun cream", "spf ", "uv filter", "uv protection",
        "photoprotection", "sun protection",
    ],
    "hair product study": [
        "hair dye", "hair color", "hair colour", "hair bleach", "shampoo",
        "hair product", "hair care", "hair straighten",
    ],
    "skin/topical study": [
        "topical", "transdermal", "skin absorption", "dermal absorption",
        "skin application", "lotion", "cream", "moisturizer", "moisturiser",
    ],
    "nail product study": [
        "nail polish", "nail lacquer", "nail varnish", "nail product",
    ],
    "clinical/hospital study": [
        "clinical trial", "clinical study", "patient", "hospital", "diagnosis",
        "treatment outcome", "therapeutic",
    ],
    "epidemiological study": [
        "cohort", "cross-sectional", "case-control", "prevalence", "incidence",
        "epidemiol", "population study", "survey",
    ],
    "biomonitoring study": [
        "biomonitor", "urinary concentration", "serum concentration", "blood level",
        "urine sample", "blood sample", "biomarker", "human exposure assessment",
    ],
    "industrial/occupational": [
        "industrial", "occupational", "factory", "worker", "workplace",
        "manufacturing plant", "production facility", "occupational exposure",
    ],
    "environmental contamination": [
        "soil contamination", "water contamination", "sediment", "groundwater",
        "river water", "lake", "effluent", "wastewater", "environmental contamination",
        "atmospheric", "air pollution",
    ],
    "food/dietary exposure": [
        "food contamination", "dietary exposure", "food safety", "edible",
        "vegetable", "fruit", "fish ", "seafood", "drinking water",
        "food intake", "diet ", "nutrition",
    ],
    "analytical/method study": [
        "analytical method", "detection method", "hplc", "gc-ms", "lc-ms",
        "chromatograph", "spectrometr", "sample preparation", "extraction method",
        "quantification method",
    ],
}

# ── Cosmetics relevance signals ───────────────────────────────────────────────
# If NONE of these appear in title+abstract, paper is flagged as off-topic

COSMETIC_SIGNALS = [
    "cosmetic", "personal care", "lotion", "shampoo", "makeup", "make-up",
    "fragrance", "nail polish", "cream", "moisturizer", "moisturiser", "skincare",
    "hair dye", "sunscreen", "lipstick", "foundation", "deodorant", "perfume",
    "toiletry", "beauty product", "face wash", "body wash", "conditioner",
    "serum", "toner", "eye shadow", "mascara", "blush", "concealer",
]

# ── Detection function ────────────────────────────────────────────────────────

def classify_paper(title: str, abstract: str) -> str:
    text = (title + " " + abstract).lower()

    categories = []
    for label, keywords in CONTEXT_CATEGORIES.items():
        if any(kw in text for kw in keywords):
            categories.append(label)

    # Flag papers with no cosmetic relevance signals
    has_cosmetic_signal = any(sig in text for sig in COSMETIC_SIGNALS)
    if not has_cosmetic_signal:
        categories.append("no cosmetics context")

    return " | ".join(categories) if categories else "unclassified"

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(CSV_FILE):
        print(f"File not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE, dtype=str).fillna("")
    print(f"Loaded {len(df)} records from {CSV_FILE}")

    df["inference"] = df.apply(
        lambda row: classify_paper(row["title"], row["abstract"]), axis=1
    )

    # Summary
    off_topic = df["inference"].str.contains("no cosmetics context").sum()
    print(f"  Off-topic papers (no cosmetics context): {off_topic}")
    print(f"  Relevant papers: {len(df) - off_topic}")

    # Per-category counts
    from collections import Counter
    counter = Counter()
    for val in df["inference"]:
        for cat in val.split(" | "):
            counter[cat.strip()] += 1
    print("\n  Breakdown by category:")
    for cat, count in counter.most_common():
        print(f"    {cat}: {count}")

    df.to_csv(CSV_FILE, index=False)
    print(f"\nDone. Saved updated file to:\n  {CSV_FILE}")

if __name__ == "__main__":
    main()
