# Libraries used:
# - streamlit
# - pandas
# - numpy
# - matplotlib
# - imageio
# - contextily (optional, for basemap tiles)
# - xyzservices (optional, provider registry for contextily)

from __future__ import annotations

import io
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

import imageio.v2 as imageio

# Optional basemap (downloads tiles from the internet)
try:
    import contextily as cx  # type: ignore
except Exception:
    cx = None


# -------------------------
# Paths / files
# -------------------------
DATA_DIR = Path(__file__).resolve().parent

FILES = {
    "stops": DATA_DIR / "stops.txt",
    "routes": DATA_DIR / "routes.txt",
    "trips": DATA_DIR / "trips_ubahn.txt",
    "calendar_dates": DATA_DIR / "calendar_dates_ubahn.txt",
    # stop_times may be .txt OR .zip (some feeds ship huge txt)
    "stop_times_txt": DATA_DIR / "stop_times_ubahn.txt",
    "stop_times_zip": DATA_DIR / "stop_times_ubahn.zip",
    "shapes": DATA_DIR / "shapes_ubahn.txt",
}

# -------------------------
# Small utilities
# -------------------------
def gtfs_time_to_sec(series: pd.Series) -> np.ndarray:
    """Parse GTFS HH:MM:SS into seconds; supports hours > 24."""
    parts = series.astype(str).str.split(":", expand=True)
    return (
        parts[0].astype(np.int32).to_numpy() * 3600
        + parts[1].astype(np.int32).to_numpy() * 60
        + parts[2].astype(np.int32).to_numpy()
    )


