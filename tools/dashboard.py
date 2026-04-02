"""
dashboard.py
------------
Streamlit dashboard for visualizing PubMed cosmetic toxicants research.
Automatically loads all pubmed_*.csv files from DATABASE_PATH.

Run with:
    streamlit run tools/dashboard.py
"""

import os
import glob
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
DATABASE_PATH = os.getenv("DATABASE_PATH")

# Fallback to Streamlit secrets (used on Streamlit Cloud)
if not DATABASE_PATH:
    try:
        DATABASE_PATH = st.secrets["DATABASE_PATH"]
    except Exception:
        pass

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CosmoTox — Cosmetic Toxicants",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 CosmoTox: Cosmetic Toxicants Research")
st.caption("Research literature from PubMed · 2000–2026 · Human studies only · Cosmetics context")

st.markdown("""
<style>
/* Enable text wrapping in all dataframe cells */
div[data-testid="stDataFrame"] .ag-cell {
    white-space: normal !important;
    word-break: break-word !important;
    line-height: 1.4 !important;
}
div[data-testid="stDataFrame"] .ag-cell-value {
    white-space: normal !important;
    overflow: visible !important;
}
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────

COMBINED_CSV = os.path.join(DATABASE_PATH, "_combined.csv")

def build_combined():
    """Merge all pubmed_*.csv (excluding _combined.csv) into one file."""
    csv_files = [
        f for f in glob.glob(os.path.join(DATABASE_PATH, "pubmed_*.csv"))
        if "_combined" not in f
    ]
    if not csv_files:
        return pd.DataFrame()
    frames = [pd.read_csv(f, dtype=str).fillna("") for f in csv_files]
    combined = pd.concat(frames, ignore_index=True)
    combined["pub_year"] = pd.to_numeric(combined["pub_year"], errors="coerce")
    combined = combined.dropna(subset=["pub_year"])
    combined["pub_year"] = combined["pub_year"].astype(int)

    # Merge toxicant labels for duplicate PMIDs, keep first row for all other columns
    toxicant_merged = (
        combined.groupby("pmid")["toxicant"]
        .apply(lambda x: " | ".join(sorted(set(x))))
        .reset_index()
    )

    # For relevant/relevance_reason: take first non-empty value per PMID
    extra_merges = {}
    for col in ("relevant", "relevance_reason"):
        if col in combined.columns:
            extra_merges[col] = (
                combined[combined["pmid"].notna()]
                .groupby("pmid")[col]
                .apply(lambda x: next((v for v in x if v.strip()), ""))
                .reset_index()
            )

    combined = combined.drop_duplicates(subset="pmid", keep="first").drop(columns=["toxicant"])
    drop_extra = [c for c in extra_merges if c in combined.columns]
    if drop_extra:
        combined = combined.drop(columns=drop_extra)
    combined = combined.merge(toxicant_merged, on="pmid")
    for col, merged_df in extra_merges.items():
        combined = combined.merge(merged_df, on="pmid")

    combined.to_csv(COMBINED_CSV, index=False)
    return combined

@st.cache_data
def load_all_data():
    # Rebuild combined if any source CSV is newer than the combined file
    source_files = [
        f for f in glob.glob(os.path.join(DATABASE_PATH, "pubmed_*.csv"))
        if "_combined" not in f
    ]
    if not source_files:
        return pd.DataFrame()
    needs_rebuild = (
        not os.path.exists(COMBINED_CSV) or
        max(os.path.getmtime(f) for f in source_files) > os.path.getmtime(COMBINED_CSV)
    )
    if needs_rebuild:
        return build_combined()
    combined = pd.read_csv(COMBINED_CSV, dtype=str).fillna("")
    combined["pub_year"] = pd.to_numeric(combined["pub_year"], errors="coerce")
    combined = combined.dropna(subset=["pub_year"])
    combined["pub_year"] = combined["pub_year"].astype(int)
    return combined

df = load_all_data()

if df.empty:
    st.error("No data found. Run fetch_pubmed.py first.")
    st.stop()

# ── Display name mapping (full forms for all labels) ──────────────────────────

TOXICANT_DISPLAY = {
    "parabens":               "Parabens",
    "phthalates":             "Phthalates",
    "siloxanes":              "Siloxanes",
    "pfas":                   "Per- and Polyfluoroalkyl Substances",
    "benzophenones":          "Benzophenones",
    "fragrance":              "Fragrance Chemicals",
    "formaldehyde_releasers": "Formaldehyde Releasers",
    "heavy_metals":           "Heavy Metals",
    "triclosan":              "Triclosan",
    "toluene":                "Toluene",
    "ethanolamines":          "Ethanolamines",
    "dioxane":                "1,4-Dioxane",
    "bha_bht":                "Butylated Hydroxyanisole / Butylated Hydroxytoluene",
    "hydroquinone":           "Hydroquinone",
    "coal_tar":               "Coal Tar",
}

def apply_display_names(toxicant_str):
    parts = [s.strip() for s in toxicant_str.split("|")]
    return " | ".join(TOXICANT_DISPLAY.get(p, p) for p in parts)

df["toxicant"] = df["toxicant"].apply(apply_display_names)

# ── Sidebar filters ───────────────────────────────────────────────────────────

st.sidebar.header("Filters")

# Toxicant selector
available_toxicants = sorted(set(
    t.strip()
    for toxicants in df["toxicant"]
    for t in toxicants.split("|")
    if t.strip()
))
selected_toxicants = st.sidebar.multiselect(
    "Toxicant", available_toxicants, default=available_toxicants
)

# Year range
year_min, year_max = int(df["pub_year"].min()), int(df["pub_year"].max())
year_range = st.sidebar.slider("Publication Year", year_min, year_max, (year_min, year_max))

# Organ filter
all_organs = sorted(set(
    organ.strip()
    for organs in df["organs"]
    for organ in organs.split("|")
    if organ.strip() and organ.strip() != "unspecified"
))
selected_organs = st.sidebar.multiselect("Filter by Organ", all_organs)

# Health effect filter
all_effects = sorted(set(
    effect.strip()
    for effects in df["health_effects"]
    for effect in effects.split("|")
    if effect.strip() and effect.strip() != "unspecified"
)) if "health_effects" in df.columns else []
selected_effects = st.sidebar.multiselect("Filter by Health Effect", all_effects)

# Product filter
all_products = sorted(set(
    p.strip()
    for products in df["products"]
    for p in products.split("|")
    if p.strip() and p.strip() != "unspecified"
)) if "products" in df.columns else []
selected_products = st.sidebar.multiselect("Filter by Product", all_products)

# Ingredient filter
all_ingredients = sorted(set(
    i.strip()
    for ingredients in df["ingredients"]
    for i in ingredients.split("|")
    if i.strip() and i.strip() != "unspecified"
)) if "ingredients" in df.columns else []
selected_ingredients = st.sidebar.multiselect("Filter by Ingredient", all_ingredients)

# Keyword search
keyword = st.sidebar.text_input("Search in Title / Abstract", "")

# Apply filters
filtered = df[
    (df["toxicant"].apply(lambda x: any(t in [s.strip() for s in x.split("|")] for t in selected_toxicants))) &
    (df["pub_year"] >= year_range[0]) &
    (df["pub_year"] <= year_range[1])
]
if selected_organs:
    filtered = filtered[
        filtered["organs"].apply(lambda x: any(o in x for o in selected_organs))
    ]
if selected_effects and "health_effects" in filtered.columns:
    filtered = filtered[
        filtered["health_effects"].apply(lambda x: any(e in x for e in selected_effects))
    ]
if selected_products and "products" in filtered.columns:
    filtered = filtered[
        filtered["products"].apply(lambda x: any(p in x for p in selected_products))
    ]
if selected_ingredients and "ingredients" in filtered.columns:
    filtered = filtered[
        filtered["ingredients"].apply(lambda x: any(i in x for i in selected_ingredients))
    ]
if keyword:
    kw = keyword.lower()
    filtered = filtered[
        filtered["title"].str.lower().str.contains(kw) |
        filtered["abstract"].str.lower().str.contains(kw)
    ]

# Explode toxicant column for charts (papers matching multiple toxicants count under each)
chart_df = filtered.copy()
chart_df["toxicant"] = chart_df["toxicant"].str.split(r"\s*\|\s*", regex=True)
chart_df = chart_df.explode("toxicant")
chart_df["toxicant"] = chart_df["toxicant"].str.strip()
chart_df = chart_df[chart_df["toxicant"].isin(selected_toxicants)]

# ── Summary metrics ───────────────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Papers", len(filtered))
col2.metric("Toxicants", len(selected_toxicants))
col3.metric("Year Range", f"{year_range[0]} – {year_range[1]}")
col4.metric("Organs Tracked", len(all_organs))

st.divider()

# 1. Publication trend
st.subheader("Publication Trend")
trend = chart_df.groupby(["pub_year", "toxicant"]).size().reset_index(name="papers")
fig1 = px.bar(
    trend, x="pub_year", y="papers", color="toxicant", barmode="group",
    labels={"pub_year": "Year", "papers": "Papers Published", "toxicant": "Toxicant"},
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig1.update_layout(legend_title="Toxicant", margin=dict(t=20, b=20))
st.plotly_chart(fig1, width='stretch')

st.divider()

# 2. Papers per toxicant
st.subheader("Papers per Toxicant")
toxicant_counts = chart_df.groupby("toxicant").size().reset_index(name="count").sort_values("count", ascending=False)
fig2 = px.bar(
    toxicant_counts, x="toxicant", y="count",
    labels={"toxicant": "Toxicant", "count": "Total Papers"},
    color="toxicant",
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig2.update_layout(showlegend=False, margin=dict(t=20, b=20), bargap=0.5)
st.plotly_chart(fig2, width='stretch')

st.divider()

# 3. Organs affected
st.subheader("Organs Affected")
organ_counts = {}
for organs in filtered["organs"]:
    for organ in organs.split("|"):
        organ = organ.strip()
        if organ and organ != "unspecified":
            organ_counts[organ] = organ_counts.get(organ, 0) + 1

if organ_counts:
    organ_df = pd.DataFrame(
        sorted(organ_counts.items(), key=lambda x: x[1], reverse=True),
        columns=["organ", "count"]
    )
    fig3 = px.bar(
        organ_df, x="count", y="organ", orientation="h",
        labels={"count": "Papers", "organ": "Organ"},
        color_discrete_sequence=["#3a7ebf"],
    )
    fig3.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=20, b=20))
    st.plotly_chart(fig3, width='stretch')
else:
    st.info("No organ data for current filters.")

st.divider()

# 4. Top journals
st.subheader("Top Journals")
top_journals = (
    filtered[filtered["journal"] != ""]
    .groupby("journal").size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
    .head(15)
)
fig4 = px.bar(
    top_journals, x="count", y="journal", orientation="h",
    labels={"count": "Papers", "journal": "Journal"},
    color_discrete_sequence=["#5a9e6f"],
)
fig4.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=20, b=20))
st.plotly_chart(fig4, width='stretch')

# ── Chart row 3 ───────────────────────────────────────────────────────────────

# 5. Health effects
if "health_effects" in filtered.columns:
    st.subheader("Health Effects Distribution")
    effect_counts = {}
    for effects in filtered["health_effects"]:
        for effect in effects.split("|"):
            effect = effect.strip()
            if effect and effect != "unspecified":
                effect_counts[effect] = effect_counts.get(effect, 0) + 1

    if effect_counts:
        effect_df = pd.DataFrame(
            sorted(effect_counts.items(), key=lambda x: x[1], reverse=True),
            columns=["effect", "count"]
        )
        fig_effects = px.bar(
            effect_df, x="count", y="effect", orientation="h",
            labels={"count": "Papers", "effect": "Health Effect"},
            color_discrete_sequence=["#b5652b"],
        )
        fig_effects.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=20, b=20))
        st.plotly_chart(fig_effects, width='stretch')
    else:
        st.info("No health effect data for current filters.")

st.divider()

# ── Heatmap: toxicant × year ──────────────────────────────────────────────────

st.subheader("Research Density Heatmap")
st.caption("Papers published per year for each toxicant — darker = more research activity")

heatmap_data = (
    chart_df.groupby(["toxicant", "pub_year"])
    .size()
    .reset_index(name="count")
)

if not heatmap_data.empty:
    pivot = heatmap_data.pivot(index="toxicant", columns="pub_year", values="count").fillna(0)
    fig5 = px.imshow(
        pivot,
        labels=dict(x="Year", y="Toxicant", color="Papers"),
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    fig5.update_layout(margin=dict(t=20, b=20), coloraxis_colorbar=dict(title="Papers"))
    fig5.update_xaxes(tickangle=-45)
    st.plotly_chart(fig5, width='stretch')

st.divider()

# ── Data tables ───────────────────────────────────────────────────────────────

REVIEW_KEYWORDS = [
    "review", "meta-analysis", "meta analysis", "systematic review",
    "narrative review", "scoping review", "literature review", "overview"
]

def is_review(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in REVIEW_KEYWORDS)

cols = ["pmid", "title", "pub_year", "toxicant", "journal", "organs"]
if "health_effects" in filtered.columns:
    cols.append("health_effects")
if "products" in filtered.columns:
    cols.append("products")
if "ingredients" in filtered.columns:
    cols.append("ingredients")
if "inference" in filtered.columns:
    cols.append("inference")

display_df = filtered[cols].copy()
display_df["pmid_link"] = display_df["pmid"].apply(
    lambda x: f"https://pubmed.ncbi.nlm.nih.gov/{x}/"
)

# Put the link column first, hide the raw pmid column
display_df = display_df[["pmid_link"] + [c for c in display_df.columns if c not in ("pmid_link", "pmid")]]

col_config = {
    "pmid_link": st.column_config.LinkColumn("Open", display_text="🔗 Open", width="small"),
    "title": st.column_config.TextColumn("Title", width="large"),
    "pub_year": st.column_config.NumberColumn("Year", format="%d"),
    "toxicant": "Toxicant",
    "journal": "Journal",
    "organs": "Organs",
}
if "health_effects" in display_df.columns:
    col_config["health_effects"] = "Health Effects"
if "products" in display_df.columns:
    col_config["products"] = "Products"
if "ingredients" in display_df.columns:
    col_config["ingredients"] = "Ingredients"
if "inference" in display_df.columns:
    col_config["inference"] = st.column_config.TextColumn("Inference", width="medium")

display_df = display_df.sort_values("pub_year", ascending=True)
is_review_mask = display_df["title"].apply(is_review)
research_df = display_df[~is_review_mask]
review_df = display_df[is_review_mask]

st.subheader(f"Research Papers ({len(research_df)} results)")
st.dataframe(research_df, column_config=col_config, width='stretch', hide_index=True, row_height=80)

st.subheader(f"Review Papers ({len(review_df)} results)")
if review_df.empty:
    st.info("No review papers found for the current filters.")
else:
    st.dataframe(review_df, column_config=col_config, width='stretch', hide_index=True, row_height=80)

# ── Relevance tables ───────────────────────────────────────────────────────────

if "relevant" in filtered.columns:
    rel_cols = ["pmid", "title", "pub_year", "toxicant", "journal", "organs"]
    if "relevant" in filtered.columns:
        rel_cols.append("relevant")
    if "relevance_reason" in filtered.columns:
        rel_cols.append("relevance_reason")

    rel_display = filtered[rel_cols].copy()
    rel_display["pmid_link"] = rel_display["pmid"].apply(
        lambda x: f"https://pubmed.ncbi.nlm.nih.gov/{x}/"
    )
    rel_display = rel_display[["pmid_link"] + [c for c in rel_display.columns if c not in ("pmid_link", "pmid")]]
    rel_display = rel_display.sort_values("pub_year", ascending=True)

    rel_col_config = {
        "pmid_link": st.column_config.LinkColumn("Open", display_text="🔗 Open", width="small"),
        "title": st.column_config.TextColumn("Title", width="large"),
        "pub_year": st.column_config.NumberColumn("Year", format="%d"),
        "toxicant": "Toxicant",
        "journal": "Journal",
        "organs": "Organs",
    }
    if "relevant" in rel_display.columns:
        rel_col_config["relevant"] = st.column_config.TextColumn("Relevant", width="small")
    if "relevance_reason" in rel_display.columns:
        rel_col_config["relevance_reason"] = st.column_config.TextColumn("Relevance Reason", width="large")

    relevant_df = rel_display[rel_display["relevant"].str.lower().str.strip() == "yes"]
    not_relevant_df = rel_display[rel_display["relevant"].str.lower().str.strip() == "no"]

    st.subheader(f"Relevant Papers ({len(relevant_df)} results)")
    if relevant_df.empty:
        st.info("No relevant papers found for the current filters.")
    else:
        st.dataframe(relevant_df, column_config=rel_col_config, width='stretch', hide_index=True, row_height=80)

    st.subheader(f"Non-Relevant Papers ({len(not_relevant_df)} results)")
    if not_relevant_df.empty:
        st.info("No non-relevant papers found for the current filters.")
    else:
        st.dataframe(not_relevant_df, column_config=rel_col_config, width='stretch', hide_index=True, row_height=80)
