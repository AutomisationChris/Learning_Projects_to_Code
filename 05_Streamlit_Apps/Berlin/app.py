# app.py
# Libraries used:
# - streamlit
# - pandas
# - numpy
# - matplotlib
# - imageio (for GIF export)
# Optional:
# - contextily (for basemap tiles behind the network, needs internet)

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

import imageio.v2 as imageio


# -------------------------
# Config
# -------------------------
st.set_page_config(page_title="Berlin U-Bahn — Day in a Minute", layout="wide")

DATA_DIR = Path(__file__).resolve().parent


def _pick_existing(*candidates: Path) -> Optional[Path]:
    for p in candidates:
        if p.exists():
            return p
    return None


FILES: Dict[str, Path] = {
    "agency": DATA_DIR / "agency.txt",
    "stops": DATA_DIR / "stops.txt",
    "routes": DATA_DIR / "routes.txt",
    "trips": DATA_DIR / "trips_ubahn.txt",
    "calendar": DATA_DIR / "calendar_ubahn.txt",
    "calendar_dates": DATA_DIR / "calendar_dates_ubahn.txt",
}

# stop_times can be huge; allow zip
_stop_times = _pick_existing(DATA_DIR / "stop_times_ubahn.txt", DATA_DIR / "stop_times_ubahn.zip")
if _stop_times:
    FILES["stop_times"] = _stop_times

# shapes can be huge; allow zip
_shapes = _pick_existing(DATA_DIR / "shapes_ubahn.txt", DATA_DIR / "shapes_ubahn.zip")
if _shapes:
    FILES["shapes"] = _shapes


# -------------------------
# Utilities
# -------------------------
def _missing_files() -> List[str]:
    missing = []
    for k in ["agency", "stops", "routes", "trips", "calendar", "calendar_dates", "stop_times", "shapes"]:
        p = FILES.get(k)
        if p is None or not p.exists():
            missing.append(k)
    return missing


def read_csv_any(path: Path, **kwargs) -> pd.DataFrame:
    """
    Read CSV from plain text OR from a .zip with exactly one file.
    Works well with typical GTFS zips (one file per archive).
    """
    path = Path(path)
    if path.suffix.lower() == ".zip":
        return pd.read_csv(path, compression="zip", **kwargs)
    return pd.read_csv(path, **kwargs)


def gtfs_time_to_sec(series: pd.Series) -> np.ndarray:
    """Supports '27:12:00' etc. Invalid rows become NaN and will be dropped later."""
    s = series.astype("string")
    parts = s.str.split(":", expand=True)
    if parts.shape[1] < 3:
        return np.full(len(series), np.nan, dtype=np.float64)

    h = pd.to_numeric(parts[0], errors="coerce")
    m = pd.to_numeric(parts[1], errors="coerce")
    sec = pd.to_numeric(parts[2], errors="coerce")
    out = (h * 3600 + m * 60 + sec).to_numpy(dtype=np.float64)
    return out


