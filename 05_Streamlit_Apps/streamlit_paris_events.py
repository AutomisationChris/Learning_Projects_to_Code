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

tag_emojis = {
    "atelier": "🎨 Kunst",
    "enfants": "🧒 Kinder",
    "sport": "🏅 Sport",
    "concert": "🎵 Konzert",
    "théâtre": "🎭 Theater",
    "expo": "🖼️ Expo",
    "photo": "📷 Photo",
    "art contemporain": "🌀 Moderne Kunst",
    "danse": "💃 Tanzveranstaltung",
    "cirque": "🎪 Zirkus",
    "bd": "📚 Comics",
    "littérature": "📖 Literatur",
    "festival": "🎉 Festival",
    "sciences": "🔬 Naturwissenschaften",
    "innovation": "💡 Innovation",
    "histoire": "🏰 Historisches",
    "nature": "🌿 Natur",
    "balade urbaine": "🚶 Balade urbaine",
    "loisirs": "🧩 Loisirs",
    "nuit": "🌙 Party, Party, Party",
    "gourmand": "🍽️ Gaumenfreuden",
    "spectacle musical": "🎶 Musikalisches Spektakel",
    "solidarité": "🤝 Solidarische Aktivitäten",
    "humour": "😂 Humour",
    "salon": "🏛️ Salon",
    "conférence": "🎤 Konferenz",
    "lgbt": "🏳️‍🌈 LGBT",
    "ecrans": "🖥️ Écrans",
    "peinture": "🖌️ Malen",
    "santé": "❤️ Santé",
    "street-art": "🧱 Street-Art",
    "brocante": "🧺 Brocante",
    "": "❓ Unbekannt"
}


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
    qfap_tags = [tag.strip().lower() for tag in qfap_tags_raw.split(";")]
    lat, long = adress_2_geocode(address)
    indoor = event['fields'].get('event_indoor')
    
    
    col1, col2 = st.columns([2, 3])
    with col1:
        if event_pic:
            st.markdown(f'<a href="{event_url}"><img src="{event_pic}" width="500"></a>', unsafe_allow_html=True)
        else:
            st.write("📸 Kein Bild vorhanden.")

    with col2:
        st.markdown(f"### 🎉 [{title}]({event_url})")
        st.markdown(f"📍 **{address_name}**, {address_street}, {address_city}")
        if price_type == "gratuit":
            st.markdown(f"🆓 Kostenloser Eintritt")
        elif price_type == "payant":
            st.markdown(f"💶💳 Kostenpflichtig")
        else:
            st.markdown(f"❓ Keine Angabe zum Eintrittspreis")
        if indoor == 1:
           st.markdown("🏠 Indoor")
        elif indoor == 0:
           st.markdown("🌳 Outdoor")
        else:
           st.markdown("❓ Keine Angabe zum Veranstaltungsort")
        emojis = [tag_emojis.get(tag, tag.title()) for tag in qfap_tags]
        st.markdown(" | ".join(emojis))
        

   
