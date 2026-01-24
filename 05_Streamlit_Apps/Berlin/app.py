# Libraries used:
# - streamlit
# - pandas
# - numpy
# - matplotlib
# - pillow (PIL)  [used only for GIF creation]

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Optional basemap tiles (requires 'contextily' in requirements)
try:
    import contextily as ctx
except Exception:
    ctx = None

from PIL import Image


# ============================================================
# Config
# ============================================================

DATA_DIR = Path(__file__).resolve().parent

STOP_TIMES_ZIP = DATA_DIR / "stop_times_ubahn.zip"
STOP_TIMES_TXT = DATA_DIR / "stop_times_ubahn.txt"
STOP_TIMES_PATH = STOP_TIMES_ZIP if STOP_TIMES_ZIP.exists() else STOP_TIMES_TXT

FILES = {
    "stops": DATA_DIR / "stops.txt",
    "routes": DATA_DIR / "routes.txt",
    "trips": DATA_DIR / "trips_ubahn.txt",
    "calendar": DATA_DIR / "calendar_ubahn.txt",
    "calendar_dates": DATA_DIR / "calendar_dates_ubahn.txt",
    "stop_times": STOP_TIMES_PATH,  # uses .zip if present, else .txt
    "shapes": DATA_DIR / "shapes_ubahn.txt",
}

APP_TITLE = "Berlin U‑Bahn — Day in a Minute (GIF)"


# ============================================================
# Time helpers (GTFS)
# ============================================================

def gtfs_time_to_sec(series: pd.Series) -> np.ndarray:
    """
    Convert GTFS time "HH:MM:SS" into seconds since 00:00.
    Supports hours > 24 (e.g. "27:12:00").
    """
    parts = series.astype(str).str.split(":", expand=True)
    h = parts[0].astype(int).to_numpy()
    m = parts[1].astype(int).to_numpy()
    s = parts[2].astype(int).to_numpy()
    return h * 3600 + m * 60 + s


