"""
fetch_pubmed.py
---------------
Fetches PubMed papers for a given cosmetic toxicant (2000-2026).

Filters applied:
  1. Query-level: toxicant keywords + cosmetics context keywords in title/abstract
  2. Post-fetch:  removes animal studies (rat, mice, murine, etc.)

Usage:
    python tools/fetch_pubmed.py --toxicant parabens
    python tools/fetch_pubmed.py --toxicant phthalates

Output: DATABASE_PATH/pubmed_<toxicant>.csv
"""

import os
import time
import argparse
import pandas as pd
from Bio import Entrez
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv()

Entrez.email = os.getenv("NCBI_EMAIL")
api_key = os.getenv("NCBI_API_KEY", "").strip()
if api_key:
    Entrez.api_key = api_key

DATABASE_PATH = os.getenv("DATABASE_PATH")
DELAY = 0.11 if api_key else 0.34

# ── Toxicant definitions ──────────────────────────────────────────────────────

TOXICANTS = {
    "parabens": (
        "parabens[tiab] OR methylparaben[tiab] OR ethylparaben[tiab] "
        "OR propylparaben[tiab] OR butylparaben[tiab]"
    ),
    "phthalates": (
        "phthalate[tiab] OR phthalates[tiab] OR DEP[tiab] OR DBP[tiab] "
        "OR DEHP[tiab] OR diethyl phthalate[tiab] OR dibutyl phthalate[tiab] "
        "OR \"di(2-ethylhexyl) phthalate\"[tiab]"
    ),
    "siloxanes": (
        "siloxane[tiab] OR siloxanes[tiab] OR D4[tiab] OR D5[tiab] "
        "OR cyclomethicone[tiab] OR octamethylcyclotetrasiloxane[tiab] "
        "OR decamethylcyclopentasiloxane[tiab]"
    ),
    "pfas": (
        "PFAS[tiab] OR perfluoroalkyl[tiab] OR polyfluoroalkyl[tiab] "
        "OR PFOA[tiab] OR PFOS[tiab] OR \"forever chemical\"[tiab] "
        "OR \"forever chemicals\"[tiab]"
    ),
    "benzophenones": (
        "benzophenone[tiab] OR benzophenones[tiab] OR oxybenzone[tiab] "
        "OR \"UV filter\"[tiab] OR \"UV filters\"[tiab] OR sulisobenzone[tiab]"
    ),
    "fragrance": (
        "fragrance chemical[tiab] OR fragrance chemicals[tiab] OR parfum[tiab] "
        "OR limonene[tiab] OR linalool[tiab] OR \"fragrance mix\"[tiab] "
        "OR \"fragrance allergen\"[tiab]"
    ),
    "formaldehyde_releasers": (
        "formaldehyde releaser[tiab] OR formaldehyde-releasing[tiab] "
        "OR \"DMDM hydantoin\"[tiab] OR quaternium-15[tiab] OR imidazolidinyl urea[tiab] "
        "OR diazolidinyl urea[tiab] OR bronopol[tiab]"
    ),
    "heavy_metals": (
        "lead[tiab] OR mercury[tiab] OR arsenic[tiab] OR cadmium[tiab] "
        "OR chromium[tiab] OR \"heavy metal\"[tiab] OR \"heavy metals\"[tiab] "
        "OR methylmercury[tiab] OR inorganic arsenic[tiab]"
    ),
    "triclosan": (
        "triclosan[tiab] OR triclocarban[tiab]"
    ),
    "toluene": (
        "toluene[tiab] OR methylbenzene[tiab]"
    ),
    "ethanolamines": (
        "diethanolamine[tiab] OR DEA[tiab] OR monoethanolamine[tiab] OR MEA[tiab] "
        "OR triethanolamine[tiab] OR TEA[tiab] OR ethanolamine[tiab] OR cocamide DEA[tiab]"
    ),
    "dioxane": (
        "1,4-dioxane[tiab] OR dioxane[tiab] OR ethylene oxide[tiab]"
    ),
    "bha_bht": (
        "butylated hydroxyanisole[tiab] OR BHA[tiab] OR butylated hydroxytoluene[tiab] "
        "OR BHT[tiab]"
    ),
    "hydroquinone": (
        "hydroquinone[tiab] OR skin lightening[tiab] OR skin bleaching[tiab] "
        "OR depigmentation[tiab]"
    ),
    "coal_tar": (
        "coal tar[tiab] OR coal-tar[tiab] OR p-phenylenediamine[tiab] OR PPD[tiab] "
        "OR hair dye[tiab] OR hair dyes[tiab] OR resorcinol[tiab]"
    ),
}

# ── Cosmetic context keywords (same for all toxicants) ────────────────────────

