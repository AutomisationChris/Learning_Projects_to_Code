# Libraries used:
# - streamlit
# - pandas
# - numpy
# - matplotlib

import time
from pathlib import Path
from typing import Dict, List, Tuple, Set

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


# -------------------------
# Config
# -------------------------
DATA_DIR = Path(__file__).resolve().parent

FILES = {
    "stops": DATA_DIR / "stops.txt",
    "routes": DATA_DIR / "routes.txt",
    "trips": DATA_DIR / "trips_ubahn.txt",
    "calendar": DATA_DIR / "calendar_ubahn.txt",
    "calendar_dates": DATA_DIR / "calendar_dates_ubahn.txt",
    "stop_times": DATA_DIR / "stop_times_ubahn.txt",
    "shapes": DATA_DIR / "shapes_ubahn.txt",
}


# -------------------------
# Helpers
# -------------------------
def sec_to_hms(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def gtfs_time_to_sec(series: pd.Series) -> np.ndarray:
    # supports "27:12:00" etc
    parts = series.astype(str).str.split(":", expand=True)
    hh = parts[0].astype(int).to_numpy(np.int32)
    mm = parts[1].astype(int).to_numpy(np.int32)
    ss = parts[2].astype(int).to_numpy(np.int32)
    return hh * 3600 + mm * 60 + ss


def normalize_hex_color(c: str) -> str:
    # GTFS route_color is usually "RRGGBB" (no '#'), may be empty
    if not isinstance(c, str):
        return "#999999"
    c = c.strip().lstrip("#")
    if len(c) != 6:
        return "#999999"
    # allow only hex
    try:
        int(c, 16)
    except ValueError:
        return "#999999"
    return "#" + c.upper()


def weekday_col_for_date(date_yyyymmdd: int) -> str:
    # returns one of: monday..sunday
    dt = pd.to_datetime(str(date_yyyymmdd), format="%Y%m%d")
    # pandas: Monday=0..Sunday=6
    cols = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return cols[int(dt.dayofweek)]


# -------------------------
# Data loading (cached)
# -------------------------
@st.cache_data(show_spinner=False)
def load_small_tables():
    stops = pd.read_csv(
        FILES["stops"],
        usecols=["stop_id", "stop_lat", "stop_lon"],
        dtype={"stop_id": "string"},
        low_memory=False,
    )

    routes = pd.read_csv(
        FILES["routes"],
        usecols=["route_id", "agency_id", "route_short_name", "route_type", "route_color"],
        dtype={"route_id": "string", "route_short_name": "string", "route_color": "string"},
        low_memory=False,
    )
    # ensure numeric for filters (some feeds store as int already; this normalizes)
    routes["agency_id"] = pd.to_numeric(routes["agency_id"], errors="coerce").astype("Int64")
    routes["route_type"] = pd.to_numeric(routes["route_type"], errors="coerce").astype("Int64")

    trips = pd.read_csv(
        FILES["trips"],
        usecols=["trip_id", "route_id", "service_id", "shape_id"],
        dtype={"trip_id": "string", "route_id": "string", "service_id": "string", "shape_id": "string"},
        low_memory=False,
    )

    cald = pd.read_csv(
        FILES["calendar_dates"],
        usecols=["service_id", "date", "exception_type"],
        dtype={"service_id": "string", "date": "int64", "exception_type": "int8"},
        low_memory=False,
    )

    cal = None
    if FILES["calendar"].exists():
        cal = pd.read_csv(
            FILES["calendar"],
            dtype={"service_id": "string"},
            low_memory=False,
        )
        # coerce to int
        for col in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            if col in cal.columns:
                cal[col] = pd.to_numeric(cal[col], errors="coerce").fillna(0).astype("int8")
        if "start_date" in cal.columns:
            cal["start_date"] = pd.to_numeric(cal["start_date"], errors="coerce").astype("Int64")
        if "end_date" in cal.columns:
            cal["end_date"] = pd.to_numeric(cal["end_date"], errors="coerce").astype("Int64")

    return stops, routes, trips, cal, cald


def get_active_services_for_date(cal: pd.DataFrame | None, cald: pd.DataFrame, date_yyyymmdd: int) -> Set[str]:
    # GTFS standard: base from calendar, then apply calendar_dates exceptions
    active: Set[str] = set()

    if cal is not None and not cal.empty:
        wcol = weekday_col_for_date(date_yyyymmdd)
        if wcol in cal.columns and "start_date" in cal.columns and "end_date" in cal.columns:
            base = cal[
                (cal["start_date"].astype("Int64") <= date_yyyymmdd)
                & (cal["end_date"].astype("Int64") >= date_yyyymmdd)
                & (cal[wcol] == 1)
            ]
            active.update(base["service_id"].astype("string").dropna().unique().tolist())

    # apply exceptions
    add = cald[(cald["date"] == date_yyyymmdd) & (cald["exception_type"] == 1)]["service_id"]
    rem = cald[(cald["date"] == date_yyyymmdd) & (cald["exception_type"] == 2)]["service_id"]
    active.update(add.astype("string").dropna().unique().tolist())
    active.difference_update(rem.astype("string").dropna().unique().tolist())

    return active


def load_shapes_filtered(shape_ids: Set[str], chunksize: int = 300_000) -> pd.DataFrame:
    if not shape_ids:
        return pd.DataFrame(columns=["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"])

    usecols = ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"]
    dtypes = {"shape_id": "string", "shape_pt_sequence": "int32"}

    keep = []
    for chunk in pd.read_csv(
        FILES["shapes"],
        usecols=usecols,
        dtype=dtypes,
        chunksize=chunksize,
        low_memory=False,
    ):
        chunk = chunk[chunk["shape_id"].isin(shape_ids)]
        if not chunk.empty:
            keep.append(chunk)

    if not keep:
        return pd.DataFrame(columns=usecols)

    shapes = pd.concat(keep, ignore_index=True)
    shapes.sort_values(["shape_id", "shape_pt_sequence"], inplace=True)
    return shapes


def load_stop_times_for_trip_ids(trip_ids: Set[str], chunksize: int = 500_000) -> pd.DataFrame:
    # stop_times can be huge -> read in chunks and keep only relevant trips
    usecols = ["trip_id", "departure_time", "stop_id", "stop_sequence"]
    dtypes = {"trip_id": "string", "stop_id": "string", "stop_sequence": "int32"}

    keep = []
    for chunk in pd.read_csv(
        FILES["stop_times"],
        usecols=usecols,
        dtype=dtypes,
        chunksize=chunksize,
        low_memory=False,
    ):
        chunk = chunk[chunk["trip_id"].isin(trip_ids)]
        if not chunk.empty:
            keep.append(chunk)

    if not keep:
        return pd.DataFrame(columns=usecols)

    st_active = pd.concat(keep, ignore_index=True)
    return st_active


def sort_key_u(line_name: str) -> int:
    # "U1".."U9" -> 1..9 ; fallback large
    try:
        digits = "".join(ch for ch in str(line_name) if ch.isdigit())
        return int(digits) if digits else 999
    except Exception:
        return 999


# -------------------------
# Build segments + shapes (cached per date)
# -------------------------
@st.cache_data(show_spinner=False)
def build_day_model(date_yyyymmdd: int) -> Dict:
    stops, routes, trips, cal, cald = load_small_tables()

    # Filter U-Bahn routes (BVG)
    routes_u = routes[
        (routes["agency_id"] == 796)
        & (routes["route_type"] == 400)
        & (routes["route_short_name"].astype(str).str.match(r"U\d+$"))
    ].copy()

    if routes_u.empty:
        raise RuntimeError("Keine U-Bahn-Routen gefunden (Filter agency_id=796, route_type=400, U\\d).")

    routes_u["route_color"] = routes_u["route_color"].fillna("").astype(str).map(normalize_hex_color)
    routes_u = routes_u[["route_id", "route_short_name", "route_color"]]

    active_services = get_active_services_for_date(cal, cald, date_yyyymmdd)
    if not active_services:
        raise RuntimeError(f"Keine aktiven service_id für Datum {date_yyyymmdd} gefunden.")

    # Trips for active services and U routes
    trips_u = trips.merge(routes_u, on="route_id", how="inner")
    trips_u = trips_u[trips_u["service_id"].isin(active_services)][
        ["trip_id", "route_short_name", "route_color", "shape_id"]
    ].copy()

    if trips_u.empty:
        raise RuntimeError(f"Keine Trips für Datum {date_yyyymmdd} (U-Bahn) gefunden.")

    # Load shapes only for used shape_ids
    shape_ids = set(trips_u["shape_id"].dropna().unique().tolist())
    shapes = load_shapes_filtered(shape_ids)

    shape_lines: List[np.ndarray] = []
    if not shapes.empty:
        for _, g in shapes.groupby("shape_id", sort=False):
            pts = np.column_stack(
                [g["shape_pt_lon"].to_numpy(np.float64), g["shape_pt_lat"].to_numpy(np.float64)]
            )
            if len(pts) >= 2:
                shape_lines.append(pts)

    # Load stop_times only for trips of the day
    trip_ids = set(trips_u["trip_id"].astype("string").dropna().unique().tolist())
    st_active = load_stop_times_for_trip_ids(trip_ids)

    if st_active.empty:
        raise RuntimeError("stop_times: keine Zeilen für die gefilterten trip_ids gefunden.")

    # Join stop coords
    st_active = st_active.merge(stops, on="stop_id", how="left").dropna(subset=["stop_lat", "stop_lon"])

    # Parse times -> seconds
    st_active["t0"] = gtfs_time_to_sec(st_active["departure_time"])
    st_active.sort_values(["trip_id", "stop_sequence"], inplace=True)

    # Build consecutive-stop segments per trip
    g = st_active.groupby("trip_id", sort=False)
    st_active["lat1"] = g["stop_lat"].shift(-1)
    st_active["lon1"] = g["stop_lon"].shift(-1)
    st_active["t1"] = g["t0"].shift(-1)

    seg = st_active.dropna(subset=["lat1", "lon1", "t1"]).copy()
    seg.rename(columns={"stop_lat": "lat0", "stop_lon": "lon0"}, inplace=True)
    seg = seg[seg["t1"] (_) > seg["t0"]] if False else seg  # safeguard placeholder (ignored)

    # forward segments only
    seg = seg[seg["t1"] > seg["t0"]]

    # add route info
    seg = seg.merge(trips_u[["trip_id", "route_short_name", "route_color"]], on="trip_id", how="left")
    seg = seg.dropna(subset=["route_short_name", "route_color"])

    # palette
    line_names = sorted(seg["route_short_name"].unique().tolist(), key=sort_key_u)
    color_map = (
        routes_u.drop_duplicates("route_short_name")
        .set_index("route_short_name")["route_color"]
        .to_dict()
    )
    palette = [color_map.get(ln, "#999999") for ln in line_names]
    idx_map = {ln: i for i, ln in enumerate(line_names)}
    seg["route_idx"] = seg["route_short_name"].map(idx_map).astype(np.int16)

    # used stops for background
    used_stop_ids = st_active["stop_id"].unique()
    used_stops = stops[stops["stop_id"].isin(used_stop_ids)]

    # arrays for fast frame computation
    model = {
        "t0": seg["t0"].to_numpy(np.int32),
        "t1": seg["t1"].to_numpy(np.int32),
        "lat0": seg["lat0"].to_numpy(np.float64),
        "lon0": seg["lon0"].to_numpy(np.float64),
        "lat1": seg["lat1"].to_numpy(np.float64),
        "lon1": seg["lon1"].to_numpy(np.float64),
        "route_idx": seg["route_idx"].to_numpy(np.int16),
        "palette": palette,
        "line_names": line_names,
        "stops_lat": used_stops["stop_lat"].to_numpy(np.float64),
        "stops_lon": used_stops["stop_lon"].to_numpy(np.float64),
        "shape_lines": shape_lines,
    }

    model["t_min"] = int(np.min(model["t0"]))
    model["t_max"] = int(np.max(model["t1"]))

    # bounds
    min_lat = float(np.min(model["stops_lat"]))
    max_lat = float(np.max(model["stops_lat"]))
    min_lon = float(np.min(model["stops_lon"]))
    max_lon = float(np.max(model["stops_lon"]))

    pad_lat = (max_lat - min_lat) * 0.05
    pad_lon = (max_lon - min_lon) * 0.05
    model["bounds"] = (min_lon - pad_lon, max_lon + pad_lon, min_lat - pad_lat, max_lat + pad_lat)

    return model


# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="Berlin U-Bahn Day-in-a-Minute", layout="centered")
st.title("Berlin U-Bahn — 1 Minute = 1 Betriebstag")

missing = [k for k, p in FILES.items() if (k != "calendar" and not p.exists())]
if missing:
    st.error(f"Fehlende Dateien: {missing} (erwartet im Ordner: {DATA_DIR.resolve()})")
    st.stop()

# Dates for UI
_, _, _, _, cald = load_small_tables()
available_dates = sorted(cald.loc[cald["exception_type"].isin([1, 2]), "date"].unique().tolist())
if not available_dates:
    st.error("Keine Daten im calendar_dates gefunden.")
    st.stop()

date = st.sidebar.selectbox("Datum (YYYYMMDD)", available_dates, index=0)

fps = st.sidebar.slider("FPS", min_value=1, max_value=12, value=6)
duration_sec = st.sidebar.slider("Dauer (Sekunden)", min_value=10, max_value=120, value=60)

try:
    data = build_day_model(int(date))
except Exception as e:
    st.error(str(e))
    st.stop()

st.caption(
    f"Datum {date} · Sim-Zeit: {sec_to_hms(data['t_min'])} → {sec_to_hms(data['t_max'])} · "
    f"Stops: {len(data['stops_lat'])} · Linien: {', '.join(data['line_names'])}"
)

start = st.button("Start")
plot_area = st.empty()

if start:
    frames = int(duration_sec * fps)
    sim_start, sim_end = data["t_min"], data["t_max"]
    xmin, xmax, ymin, ymax = data["bounds"]

    for k in range(frames):
        sim_t = int(sim_start + (k / max(frames - 1, 1)) * (sim_end - sim_start))

        mask = (data["t0"] <= sim_t) & (data["t1"] >= sim_t)
        if np.any(mask):
            dt = (data["t1"][mask] - data["t0"][mask]).astype(np.float64)
            alpha = (sim_t - data["t0"][mask]).astype(np.float64) / dt

            lat = data["lat0"][mask] + alpha * (data["lat1"][mask] - data["lat0"][mask])
            lon = data["lon0"][mask] + alpha * (data["lon1"][mask] - data["lon0"][mask])
            colors = [data["palette"][i] for i in data["route_idx"][mask]]
        else:
            lat = np.array([], dtype=np.float64)
            lon = np.array([], dtype=np.float64)
            colors = []

        fig, ax = plt.subplots(figsize=(7, 7))

        # Shapes (lines)
        if data["shape_lines"]:
            lc = LineCollection(data["shape_lines"], linewidths=0.6, alpha=0.25)
            ax.add_collection(lc)

        # Stops
        ax.scatter(data["stops_lon"], data["stops_lat"], s=2.5, alpha=0.25)

        # Trains
        ax.scatter(lon, lat, s=9, c=colors, alpha=0.9)

        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, alpha=0.2)
        ax.set_xlabel("lon")
        ax.set_ylabel("lat")
        ax.set_title(f"U-Bahn {date} — {sec_to_hms(sim_t)}")

        plot_area.pyplot(fig, clear_figure=True)
        plt.close(fig)

        time.sleep(1 / fps)