def sec_to_hms(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def yyyymmdd_to_datetime(date_yyyymmdd: int) -> pd.Timestamp:
    return pd.to_datetime(str(int(date_yyyymmdd)), format="%Y%m%d")


# ============================================================
# Geo helpers (Web Mercator)
# ============================================================

RADIUS_EARTH = 6378137.0

def lonlat_to_mercator(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """EPSG:4326 -> EPSG:3857 (meters)."""
    lon = lon.astype(np.float64)
    lat = lat.astype(np.float64)
    x = RADIUS_EARTH * np.deg2rad(lon)
    lat = np.clip(lat, -85.05112878, 85.05112878)
    y = RADIUS_EARTH * np.log(np.tan(np.pi / 4.0 + np.deg2rad(lat) / 2.0))
    return x, y


# ============================================================
# Data loading (cached)
# ============================================================

@st.cache_data(show_spinner=False)
def load_tables():
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

    trips = pd.read_csv(
        FILES["trips"],
        usecols=["trip_id", "route_id", "service_id", "shape_id"],
        dtype={"trip_id": "string", "route_id": "string", "service_id": "string", "shape_id": "string"},
        low_memory=False,
    )

    calendar = pd.read_csv(
        FILES["calendar"],
        dtype={"service_id": "string"},
        low_memory=False,
    )

    calendar_dates = pd.read_csv(
        FILES["calendar_dates"],
        usecols=["service_id", "date", "exception_type"],
        dtype={"service_id": "string", "date": "int64", "exception_type": "int8"},
        low_memory=False,
    )

    return stops, routes, trips, calendar, calendar_dates


def iter_stop_times_filtered(
    stop_times_path: Path,
    trip_ids: set[str],
    chunksize: int = 600_000,
) -> pd.DataFrame:
    """
    Read stop_times in chunks and keep only rows whose trip_id is in trip_ids.
    Supports:
      - .zip (with one .txt/.csv inside)
      - plain .txt/.csv
    """
    usecols = ["trip_id", "departure_time", "stop_id", "stop_sequence"]
    dtypes = {
        "trip_id": "string",
        "stop_id": "string",
        "stop_sequence": "int32",
        "departure_time": "string",
    }

    keep = []

    suffix = stop_times_path.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(stop_times_path) as zf:
            members = [n for n in zf.namelist() if n.lower().endswith((".txt", ".csv"))]
            if not members:
                raise RuntimeError("stop_times ZIP enthält keine .txt/.csv Datei.")
            name = members[0]
            with zf.open(name) as f:
                for chunk in pd.read_csv(f, usecols=usecols, dtype=dtypes, chunksize=chunksize, low_memory=False):
                    m = chunk["trip_id"].isin(trip_ids)
                    if m.any():
                        keep.append(chunk.loc[m])
    else:
        for chunk in pd.read_csv(stop_times_path, usecols=usecols, dtype=dtypes, chunksize=chunksize, low_memory=False):
            m = chunk["trip_id"].isin(trip_ids)
            if m.any():
                keep.append(chunk.loc[m])

    if not keep:
        return pd.DataFrame(columns=usecols)

    return pd.concat(keep, ignore_index=True)


def load_shapes_filtered(shape_ids: set[str], chunksize: int = 400_000) -> pd.DataFrame:
    usecols = ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"]
    dtypes = {"shape_id": "string", "shape_pt_sequence": "int32"}
    keep = []
    for chunk in pd.read_csv(FILES["shapes"], usecols=usecols, dtype=dtypes, chunksize=chunksize, low_memory=False):
        chunk = chunk[chunk["shape_id"].isin(shape_ids)]
        if not chunk.empty:
            keep.append(chunk)
    if not keep:
        return pd.DataFrame(columns=usecols)
    shapes = pd.concat(keep, ignore_index=True)
    shapes.sort_values(["shape_id", "shape_pt_sequence"], inplace=True)
    return shapes


# ============================================================
# Service selection (calendar + calendar_dates)
# ============================================================

WEEKDAY_COLS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

def active_services_for_date(calendar: pd.DataFrame, calendar_dates: pd.DataFrame, date_yyyymmdd: int) -> set[str]:
    d = yyyymmdd_to_datetime(date_yyyymmdd)
    dow = d.day_name().lower()
    if dow not in WEEKDAY_COLS:
        dow = "monday"

    cal = calendar.copy()
    cal["start_date"] = cal["start_date"].astype(int)
    cal["end_date"] = cal["end_date"].astype(int)

    base = cal[
        (cal["start_date"] <= date_yyyymmdd)
        & (cal["end_date"] >= date_yyyymmdd)
        & (cal[dow].astype(int) == 1)
    ]["service_id"].astype("string")

    active = set(base.tolist())

    ex = calendar_dates[calendar_dates["date"] == date_yyyymmdd]
    if not ex.empty:
        add = ex.loc[ex["exception_type"] == 1, "service_id"].astype("string")
        rem = ex.loc[ex["exception_type"] == 2, "service_id"].astype("string")
        active.update(add.tolist())
        active.difference_update(rem.tolist())

    return active


# ============================================================
# Build day data (segments + background)
# ============================================================

@dataclass
class DayData:
    t0: np.ndarray
    t1: np.ndarray
    x0: np.ndarray
    y0: np.ndarray
    x1: np.ndarray
    y1: np.ndarray
    route_idx: np.ndarray

    palette: list[str]
    line_names: list[str]

    stops_x: np.ndarray
    stops_y: np.ndarray
    shape_lines_xy: list[np.ndarray]

    bounds: tuple[float, float, float, float]  # xmin, xmax, ymin, ymax
    t_min: int
    t_max: int


@st.cache_data(show_spinner=False)
def build_day_data(date_yyyymmdd: int) -> DayData:
    stops, routes, trips, calendar, calendar_dates = load_tables()

    routes = routes.copy()
    routes["route_short_name"] = routes["route_short_name"].fillna("")
    routes["route_color"] = routes["route_color"].fillna("").replace("", "999999")

    # U1..U9
    is_u = routes["route_short_name"].str.match(r"^U\d+$")
    # Some feeds use route_type=400 for metro
    if "route_type" in routes.columns:
        is_u = is_u | (routes["route_type"].fillna(-1).astype(int) == 400)

    routes_u = routes.loc[is_u, ["route_id", "route_short_name", "route_color"]].copy()
    if routes_u.empty:
        raise RuntimeError("Keine U‑Bahn routes gefunden (Filter in routes.txt passt nicht).")

    active_services = active_services_for_date(calendar, calendar_dates, date_yyyymmdd)
    if not active_services:
        raise RuntimeError(f"Keine aktiven service_ids für {date_yyyymmdd} gefunden.")

    trips_u = trips.merge(routes_u, on="route_id", how="inner")
    trips_u = trips_u[trips_u["service_id"].isin(active_services)][
        ["trip_id", "route_short_name", "route_color", "shape_id"]
    ].copy()

    if trips_u.empty:
        raise RuntimeError(f"Keine U‑Bahn trips für {date_yyyymmdd} gefunden.")

    trip_ids = set(trips_u["trip_id"].astype("string").tolist())

    stop_times = iter_stop_times_filtered(FILES["stop_times"], trip_ids=trip_ids)
    if stop_times.empty:
        raise RuntimeError("stop_times gefiltert ist leer (trip_ids Filter / stop_times Datei prüfen).")

    stops = stops.dropna(subset=["stop_lat", "stop_lon"]).copy()
    stop_times = stop_times.merge(stops, on="stop_id", how="left").dropna(subset=["stop_lat", "stop_lon"])

    stop_times["t0"] = gtfs_time_to_sec(stop_times["departure_time"])
    stop_times.sort_values(["trip_id", "stop_sequence"], inplace=True)

    g = stop_times.groupby("trip_id", sort=False)
    stop_times["stop_lat_1"] = g["stop_lat"].shift(-1)
    stop_times["stop_lon_1"] = g["stop_lon"].shift(-1)
    stop_times["t1"] = g["t0"].shift(-1)

    seg = stop_times.dropna(subset=["stop_lat_1", "stop_lon_1", "t1"]).copy()
    seg = seg[seg["t1"] > seg["t0"]]

    seg = seg.merge(
        trips_u[["trip_id", "route_short_name", "route_color"]],
        on="trip_id",
        how="left",
    ).dropna(subset=["route_short_name", "route_color"])

    def _u_sort_key(name: str) -> int:
        try:
            return int(str(name).replace("U", ""))
        except Exception:
            return 999

    line_names = sorted(seg["route_short_name"].astype(str).unique().tolist(), key=_u_sort_key)

    palette: list[str] = []
    for ln in line_names:
        s = routes_u.loc[routes_u["route_short_name"] == ln, "route_color"]
        palette.append("#" + (s.iloc[0] if len(s) else "999999"))

    idx_map = {ln: i for i, ln in enumerate(line_names)}
    seg["route_idx"] = seg["route_short_name"].map(idx_map).astype(np.int16)

    # Mercator endpoints
    x0, y0 = lonlat_to_mercator(seg["stop_lon"].to_numpy(np.float64), seg["stop_lat"].to_numpy(np.float64))
    x1, y1 = lonlat_to_mercator(seg["stop_lon_1"].to_numpy(np.float64), seg["stop_lat_1"].to_numpy(np.float64))

    # Background stops (used only)
    used_stop_ids = stop_times["stop_id"].astype("string").unique().tolist()
    used_stops = stops[stops["stop_id"].isin(used_stop_ids)]
    stops_x, stops_y = lonlat_to_mercator(
        used_stops["stop_lon"].to_numpy(np.float64),
        used_stops["stop_lat"].to_numpy(np.float64),
    )

    # Background shapes (polylines)
    shape_lines_xy: list[np.ndarray] = []
    shape_ids = set(trips_u["shape_id"].dropna().astype("string").unique().tolist())
    shapes = load_shapes_filtered(shape_ids)
    if not shapes.empty:
        for _, gsh in shapes.groupby("shape_id", sort=False):
            sx, sy = lonlat_to_mercator(
                gsh["shape_pt_lon"].to_numpy(np.float64),
                gsh["shape_pt_lat"].to_numpy(np.float64),
            )
            pts = np.column_stack([sx, sy])
            if len(pts) >= 2:
                shape_lines_xy.append(pts)

    # Bounds + padding
    xmin = float(np.min(stops_x))
    xmax = float(np.max(stops_x))
    ymin = float(np.min(stops_y))
    ymax = float(np.max(stops_y))
    pad_x = (xmax - xmin) * 0.06
    pad_y = (ymax - ymin) * 0.06
    bounds = (xmin - pad_x, xmax + pad_x, ymin - pad_y, ymax + pad_y)

    t_min = int(seg["t0"].min())
    t_max = int(seg["t1"].max())

    return DayData(
        t0=seg["t0"].to_numpy(np.int32),
        t1=seg["t1"].to_numpy(np.int32),
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        route_idx=seg["route_idx"].to_numpy(np.int16),
        palette=palette,
        line_names=line_names,
        stops_x=stops_x,
        stops_y=stops_y,
        shape_lines_xy=shape_lines_xy,
        bounds=bounds,
        t_min=t_min,
        t_max=t_max,
    )


# ============================================================
# Rendering
# ============================================================

def fig_to_rgb(fig: plt.Figure) -> np.ndarray:
    """
    Matplotlib Figure -> RGB uint8 image (HxWx3).
    Uses buffer_rgba (works on newer Matplotlib versions).
    """
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())  # HxWx4
    return buf[..., :3].copy()


def render_frame(
    day: DayData,
    sim_t: int,
    width_px: int,
    height_px: int,
    show_shapes: bool,
    show_stops: bool,
    basemap_img: np.ndarray | None = None,
    basemap_extent: tuple[float, float, float, float] | None = None,
    basemap_alpha: float = 0.85,
) -> np.ndarray:
    xmin, xmax, ymin, ymax = day.bounds

    mask = (day.t0 <= sim_t) & (day.t1 >= sim_t)
    if np.any(mask):
        dt = (day.t1[mask] - day.t0[mask]).astype(np.float64)
        alpha = (sim_t - day.t0[mask]).astype(np.float64) / dt
        x = day.x0[mask] + alpha * (day.x1[mask] - day.x0[mask])
        y = day.y0[mask] + alpha * (day.y1[mask] - day.y0[mask])
        colors = [day.palette[i] for i in day.route_idx[mask]]
    else:
        x = np.array([], dtype=np.float64)
        y = np.array([], dtype=np.float64)
        colors = []

    dpi = 110
    fig_w = max(width_px / dpi, 4.0)
    fig_h = max(height_px / dpi, 4.0)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)

    # Basemap (draw first so everything else sits on top)
    if basemap_img is not None and basemap_extent is not None:
        ax.imshow(
            basemap_img,
            extent=basemap_extent,
            alpha=float(basemap_alpha),
            zorder=0,
        )


    # shapes = faint network
    if show_shapes and day.shape_lines_xy:
        for pts in day.shape_lines_xy:
            ax.plot(pts[:, 0], pts[:, 1], linewidth=0.8, alpha=0.28)

    # stops = faint dots
    if show_stops:
        ax.scatter(day.stops_x, day.stops_y, s=1.5, alpha=0.22)

    # trains = colored dots
    ax.scatter(x, y, s=12, c=colors, alpha=0.95)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(sec_to_hms(sim_t), fontsize=12)

    rgb = fig_to_rgb(fig)
    plt.close(fig)
    return rgb


