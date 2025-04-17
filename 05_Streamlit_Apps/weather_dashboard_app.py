import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime

# --- Konstanten ---
min_date = datetime.date(1981, 9, 26)
max_date = datetime.date.today()

# --- App Titel & Beschreibung ---
st.title("Weather Data Dashboard 🌦️")
st.write("Explore historical weather data for your selected locations!")

# --- Eingabe Städte ---
st.subheader("Enter city names (one per line):")
städte_input = st.text_area("Cities:", placeholder="e.g.\nBerlin\nParis\nLondon")
städte_input = städte_input.replace(" ", "")
ort = städte_input.splitlines() if städte_input else []

# --- Datumsbereich ---
start = st.date_input("Startdatum", value=datetime.date(2024, 1, 1), min_value=min_date)
end = st.date_input("Enddatum", value=datetime.date(2024, 12, 31), max_value=max_date)

if start > end:
    st.error("Das Startdatum darf nicht nach dem Enddatum liegen.")
    st.stop()

# --- Wetterparameter Auswahl ---
auswahl_parameter = st.multiselect(
    "Select weather parameters to visualize:",
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

# --- Hilfsfunktionen ---
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
    return df_gruppe

# --- Hauptlogik ---
if st.button("Show weather data"):
    if not ort:
        st.warning("Please enter at least one city.")
    elif not auswahl_parameter:
        st.warning("Please select at least one weather parameter.")
    else:
        for ort_element in ort:
            lat, long = geodaten_abfragen(ort_element)
            if lat is None or long is None:
                continue

            df_all = pd.DataFrame()
            for parameter in auswahl_parameter:
                zeitleiste, werteleiste = url_past(lat, long, start, end, parameter)
                if not zeitleiste or not werteleiste:
                    st.warning(f"No data available for {ort_element} and '{parameter}'")
                    continue
                df_param = tagesmittelwert(zeitleiste, werteleiste, parameter)

                if df_all.empty:
                    df_all["Datum"] = df_param["Datum"]

                df_all = df_all.merge(df_param[["Datum", parameter]], on="Datum", how="outer")

            if not df_all.empty:
                # --- Plot pro Stadt mit allen Parametern ---
                plt.figure(figsize=(12, 6))
                for parameter in auswahl_parameter:
                    if parameter in df_all.columns:
                        plt.plot(df_all["Datum"], df_all[parameter], label=parameter)

                plt.title(f"Wetterparameter für {ort_element}")
                plt.xlabel("Datum")
                plt.ylabel("Wert")
                plt.legend()
                plt.grid(True)
                plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
                plt.gcf().autofmt_xdate()
                st.pyplot(plt)

                st.write(f"**{ort_element} – Datenübersicht:**")
                st.dataframe(df_all)
