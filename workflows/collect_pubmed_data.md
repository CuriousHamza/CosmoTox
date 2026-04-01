# Workflow: Collect PubMed Data for Cosmetic Toxicants

## Objective
Fetch research papers from PubMed for a given cosmetic toxicant, filter for human cosmetics-context studies only, enrich with metadata tags, and save to the shared database as a CSV.

## Current Status
All 15 toxicants collected and fully enriched.

| Toxicant | Papers | File |
|---|---|---|
| parabens | 351 | pubmed_parabens.csv |
| phthalates | 272 | pubmed_phthalates.csv |
| siloxanes | 69 | pubmed_siloxanes.csv |
| pfas | 44 | pubmed_pfas.csv |
| benzophenones | 352 | pubmed_benzophenones.csv |
| fragrance | 1,066 | pubmed_fragrance.csv |
| formaldehyde_releasers | 92 | pubmed_formaldehyde_releasers.csv |
| heavy_metals | 2,853 | pubmed_heavy_metals.csv |
| triclosan | 164 | pubmed_triclosan.csv |
| toluene | 76 | pubmed_toluene.csv |
| ethanolamines | 492 | pubmed_ethanolamines.csv |
| dioxane | 57 | pubmed_dioxane.csv |
| bha_bht | 62 | pubmed_bha_bht.csv |
| hydroquinone | 689 | pubmed_hydroquinone.csv |
| coal_tar | 353 | pubmed_coal_tar.csv |
| **Total** | **~6,892** | _combined.csv (auto-built) |

## CSV Schema
Each file has these columns (in order):
`pmid, title, abstract, pub_year, journal, toxicant, organs, health_effects, products, ingredients`

---

## How to Run (for a new toxicant)

### 1. Install dependencies (first time only)
```bash
cd "c:/Users/hamza/My stuff/btech cse/DTI Automation/automating agent"
pip install -r requirements.txt
```

### 2. Add the toxicant to fetch_pubmed.py
Open `tools/fetch_pubmed.py` and add the toxicant's PubMed query to the `TOXICANTS` dict.

### 3. Run the full pipeline
```bash
python tools/fetch_pubmed.py --toxicant <name>
python tools/add_organs.py --toxicant <name>
python tools/add_health_effects.py --toxicant <name>
python tools/add_products.py --toxicant <name>
python tools/add_ingredients.py --toxicant <name>
```

### 4. Launch the dashboard
```bash
streamlit run tools/dashboard.py
```
Opens at http://localhost:8501. The `_combined.csv` is auto-rebuilt when source files change.

---

## Query Strategy

Each query combines:
1. **Toxicant keywords** — searched in title + abstract (`[tiab]`)
2. **Cosmetic context keywords** — at least one must appear in title or abstract
3. **Date range** — 2000–2026

This ensures only cosmetics-related papers come back, not industrial or food toxicology papers that mention the same chemical.

---

## Post-Fetch Filters

### Animal exclusion
Papers are dropped if any of these appear in title or abstract:
`rat, rats, mouse, mice, murine, rabbit, hamster, rodent, zebrafish, bovine, porcine, in vitro, cell line, hela, mcf-7`

**Why:** Many toxicology papers study the same chemicals in animal models. These are not relevant to human cosmetics exposure.

---

## Known Quirks
- **Phthalates**: many papers about industrial or food plasticizer exposure — cosmetic context filter is critical to avoid false positives.
- **Abstracts**: some older papers have no abstract on PubMed. These will have an empty `abstract` column — keep them, the title is still useful.
- **Rate limits**: without an NCBI API key the script runs at 3 requests/sec. With a free key (register at ncbi.nlm.nih.gov/account) it runs at 10/sec. Add key to `.env` as `NCBI_API_KEY`.
- **Re-running**: the pipeline scripts are safe to re-run — `fetch_pubmed.py` skips PMIDs already in the CSV; enrichment scripts overwrite the column in-place.
- **_combined.csv**: auto-rebuilt by the dashboard whenever any source CSV is newer. No manual step needed.
