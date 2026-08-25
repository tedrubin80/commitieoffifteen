"""Streamlit explorer for Committee of Fifteen records."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ENRICHED = DATA / "processed" / "committee_of_fifteen_enriched.parquet"


@st.cache_data
def load_data() -> pd.DataFrame:
    if ENRICHED.exists():
        return pd.read_parquet(ENRICHED)
    return pd.read_csv(DATA / "processed" / "committee_of_fifteen_index.csv")


def main() -> None:
    st.set_page_config(page_title="Committee of Fifteen", layout="wide")
    st.title("Committee of Fifteen — NYC vice investigation records (~1900)")
    st.caption("NYPL Manuscripts & Archives · ~1,731 digitized affidavits by address & precinct")

    df = load_data()
    st.metric("Total items", len(df))
    c1, c2, c3 = st.columns(3)
    if "title_kind" in df.columns:
        c1.metric("Address records", int((df["title_kind"] == "address").sum()))
        c2.metric("Precincts", df["precinct"].nunique(dropna=True))
        c3.metric("With OCR", int(df.get("has_ocr", pd.Series(False)).sum()))

    if "precinct" in df.columns:
        st.subheader("Records by police precinct")
        pc = df["precinct"].value_counts().reset_index()
        pc.columns = ["precinct", "count"]
        fig = px.bar(pc, x="precinct", y="count", title="Affidavits per precinct")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Browse records")
    filters = st.columns(4)
    precincts = ["(all)"] + sorted(df["precinct"].dropna().unique()) if "precinct" in df.columns else ["(all)"]
    sel_precinct = filters[0].selectbox("Precinct", precincts)
    kinds = ["(all)"] + sorted(df["title_kind"].dropna().unique()) if "title_kind" in df.columns else ["(all)"]
    sel_kind = filters[1].selectbox("Title type", kinds)
    q = filters[2].text_input("Search title")

    view = df.copy()
    if sel_precinct != "(all)" and "precinct" in view.columns:
        view = view[view["precinct"] == sel_precinct]
    if sel_kind != "(all)" and "title_kind" in view.columns:
        view = view[view["title_kind"] == sel_kind]
    if q:
        col = "mods_title" if "mods_title" in view.columns else "title"
        view = view[view[col].astype(str).str.contains(q, case=False, na=False)]

    cols = [c for c in ["mods_title", "precinct", "title_kind", "date_start", "uuid"] if c in view.columns]
    st.dataframe(view[cols].head(500), use_container_width=True)

    st.subheader("Sample scan")
    if len(view):
        pick = st.selectbox("Item", view["uuid"].tolist())
        img = DATA / "images" / f"{pick}.jpg"
        ocr = DATA / "ocr" / f"{pick}.txt"
        col_a, col_b = st.columns(2)
        if img.exists():
            col_a.image(str(img), caption=view.loc[view["uuid"] == pick, "mods_title"].iloc[0])
        if ocr.exists():
            col_b.text_area("OCR text", ocr.read_text(), height=400)
        else:
            col_b.info("No OCR yet — run `python src/ocr.py` in the container.")


if __name__ == "__main__":
    main()
