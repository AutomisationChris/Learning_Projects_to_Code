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
        dtype={"trip_id": "string", "route_id": "string", "service_id": "s_
