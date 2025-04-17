import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime

#constants
min_date = datetime.date(1981, 9, 26)
max_date = datetime.date.today()

# App title
st.title("Weather Data Dashboard 🌦️")
st.write("Explore historical weather data for your selected locations!")

# User input: multiple cities
st.subheader("Enter city names (one per line):")
städte_input = st.text_area("Cities:", placeholder="e.g.\nBerlin\nParis\nLondon")
städte_input = städte_input.replace(" ","")
ort = städte_input.splitlines() if städte_input else []
start = st.date_input("Startdatum", value=datetime.date(2024, 1, 1), min_value=min_date )
end = st.date_input("Enddatum", value=datetime.date(2024, 12, 31), max_value=max_date )

if start > end:
    st.error("Das Startdatum darf nicht nach dem Enddatum liegen.")
    st.stop()
    
# User input: weather parameter selection
auswahl_parameter = st.multiselect(
    "Select a weather parameter to visualize:",
    [
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "apparent_temperature",
        "pressure_msl",
        "surface_pressure",
        "precipitation",
        "rain",
        "snowfall",
        "cloud_cover",
        "shortwave_radiation",
        "diffuse_radiation",
        "sunshine_duration",
        "wind_speed_10m",
        "wind_speed_100m",
        "et0_fao_evapotranspiration",
        "snow_depth",
        "soil_temperature_0_to_7cm",
        "soil_temperature_7_to_28cm",
        "soil_temperature_28_to_100cm",
        "soil_temperature_100_to_255cm",
        "soil_moisture_0_to_7cm",
        "soil_moisture_7_to_28cm",
        "soil_moisture_28_to_100cm",
        "soil_moisture_100_to_255cm"
    ]
)

# Helper functions
def geodaten_abfragen(ort):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={ort}&count=1"
    response = requests.get(url)
    daten = response.json()
    if "results" in daten:
        latitude = daten["results"][0]["latitude"]
        longitude = daten["results"][0]["longitude"]
        return latitude, longitude
    else:
        st.warning(f"Location '{ort}' not found.")
        return None, None

def url_past(lat, long, start, end, param):
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={long}&hourly={param}"
        f"&start_date={start}&end_date={end}"
    )
    response = requests.get(url)
    daten = response.json()
    zeitleiste = daten["hourly"]["time"]
    paramleiste = daten["hourly"].get(param, [])
    return zeitleiste, paramleiste

def tagesmittelwert(zeitleiste, werteleiste, parameter):
    df = pd.DataFrame({"Zeit": zeitleiste, parameter: werteleiste})
    df["Zeit"] = pd.to_datetime(df["Zeit"])
    df["Datum"] = df["Zeit"].dt.date
    df = df.dropna(subset=[parameter])
    df_gruppe = df.groupby("Datum").mean().reset_index()
    return df_gruppe  # Gib den DataFrame direkt zurück

# Process and plot data
     
if st.button("Show weather data"):
        if not ort:
            st.warning("Please enter at least one city.")
        else:
            for parameter in auswahl_parameter:
                plt.figure(figsize=(12, 6))  # 📌 Neu: pro Parameter ein Plot
                for ort_element in ort:
                    lat, long = geodaten_abfragen(ort_element)
                    if lat is None or long is None:
                        continue
                    zeitleiste, werteleiste = url_past(lat, long, start, end, parameter)
                    if not zeitleiste or not werteleiste:
                        continue
                    df_param = tagesmittelwert(zeitleiste, werteleiste, parameter)
                    df_all = df_all.merge(df_parameter[["Datum", param]], on="Datum", how="outer")
    
                    # 🔁 Für jede Stadt eine Linie
                    plt.plot(df_mittelwert["Datum"], df_mittelwert[parameter], label=ort_element)
                    st.write(f"**{ort_element}** (parameter): Min = {df_mittelwert[parameter].min():.2f}, Max = {df_mittelwert[parameter].max():.2f}")
                    st.dataframe(df_mittelwert)
                
                plt.plot(df_all["Datum"], df_all[param], label=f"{stadt} – {param}")
                
                # 📊 Titel & Legende pro Parameter
                plt.title(f"{parameter.replace('_', ' ').title()} (Daily Average)")
                plt.xlabel("Date")
                plt.ylabel(parameter.replace('_', ' ').title())
                plt.legend()
                plt.grid(True)
                plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
                plt.gcf().autofmt_xdate()
                st.pyplot(plt)
