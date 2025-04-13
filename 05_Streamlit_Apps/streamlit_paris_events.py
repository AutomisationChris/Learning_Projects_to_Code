import streamlit as st
import requests

# Titel der App
st.title("🎉 Paris Event Dashboard")

# Beschreibung
st.markdown("Erkunde aktuelle Veranstaltungen in Paris – direkt aus der Open Data API!")

# Eingabefeld für Anzahl Events
anzahl_events = st.slider("Wie viele Events möchtest du sehen?", min_value=1, max_value=20, value=10)

# API Request
url = f"https://opendata.paris.fr/api/records/1.0/search/?dataset=que-faire-a-paris-&rows={anzahl_events}"
response = requests.get(url)
daten = response.json()

st.subheader("📅 Veranstaltungen:")

for event in daten['records']:
    title = event['fields'].get('title', 'Kein Titel')
    address_name = event['fields'].get('address_name', 'Ort unbekannt')
    address_street = event['fields'].get('address_street', '')
    address_city = event['fields'].get('address_city', '')
    event_url = event['fields'].get('url', '')
    event_pic = event['fields'].get('cover_url','')
     col1, col2 = st.columns([2, 3])
    with col1:
        if event_pic:
            st.image(event_pic, use_column_width=True)
        else:
            st.write("📸 Kein Bild vorhanden.")

    with col2:
        st.markdown(f"### 🎉 {title}")
        st.markdown(f"📍 **{address_name}**, {address_street}, {address_city}")
        st.markdown(f"[🔗 Mehr Infos]({event_url})")

   