def render_gif_bytes(
    date_yyyymmdd: int,
    fps: int,
    duration_sec: int,
    width_px: int,
    height_px: int,
    show_basemap: bool,
    basemap_provider: str,
    basemap_zoom: int,
    basemap_alpha: float,
    show_shapes: bool,
    show_stops: bool,
) -> bytes:
    day = build_day_data(date_yyyymmdd)

    basemap_img, basemap_extent = (None, None)
    if show_basemap and ctx is not None:
        basemap_img, basemap_extent = fetch_basemap(day.bounds, basemap_provider, int(basemap_zoom))


    frames_target = int(duration_sec * fps)
    MAX_FRAMES = 240  # safety for Streamlit Cloud
    if frames_target > MAX_FRAMES:
        frames_target = MAX_FRAMES

    sim_start, sim_end = day.t_min, day.t_max

    frames: list[Image.Image] = []
    for k in range(frames_target):
        sim_t = int(sim_start + (k / max(frames_target - 1, 1)) * (sim_end - sim_start))
        rgb = render_frame(
            day=day,
            sim_t=sim_t,
            width_px=width_px,
            height_px=height_px,
            show_shapes=show_shapes,
            show_stops=show_stops,
            basemap_img=basemap_img,
            basemap_extent=basemap_extent,
            basemap_alpha=float(basemap_alpha),
        )
        im = Image.fromarray(rgb)
        # quantize so GIF doesn't explode
        im = im.convert("P", palette=Image.ADAPTIVE, colors=128)
        frames.append(im)

    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / max(fps, 1)),
        loop=0,
        optimize=True,
        disposal=2,
    )
    return buf.getvalue()


