import streamlit as st
import requests
from requests.utils import quote

def adress_2_geocode(address):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={address}&count=1"
    response = requests.get(url)
    daten = response.json()
    if "results" in daten:
        latitude = daten["results"][0]["latitude"]
        longitude = daten["results"][0]["longitude"]
        return latitude, longitude
    else:
        st.warning(f"Location '{address}' not found.")
        return None, None

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
    price_type = event['fields'].get('price_type', '')
    qfap_tags_raw = event['fields'].get('qfap_tags', '')
    address = f"{address_city}"
    qfap_tags = [tag.strip().lower() for tag in tags_raw.split(";")]
    lat, long = adress_2_geocode(address)
    indoor = event['fields'].get('event_indoor')
    
    
    col1, col2 = st.columns([2, 3])
    with col1:
        if event_pic:
            st.markdown(f'<a href="{event_url}"><img src="{event_pic}"></a>', unsafe_allow_html=True)
        else:
            st.write("📸 Kein Bild vorhanden.")

    with col2:
        st.markdown(f"### 🎉 [{title}]({event_url})")
        st.markdown(f"📍 **{address_name}**, {address_street}, {address_city}")
        st.markdown(f"{lat},{long}")
        st.markdown(f"{qfap_tags}")
        if price_type == "gratuit":
            st.markdown(f"🆓 Kostenloser Eintritt")
        elif price_type == "payant":
            st.markdown(f"💶💳 Kostenpflichtig")
        else:
            st.markdown(f"❓ Keine Angabe")
        if indoor == 1:
           st.markdown("🏠 Indoor")
        elif indoor == 0:
           st.markdown("🌳 Outdoor")
        else:
           st.markdown("❓ Nicht angegeben")

        

   
