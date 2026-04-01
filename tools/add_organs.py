"""
add_organs.py
-------------
Reads a pubmed_<toxicant>.csv, detects which organ(s) are mentioned/affected
in each paper's title + abstract, and adds an "organs" column.

Usage:
    python tools/add_organs.py --toxicant parabens
    python tools/add_organs.py --toxicant phthalates

Multiple organs are separated by " | " in the column.
If no organ is detected, the value is "unspecified".
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

# ── Organ keyword map ─────────────────────────────────────────────────────────
# Format: "organ label": [keywords to scan for]

ORGAN_KEYWORDS = {
    "skin":           ["skin", "dermal", "dermis", "epidermis", "keratinocyte", "subcutaneous", "cutaneous", "transdermal"],
    "breast":         ["breast", "mammary", "nipple"],
    "liver":          ["liver", "hepatic", "hepato", "hepatocyte"],
    "kidney":         ["kidney", "renal", "nephro", "nephric"],
    "uterus":         ["uterus", "uterine", "endometrium", "endometrial", "myometrium"],
    "ovary":          ["ovary", "ovarian", "follicle", "oocyte"],
    "testis":         ["testis", "testicular", "spermatogenesis", "sertoli", "leydig"],
    "prostate":       ["prostate", "prostatic"],
    "thyroid":        ["thyroid", "thyroid gland", "thyroxine", "tsh"],
    "brain":          ["brain", "neural", "neuron", "neurological", "hypothalamus", "pituitary", "cerebral", "cortex", "hippocampus", "neurotoxic"],
    "lung":           ["lung", "pulmonary", "respiratory", "airway", "bronchial", "alveolar"],
    "blood":          ["blood", "serum", "plasma", "erythrocyte", "leukocyte", "hemato", "haemato"],
    "adipose tissue": ["adipose", "fat tissue", "adipocyte", "lipid accumulation"],
    "gut":            ["gut", "intestine", "intestinal", "colon", "colorectal", "gastrointestinal"],
    "heart":          ["heart", "cardiac", "cardiovascular", "myocardial"],
    "eye":            ["eye", "ocular", "cornea", "retina"],
    "placenta":       ["placenta", "placental", "fetal", "foetal", "umbilical"],
    "immune system":  ["immune", "immunotoxic", "lymphocyte", "macrophage", "cytokine", "allerg"],
    "sperm":          ["sperm", "spermatozoa", "ejaculate", "seminal"],
}

# ── Detection function ────────────────────────────────────────────────────────

def detect_organs(title: str, abstract: str) -> str:
    text = (title + " " + abstract).lower()
    found = []
    for organ, keywords in ORGAN_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            found.append(organ)
    return " | ".join(found) if found else "unspecified"

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(CSV_FILE):
        print(f"File not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE, dtype=str).fillna("")
    print(f"Loaded {len(df)} records from {CSV_FILE}")

    df["organs"] = df.apply(
        lambda row: detect_organs(row["title"], row["abstract"]), axis=1
    )

    # Summary
    unspecified = (df["organs"] == "unspecified").sum()
    print(f"  Organs detected in {len(df) - unspecified} papers")
    print(f"  Unspecified (no organ found): {unspecified} papers")

    df.to_csv(CSV_FILE, index=False)
    print(f"\nDone. Saved updated file to:\n  {CSV_FILE}")

if __name__ == "__main__":
    main()