# ============================================================
# Streamlit UI
# ============================================================

st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

missing = [k for k, p in FILES.items() if not p.exists()]
if missing:
    st.error(f"Fehlende Dateien: {missing} (erwartet im Ordner: {DATA_DIR.resolve()})")
    st.stop()

st.sidebar.header("Settings")

_, _, _, calendar, calendar_dates = load_tables()
available_dates = sorted(calendar_dates["date"].unique().tolist())
if not available_dates:
    # fallback: start/end from calendar
    available_dates = [int(calendar["start_date"].min()), int(calendar["end_date"].max())]

date = st.sidebar.selectbox("Datum (YYYYMMDD)", available_dates, index=max(0, len(available_dates) - 1))

fps = st.sidebar.slider("FPS", 2, 12, 6)
duration_sec = st.sidebar.slider("Dauer (Sek.)", 10, 120, 60)

width_px = st.sidebar.slider("Breite (px)", 700, 1800, 1400, 50)
height_px = st.sidebar.slider("Höhe (px)", 700, 1800, 1400, 50)

show_basemap = st.sidebar.checkbox("Basemap (Berlin-Karte) anzeigen", value=True)
if show_basemap and ctx is None:
    st.sidebar.warning("Basemap benötigt 'contextily' in requirements.txt (und Internet-Zugriff).")
    show_basemap = False

