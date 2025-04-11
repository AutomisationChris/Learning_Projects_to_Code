import requests
import matplotlib.pyplot as plt
import pandas as pd 

def wetter_abfragen(ort):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={ort}&count=1"
    response = requests.get(url)
    daten = response.json()

    if "results" in daten:
        latitude = daten["results"][0]["latitude"]
        longitude = daten["results"][0]["longitude"]

        wetter_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
        wetter_response = requests.get(wetter_url)
        wetterdaten = wetter_response.json()
        
        hoehe = wetterdaten["elevation"]
        temperatur = wetterdaten["current_weather"]["temperature"]
        wind = wetterdaten["current_weather"]["windspeed"]
        wind_direction = wetterdaten["current_weather"]["winddirection"]
        print(f"Das aktuelle Wetter in {ort} ({hoehe} m Höhe über dem Meeresspiegel):")
        print(f"Temperatur: {temperatur}°C")
        print(f"Windgeschwindigkeit: {wind} km/h")
        print(f"Windrichtung: {wind_direction} °")
    else:
        print("Ort nicht gefunden.")

def geodaten_abfragen(ort):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={ort}&count=1"
    response = requests.get(url)
    daten = response.json()

    if "results" in daten:
        latitude = daten["results"][0]["latitude"]
        longitude = daten["results"][0]["longitude"]
        return latitude, longitude
    else:
        print("Ort nicht gefunden.")
        

def url_builder(ort, parameter):
    lat, long = geodaten_abfragen(ort)
    url = (
      f"https://api.open-meteo.com/v1/forecast?"
      f"latitude={lat}&"
      f"longitude={long}&"
      f"minutely_15=temperature_2m"
      f"&past_days=92"
    )
    response = requests.get(url)
    daten = response.json()
    zeitleiste = daten["minutely_15"]["time"]
    paramleiste = daten["minutely_15"]["temperature_2m"]
    return zeitleiste, paramleiste
    
def url_past(ort, param):
  lat, long = geodaten_abfragen(ort)
  url = (
      f"https://archive-api.open-meteo.com/v1/archive?"
      f"latitude={-2.7623779854198993}&"
      f"longitude={-79.0722852711649}&"
      f"hourly={param}&"
      f"start_date=2024-01-01&"
      f"end_date=2025-01-01"
    )
  response = requests.get(url)
  daten = response.json()
  zeitleiste = daten["hourly"]["time"]
  paramleiste = daten["hourly"][param]
  return zeitleiste, paramleiste

def tagesmittelwert(zeitleiste, temperaturleiste):
    df = pd.DataFrame({"Zeit": zeitleiste, "Temperatur": temperaturleiste})
    df["Zeit"] = pd.to_datetime(df["Zeit"])
    df["Datum"] = df["Zeit"].dt.date

    # Entferne ungültige Daten
    df = df.dropna(subset=["Temperatur"])

    # Berechne Tagesmittelwert
    df_gruppe = df.groupby("Datum").mean().reset_index()

    return df_gruppe["Datum"], df_gruppe["Temperatur"]
   
def plot_parameter(zeitleiste, werteleiste, ort, param):
    zeitleiste, werteleiste = url_past(ort_element, param)
    zeitleiste, werteleiste = tagesmittelwert(zeitleiste, werteleiste)
    if len(zeitleiste) == 0 or len(werteleiste) == 0:
        print(f"⚠️ Keine gültigen Daten für {ort}.")
        return

    plt.figure(figsize=(12, 5))
    plt.plot(zeitleiste, werteleiste, color="tab:orange", label="Tagesmittel")

    plt.title(f"{param} in {ort} (Tagesmittel)")
    plt.xlabel("Datum")
    plt.ylabel("{param} (%)")

    # 💡 Verbesserte X-Achse: automatische Datumsformatierung!
    import matplotlib.dates as mdates
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.gcf().autofmt_xdate()  # Automatische Drehung

    # Optional: saubere Y-Achsen-Grenzen
    plt.ylim(min(werteleiste) - 2, max(werteleiste) + 2)

    plt.grid(True)
    plt.tight_layout()
    plt.legend()
    plt.show()
    print(f"{ort_element}: Min={min(werteleiste)}, Max={max(werteleiste)}")
  
        
def plot_vergleich(ort):
  plt.figure()
  for temp_ort in ort:
    zeitleiste, paramleiste = url_builder(temp_ort, parameter="test")
    plt.plot(zeitleiste, paramleiste, label = temp_ort)
    bplt.title(f"Vergleich von Temperatur in verschiedenen Städten")
    plt.xlabel("Datum")
    plt.ylabel("Temperatur")
    plt.xticks(ticks=range(0, len(zeitleiste), 100), 
           labels=zeitleiste[::100], rotation=45)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
        
# def wetter_historical(ort):
abbruch = ""
ort = []
parameter = ""
while abbruch != "n":
  ort_temp = input("Für welche Stadt möchtest du das Wetter wissen? ")
  ort.append(ort_temp)
  abbruch = input("Möchtest du das Wetter einer weiteren Stadt wissen?")
for ort_element in ort:
  zeitleiste, werteleiste = url_builder(ort_element, parameter)
  print(len(werteleiste))
  #plot_temperature(zeitleiste, werteleiste,ort_element)

#plot_vergleich(ort)  
print("*****************************************************************")
for ort_element in ort:
  
  plot_parameter(zeitleiste, werteleiste, ort_element, param="relative_humidity_2m")
  
  
  plot_parameter(zeitleiste, werteleiste, ort_element, param="temperature_2m")
  
  plot_parameter(zeitleiste, werteleiste, ort_element, param="dew_point_2m")
  
  plot_parameter(zeitleiste, werteleiste, ort_element, param="apparent_temperature")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="pressure_msl")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="surface_pressure")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="precipitation")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="rain")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="snowfall")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="cloud_cover")
  
  plot_parameter(zeitleiste, werteleiste, ort_element, param="dew_point_2m")
  
  plot_parameter(zeitleiste, werteleiste, ort_element, param="shortwave_radiation")
  #plot_parameter(zeitleiste, werteleiste, ort_element, param="direct_radiation")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="diffuse_radiation")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="sunshine_duration")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="wind_speed_10m")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="wind_speed_100m")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="et0_fao_evapotranspiration")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="snow_depth")
  

  plot_parameter(zeitleiste, werteleiste, ort_element, param="soil_temperature_0_to_7cm")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="soil_temperature_7_to_28cm")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="soil_temperature_28_to_100cm")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="soil_temperature_100_to_255cm")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="soil_moisture_0_to_7cm")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="soil_moisture_7_to_28cm")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="soil_moisture_28_to_100cm")
  plot_parameter(zeitleiste, werteleiste, ort_element, param="soil_moisture_100_to_255cm")
  
  
  
