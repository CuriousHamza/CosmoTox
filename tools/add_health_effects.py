"""
add_health_effects.py
---------------------
Reads a pubmed_<toxicant>.csv, detects which health effect categories are mentioned
in each paper's title + abstract, and adds a "health_effects" column.

Usage:
    python tools/add_health_effects.py --toxicant parabens
    python tools/add_health_effects.py --toxicant phthalates

Multiple effects are separated by " | " in the column.
If no effect is detected, the value is "unspecified".
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

# ── Health effect keyword map ─────────────────────────────────────────────────
# Format: "effect label": [keywords to scan for]

HEALTH_EFFECT_KEYWORDS = {
    "endocrine disruption":   ["endocrine disrupt", "estrogenic", "androgenic", "hormone disrupt",
                                "estrogen receptor", "androgen receptor", "xenoestrogen",
                                "endocrine system", "hormonal effect"],
    "reproductive toxicity":  ["reproductive toxicity", "reproductive effect", "fertility",
                                "infertility", "miscarriage", "birth defect", "sperm quality",
                                "ovarian function", "menstrual", "menstruation", "semen quality"],
    "carcinogenicity":        ["cancer", "tumor", "tumour", "carcinogen", "carcinoma",
                                "malignant", "oncogenic", "breast cancer", "prostate cancer"],
    "neurotoxicity":          ["neurotoxic", "cognitive impairment", "neurodevelopmental",
                                "developmental neurotoxic", "brain development", "neurological effect"],
    "skin sensitization":     ["skin sensitization", "allergic contact", "contact dermatitis",
                                "patch test", "sensitizer", "skin allerg", "skin reaction"],
    "oxidative stress":       ["oxidative stress", "reactive oxygen", "ros ", "antioxidant",
                                "lipid peroxidation", "free radical", "malondialdehyde"],
    "developmental toxicity": ["developmental toxicity", "fetal toxicity", "embryotoxic",
                                "prenatal exposure", "gestational", "teratogen", "in utero",
                                "fetal development", "foetal"],
    "immune disruption":      ["immunosuppression", "immune disruption", "autoimmune",
                                "immunotoxic", "cytokine", "immune response", "lymphocyte proliferation"],
    "genotoxicity":           ["genotoxic", "dna damage", "chromosomal aberration",
                                "micronucleus", "double strand break", "dna strand break", "mutagenic"],
    "thyroid disruption":     ["thyroid disruption", "thyroid function", "tsh", "thyroxine",
                                "hypothyroid", "hyperthyroid", "thyroid hormone"],
}

# ── Detection function ────────────────────────────────────────────────────────

def detect_health_effects(title: str, abstract: str) -> str:
    text = (title + " " + abstract).lower()
    found = []
    for effect, keywords in HEALTH_EFFECT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            found.append(effect)
    return " | ".join(found) if found else "unspecified"

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(CSV_FILE):
        print(f"File not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE, dtype=str).fillna("")
    print(f"Loaded {len(df)} records from {CSV_FILE}")

    df["health_effects"] = df.apply(
        lambda row: detect_health_effects(row["title"], row["abstract"]), axis=1
    )

    # Summary
    unspecified = (df["health_effects"] == "unspecified").sum()
    print(f"  Health effects detected in {len(df) - unspecified} papers")
    print(f"  Unspecified (no effect found): {unspecified} papers")

    # Per-category counts
    from collections import Counter
    counter = Counter()
    for val in df["health_effects"]:
        if val != "unspecified":
            for effect in val.split(" | "):
                counter[effect.strip()] += 1
    print("\n  Breakdown by effect:")
    for effect, count in counter.most_common():
        print(f"    {effect}: {count}")

    df.to_csv(CSV_FILE, index=False)
    print(f"\nDone. Saved updated file to:\n  {CSV_FILE}")

if __name__ == "__main__":
    main()