basemap_provider = "CartoDB.Positron"
basemap_zoom = 11
basemap_alpha = 0.85
if show_basemap:
    basemap_provider = st.sidebar.selectbox(
        "Basemap Style",
        options=list(BASEMAP_PROVIDERS.keys()) if BASEMAP_PROVIDERS else ["CartoDB.Positron"],
        index=0,
    )
    basemap_zoom = st.sidebar.slider("Basemap Zoom", min_value=8, max_value=14, value=11)
    basemap_alpha = st.sidebar.slider("Basemap Transparenz", min_value=0.2, max_value=1.0, value=0.85)

show_shapes = st.sidebar.checkbox("Linien (shapes)", True)
show_stops = st.sidebar.checkbox("Stops", True)

st.sidebar.caption("GIFs werden intern auf max. 240 Frames begrenzt (sonst knallt Streamlit Cloud).")

with st.spinner("Baue Tagesdaten (Trips + stop_times chunked)…"):
    day = build_day_data(int(date))

# Basemap for preview frame
basemap_img, basemap_extent = (None, None)
if show_basemap and ctx is not None:
    basemap_img, basemap_extent = fetch_basemap(day.bounds, basemap_provider, int(basemap_zoom))


st.write(
    f"**Datum:** {date}  \n"
    f"**Linien:** {', '.join(day.line_names)}  \n"
    f"**Sim‑Zeit:** {sec_to_hms(day.t_min)} → {sec_to_hms(day.t_max)}  \n"
    f"**Stops:** {len(day.stops_x):,}  \n"
    f"**Segmente:** {len(day.t0):,}"
)

st.subheader("Preview (ein Frame)")
c1, c2 = st.columns([2, 1], gap="large")
with c2:
    t_preview = st.slider("Preview‑Zeit", int(day.t_min), int(day.t_max), int(day.t_min))
    st.caption(sec_to_hms(int(t_preview)))

with c1:
    rgb = render_frame(
        day=day,
        sim_t=int(t_preview),
        width_px=int(width_px),
        height_px=int(height_px),
        show_shapes=bool(show_shapes),
        show_stops=bool(show_stops),
        basemap_img=basemap_img,
        basemap_extent=basemap_extent,
        basemap_alpha=float(basemap_alpha),
    )
    st.image(rgb, use_container_width=True)

st.subheader("GIF rendern")
if st.button("GIF bauen"):
    with st.spinner("Rendere GIF…"):
        gif_bytes = render_gif_bytes(
            date_yyyymmdd=int(date),
            fps=int(fps),
            duration_sec=int(duration_sec),
            width_px=int(width_px),
            height_px=int(height_px),
            show_basemap=bool(show_basemap),
            basemap_provider=str(basemap_provider),
            basemap_zoom=int(basemap_zoom),
            basemap_alpha=float(basemap_alpha),
            show_shapes=bool(show_shapes),
            show_stops=bool(show_stops),
        )

    st.success(f"GIF fertig: {len(gif_bytes)/1024/1024:.1f} MB")
    st.image(gif_bytes, caption="Animation", use_container_width=True)
    st.download_button(
        "GIF herunterladen",
        data=gif_bytes,
        file_name=f"berlin_ubahn_{date}.gif",
        mime="image/gif",
    )
