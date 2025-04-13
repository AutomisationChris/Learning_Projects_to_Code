import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# App title
st.title("Weather Data Dashboard 🌦️")
st.write("Explore historical weather data for your selected locations!")

# User input: multiple cities
st.subheader("Enter city names (one per line):")
städte_input = st.text_area("Cities:", placeholder="e.g.\nBerlin\nParis\nLondon")
ort = städte_input.splitlines().replace(" ","") if städte_input else []

# User input: weather parameter selection
parameter = st.selectbox(
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

def url_past(lat, long, param):
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={long}&hourly={param}"
        f"&start_date=2024-01-01&end_date=2025-01-01"
    )
    response = requests.get(url)
    daten = response.json()
    zeitleiste = daten["hourly"]["time"]
    paramleiste = daten["hourly"].get(param, [])
    return zeitleiste, paramleiste

def tagesmittelwert(zeitleiste, werteleiste):
    df = pd.DataFrame({"Zeit": zeitleiste, "Wert": werteleiste})
    df["Zeit"] = pd.to_datetime(df["Zeit"])
    df["Datum"] = df["Zeit"].dt.date
    df = df.dropna(subset=["Wert"])
    df_gruppe = df.groupby("Datum").mean().reset_index()
    return df_gruppe["Datum"], df_gruppe["Wert"]

# Process and plot data
if st.button("Show weather data"):
    if not ort:
        st.warning("Please enter at least one city.")
    else:
        plt.figure(figsize=(12, 6))
        for ort_element in ort:
            lat, long = geodaten_abfragen(ort_element)
            if lat is None or long is None:
                continue
            zeitleiste, werteleiste = url_past(lat, long, parameter)
            if not zeitleiste or not werteleiste:
                st.warning(f"No data available for {ort_element} and parameter '{parameter}'.")
                continue
            zeitleiste, werteleiste = tagesmittelwert(zeitleiste, werteleiste)

            # Plotting
            plt.plot(zeitleiste, werteleiste, label=ort_element)

            # Output min/max info
            st.write(f"**{ort_element}:** Min = {min(werteleiste):.2f}, Max = {max(werteleiste):.2f}")

        plt.title(f"{parameter.replace('_', ' ').title()} (Daily Average)")
        plt.xlabel("Date")
        plt.ylabel(parameter.replace('_', ' ').title())
        plt.legend()
        plt.grid(True)
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        plt.gcf().autofmt_xdate()
        st.pyplot(plt)