def sec_to_hms(sec: int) -> str:
    h = int(sec) // 3600
    m = (int(sec) % 3600) // 60
    s = int(sec) % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def lonlat_to_webmercator(lon: np.ndarray, lat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """EPSG:4326 -> EPSG:3857 (Web Mercator), vectorized."""
    lat = np.clip(lat, -85.05112878, 85.05112878)
    x = lon * 20037508.34 / 180.0
    y = np.log(np.tan((90.0 + lat) * math.pi / 360.0)) * 20037508.34 / math.pi
    return x.astype(np.float64), y.astype(np.float64)


# -------------------------
# Data model
# -------------------------
@dataclass(frozen=True)
class DayModel:
    date_yyyymmdd: int
    line_names: List[str]
    palette: List[str]

    t0: np.ndarray
    t1: np.ndarray

    lon0: np.ndarray
    lat0: np.ndarray
    lon1: np.ndarray
    lat1: np.ndarray

    route_idx: np.ndarray

    stops_lon: np.ndarray
    stops_lat: np.ndarray

    shape_lines: List[np.ndarray]

    bounds: Tuple[float, float, float, float]
    t_min: int
    t_max: int


# -------------------------
# Data loading / preprocessing (cached)
# -------------------------
@st.cache_data(show_spinner=False)
def load_tables():
    stops = read_csv_any(
        FILES["stops"],
        usecols=["stop_id", "stop_lat", "stop_lon"],
        dtype={"stop_id": "string"},
    )

    routes = read_csv_any(
        FILES["routes"],
        dtype={"route_id": "string", "route_short_name": "string", "route_color": "string"},
    )
    for col in ["agency_id", "route_type"]:
        if col in routes.columns:
            routes[col] = pd.to_numeric(routes[col], errors="coerce").astype("Int64")

    trips = read_csv_any(
        FILES["trips"],
        usecols=["trip_id", "route_id", "service_id", "shape_id"],
        dtype={"trip_id": "string", "route_id": "string", "service_id": "string", "shape_id": "string"},
    )

    calendar = read_csv_any(FILES["calendar"], dtype={"service_id": "string"})
    for col in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"]:
        if col not in calendar.columns:
            calendar[col] = 0

    for col in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        calendar[col] = pd.to_numeric(calendar[col], errors="coerce").fillna(0).astype(np.int8)
    calendar["start_date"] = pd.to_numeric(calendar["start_date"], errors="coerce").fillna(0).astype(np.int64)
    calendar["end_date"] = pd.to_numeric(calendar["end_date"], errors="coerce").fillna(0).astype(np.int64)

    cald = read_csv_any(
        FILES["calendar_dates"],
        usecols=["service_id", "date", "exception_type"],
        dtype={"service_id": "string", "date": "int64", "exception_type": "int8"},
    )

    stop_times = read_csv_any(
        FILES["stop_times"],
        usecols=["trip_id", "departure_time", "stop_id", "stop_sequence"],
        dtype={"trip_id": "string", "stop_id": "string", "departure_time": "string", "stop_sequence": "int32"},
    )

    return stops, routes, trips, calendar, cald, stop_times


def _calendar_has_week_pattern(calendar: pd.DataFrame) -> bool:
    daycols = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return bool(calendar[daycols].to_numpy().sum() > 0)


def active_services_for_date(date_yyyymmdd: int, calendar: pd.DataFrame, calendar_dates: pd.DataFrame) -> set[str]:
    """
    - If calendar has weekly pattern: start there, then apply calendar_dates.
    - If calendar is basically empty: use calendar_dates exception_type=1 as truth.
    """
    active: set[str] = set()

    if _calendar_has_week_pattern(calendar):
        dt = pd.to_datetime(str(date_yyyymmdd), format="%Y%m%d")
        daycol = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][dt.dayofweek]
        m = (
            (calendar["start_date"] <= date_yyyymmdd)
            & (calendar["end_date"] >= date_yyyymmdd)
            & (calendar[daycol] == 1)
        )
        active = set(calendar.loc[m, "service_id"].astype("string").tolist())

    cd = calendar_dates[calendar_dates["date"] == date_yyyymmdd]
    if not cd.empty:
        add = cd.loc[cd["exception_type"] == 1, "service_id"].astype("string").tolist()
        remove = cd.loc[cd["exception_type"] == 2, "service_id"].astype("string").tolist()
        active.update(add)
        for s in remove:
            active.discard(s)

    return active


def load_shapes_filtered(shape_ids: set[str], chunksize: int = 500_000) -> List[np.ndarray]:
    if not shape_ids:
        return []

    usecols = ["shape_id", "shape_pt_lon", "shape_pt_lat", "shape_pt_sequence"]
    dtypes = {"shape_id": "string", "shape_pt_sequence": "int32"}

    keep: List[pd.DataFrame] = []
    for chunk in read_csv_any(FILES["shapes"], usecols=usecols, dtype=dtypes, chunksize=chunksize):
        chunk = chunk[chunk["shape_id"].isin(shape_ids)]
        if not chunk.empty:
            keep.append(chunk)

    if not keep:
        return []

    shapes = pd.concat(keep, ignore_index=True)
    shapes["shape_pt_lon"] = pd.to_numeric(shapes["shape_pt_lon"], errors="coerce")
    shapes["shape_pt_lat"] = pd.to_numeric(shapes["shape_pt_lat"], errors="coerce")
    shapes = shapes.dropna(subset=["shape_pt_lon", "shape_pt_lat"])
    shapes.sort_values(["shape_id", "shape_pt_sequence"], inplace=True)

    lines: List[np.ndarray] = []
    for _, g in shapes.groupby("shape_id", sort=False):
        pts = np.column_stack([g["shape_pt_lon"].to_numpy(np.float64), g["shape_pt_lat"].to_numpy(np.float64)])
        if len(pts) >= 2:
            lines.append(pts)
    return lines


