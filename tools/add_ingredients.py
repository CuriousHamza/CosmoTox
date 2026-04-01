"""
add_ingredients.py
------------------
Reads a pubmed_<toxicant>.csv, detects which common cosmetic ingredients are mentioned
in each paper's title + abstract, and adds an "ingredients" column.

Usage:
    python tools/add_ingredients.py --toxicant parabens
    python tools/add_ingredients.py --toxicant phthalates

Multiple ingredients are separated by " | " in the column.
If no ingredient is detected, the value is "unspecified".
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

# ── Ingredient keyword map ────────────────────────────────────────────────────

INGREDIENT_KEYWORDS = {
    "retinol":          ["retinol", "retinoid", "retinoic acid", "tretinoin", "vitamin a"],
    "niacinamide":      ["niacinamide", "nicotinamide"],
    "hyaluronic acid":  ["hyaluronic acid", "hyaluronate", "sodium hyaluronate"],
    "glycerin":         ["glycerin", "glycerol", "glycerine"],
    "Sodium Lauryl Sulfate / Sodium Laureth Sulfate": ["sodium lauryl sulfate", "sls", "sodium laureth sulfate",
                         "sodium lauryl sulphate", "sles"],
    "titanium dioxide": ["titanium dioxide", "tio2"],
    "zinc oxide":       ["zinc oxide"],
    "vitamin C":        ["vitamin c", "ascorbic acid", "ascorbate", "l-ascorbic acid"],
    "vitamin E":        ["vitamin e", "tocopherol", "tocopheryl"],
    "salicylic acid":   ["salicylic acid", "beta hydroxy acid"],
    "kojic acid":       ["kojic acid"],
    "arbutin":          ["arbutin", "alpha-arbutin"],
    "ceramides":        ["ceramide", "ceramides"],
    "glycolic acid":    ["glycolic acid", "alpha hydroxy acid", "aha"],
    "mineral oil":      ["mineral oil", "paraffinum liquidum", "liquid paraffin"],
    "aloe vera":        ["aloe vera", "aloe barbadensis"],
    "benzoyl peroxide": ["benzoyl peroxide"],
    "silicone":         ["silicone", "dimethicone", "cyclomethicone", "siloxane"],
    "lanolin":          ["lanolin", "wool wax", "wool grease"],
    "propylene glycol": ["propylene glycol"],
    "phenoxyethanol":   ["phenoxyethanol"],
    "benzyl alcohol":   ["benzyl alcohol"],
    "citric acid":      ["citric acid"],
    "lactic acid":      ["lactic acid"],
    "collagen":         ["collagen", "hydrolyzed collagen"],
    "peptides":         ["peptide", "peptides", "palmitoyl"],
    "sunscreen agent":  ["avobenzone", "octocrylene", "octinoxate", "octyl methoxycinnamate",
                         "homosalate", "octisalate"],
}

# ── Detection function ────────────────────────────────────────────────────────

def detect_ingredients(title: str, abstract: str) -> str:
    text = (title + " " + abstract).lower()
    found = []
    for ingredient, keywords in INGREDIENT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            found.append(ingredient)
    return " | ".join(found) if found else "unspecified"

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(CSV_FILE):
        print(f"File not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE, dtype=str).fillna("")
    print(f"Loaded {len(df)} records from {CSV_FILE}")

    df["ingredients"] = df.apply(
        lambda row: detect_ingredients(row["title"], row["abstract"]), axis=1
    )

    unspecified = (df["ingredients"] == "unspecified").sum()
    print(f"  Ingredients detected in {len(df) - unspecified} papers")
    print(f"  Unspecified: {unspecified} papers")

    from collections import Counter
    counter = Counter()
    for val in df["ingredients"]:
        if val != "unspecified":
            for ing in val.split(" | "):
                counter[ing.strip()] += 1
    print("\n  Breakdown by ingredient:")
    for ingredient, count in counter.most_common():
        print(f"    {ingredient}: {count}")

    df.to_csv(CSV_FILE, index=False)
    print(f"\nDone. Saved to:\n  {CSV_FILE}")

if __name__ == "__main__":
    main()
