import time
import zipfile
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# -------------------------
# Helpers
# -------------------------
def gtfs_time_to_sec(series: pd.Series) -> np.ndarray:
    # Accepts times like "5:27:30" or "27:12:00"
    parts = series.astype(str).str.split(":", expand=True)
    return (parts[0].astype(int).to_numpy() * 3600
            + parts[1].astype(int).to_numpy() * 60
            + parts[2].astype(int).to_numpy())

def sec_to_hms(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# -------------------------
# Data loading / preprocessing (cached)
# -------------------------
@st.cache_data(show_spinner=False)
def load_base_tables():
    stops = pd.read_csv("stops.txt", usecols=["stop_id", "stop_lat", "stop_lon"])
    routes = pd.read_csv("routes.txt")
    trips = pd.read_csv("trips_ubahn.txt")
    cald = pd.read_csv("calendar_dates_ubahn.txt")
    return stops, routes, trips, cald

@st.cache_data(show_spinner=False)
def load_stop_times_from_zip(zip_path="stop_times_ubahn.zip"):
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open("stop_times_ubahn.txt") as f:
            return pd.read_csv(f)

@st.cache_data(show_spinner=False)
def build_segments_for_date(date_yyyymmdd: int):
    stops, routes, trips, cald = load_base_tables()
    stop_times = load_stop_times_from_zip()

    # U-Bahn Routes (dein Feed: agency_id=796, route_type=400, route_short_name U*)
    routes_u = routes[
        (routes["agency_id"] == 796) &
        (routes["route_type"] == 400) &
        (routes["route_short_name"].astype(str).str.match(r"U\d+"))
    ][["route_id", "route_short_name", "route_color"]].copy()

    # Active services for selected date (bei dir läuft's über calendar_dates)
    active_services = set(
        cald.loc[(cald["date"] == date_yyyymmdd) & (cald["exception_type"] == 1), "service_id"]
    )

    trips_u = trips.merge(routes_u, on="route_id", how="inner")
    trips_u = trips_u[trips_u["service_id"].isin(active_services)][["trip_id", "route_short_name", "route_color"]]

    trip_ids = set(trips_u["trip_id"].unique())
    st_active = stop_times[stop_times["trip_id"].isin(trip_ids)].copy()

    # Join stop coords
    st_active = st_active.merge(stops, on="stop_id", how="left")
    st_active = st_active.dropna(subset=["stop_lat", "stop_lon"])

    # Parse times
    st_active["dep_sec"] = gtfs_time_to_sec(st_active["departure_time"])
    st_active.sort_values(["trip_id", "stop_sequence"], inplace=True)

    # Build segments (between consecutive stops in each trip)
    g = st_active.groupby("trip_id", sort=False)
    st_active["lat1"] = g["stop_lat"].shift(-1)
    st_active["lon1"] = g["stop_lon"].shift(-1)
    st_active["t1"] = g["dep_sec"].shift(-1)

    seg = st_active.dropna(subset=["lat1", "lon1", "t1"]).copy()
    seg.rename(columns={"stop_lat": "lat0", "stop_lon": "lon0", "dep_sec": "t0"}, inplace=True)

    # Keep only forward-in-time segments
    seg = seg[seg["t1"] > seg["t0"]]

    # Add route info (for color)
    seg = seg.merge(trips_u, on="trip_id", how="left").dropna(subset=["route_short_name", "route_color"])

    # Palette mapping (only 8 lines -> super cheap)
    line_names = sorted(seg["route_short_name"].unique(), key=lambda x: int(x[1:]))
    palette = ["#" + routes_u.loc[routes_u["route_short_name"] == ln, "route_color"].iloc[0] for ln in line_names]
    idx_map = {ln: i for i, ln in enumerate(line_names)}
    seg["route_idx"] = seg["route_short_name"].map(idx_map).astype(int)

    # Stops used (for plotting)
    used_stop_ids = st_active["stop_id"].unique()
    used_stops = stops[stops["stop_id"].isin(used_stop_ids)].copy()

    # Arrays for fast animation
    arrays = {
        "t0": seg["t0"].to_numpy(dtype=np.int32),
        "t1": seg["t1"].to_numpy(dtype=np.int32),
        "lat0": seg["lat0"].to_numpy(dtype=np.float64),
        "lon0": seg["lon0"].to_numpy(dtype=np.float64),
        "lat1": seg["lat1"].to_numpy(dtype=np.float64),
        "lon1": seg["lon1"].to_numpy(dtype=np.float64),
        "route_idx": seg["route_idx"].to_numpy(dtype=np.int8),
        "palette": palette,
        "line_names": line_names,
        "stops_lat": used_stops["stop_lat"].to_numpy(dtype=np.float64),
        "stops_lon": used_stops["stop_lon"].to_numpy(dtype=np.float64),
    }

    arrays["t_min"] = int(seg["t0"].min())
    arrays["t_max"] = int(seg["t1"].max())

    # Plot bounds (+ padding)
    min_lat, max_lat = float(used_stops["stop_lat"].min()), float(used_stops["stop_lat"].max())
    min_lon, max_lon = float(used_stops["stop_lon"].min()), float(used_stops["stop_lon"].max())
    pad_lat = (max_lat - min_lat) * 0.05
    pad_lon = (max_lon - min_lon) * 0.05
    arrays["bounds"] = (min_lon - pad_lon, max_lon + pad_lon, min_lat - pad_lat, max_lat + pad_lat)

    return arrays

# -------------------------
# Streamlit UI
# -------------------------
st.title("Berlin U-Bahn — 1 Minute = 1 Betriebstag")

stops, routes, trips, cald = load_base_tables()
available_dates = sorted(cald.loc[cald["exception_type"] == 1, "date"].unique().tolist())

date = st.sidebar.selectbox("Datum (YYYYMMDD)", available_dates, index=0)
fps = st.sidebar.slider("FPS", min_value=1, max_value=10, value=4)
duration_sec = st.sidebar.slider("Dauer der Animation (s)", min_value=10, max_value=120, value=60)

data = build_segments_for_date(int(date))

st.caption(
    f"Datum {date} · Sim-Zeit: {sec_to_hms(data['t_min'])} → {sec_to_hms(data['t_max'])} · "
    f"U-Bahn Stops: {len(data['stops_lat'])}"
)

start = st.button("Start 🚇")

plot_area = st.empty()

if start:
    frames = int(duration_sec * fps)
    t0 = data["t_min"]
    t1 = data["t_max"]

    xmin, xmax, ymin, ymax = data["bounds"]

    for k in range(frames):
        sim_t = int(t0 + (k / max(frames - 1, 1)) * (t1 - t0))

        mask = (data["t0"] <= sim_t) & (data["t1"] >= sim_t)
        if np.any(mask):
            dt_seg = (data["t1"][mask] - data["t0"][mask]).astype(np.float64)
            alpha = (sim_t - data["t0"][mask]).astype(np.float64) / dt_seg
            lat = data["lat0"][mask] + alpha * (data["lat1"][mask] - data["lat0"][mask])
            lon = data["lon0"][mask] + alpha * (data["lon1"][mask] - data["lon0"][mask])
            colors = [data["palette"][i] for i in data["route_idx"][mask]]
        else:
            lat = np.array([])
            lon = np.array([])
            colors = []

        fig, ax = plt.subplots(figsize=(7, 7))
        ax.scatter(data["stops_lon"], data["stops_lat"], s=3, alpha=0.25)  # stops
        ax.scatter(lon, lat, s=8, c=colors, alpha=0.9)  # trains

        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_xlabel("lon")
        ax.set_ylabel("lat")
        ax.set_title(f"U-Bahn — {date} — {sec_to_hms(sim_t)} (komprimiert)")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, alpha=0.2)

        plot_area.pyplot(fig, clear_figure=True)
        plt.close(fig)

        time.sleep(1 / fps)