@st.cache_data(show_spinner=False)
def available_dates() -> List[int]:
    _, _, _, calendar, cald, _ = load_tables()

    d: set[int] = set()
    if not cald.empty:
        d.update(cald["date"].astype(int).unique().tolist())

    if _calendar_has_week_pattern(calendar):
        start = int(calendar["start_date"].min())
        end = int(calendar["end_date"].max())
        dt_start = pd.to_datetime(str(start), format="%Y%m%d")
        dt_end = pd.to_datetime(str(end), format="%Y%m%d")
        rng = pd.date_range(dt_start, dt_end, freq="D")
        d.update([int(x.strftime("%Y%m%d")) for x in rng])

    return sorted(d)


@st.cache_data(show_spinner=False)
def build_day_model(date_yyyymmdd: int) -> DayModel:
    stops, routes, trips, calendar, cald, stop_times = load_tables()

    # U-Bahn routes: agency_id=796, route_type=400
    routes_u = routes.copy()
    if "agency_id" in routes_u.columns:
        routes_u["agency_id"] = pd.to_numeric(routes_u["agency_id"], errors="coerce").astype("Int64")
    if "route_type" in routes_u.columns:
        routes_u["route_type"] = pd.to_numeric(routes_u["route_type"], errors="coerce").astype("Int64")

    routes_u = routes_u[(routes_u["agency_id"] == 796) & (routes_u["route_type"] == 400)].copy()
    routes_u["route_color"] = routes_u.get("route_color", pd.Series(["999999"] * len(routes_u))).astype("string")
    routes_u["route_color"] = routes_u["route_color"].fillna("").replace("", "999999")
    routes_u = routes_u[["route_id", "route_short_name", "route_color"]]

    active_services = active_services_for_date(date_yyyymmdd, calendar, cald)
    if not active_services:
        active_services = set(
            cald.loc[cald["exception_type"] == 1, "service_id"].astype("string").unique().tolist()
        )

    trips_u = trips.merge(routes_u, on="route_id", how="inner")
    trips_u = trips_u[trips_u["service_id"].isin(active_services)].copy()
    if trips_u.empty:
        raise ValueError(f"No U-Bahn trips found for date {date_yyyymmdd}.")

    def _u_sort_key(name: str) -> int:
        digits = "".join(ch for ch in name if ch.isdigit())
        return int(digits) if digits else 999

    line_names = sorted(trips_u["route_short_name"].astype("string").unique().tolist(), key=_u_sort_key)
    palette = ["#" + str(routes_u.loc[routes_u["route_short_name"] == ln, "route_color"].iloc[0]) for ln in line_names]
    idx_map = {ln: i for i, ln in enumerate(line_names)}
    trips_u["route_idx"] = trips_u["route_short_name"].map(idx_map).astype(np.int16)

    trip_ids = trips_u["trip_id"].astype("string").unique().tolist()
    stt = stop_times[stop_times["trip_id"].isin(trip_ids)].copy()
    if stt.empty:
        raise ValueError("stop_times has no rows for the selected trips.")

    stt = stt.merge(stops, on="stop_id", how="left")
    stt["stop_lon"] = pd.to_numeric(stt["stop_lon"], errors="coerce")
    stt["stop_lat"] = pd.to_numeric(stt["stop_lat"], errors="coerce")
    stt = stt.dropna(subset=["stop_lon", "stop_lat"])

    stt["t0"] = gtfs_time_to_sec(stt["departure_time"])
    stt = stt.dropna(subset=["t0"])
    stt["t0"] = stt["t0"].astype(np.int32)

    stt.sort_values(["trip_id", "stop_sequence"], inplace=True)
    g = stt.groupby("trip_id", sort=False)
    stt["lon1"] = g["stop_lon"].shift(-1)
    stt["lat1"] = g["stop_lat"].shift(-1)
    stt["t1"] = g["t0"].shift(-1)

    seg = stt.dropna(subset=["lon1", "lat1", "t1"]).copy()
    seg = seg[seg["t1"] > seg["t0"]].copy()
    seg.rename(columns={"stop_lon": "lon0", "stop_lat": "lat0"}, inplace=True)

    seg = seg.merge(trips_u[["trip_id", "route_idx"]], on="trip_id", how="left")
    seg = seg.dropna(subset=["route_idx"])
    seg["route_idx"] = seg["route_idx"].astype(np.int16)

    used_stop_ids = stt["stop_id"].astype("string").unique().tolist()
    used_stops = stops[stops["stop_id"].isin(used_stop_ids)].copy()
    used_stops["stop_lon"] = pd.to_numeric(used_stops["stop_lon"], errors="coerce")
    used_stops["stop_lat"] = pd.to_numeric(used_stops["stop_lat"], errors="coerce")
    used_stops = used_stops.dropna(subset=["stop_lon", "stop_lat"])

    shape_ids = set(trips_u["shape_id"].dropna().astype("string").unique().tolist())
    shape_lines = load_shapes_filtered(shape_ids)

    xmin = float(used_stops["stop_lon"].min())
    xmax = float(used_stops["stop_lon"].max())
    ymin = float(used_stops["stop_lat"].min())
    ymax = float(used_stops["stop_lat"].max())
    pad_x = (xmax - xmin) * 0.05
    pad_y = (ymax - ymin) * 0.05
    bounds = (xmin - pad_x, xmax + pad_x, ymin - pad_y, ymax + pad_y)

    t_min = int(seg["t0"].min())
    t_max = int(seg["t1"].max())

    return DayModel(
        date_yyyymmdd=date_yyyymmdd,
        line_names=line_names,
        palette=palette,
        t0=seg["t0"].to_numpy(np.int32),
        t1=seg["t1"].to_numpy(np.int32),
        lon0=seg["lon0"].to_numpy(np.float64),
        lat0=seg["lat0"].to_numpy(np.float64),
        lon1=seg["lon1"].to_numpy(np.float64),
        lat1=seg["lat1"].to_numpy(np.float64),
        route_idx=seg["route_idx"].to_numpy(np.int16),
        stops_lon=used_stops["stop_lon"].to_numpy(np.float64),
        stops_lat=used_stops["stop_lat"].to_numpy(np.float64),
        shape_lines=shape_lines,
        bounds=bounds,
        t_min=t_min,
        t_max=t_max,
    )


