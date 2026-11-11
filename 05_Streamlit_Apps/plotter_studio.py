"""Export a photo as millimetre-scale pen-plotter hatching."""
from io import BytesIO
import math
from pathlib import Path

from PIL import Image, ImageOps

BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def line_bounds(offset, cosine, sine, width, height):
    lower, upper = -math.inf, math.inf
    for origin, direction, extent in (
        (-offset * sine, cosine, width),
        (offset * cosine, sine, height),
    ):
        if abs(direction) < 1e-12:
            if not 0 <= origin <= extent:
                return 0, 0
            continue
        a, b = sorted((-origin / direction, (extent - origin) / direction))
        lower, upper = max(lower, a), min(upper, b)
    return lower, upper


def hatch(image, width, height, spacing, cell, minimum, angle, threshold):
    cosine, sine = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    offsets = (0, -width * sine, height * cosine, height * cosine - width * sine)
    pixels = image.load()
    paths = []
    for row in range(math.floor(min(offsets) / spacing) + 1,
                     math.ceil(max(offsets) / spacing)):
        offset = row * spacing
        lower, upper = line_bounds(offset, cosine, sine, width, height)
        phase = cell / 2 if row % 2 else 0
        intervals = []
        for column in range(math.floor((lower - phase) / cell),
                            math.ceil((upper - phase) / cell)):
            start = max(lower, phase + column * cell)
            end = min(upper, phase + (column + 1) * cell)
            if end - start < minimum:
                continue
            darkness = 0
            for sample in range(5):
                t = start + (end - start) * (sample + 0.5) / 5
                x = t * cosine - offset * sine
                y = t * sine + offset * cosine
                px = min(image.width - 1, max(0, int(x / width * image.width)))
                py = min(image.height - 1, max(0, int(y / height * image.height)))
                darkness += 1 - pixels[px, py] / 255
            coverage = max(0, (darkness / 5 - threshold) / (1 - threshold))
            length = (end - start) * coverage
            if length < minimum:
                cutoff = (BAYER[row % 4][column % 4] + 0.5) / 16
                if length / minimum < cutoff:
                    continue
                length = minimum
            inset = (end - start - length) / 2
            a, b = start + inset, end - inset
            if intervals and a - intervals[-1][1] <= minimum / 2:
                intervals[-1] = (intervals[-1][0], b)
            else:
                intervals.append((a, b))
        if row % 2:
            intervals = [(b, a) for a, b in reversed(intervals)]
        for a, b in intervals:
            x1, y1 = a * cosine - offset * sine, a * sine + offset * cosine
            x2, y2 = b * cosine - offset * sine, b * sine + offset * cosine
            paths.append(f'M {x1:.4f},{y1:.4f} L {x2:.4f},{y2:.4f}')
    return paths


def render_svg(image, width, spacing, cell, pen, minimum, shadow):
    height = width * image.height / image.width
    margin = pen / 2
    page_w, page_h = width + pen, height + pen
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{page_w:.6f}mm" '
        f'height="{page_h:.6f}mm" viewBox="{-margin} {-margin} {page_w:.6f} {page_h:.6f}">'
    ]
    counts = []
    for name, angle, threshold, ink in (
        ("horizontal", 0, 0, "#243e68"),
        ("diagonal", 32, shadow, "#a85242"),
    ):
        paths = hatch(image, width, height, spacing, cell, minimum, angle, threshold)
        counts.append(len(paths))
        svg.append(f'<g id="{name}" fill="none" stroke="{ink}" '
                   f'stroke-width="{pen}" stroke-linecap="round">')
        svg.extend(f'<path d="{path}"/>' for path in paths)
        svg.append('</g>')
    svg.append('</svg>')
    return '\n'.join(svg), height, counts


def main():
    import base64
    import streamlit as st

    st.set_page_config(page_title="Plotter Studio", layout="wide")
    st.markdown("""
    <style>
    .stApp {
      color-scheme: light;
      background-color: #f4f0e6;
      background-image: radial-gradient(ellipse at 90% 0%, #d9e2ed 0%, transparent 55%),
                        radial-gradient(#9b9b852d 1px, transparent 1px);
      background-size: auto, 18px 18px;
    }
    .stApp [data-testid="stHeader"] {background: transparent;}
    [data-testid="stSidebar"] {background: #e5eaf1;}
    [data-testid="stAppViewContainer"] .block-container {max-width: 1160px;}
    .stApp h1 {color: #243855; font-family: Georgia, serif; font-size: clamp(3rem, 7vw, 5rem);}
    .stApp h2, .stApp p, .stApp label, .stApp [data-testid="stMetricValue"] {color: #243855;}
    .plot-paper {background: #fffefa; padding: 5%; border: 1px solid #d9d6c9;
                 box-shadow: 0 12px 30px #2438551a; border-radius: 5px;}
    .plot-paper img {display: block; width: 100%; max-height: 65vh; object-fit: contain;}
    </style>
    """, unsafe_allow_html=True)
    st.title("Plotter Studio")
    st.write("Turn a photo into a two-ink engraving for your pen plotter.")
    photo = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png", "webp"])

    with st.sidebar:
        st.header("Hatching settings")
        width = st.slider("Artwork width (mm)", 20, 841, 180)
        spacing = st.slider("Line spacing (mm)", 0.2, 5.0, 0.6, 0.05)
        cell = st.slider("Cell length (mm)", 0.2, 8.0, 1.2, 0.05)
        pen = st.slider("Pen width (mm)", 0.05, 2.0, 0.2, 0.05)
        minimum = st.slider("Minimum stroke (mm)", 0.05, 2.0, 0.2, 0.05,
                            help="Must be at most the cell length.")
        shadow = st.slider("Diagonal darkness threshold", 0.0, 0.95, 0.15, 0.05,
                           help="Lower values add diagonal hatching to lighter tones.")
        generate = st.button("Generate hatching", type="primary")

    if photo is None:
        st.info("Upload a photo to get started.")
        return
    data = photo.getvalue()
    settings = (width, spacing, cell, pen, minimum, shadow)
    if generate:
        if minimum > cell:
            st.error("Minimum stroke must be at most the cell length.")
        else:
            try:
                with Image.open(BytesIO(data)) as source:
                    gray = ImageOps.autocontrast(
                        ImageOps.exif_transpose(source).convert("L"), cutoff=1
                    )
                with st.spinner("Generating hatching…"):
                    result = render_svg(gray, *settings)
                st.session_state["plot"] = (data, settings, result)
            except (OSError, Image.DecompressionBombError):
                st.error("Could not read this image.")

    original, result_column = st.columns([1, 1.45], gap="large")
    with original:
        st.subheader("Original")
        st.image(data, width="stretch")
    with result_column:
        st.subheader("Plot preview")
        saved = st.session_state.get("plot")
        if saved is None or saved[0] != data or saved[1] != settings:
            st.info("Click “Generate hatching” to apply the current settings.")
            return
        svg, height, counts = saved[2]
        encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        st.markdown(f'<div class="plot-paper"><img alt="Hatching preview" '
                    f'src="data:image/svg+xml;base64,{encoded}"></div>', unsafe_allow_html=True)
        st.caption(f"Artwork {width:g} × {height:.1f} mm · "
                   f"{counts[0]:,} horizontal / {counts[1]:,} diagonal strokes".replace(",", " "))
        st.download_button("Download SVG", svg, f"{Path(photo.name).stem}_plot.svg",
                           "image/svg+xml")


if __name__ == "__main__":
    main()