COSMETIC_TERMS = (
    'cosmetic[tiab] OR "personal care product"[tiab] OR lotion[tiab] '
    'OR shampoo[tiab] OR makeup[tiab] OR perfume[tiab] OR fragrance[tiab] '
    'OR "nail polish"[tiab] OR cream[tiab] OR moisturizer[tiab] OR skincare[tiab]'
)

DATE_FILTER = '"2000/01/01"[dp]:"2026/12/31"[dp]'

# ── Animal exclusion keywords ─────────────────────────────────────────────────

ANIMAL_KEYWORDS = [
    "rat ", "rats ", " rat,", " rats,", "mouse", "mice", "murine",
    "rabbit", "hamster", "rodent", "zebrafish", "bovine", "porcine",
    "in vitro", "cell line", "hela", "mcf-7",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def is_animal_study(title: str, abstract: str) -> bool:
    combined = (title + " " + abstract).lower()
    return any(kw in combined for kw in ANIMAL_KEYWORDS)


def fetch_pmids(query: str):
    print("Searching PubMed...")
    handle = Entrez.esearch(db="pubmed", term=query, retmax=10000, usehistory="y")
    record = Entrez.read(handle)
    handle.close()
    total = int(record["Count"])
    print(f"  Found {total} papers matching the query.")
    return record["WebEnv"], record["QueryKey"], total


def fetch_records_batch(webenv: str, query_key: str, total: int, toxicant: str) -> list[dict]:
    records = []
    batch_size = 100
    for start in range(0, total, batch_size):
        print(f"  Fetching records {start + 1}–{min(start + batch_size, total)}...")
        handle = Entrez.efetch(
            db="pubmed",
            rettype="xml",
            retmode="xml",
            retstart=start,
            retmax=batch_size,
            webenv=webenv,
            query_key=query_key,
        )
        batch = Entrez.read(handle)
        handle.close()
        time.sleep(DELAY)

        for article in batch["PubmedArticle"]:
            try:
                medline = article["MedlineCitation"]
                art = medline["Article"]

                pmid = str(medline["PMID"])
                title = str(art.get("ArticleTitle", "")).strip()

                abstract_raw = art.get("Abstract", {}).get("AbstractText", "")
                if isinstance(abstract_raw, list):
                    abstract = " ".join(str(a) for a in abstract_raw).strip()
                else:
                    abstract = str(abstract_raw).strip()

                pub_date = art.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
                pub_year = str(pub_date.get("Year", pub_date.get("MedlineDate", "")[:4])).strip()

                journal = str(art.get("Journal", {}).get("Title", "")).strip()

                records.append({
                    "pmid": pmid,
                    "title": title,
                    "abstract": abstract,
                    "pub_year": pub_year,
                    "journal": journal,
                    "toxicant": toxicant,
                })
            except Exception as e:
                print(f"  Warning: skipped a record ({e})")

    return records


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--toxicant", required=True, choices=TOXICANTS.keys(),
                        help="Toxicant to fetch (e.g. parabens, phthalates)")
    args = parser.parse_args()
    toxicant = args.toxicant

    if not Entrez.email:
        raise ValueError("NCBI_EMAIL not set in .env")
    if not DATABASE_PATH:
        raise ValueError("DATABASE_PATH not set in .env")

    os.makedirs(DATABASE_PATH, exist_ok=True)
    output_file = os.path.join(DATABASE_PATH, f"pubmed_{toxicant}.csv")

    query = f"({TOXICANTS[toxicant]}) AND ({COSMETIC_TERMS}) AND {DATE_FILTER}"
    print(f"\nToxicant: {toxicant}")

    webenv, query_key, total = fetch_pmids(query)
    if total == 0:
        print("No papers found.")
        return

    print(f"\nFetching full records for {total} papers...")
    records = fetch_records_batch(webenv, query_key, total, toxicant)
    print(f"  Fetched {len(records)} records.")

    before = len(records)
    records = [r for r in records if not is_animal_study(r["title"], r["abstract"])]
    after = len(records)
    print(f"\nAnimal filter: removed {before - after} papers, {after} remain.")

    df = pd.DataFrame(records).drop_duplicates(subset="pmid")

    if os.path.exists(output_file):
        existing = pd.read_csv(output_file, dtype=str)
        new_only = df[~df["pmid"].isin(existing["pmid"])]
        df = pd.concat([existing, new_only], ignore_index=True)
        print(f"Appended {len(new_only)} new records to existing file.")
    else:
        print(f"Creating new file with {len(df)} records.")

    df.to_csv(output_file, index=False)
    print(f"\nDone. Saved {len(df)} total records to:\n  {output_file}")


if __name__ == "__main__":
    main()