# -------------------------
# Basemap (optional)
# -------------------------
def _maybe_load_basemap(bounds_3857: Tuple[float, float, float, float], zoom: int):
    try:
        import contextily as ctx  # optional
    except Exception:
        return None, None

    xmin, xmax, ymin, ymax = bounds_3857
    try:
        img, ext = ctx.bounds2img(
            xmin, ymin, xmax, ymax,
            zoom=zoom, ll=False,
            source=ctx.providers.CartoDB.Positron
        )
        extent = (ext[0], ext[2], ext[1], ext[3])  # (xmin,xmax,ymin,ymax)
        return img, extent
    except Exception:
        return None, None


# -------------------------
# GIF rendering (cached)
# -------------------------
@st.cache_data(show_spinner=False)
def render_gif_bytes(
    date_yyyymmdd: int,
    fps: int,
    duration_sec: int,
    width_px: int,
    show_shapes: bool,
    show_stops: bool,
    use_basemap: bool,
    basemap_zoom: int,
) -> bytes:
    model = build_day_model(date_yyyymmdd)

    frames = int(duration_sec * fps)
    sim_start, sim_end = model.t_min, model.t_max

    if use_basemap:
        stops_x, stops_y = lonlat_to_webmercator(model.stops_lon, model.stops_lat)
        lon0x, lat0y = lonlat_to_webmercator(model.lon0, model.lat0)
        lon1x, lat1y = lonlat_to_webmercator(model.lon1, model.lat1)

        xmin, xmax, ymin, ymax = model.bounds
        bx, by = lonlat_to_webmercator(np.array([xmin, xmax, xmin, xmax]), np.array([ymin, ymin, ymax, ymax]))
        bounds = (float(bx.min()), float(bx.max()), float(by.min()), float(by.max()))

        shape_lines_xy: List[np.ndarray] = []
        if show_shapes and model.shape_lines:
            for ln in model.shape_lines:
                x, y = lonlat_to_webmercator(ln[:, 0], ln[:, 1])
                shape_lines_xy.append(np.column_stack([x, y]))
    else:
        stops_x, stops_y = model.stops_lon, model.stops_lat
        lon0x, lat0y = model.lon0, model.lat0
        lon1x, lat1y = model.lon1, model.lat1
        bounds = model.bounds
        shape_lines_xy = model.shape_lines if show_shapes else []

    xmin, xmax, ymin, ymax = bounds

    bg_img, bg_extent = (None, None)
    if use_basemap:
        bg_img, bg_extent = _maybe_load_basemap(bounds, basemap_zoom)

    dpi = 110
    fig_w = max(6.0, width_px / dpi)
    fig_h = fig_w

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)

    if bg_img is not None and bg_extent is not None:
        ax.imshow(bg_img, extent=bg_extent, origin="upper", alpha=0.95)
    else:
        ax.set_facecolor("white")

    if show_shapes and shape_lines_xy:
        for ln in shape_lines_xy:
            ax.plot(ln[:, 0], ln[:, 1], linewidth=1.2, alpha=0.35)

    if show_stops:
        ax.scatter(stops_x, stops_y, s=3.0, alpha=0.25)

    train_scatter = ax.scatter([], [], s=14.0, alpha=0.95)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    title = ax.set_title("", fontsize=14)
    fig.tight_layout(pad=0.5)

    buf = io.BytesIO()
    with imageio.get_writer(buf, format="GIF", mode="I", duration=1 / max(fps, 1), loop=0) as writer:
        for k in range(frames):
            sim_t = int(sim_start + (k / max(frames - 1, 1)) * (sim_end - sim_start))

            mask = (model.t0 <= sim_t) & (model.t1 >= sim_t)
            if np.any(mask):
                dt = (model.t1[mask] - model.t0[mask]).astype(np.float64)
                alpha = (sim_t - model.t0[mask]).astype(np.float64) / dt

                x = lon0x[mask] + alpha * (lon1x[mask] - lon0x[mask])
                y = lat0y[mask] + alpha * (lat1y[mask] - lat0y[mask])

                train_scatter.set_offsets(np.column_stack([x, y]))
                colors = np.array([model.palette[i] for i in model.route_idx[mask]], dtype=object)
                train_scatter.set_color(colors)
            else:
                train_scatter.set_offsets(np.empty((0, 2)))
                train_scatter.set_color([])

            title.set_text(f"Berlin U-Bahn {date_yyyymmdd} · {sec_to_hms(sim_t)}")
            fig.canvas.draw()

            # Matplotlib >= 3.9: use RGBA buffer
            w, h = fig.canvas.get_width_height()
            rgba = np.asarray(fig.canvas.buffer_rgba(), dtype=np.uint8).reshape(h, w, 4)
            rgb = rgba[:, :, :3]  # drop alpha
            writer.append_data(rgb)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# -------------------------
