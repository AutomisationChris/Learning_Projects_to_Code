import streamlit as st
import requests
from datetime import datetime, date, time as dtime
from urllib.parse import quote

# ─── Seitenkonfiguration ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="DB Navigator – Fahrrad",
    page_icon="🚆",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── CSS: DB Navigator Look ───────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DB+Sans:wght@400;500;700&family=Source+Sans+3:wght@400;600;700&display=swap');

/* DB Rot: #EC0016  |  DB Dunkel: #131821  |  DB Grau: #F0F3F5 */

html, body, [class*="css"] {
    font-family: 'Source Sans 3', 'Helvetica Neue', sans-serif;
    background-color: #F0F3F5;
}

/* Header */
.db-header {
    background: #EC0016;
    color: white;
    padding: 14px 20px 12px 20px;
    border-radius: 0 0 0 0;
    display: flex;
    align-items: center;
    gap: 12px;
    margin: -1rem -1rem 1.5rem -1rem;
    font-size: 1.15rem;
    font-weight: 700;
    letter-spacing: .3px;
}
.db-logo {
    background: white;
    color: #EC0016;
    font-weight: 900;
    font-size: 1.1rem;
    padding: 2px 8px;
    border-radius: 3px;
    letter-spacing: 1px;
}

/* Suchfeld-Karte */
.db-card {
    background: white;
    border-radius: 8px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.10);
    margin-bottom: 1rem;
}
.db-card-title {
    font-size: .78rem;
    font-weight: 700;
    color: #646973;
    text-transform: uppercase;
    letter-spacing: .8px;
    margin-bottom: .7rem;
}

/* Verbindungs-Karte */
.conn-card {
    background: white;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,.10);
    margin-bottom: .8rem;
    overflow: hidden;
    border-left: 5px solid #EC0016;
    transition: box-shadow .15s;
}
.conn-card:hover { box-shadow: 0 3px 12px rgba(0,0,0,.14); }
.conn-header {
    padding: .9rem 1.1rem .5rem 1.1rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}
