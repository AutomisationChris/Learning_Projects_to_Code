
    
  
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
    for name, angle, threshold in (('horizontal', 0, 0), ('diagonal', 45, shadow)):
        paths = hatch(image, width, height, spacing, cell, minimum, angle, threshold)
        counts.append(len(paths))
        svg.append(f'<g id="{name}" fill="none" stroke="#000" '
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
      background-image: radial-gradient(ellipse at 90% 0%, #d4e6dc 0%, transparent 55%),
                        radial-gradient(#9b9b852d 1px, transparent 1px);
      background-size: auto, 18px 18px;
    }
    .stApp [data-testid="stHeader"] {background: transparent;}
    [data-testid="stSidebar"] {background: #e6eee5;}
    [data-testid="stAppViewContainer"] .block-container {max-width: 1160px;}
    .stApp h1 {color: #183c32; font-family: Georgia, serif; font-size: clamp(3rem, 7vw, 5rem);}
    .stApp h2, .stApp p, .stApp label, .stApp [data-testid="stMetricValue"] {color: #183c32;}
    .plot-paper {background: #fffefa; padding: 5%; border: 1px solid #d9d6c9;
                 box-shadow: 0 12px 30px #183c321a; border-radius: 5px;}
    .plot-paper img {display: block; width: 100%; max-height: 65vh; object-fit: contain;}
    </style>
    """, unsafe_allow_html=True)
    st.title("Plotter Studio")
    st.write("Vom Foto zur Schraffur in Millimetern.")
    photo = st.file_uploader("Foto auswählen", type=["jpg", "jpeg", "png", "webp"])

    with st.sidebar:
        st.header("Schraffur einstellen")
        width = st.slider("Motivbreite (mm)", 20, 841, 180)
        spacing = st.slider("Linienabstand (mm)", 0.2, 5.0, 0.6, 0.05)
        cell = st.slider("Zelllänge (mm)", 0.2, 8.0, 1.2, 0.05)
        pen = st.slider("Stiftbreite (mm)", 0.05, 2.0, 0.2, 0.05)
        minimum = st.slider("Mindeststrich (mm)", 0.05, 2.0, 0.2, 0.05,
                            help="Darf höchstens so groß wie die Zelllänge sein.")
        shadow = st.slider("Schattenschwelle", 0.0, 0.95, 0.6, 0.05,
                           help="Je höher der Wert, desto dunkler muss eine Stelle für diagonale Linien sein.")
        generate = st.button("Schraffur berechnen", type="primary")

    if photo is None:
        st.info("Lade ein Foto hoch, um zu starten.")
        return
    data = photo.getvalue()
    settings = (width, spacing, cell, pen, minimum, shadow)
    if generate:
        if minimum > cell:
            st.error("Der Mindeststrich darf höchstens so groß wie die Zelllänge sein.")
        else:
            try:
                with Image.open(BytesIO(data)) as source:
                    gray = ImageOps.autocontrast(
                        ImageOps.exif_transpose(source).convert("L"), cutoff=1
                    )
                with st.spinner("Schraffur wird berechnet …"):
                    result = render_svg(gray, *settings)
                st.session_state["plot"] = (data, settings, result)
            except (OSError, Image.DecompressionBombError):
                st.error("Das Foto konnte nicht gelesen werden.")

    original, result_column = st.columns([1, 1.45], gap="large")
    with original:
        st.subheader("Original")
        st.image(data, width="stretch")
    with result_column:
        st.subheader("Plotter-Vorschau")
        saved = st.session_state.get("plot")
        if saved is None or saved[0] != data or saved[1] != settings:
            st.info("Klicke auf „Schraffur berechnen“, um die aktuellen Einstellungen anzuwenden.")
            return
        svg, height, counts = saved[2]
        encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        st.markdown(f'<div class="plot-paper"><img alt="Schraffurvorschau" '
                    f'src="data:image/svg+xml;base64,{encoded}"></div>', unsafe_allow_html=True)
        st.caption(f"Motiv {width:g} × {height:.1f} mm · "
                   f"{counts[0]:,} horizontale / {counts[1]:,} diagonale Striche".replace(",", " "))
        st.download_button("SVG herunterladen", svg, f"{Path(photo.name).stem}_plot.svg",
                           "image/svg+xml")


if __name__ == "__main__":
    main()