# Streamlit UI
# -------------------------
st.title("Berlin U-Bahn — Day-in-a-Minute (als GIF)")

missing = _missing_files()
if missing:
    st.error(
        "Fehlende Dateien im App-Ordner:\n\n"
        + "\n".join([f"- {m}: erwartet {FILES.get(m, '<none>')}" for m in missing])
    )
    st.stop()

dates = available_dates()
if not dates:
    st.error("Konnte keine verfügbaren Daten (calendar/calendar_dates) finden.")
    st.stop()

col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.subheader("Einstellungen")
    date = st.selectbox("Datum (YYYYMMDD)", dates, index=0)

    fps = st.slider("FPS (Animation)", 1, 20, 10)
    duration_sec = st.slider("GIF-Dauer (Sekunden)", 10, 120, 60)
    width_px = st.slider("Größe (px, Breite)", 600, 1600, 1100, step=50)

    show_shapes = st.checkbox("U-Bahn-Linien (shapes) zeichnen", value=True)
    show_stops = st.checkbox("Stops als Punkte zeichnen", value=True)

    use_basemap = st.checkbox("Berlin-Karte als Hintergrund (Tiles)", value=False)
    basemap_zoom = st.slider("Hintergrund-Zoom", 10, 16, 12) if use_basemap else 12

    st.caption(
        "Tipp: Erst ohne Hintergrund testen (schneller). "
        "Basemap braucht optional `contextily` + Internetzugang."
    )

    render = st.button("GIF rendern")

with col_right:
    st.subheader("Vorschau")

    if render:
        with st.status("Render läuft…", expanded=True) as status:
            try:
                gif_bytes = render_gif_bytes(
                    date_yyyymmdd=int(date),
                    fps=int(fps),
                    duration_sec=int(duration_sec),
                    width_px=int(width_px),
                    show_shapes=bool(show_shapes),
                    show_stops=bool(show_stops),
                    use_basemap=bool(use_basemap),
                    basemap_zoom=int(basemap_zoom),
                )
                status.update(label="Fertig ✅", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Fehler beim Rendern", state="error", expanded=True)
                st.exception(e)
                st.stop()

        st.image(gif_bytes)
        st.download_button(
            "GIF herunterladen",
            data=gif_bytes,
            file_name=f"berlin_ubahn_{date}_day_in_a_minute.gif",
            mime="image/gif",
        )
    else:
        st.info("Links Einstellungen setzen → „GIF rendern“ klicken.")