.conn-zeit {
    font-size: 1.45rem;
    font-weight: 700;
    color: #131821;
    letter-spacing: -.5px;
}
.conn-dauer {
    font-size: .82rem;
    color: #646973;
    margin-top: 2px;
}
.conn-zuege {
    font-size: .88rem;
    color: #131821;
    padding: 0 1.1rem .3rem 1.1rem;
}
.conn-zug-chip {
    display: inline-block;
    background: #F0F3F5;
    border: 1px solid #D7DCE1;
    border-radius: 4px;
    padding: 1px 7px;
    font-size: .8rem;
    font-weight: 600;
    margin-right: 4px;
    color: #131821;
}
.conn-zug-chip.ice { background: #131821; color: white; border-color: #131821; }
.conn-zug-chip.ic  { background: #EC0016; color: white; border-color: #EC0016; }
.conn-zug-chip.re  { background: #3C6EA6; color: white; border-color: #3C6EA6; }
.conn-zug-chip.rb  { background: #3C6EA6; color: white; border-color: #3C6EA6; }
.conn-zug-chip.sb  { background: #006F35; color: white; border-color: #006F35; }

/* Fahrrad-Badge */
.bike-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    border-radius: 20px;
    padding: 3px 11px 3px 8px;
    font-size: .82rem;
    font-weight: 700;
    margin: .5rem 1.1rem .9rem 1.1rem;
}
.bike-badge.ok     { background: #E8F5E9; color: #1B5E20; border: 1.5px solid #4CAF50; }
.bike-badge.ticket { background: #FFF8E1; color: #7d5200; border: 1.5px solid #FFC107; }
.bike-badge.hvz    { background: #FFEBEE; color: #B71C1C; border: 1.5px solid #F44336; }
.bike-badge.fold   { background: #E3F2FD; color: #0D47A1; border: 1.5px solid #2196F3; }

/* Leg-Details */
.leg-row {
    padding: .35rem 1.1rem;
    border-top: 1px solid #F0F3F5;
    font-size: .85rem;
    color: #3a3f48;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.leg-left { flex: 1; }
.leg-right { text-align: right; font-size: .78rem; color: #646973; }

/* Divider */
.db-divider { border: none; border-top: 1px solid #D7DCE1; margin: .8rem 0; }

/* Streckeninfo oben */
.route-info {
    background: #EC0016;
    color: white;
    border-radius: 8px;
    padding: .7rem 1.1rem;
    font-size: .95rem;
    font-weight: 600;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Streamlit overrides */
div[data-testid="stExpander"] {
    background: white;
    border-radius: 8px !important;
    border: 1px solid #D7DCE1 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.07);
}
button[data-testid="baseButton-primary"] {
    background: #EC0016 !important;
    border: none !important;
    font-weight: 700 !important;
    letter-spacing: .3px !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="db-header">
    <span class="db-logo">DB</span>
    Navigator &nbsp;·&nbsp; 🚲 Fahrrad-Check
</div>
""", unsafe_allow_html=True)

# ─── Konstanten ───────────────────────────────────────────────────────────────
API_BASE = "https://v6.db.transport.rest"

PRODUKT_REGELN = {
    "nationalExpress": dict(name="ICE",  chip="ice", ticket=True,  hvz=False, preis="~9 €", faltrad_frei=True,  hinweis="Reservierung + Fahrradticket Pflicht."),
    "national":        dict(name="IC/EC",chip="ic",  ticket=True,  hvz=False, preis="~9 €", faltrad_frei=True,  hinweis="Ticket + Reservierung empfohlen."),
    "regionalExp":     dict(name="RE",   chip="re",  ticket=True,  hvz=True,  preis="~3–6 €",faltrad_frei=True, hinweis="Ticket nötig. HVZ: oft verboten."),
    "regional":        dict(name="RB",   chip="rb",  ticket=True,  hvz=True,  preis="~3–6 €",faltrad_frei=True, hinweis="Ticket nötig. HVZ: eingeschränkt."),
    "suburban":        dict(name="S",    chip="sb",  ticket=True,  hvz=True,  preis="~2–4 €",faltrad_frei=True, hinweis="Nur außerhalb HVZ erlaubt."),
    "subway":          dict(name="U",    chip="",    ticket=False, hvz=True,  preis="kostenlos",faltrad_frei=True,hinweis="Kostenlos, HVZ beachten."),
    "tram":            dict(name="Tram", chip="",    ticket=False, hvz=False, preis="kostenlos",faltrad_frei=True,hinweis="Meist kostenlos, wenn Platz da."),
    "bus":             dict(name="Bus",  chip="",    ticket=False, hvz=False, preis="–",      faltrad_frei=False,hinweis="Fahrräder meist NICHT erlaubt."),
    "ferry":           dict(name="Fähre",chip="",    ticket=False, hvz=False, preis="ggf. Entgelt",faltrad_frei=True,hinweis="Meist erlaubt, kleines Entgelt."),
}

def ist_hvz(dt: datetime) -> bool:
    if dt.weekday() >= 5: return False
    t = dt.hour * 60 + dt.minute
    return (360 <= t <= 540) or (960 <= t <= 1140)

def format_zeit(iso: str) -> str:
    if not iso: return "?"
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%H:%M")
    except: return iso[:5]

def calc_dauer(dep: str, arr: str) -> str:
    try:
        d = datetime.fromisoformat(dep.replace("Z", "+00:00"))
        a = datetime.fromisoformat(arr.replace("Z", "+00:00"))
        m = int((a - d).total_seconds() // 60)
        return f"{m // 60}h {m % 60:02d}min" if m >= 60 else f"{m} min"
    except: return ""

def get_produkt(line: dict) -> str:
    p = (line or {}).get("product", "regional")
    return p if p in PRODUKT_REGELN else "regional"

def chip_class(produkt_key: str) -> str:
    return PRODUKT_REGELN.get(produkt_key, {}).get("chip", "")

@st.cache_data(ttl=60, show_spinner=False)
def suche_bahnhof(name: str) -> list:
    try:
        r = requests.get(f"{API_BASE}/locations?query={quote(name)}&results=6&stops=true", timeout=8)
        r.raise_for_status()
        return [s for s in r.json() if s.get("type") in ("stop", "station")]
    except: return []

@st.cache_data(ttl=60, show_spinner=False)
def suche_verbindung(von_id: str, nach_id: str, abfahrt_iso: str) -> list:
    try:
        url = f"{API_BASE}/journeys?from={von_id}&to={nach_id}&departure={quote(abfahrt_iso)}&results=4&stopovers=false"
        r = requests.get(url, timeout=14)
        r.raise_for_status()
        return r.json().get("journeys", [])
    except: return []

def analysiere(journey: dict, faltrad: bool):
    legs_out = []
    braucht_ticket = False
    hvz_problem = False

    for leg in journey.get("legs", []):
        if leg.get("walking"): continue
        line = leg.get("line", {})
        pk = get_produkt(line)
        regel = PRODUKT_REGELN[pk]

        dep_str = leg.get("departure") or leg.get("plannedDeparture", "")
        arr_str = leg.get("arrival") or leg.get("plannedArrival", "")
        dep_dt = None
        try: dep_dt = datetime.fromisoformat(dep_str.replace("Z", "+00:00"))
        except: pass

        hvz = bool(dep_dt and regel["hvz"] and ist_hvz(dep_dt))
        frei = faltrad and regel["faltrad_frei"]
        ticket = regel["ticket"] and not frei

        if ticket: braucht_ticket = True
        if hvz:    hvz_problem = True

        legs_out.append({
            "zugname":   line.get("name", "?"),
            "pk":        pk,
            "chip":      chip_class(pk),
            "von":       leg.get("origin", {}).get("name", "?"),
            "nach":      leg.get("destination", {}).get("name", "?"),
            "dep":       dep_str,
            "arr":       arr_str,
            "ticket":    ticket,
            "frei":      frei,
            "hvz":       hvz,
            "preis":     regel["preis"],
            "hinweis":   regel["hinweis"],
            "regel_name":regel["name"],
        })

    return legs_out, braucht_ticket, hvz_problem

# ─── Suchmaske ────────────────────────────────────────────────────────────────
st.markdown('<div class="db-card"><div class="db-card-title">Verbindung suchen</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    von_input  = st.text_input("Von", placeholder="München Hbf", label_visibility="visible")
with col2:
    nach_input = st.text_input("Nach", placeholder="Hamburg Hbf", label_visibility="visible")

col3, col4 = st.columns(2)
with col3:
    reisetag = st.date_input("Datum", value=date.today())
with col4:
    reisezeit = st.time_input("Abfahrt", value=dtime(8, 0))

faltrad = st.checkbox("🔧 Faltrad (zusammengeklappt in Tasche)")

st.markdown('</div>', unsafe_allow_html=True)

suchen = st.button("🔍  Verbindungen suchen", type="primary", use_container_width=True)

# ─── Suche ────────────────────────────────────────────────────────────────────
if suchen:
    if not von_input.strip() or not nach_input.strip():
        st.warning("Bitte Start- und Zielbahnhof eingeben.")
        st.stop()

    with st.spinner("Suche Bahnhöfe..."):
        von_list  = suche_bahnhof(von_input)
        nach_list = suche_bahnhof(nach_input)

    if not von_list:  st.error(f"'{von_input}' nicht gefunden."); st.stop()
    if not nach_list: st.error(f"'{nach_input}' nicht gefunden."); st.stop()

    von_s  = von_list[0]
    nach_s = nach_list[0]

    abfahrt_dt  = datetime.combine(reisetag, reisezeit)
    abfahrt_iso = abfahrt_dt.strftime("%Y-%m-%dT%H:%M:%S") + "+02:00"

    with st.spinner("Suche Verbindungen..."):
        journeys = suche_verbindung(von_s["id"], nach_s["id"], abfahrt_iso)

    if not journeys:
        st.error("Keine Verbindungen gefunden. Bitte anderen Zeitpunkt versuchen.")
        st.stop()

    # Streckenheader
    st.markdown(f"""
    <div class="route-info">
        🚉 {von_s['name']}
        &nbsp;→&nbsp;
        {nach_s['name']}
        &nbsp;&nbsp;|&nbsp;&nbsp;
        {abfahrt_dt.strftime('%a, %d.%m.%Y')}
    </div>
    """, unsafe_allow_html=True)

    # ─── Verbindungskarten ────────────────────────────────────────────────────
    for idx, journey in enumerate(journeys):
        legs = journey.get("legs", [])
        if not legs: continue

        first_dep = legs[0].get("departure") or legs[0].get("plannedDeparture", "")
        last_arr  = legs[-1].get("arrival")  or legs[-1].get("plannedArrival", "")
        dauer     = calc_dauer(first_dep, last_arr)

        zug_legs = [l for l in legs if not l.get("walking")]
        leg_infos, braucht_ticket, hvz_problem = analysiere(journey, faltrad)

        # Fahrrad-Badge bestimmen
        if hvz_problem:
            badge_cls = "hvz";    badge_txt = "⛔ Fahrrad während HVZ eingeschränkt"
        elif faltrad:
            badge_cls = "fold";   badge_txt = "🔧 Faltrad – meist kostenlos"
        elif braucht_ticket:
            badge_cls = "ticket"; badge_txt = "🎟️ Fahrradticket erforderlich"
        else:
            badge_cls = "ok";     badge_txt = "✅ Kein Fahrradticket nötig"

        # Zugchips HTML
        chips_html = ""
        for l in zug_legs:
            line = l.get("line", {})
            pk   = get_produkt(line)
            cls  = chip_class(pk)
            name = line.get("name", "?")
            chips_html += f'<span class="conn-zug-chip {cls}">{name}</span>'

        # Umsteigezahl
        umstiege = max(0, len(zug_legs) - 1)
        umstieg_txt = "Direktverbindung" if umstiege == 0 else f"{umstiege} Umstieg{'e' if umstiege > 1 else ''}"

        # Karte rendern
        with st.expander(
            f"{format_zeit(first_dep)} → {format_zeit(last_arr)}   |   {dauer}   |   {umstieg_txt}",
            expanded=(idx == 0)
        ):
            # Header
            st.markdown(f"""
            <div class="conn-header">
                <div>
                    <div class="conn-zeit">{format_zeit(first_dep)} → {format_zeit(last_arr)}</div>
                    <div class="conn-dauer">⏱ {dauer} &nbsp;·&nbsp; {umstieg_txt}</div>
                </div>
            </div>
            <div class="conn-zuege">{chips_html}</div>
            <div>
                <span class="bike-badge {badge_cls}">{badge_txt}</span>
            </div>
            <hr class="db-divider">
            """, unsafe_allow_html=True)

            # Abschnitte
            for leg in leg_infos:
                if leg["hvz"]:
                    status_icon = "⛔"
                    status_txt  = f"HVZ – Fahrrad evtl. verboten"
                elif leg["frei"]:
                    status_icon = "🔧"
                    status_txt  = "Faltrad – kostenlos"
                elif leg["ticket"]:
                    status_icon = "🎟️"
                    status_txt  = f"Ticket nötig ({leg['preis']})"
                else:
                    status_icon = "✅"
                    status_txt  = "Kein Ticket nötig"

                chip_cls = leg["chip"]
                st.markdown(f"""
                <div class="leg-row">
                    <div class="leg-left">
                        <span class="conn-zug-chip {chip_cls}">{leg['zugname']}</span>
                        &nbsp; {leg['von']} → {leg['nach']}
                        <br><small style="color:#646973;margin-left:4px">{leg['hinweis']}</small>
                    </div>
                    <div class="leg-right">
                        {format_zeit(leg['dep'])} – {format_zeit(leg['arr'])}<br>
                        <strong>{status_icon} {status_txt}</strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # HVZ-Globalwarnung
    abfahrt_check = datetime.combine(reisetag, reisezeit)
    if ist_hvz(abfahrt_check):
        st.warning("⚠️ **Reisezeit liegt in der Hauptverkehrszeit (Mo–Fr 6–9 oder 16–19 Uhr).** "
                   "In S-Bahn, RE und RB ist die Fahrradmitnahme oft verboten. "
                   "Bitte Regeln des jeweiligen Verkehrsverbunds prüfen.")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("""
<br>
<small style="color:#646973">
Verbindungsdaten: <a href="https://v6.db.transport.rest" target="_blank">v6.db.transport.rest</a>
(Community-API, kein offizielles DB-Produkt). Fahrrad-Regeln sind allgemeine Richtwerte –
bitte die Beförderungsbedingungen des jeweiligen Verbunds prüfen.
</small>
""", unsafe_allow_html=True)
