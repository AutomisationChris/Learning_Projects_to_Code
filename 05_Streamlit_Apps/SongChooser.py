# Liedauswahl-Tool basierend auf der Liederdatenbank

import pandas as pd
import streamlit as st
import os

st.title("🎸 Liedauswahl mit Akkorddiagrammen und Übungsplan")

# CSV-Datei aus dem lokalen Projektverzeichnis laden
csv_path = os.path.join("Liederdatenbank_gesamt.csv")
if not os.path.exists(csv_path):
    st.error(f"❌ Datei '{csv_path}' nicht gefunden. Bitte im gleichen Ordner wie das Skript ablegen.")
    st.stop()

# Gesamtdatenbank laden
df = pd.read_csv(csv_path)

# Akkorddiagramm-Linkgenerator (vereinfachte Form)
def akkord_diagramm_links(akkord_string):
    basis = "https://www.ultimate-guitar.com/search.php?search_type=title&value="
    return [f"{basis}{a}" for a in akkord_string.split(", ")]

# Filteroptionen
komplexitaet = st.multiselect("Wähle die Komplexität:", options=df["Komplexität"].unique(), default=df["Komplexität"].unique())
kategorie = st.multiselect("Kategorie:", options=df["Kategorie"].unique() if "Kategorie" in df.columns else [], default=df["Kategorie"].unique() if "Kategorie" in df.columns else [])
barre = st.selectbox("Barrégriffe enthalten?", options=["egal", "Ja", "Nein", "Gelegentlich"])

# Filter anwenden
filtered = df[df["Komplexität"].isin(komplexitaet)]
if "Kategorie" in df.columns:
    filtered = filtered[filtered["Kategorie"].isin(kategorie)]
if barre != "egal":
    filtered = filtered[filtered["Barrégriff"] == barre]

st.write("### Gefundene Songs:")
for _, row in filtered.iterrows():
    st.subheader(row["Songtitel"])
    st.markdown(f"**Komplexität:** {row['Komplexität']}  |  **Akkorde:** {row['Akkorde']}  |  **Barrégriff:** {row['Barrégriff']}")
    if "YouTube" in row and pd.notna(row['YouTube']):
        st.markdown(f"[🎬 YouTube ansehen]({row['YouTube']})")
    st.markdown("**Akkorddiagramme:**")
    links = akkord_diagramm_links(row["Akkorde"])
    for link in links:
        st.markdown(f"- [ {link.split('=')[-1]} ]({link})")
    st.markdown("\n---")

# Übungsplan-Vorschlag anzeigen
st.sidebar.title("🎯 Automatischer Übungsplan")
st.sidebar.markdown("Wähle täglich 2 Lieder:")
uebungsplan = filtered.sample(min(2, len(filtered))) if len(filtered) > 0 else pd.DataFrame()
for _, song in uebungsplan.iterrows():
    st.sidebar.markdown(f"- ✅ **{song['Songtitel']}**")
