"""
classify_relevance.py
---------------------
Uses Groq API (Llama 3) to classify each paper as relevant or not to
cosmetic toxicants research. Adds two columns:
  - relevant:          "yes" or "no"
  - relevance_reason:  one sentence explanation from the model

Sends 5 papers per API call (batching) for ~5x speed improvement over single calls.

Usage:
    python tools/classify_relevance.py --toxicant parabens
    python tools/classify_relevance.py --toxicant all

Supports pause/resume via checkpointing — safe to re-run at any time.
Rate limit: 30 RPM on Groq free tier (handled automatically).
"""

import os
import re
import time
import argparse
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
DATABASE_PATH = os.getenv("DATABASE_PATH")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

BATCH_SIZE = 5

TOXICANTS = [
    "parabens", "phthalates", "siloxanes", "pfas", "benzophenones",
    "fragrance", "formaldehyde_releasers", "heavy_metals", "triclosan",
    "toluene", "ethanolamines", "dioxane", "bha_bht", "hydroquinone", "coal_tar"
]

BATCH_PROMPT_TEMPLATE = """You are a research assistant filtering scientific papers for a study on health effects of chemical toxicants in cosmetic products (skincare, haircare, makeup, personal care products).

For each paper below, answer:
1. Is it relevant to health effects of chemical toxicants in cosmetic products? (yes/no)
2. One sentence explaining why.

{papers}

Respond in this exact format for each paper:
PAPER 1
relevant: yes/no
reason: <one sentence>

PAPER 2
relevant: yes/no
reason: <one sentence>

(and so on for all papers)"""


def build_papers_block(batch: list[dict]) -> str:
    lines = []
    for i, row in enumerate(batch, 1):
        abstract = row["abstract"][:600] if row["abstract"] else "No abstract available."
        lines.append(f"PAPER {i}\nTitle: {row['title']}\nAbstract: {abstract}")
    return "\n\n".join(lines)


def parse_batch_response(text: str, batch_size: int) -> list[tuple[str, str]]:
    results = []
    for i in range(1, batch_size + 1):
        pattern = rf"PAPER {i}.*?relevant:\s*(yes|no).*?reason:\s*(.+?)(?=PAPER {i+1}|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            relevant = match.group(1).strip().lower()
            reason = match.group(2).strip().split("\n")[0].strip()
            results.append((relevant, reason))
        else:
            results.append(("", ""))  # Will be retried via checkpointing
    return results


def classify_batch(client: Groq, batch: list[dict]) -> list[tuple[str, str]]:
    papers_block = build_papers_block(batch)
    prompt = BATCH_PROMPT_TEMPLATE.format(papers=papers_block)
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=600,
        )
        text = response.choices[0].message.content.strip()
        return parse_batch_response(text, len(batch))
    except Exception as e:
        print(f"  API error: {e}")
        return [("", "")] * len(batch)


def process_file(csv_file: str, client: Groq):
    if not os.path.exists(csv_file):
        print(f"File not found: {csv_file}")
        return

    df = pd.read_csv(csv_file, dtype=str).fillna("")
    print(f"\nLoaded {len(df)} records from {csv_file}")

    if "relevant" not in df.columns:
        df["relevant"] = ""
    if "relevance_reason" not in df.columns:
        df["relevance_reason"] = ""

    todo = df[df["relevant"] == ""].index.tolist()
    already_done = len(df) - len(todo)
    print(f"  Already classified: {already_done}")
    print(f"  To classify: {len(todo)}")

    if not todo:
        print("  Nothing to do — all rows already classified.")
        return

    processed = 0
    for i in range(0, len(todo), BATCH_SIZE):
        batch_indices = todo[i:i + BATCH_SIZE]
        batch = [{"title": df.at[idx, "title"], "abstract": df.at[idx, "abstract"]} for idx in batch_indices]

        results = classify_batch(client, batch)

        for idx, (relevant, reason) in zip(batch_indices, results):
            df.at[idx, "relevant"] = relevant
            df.at[idx, "relevance_reason"] = reason

        processed += len(batch_indices)

        if processed % 50 == 0 or processed == len(todo):
            df.to_csv(csv_file, index=False)
            print(f"  [{processed}/{len(todo)}] checkpoint saved.")
        elif processed % 10 == 0:
            last_relevant, last_reason = results[-1]
            print(f"  [{processed}/{len(todo)}] last: {last_relevant} — {last_reason[:60]}")

        # 2.1s between calls = stay under 30 RPM
        time.sleep(2.1)

    df.to_csv(csv_file, index=False)
    yes_count = (df["relevant"] == "yes").sum()
    no_count = (df["relevant"] == "no").sum()
    print(f"\n  Done. Relevant: {yes_count} | Not relevant: {no_count}")
    print(f"  Saved to: {csv_file}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--toxicant", required=True,
                        help="Toxicant name (e.g. parabens) or 'all' to process all 15")
    args = parser.parse_args()

    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY not found in .env")
        return

    client = Groq(api_key=GROQ_API_KEY)

    if args.toxicant == "all":
        for toxicant in TOXICANTS:
            csv_file = os.path.join(DATABASE_PATH, f"pubmed_{toxicant}.csv")
            process_file(csv_file, client)
    else:
        csv_file = os.path.join(DATABASE_PATH, f"pubmed_{args.toxicant}.csv")
        process_file(csv_file, client)


if __name__ == "__main__":
    main()