def sec_to_hms(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def lonlat_to_webmercator(lon: np.ndarray, lat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """EPSG:4326 -> EPSG:3857 (Web Mercator)."""
    # clamp latitude to avoid infinity at poles
    lat = np.clip(lat, -85.05112878, 85.05112878)
    r = 6378137.0
    x = r * np.deg2rad(lon)
    y = r * np.log(np.tan(np.pi / 4 + np.deg2rad(lat) / 2))
    return x, y


def pick_ubahn_routes(routes: pd.DataFrame) -> pd.DataFrame:
    """Pick Berlin U-Bahn routes from routes.txt (robust against feed quirks)."""
    r = routes.copy()
    r["route_short_name"] = r["route_short_name"].astype(str)
    is_u = r["route_short_name"].str.match(r"^U\d+$", na=False)
    # BVG agency_id is often 796 in public feeds; keep fallback if missing
    if "agency_id" in r.columns:
        is_bvg = r["agency_id"].astype(str).isin(["796", "BVG"])
        r = r[is_u & is_bvg].copy() if is_bvg.any() else r[is_u].copy()
    else:
        r = r[is_u].copy()

    # Some feeds use route_type 400, some 700 for subway variants -> don't overfilter.
    r["route_color"] = r.get("route_color", "").fillna("").replace("", "999999")
    return r[["route_id", "route_short_name", "route_color"]].drop_duplicates()


def read_stop_times(path_txt: Path, path_zip: Path) -> pd.DataFrame:
    """Read stop_times_ubahn from txt or from zip (first *.txt inside)."""
    usecols = ["trip_id", "departure_time", "stop_id", "stop_sequence"]
    dtypes = {"trip_id": "string", "stop_id": "string", "stop_sequence": "int32"}

    if path_txt.exists():
        return pd.read_csv(path_txt, usecols=usecols, dtype=dtypes)

    if path_zip.exists():
        with zipfile.ZipFile(path_zip, "r") as zf:
            # pick first txt file
            txts = [n for n in zf.namelist() if n.lower().endswith(".txt")]
            if not txts:
                raise FileNotFoundError("stop_times_ubahn.zip contains no .txt file")
            with zf.open(txts[0]) as f:
                return pd.read_csv(f, usecols=usecols, dtype=dtypes)

    raise FileNotFoundError("Missing stop_times_ubahn.txt and stop_times_ubahn.zip")


# -------------------------
# Data loading (cached)
# -------------------------
@st.cache_data(show_spinner=False)
def load_tables() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    stops = pd.read_csv(
        FILES["stops"],
        usecols=["stop_id", "stop_lat", "stop_lon"],
        dtype={"stop_id": "string", "stop_lat": "float64", "stop_lon": "float64"},
    )

    routes = pd.read_csv(
        FILES["routes"],
        usecols=["route_id", "agency_id", "route_short_name", "route_type", "route_color"],
        dtype={"route_id": "string", "agency_id": "string", "route_short_name": "string", "route_color": "string"},
    )

    trips = pd.read_csv(
        FILES["trips"],
        usecols=["trip_id", "route_id", "service_id", "shape_id"],
        dtype={"trip_id": "string", "route_id": "string", "service_id": "string", "shape_id": "string"},
    )

    cald = pd.read_csv(
        FILES["calendar_dates"],
        usecols=["service_id", "date", "exception_type"],
        dtype={"service_id": "string", "date": "int64", "exception_type": "int8"},
    )

    stop_times = read_stop_times(FILES["stop_times_txt"], FILES["stop_times_zip"])

    shapes = pd.read_csv(
        FILES["shapes"],
        usecols=["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
        dtype={"shape_id": "string", "shape_pt_lat": "float64", "shape_pt_lon": "float64", "shape_pt_sequence": "int32"},
    )

    return stops, routes, trips, cald, stop_times, shapes


@dataclass
class DayData:
    # segments for animation
    t0: np.ndarray
    t1: np.ndarray
    x0: np.ndarray
    y0: np.ndarray
    x1: np.ndarray
    y1: np.ndarray
    route_idx: np.ndarray

    # background
    stops_x: np.ndarray
    stops_y: np.ndarray
    shape_lines: List[np.ndarray]  # list of (N,2) arrays (x,y)

    # styling
    palette: List[str]
    line_names: List[str]

    # meta
    t_min: int
    t_max: int
    bounds: Tuple[float, float, float, float]  # xmin,xmax,ymin,ymax


@st.cache_data(show_spinner=False)
def build_day(date_yyyymmdd: int) -> DayData:
    stops, routes, trips, cald, stop_times, shapes = load_tables()

    routes_u = pick_ubahn_routes(routes)

    # Services active on that date (this feed is basically "calendar_dates is the calendar")
    active_services = set(
        cald.loc[(cald["date"] == date_yyyymmdd) & (cald["exception_type"] == 1), "service_id"].tolist()
    )
    if not active_services:
        raise ValueError(f"No active services found for {date_yyyymmdd}")

    trips_u = trips.merge(routes_u, on="route_id", how="inner")
    trips_u = trips_u[trips_u["service_id"].isin(active_services)][
        ["trip_id", "route_id", "route_short_name", "route_color", "shape_id"]
    ].copy()

    active_trip_ids = set(trips_u["trip_id"].tolist())
    if not active_trip_ids:
        raise ValueError(f"No trips found for {date_yyyymmdd} (after filtering to U-Bahn)")

    # Filter stop_times to active trips
    stt = stop_times[stop_times["trip_id"].isin(active_trip_ids)].copy()

    # Join stop coords
    stt = stt.merge(stops, on="stop_id", how="left").dropna(subset=["stop_lat", "stop_lon"])

    # Parse times -> seconds
    stt["t0"] = gtfs_time_to_sec(stt["departure_time"])
    stt.sort_values(["trip_id", "stop_sequence"], inplace=True)

    # Build consecutive-stop segments per trip
    g = stt.groupby("trip_id", sort=False)
    stt["lat1"] = g["stop_lat"].shift(-1)
    stt["lon1"] = g["stop_lon"].shift(-1)
    stt["t1"] = g["t0"].shift(-1)

    seg = stt.dropna(subset=["lat1", "lon1", "t1"]).copy()
    seg.rename(columns={"stop_lat": "lat0", "stop_lon": "lon0"}, inplace=True)

    # forward only
    seg = seg[seg["t1"] > seg["t0"]]

    # add route for coloring
    seg = seg.merge(trips_u[["trip_id", "route_short_name", "route_color"]], on="trip_id", how="left")
    seg = seg.dropna(subset=["route_short_name", "route_color"])

    # palette mapping
    line_names = sorted(seg["route_short_name"].unique().tolist(), key=lambda x: int(str(x)[1:]))
    palette = []
    for ln in line_names:
        col = trips_u.loc[trips_u["route_short_name"] == ln, "route_color"]
        c = (col.iloc[0] if len(col) else "999999")
        palette.append("#" + str(c))

    idx_map = {ln: i for i, ln in enumerate(line_names)}
    seg["route_idx"] = seg["route_short_name"].map(idx_map).astype(np.int16)

    # background stops (only used stops)
    used_stop_ids = stt["stop_id"].unique()
    used_stops = stops[stops["stop_id"].isin(used_stop_ids)].copy()

    # Convert to Web Mercator (for basemap + consistent aspect)
    x0, y0 = lonlat_to_webmercator(seg["lon0"].to_numpy(np.float64), seg["lat0"].to_numpy(np.float64))
    x1, y1 = lonlat_to_webmercator(seg["lon1"].to_numpy(np.float64), seg["lat1"].to_numpy(np.float64))
    stops_x, stops_y = lonlat_to_webmercator(
        used_stops["stop_lon"].to_numpy(np.float64), used_stops["stop_lat"].to_numpy(np.float64)
    )

    # Shape polylines (background track lines)
    # Keep only shape_ids referenced by our active trips
    shape_ids = set(trips_u["shape_id"].dropna().unique().tolist())
    shapes_u = shapes[shapes["shape_id"].isin(shape_ids)].copy()
    shapes_u.sort_values(["shape_id", "shape_pt_sequence"], inplace=True)

    shape_lines: List[np.ndarray] = []
    if not shapes_u.empty:
        for _, gg in shapes_u.groupby("shape_id", sort=False):
            xs, ys = lonlat_to_webmercator(
                gg["shape_pt_lon"].to_numpy(np.float64), gg["shape_pt_lat"].to_numpy(np.float64)
            )
            pts = np.column_stack([xs, ys])
            if len(pts) >= 2:
                shape_lines.append(pts)

    # Bounds (with padding)
    xmin, xmax = float(stops_x.min()), float(stops_x.max())
    ymin, ymax = float(stops_y.min()), float(stops_y.max())
    pad_x = (xmax - xmin) * 0.06
    pad_y = (ymax - ymin) * 0.06
    bounds = (xmin - pad_x, xmax + pad_x, ymin - pad_y, ymax + pad_y)

    return DayData(
        t0=seg["t0"].to_numpy(np.int32),
        t1=seg["t1"].to_numpy(np.int32),
        x0=x0.astype(np.float64),
        y0=y0.astype(np.float64),
        x1=x1.astype(np.float64),
        y1=y1.astype(np.float64),
        route_idx=seg["route_idx"].to_numpy(np.int16),
        stops_x=stops_x.astype(np.float64),
        stops_y=stops_y.astype(np.float64),
        shape_lines=shape_lines,
        palette=palette,
        line_names=line_names,
        t_min=int(seg["t0"].min()),
        t_max=int(seg["t1"].max()),
        bounds=bounds,
    )


# -------------------------
# Basemap (cached) — downloaded once, reused for all frames
# -------------------------
@st.cache_data(show_spinner=False)
def get_basemap_img(bounds: Tuple[float, float, float, float], zoom: int, provider_name: str):
    """
    Returns (img, extent) in WebMercator coords.
    extent = (xmin, xmax, ymin, ymax) for imshow.
    """
    if cx is None:
        return None, None, "contextily not installed (add it to requirements.txt)."

    providers = {
        "CartoDB Positron": cx.providers.CartoDB.Positron,
        "CartoDB Voyager": cx.providers.CartoDB.Voyager,
        "OpenStreetMap Mapnik": cx.providers.OpenStreetMap.Mapnik,
    }
    provider = providers.get(provider_name, cx.providers.CartoDB.Positron)

    xmin, xmax, ymin, ymax = bounds
    try:
        # bounds2img expects w,s,e,n
        img, ext = cx.bounds2img(xmin, ymin, xmax, ymax, zoom=zoom, source=provider, ll=False)
        # cx returns ext = (w, e, s, n) -> convert to imshow extent (xmin, xmax, ymin, ymax)
        extent = (ext[0], ext[1], ext[2], ext[3])
        return img, extent, None
    except Exception as e:
        return None, None, f"Basemap download failed: {e}"


# -------------------------
# Rendering (GIF bytes)
# -------------------------
@st.cache_data(show_spinner=False)
def render_gif_bytes(
    date_yyyymmdd: int,
    fps: int,
    duration_sec: int,
    show_shapes: bool,
    show_stops: bool,
    show_basemap: bool,
    basemap_provider: str,
    basemap_zoom: int,
    basemap_alpha: float,
    point_size: float,
    train_size: float,
) -> Tuple[bytes, Dict]:
    day = build_day(date_yyyymmdd)

    # Pre-fetch basemap once
    basemap_img, basemap_extent, basemap_err = (None, None, None)
    if show_basemap:
        basemap_img, basemap_extent, basemap_err = get_basemap_img(day.bounds, basemap_zoom, basemap_provider)

    frames = int(duration_sec * fps)
    sim_start, sim_end = day.t_min, day.t_max

    xmin, xmax, ymin, ymax = day.bounds

    meta = {
        "t_min": day.t_min,
        "t_max": day.t_max,
        "lines": day.line_names,
        "stops": len(day.stops_x),
        "basemap_error": basemap_err,
        "basemap_ok": basemap_img is not None,
    }

    imgs: List[np.ndarray] = []

    for k in range(frames):
        sim_t = int(sim_start + (k / max(frames - 1, 1)) * (sim_end - sim_start))

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

        fig, ax = plt.subplots(figsize=(10, 10), dpi=120)

        # Basemap
        if basemap_img is not None and basemap_extent is not None:
            ax.imshow(
                basemap_img,
                extent=basemap_extent,
                origin="upper",
                alpha=basemap_alpha,
                zorder=0,
            )

        # Shapes (track lines)
        if show_shapes and day.shape_lines:
            for pts in day.shape_lines:
                ax.plot(pts[:, 0], pts[:, 1], linewidth=1.2, alpha=0.55, zorder=1)

        # Stops
        if show_stops:
            ax.scatter(day.stops_x, day.stops_y, s=point_size, alpha=0.25, zorder=2)

        # Trains
        ax.scatter(x, y, s=train_size, c=colors, alpha=0.95, zorder=3)

        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal", adjustable="box")
        ax.set_axis_off()
        ax.set_title(f"Berlin U-Bahn {date_yyyymmdd} — {sec_to_hms(sim_t)}", fontsize=14)

        # Convert figure -> RGB image (robust across Matplotlib versions)
        fig.canvas.draw()
        rgba = np.asarray(fig.canvas.buffer_rgba())
        rgb = rgba[..., :3].copy()

        imgs.append(rgb)
        plt.close(fig)

    buf = io.BytesIO()
    imageio.mimsave(buf, imgs, format="GIF", fps=fps)
    return buf.getvalue(), meta


# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="Berlin U-Bahn Day-in-a-Minute", layout="wide")
st.title("Berlin U-Bahn — 1 Minute = 1 Betriebstag")

# sanity checks
missing = []
for k, p in FILES.items():
    if k in ("stop_times_txt", "stop_times_zip"):
        continue
    if not p.exists():
        missing.append(k)

# stop_times needs either txt or zip
if not (FILES["stop_times_txt"].exists() or FILES["stop_times_zip"].exists()):
    missing.append("stop_times_ubahn (.txt oder .zip)")

if missing:
    st.error(f"Fehlende Dateien: {missing} (erwartet im Ordner: {DATA_DIR.resolve()})")
    st.stop()

with st.expander("Status / Debug", expanded=False):
    st.write("DATA_DIR:", str(DATA_DIR))
    st.write("contextily verfügbar:", cx is not None)
    if cx is None:
        st.info("Wenn du eine Karte willst: 'contextily' in requirements.txt aufnehmen (und deploy neu starten).")

# Load dates
_, _, _, cald, _, _ = load_tables()
available_dates = sorted(cald.loc[cald["exception_type"] == 1, "date"].unique().tolist())
if not available_dates:
    st.error("Keine verfügbaren Betriebstage in calendar_dates_ubahn.txt gefunden.")
    st.stop()

# Sidebar controls
st.sidebar.header("Einstellungen")
date = st.sidebar.selectbox("Datum (YYYYMMDD)", available_dates, index=min(0, len(available_dates) - 1))

fps = st.sidebar.slider("FPS (GIF)", min_value=2, max_value=20, value=8)
duration_sec = st.sidebar.slider("Dauer (Sekunden)", min_value=10, max_value=90, value=60)

st.sidebar.divider()
show_basemap = st.sidebar.checkbox("Karte (Basemap) anzeigen", value=True)
basemap_provider = st.sidebar.selectbox(
    "Basemap Provider",
    ["CartoDB Positron", "CartoDB Voyager", "OpenStreetMap Mapnik"],
    index=0,
)
basemap_zoom = st.sidebar.slider("Basemap Zoom", min_value=10, max_value=15, value=12)
basemap_alpha = st.sidebar.slider("Basemap Deckkraft", min_value=0.2, max_value=1.0, value=0.9)

st.sidebar.divider()
show_shapes = st.sidebar.checkbox("U-Bahn Linien (shapes) anzeigen", value=True)
show_stops = st.sidebar.checkbox("Stops anzeigen", value=True)

point_size = st.sidebar.slider("Stop-Punktgröße", min_value=0.5, max_value=6.0, value=1.8)
train_size = st.sidebar.slider("Zug-Punktgröße", min_value=4.0, max_value=30.0, value=11.0)

# Main action
col_left, col_right = st.columns([1, 2])

with col_left:
    st.markdown("**Output**")
    st.caption("Erzeugt ein GIF (1 Minute) und spielt es ab. Danach kannst du es direkt herunterladen.")

    render = st.button("GIF rendern")

with col_right:
    st.markdown("**Preview**")
    placeholder = st.empty()

if render:
    with st.spinner("Rendering… (Tiles + GTFS + GIF)"):
        gif_bytes, meta = render_gif_bytes(
            date_yyyymmdd=int(date),
            fps=int(fps),
            duration_sec=int(duration_sec),
            show_shapes=bool(show_shapes),
            show_stops=bool(show_stops),
            show_basemap=bool(show_basemap),
            basemap_provider=str(basemap_provider),
            basemap_zoom=int(basemap_zoom),
            basemap_alpha=float(basemap_alpha),
            point_size=float(point_size),
            train_size=float(train_size),
        )

    if show_basemap and not meta.get("basemap_ok", False):
        st.warning(
            "Basemap konnte nicht geladen werden. "
            "Typisch: contextily fehlt in requirements.txt oder Tiles sind von Streamlit Cloud/Netzwerk geblockt.\n\n"
            f"Details: {meta.get('basemap_error')}"
        )

    placeholder.image(gif_bytes, caption=f"Berlin U-Bahn {date} — {duration_sec}s @ {fps} FPS", use_container_width=True)
    st.download_button("GIF herunterladen", data=gif_bytes, file_name=f"berlin_ubahn_{date}.gif", mime="image/gif")

    st.caption(
        f"Sim-Zeit: {sec_to_hms(meta['t_min'])} → {sec_to_hms(meta['t_max'])} · "
        f"Stops: {meta['stops']} · Linien: {', '.join(meta['lines'])}"
    )
