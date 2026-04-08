import re
import base64
import logging
import streamlit as st
from core.metrics import calcular_metricas
from core.rules_engine import analizar_flags
from core.report_generator import generar_informe

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

_PRIORIDADES_VALIDAS = {"balanced", "ruido", "eficiencia"}
_TIPOS_VALIDOS       = {"Quadcóptero", "Hexacóptero", "Octocóptero"}
_TIPOS_LIST          = ["Quadcóptero", "Hexacóptero", "Octocóptero"]
_PRIORIDADES_LIST    = ["balanced", "ruido", "eficiencia"]


def _sanitizar_texto(texto: str, max_len: int = 100) -> str:
    texto = texto.strip()
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)
    return texto[:max_len]


# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ADF Blades — Analizador de Rotores UAV",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── SVG ICON (base64) ──────────────────────────────────────────────────────────
_SVG_RAW = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">'
    '<circle cx="40" cy="40" r="9" fill="rgba(255,255,255,0.95)"/>'
    '<circle cx="40" cy="40" r="4.5" fill="#60A5FA"/>'
    '<line x1="40" y1="40" x2="16" y2="16" stroke="rgba(255,255,255,0.72)" stroke-width="3" stroke-linecap="round"/>'
    '<line x1="40" y1="40" x2="64" y2="16" stroke="rgba(255,255,255,0.72)" stroke-width="3" stroke-linecap="round"/>'
    '<line x1="40" y1="40" x2="16" y2="64" stroke="rgba(255,255,255,0.72)" stroke-width="3" stroke-linecap="round"/>'
    '<line x1="40" y1="40" x2="64" y2="64" stroke="rgba(255,255,255,0.72)" stroke-width="3" stroke-linecap="round"/>'
    '<ellipse cx="16" cy="16" rx="13" ry="4" fill="rgba(255,255,255,0.85)" transform="rotate(-45 16 16)"/>'
    '<ellipse cx="64" cy="16" rx="13" ry="4" fill="rgba(255,255,255,0.85)" transform="rotate(45 64 16)"/>'
    '<ellipse cx="16" cy="64" rx="13" ry="4" fill="rgba(255,255,255,0.85)" transform="rotate(45 16 64)"/>'
    '<ellipse cx="64" cy="64" rx="13" ry="4" fill="rgba(255,255,255,0.85)" transform="rotate(-45 64 64)"/>'
    '</svg>'
)
_ICON_URI = "data:image/svg+xml;base64," + base64.b64encode(_SVG_RAW.encode()).decode()

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── App background ── */
.stApp { background-color: #EEF2F7; }
.main .block-container { padding: 1.75rem 2rem 2rem; max-width: 1060px; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid #DDE3ED;
    box-shadow: 3px 0 16px rgba(0,0,0,0.07);
    min-width: 270px !important;
    max-width: 270px !important;
}
section[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }

.sb-head {
    background: linear-gradient(150deg, #0C1F3D 0%, #1A3460 55%, #2357C8 100%);
    padding: 1.6rem 1.25rem 1.3rem;
}
.sb-head h2 { color:#fff; font-size:1.05rem; font-weight:700; margin:0.65rem 0 0.15rem; letter-spacing:-0.02em; }
.sb-head p  { color:rgba(255,255,255,0.5); font-size:0.72rem; margin:0; }

.sb-body { padding: 0.25rem 1rem 1rem; }
.sb-sep {
    font-size:0.63rem; font-weight:700; letter-spacing:0.1em;
    text-transform:uppercase; color:#9EADC2;
    margin: 1.1rem 0 0.6rem;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid #EEF2F7;
}
.sb-foot {
    padding: 0.85rem 1.25rem;
    border-top: 1px solid #EEF2F7;
    font-size: 0.7rem;
    color: #B0BCCF;
    text-align: center;
}

/* ── Inputs ── */
label { font-size:0.78rem !important; font-weight:500 !important; color:#4A5568 !important; }

/* ── Page header banner ── */
.pg-header {
    background: linear-gradient(135deg, #0C1F3D 0%, #1A3460 50%, #2357C8 100%);
    border-radius: 14px;
    padding: 1.75rem 2.2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1.4rem;
    box-shadow: 0 6px 24px rgba(12,31,61,0.22);
}
.pg-header-text h1 {
    color: #fff;
    font-size: 1.45rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.025em;
}
.pg-header-text p {
    color: rgba(255,255,255,0.55);
    font-size: 0.8rem;
    margin: 0.25rem 0 0;
}

/* ── Section label ── */
.sec-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #7A8FA6;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #2357C8;
    margin-bottom: 1rem;
}

/* ── Content card ── */
.c-card {
    background: #fff;
    border: 1px solid #DDE3ED;
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

/* ── Metric cards ── */
.m-grid4 { display:grid; grid-template-columns:repeat(4,1fr); gap:0.75rem; margin-bottom:0.75rem; }
.m-grid3 { display:grid; grid-template-columns:repeat(3,1fr); gap:0.75rem; }
.m-card {
    background:#F7FAFC;
    border:1px solid #DDE3ED;
    border-radius:10px;
    padding:1rem 1.1rem;
    transition: box-shadow .2s, transform .2s;
}
.m-card:hover { box-shadow:0 4px 14px rgba(35,87,200,.1); transform:translateY(-1px); }
.m-lbl { font-size:.63rem; font-weight:700; color:#94A3B8; text-transform:uppercase; letter-spacing:.08em; margin-bottom:.35rem; }
.m-val { font-size:1.5rem; font-weight:700; color:#1A2840; line-height:1.1; }
.m-unit { font-size:.75rem; font-weight:400; color:#B0BCCF; margin-left:.15rem; }

/* ── Severity badge ── */
.sev-pill {
    display:inline-flex; align-items:center; gap:.4rem;
    padding:.38rem .95rem; border-radius:100px;
    font-weight:600; font-size:.75rem; margin-bottom:.9rem; letter-spacing:.04em;
}
.sev-ok   { background:#EDFAF4; color:#047857; border:1px solid #6EE7B7; }
.sev-warn { background:#FFFBEB; color:#B45309; border:1px solid #FCD34D; }
.sev-crit { background:#FFF0F1; color:#C8003A; border:1px solid #FDA4AF; }

/* ── Flag rows ── */
.flag {
    border-radius:8px; padding:.7rem .95rem;
    margin-bottom:.45rem; display:flex;
    align-items:flex-start; gap:.8rem;
    border-left:3px solid transparent;
}
.flag-ok   { background:#F0FDF4; border-color:#22C55E; }
.flag-info { background:#F0F9FF; border-color:#0EA5E9; }
.flag-warn { background:#FFFBEB; border-color:#F59E0B; }
.flag-crit { background:#FFF0F1; border-color:#F43F5E; }
.f-code {
    font-size:.63rem; font-weight:700; letter-spacing:.07em;
    text-transform:uppercase; white-space:nowrap; min-width:175px;
}
.flag-ok   .f-code { color:#16A34A; }
.flag-info .f-code { color:#0284C7; }
.flag-warn .f-code { color:#D97706; }
.flag-crit .f-code { color:#E11D48; }
.f-msg { font-size:.8rem; color:#374151; line-height:1.45; }

/* ── Recommendation rows ── */
.rec {
    background:#F7FAFC; border:1px solid #DDE3ED;
    border-radius:8px; padding:.7rem .95rem;
    margin-bottom:.4rem; display:flex; gap:.6rem; align-items:flex-start;
}
.rec-n {
    background:#2357C8; color:#fff; border-radius:50%;
    width:19px; height:19px; min-width:19px;
    display:flex; align-items:center; justify-content:center;
    font-size:.62rem; font-weight:700; margin-top:2px;
}
.rec-t { font-size:.8rem; color:#374151; line-height:1.5; }

/* ── Empty state ── */
.empty {
    background:#fff; border:1px solid #DDE3ED; border-radius:14px;
    padding:3.5rem 2rem; text-align:center;
    box-shadow:0 1px 3px rgba(0,0,0,0.04);
}
.empty-ico {
    width:52px; height:52px; background:#EEF4FF; border-radius:50%;
    display:flex; align-items:center; justify-content:center; margin:0 auto .75rem;
}
.empty h3 { font-size:1.1rem; font-weight:600; color:#1A2840; margin:0 0 .35rem; }
.empty p  { font-size:.82rem; color:#94A3B8; margin:0; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg,#1A3460 0%,#2357C8 100%) !important;
    color:#fff !important; border:none !important; border-radius:8px !important;
    font-weight:600 !important; font-size:.85rem !important; height:2.7rem !important;
    box-shadow:0 4px 12px rgba(35,87,200,.3) !important; transition:all .2s !important;
}
.stButton > button:hover { transform:translateY(-1px) !important; box-shadow:0 6px 18px rgba(35,87,200,.4) !important; }
.stDownloadButton > button {
    background:#fff !important; color:#1A3460 !important;
    border:1.5px solid #1A3460 !important; border-radius:8px !important;
    font-weight:600 !important; font-size:.82rem !important; height:2.7rem !important;
    transition:all .2s !important;
}
.stDownloadButton > button:hover { background:#EEF4FF !important; border-color:#2357C8 !important; color:#2357C8 !important; }
hr { border:none; border-top:1px solid #DDE3ED; margin:1.1rem 0; }
</style>
""", unsafe_allow_html=True)


# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<div class="sb-head">'
        f'<img src="{_ICON_URI}" width="34" height="34" alt=""/>'
        f'<h2>ADF Blades</h2>'
        f'<p>Analizador de Rotores UAV</p>'
        f'</div>'
        f'<div class="sb-body">',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sb-sep">Sistema</div>', unsafe_allow_html=True)
    tipo        = st.selectbox("Tipo de multirrotor", _TIPOS_LIST)
    num_rotores = st.number_input("Número de rotores", min_value=4, max_value=8, value=6, step=2)
    peso_kg     = st.number_input("Peso total MTOW (kg)", min_value=0.5, max_value=50.0, value=7.7, step=0.1)
    prioridad   = st.selectbox("Prioridad de análisis", _PRIORIDADES_LIST)

    st.markdown('<div class="sb-sep">Hélice</div>', unsafe_allow_html=True)
    diametro_in  = st.number_input("Diámetro (pulgadas)", min_value=5.0, max_value=30.0, value=17.0, step=0.5)
    rpm          = st.number_input("RPM en hover", min_value=500, max_value=15000, value=3400, step=100)
    altitud_m    = st.number_input("Altitud (m)", min_value=0, max_value=5000, value=0, step=100)
    temperatura_C = st.number_input("Temperatura (°C)", min_value=-20, max_value=50, value=15, step=1)
    nombre_helice = st.text_input("Referencia", value="APC 17x12", max_chars=100,
                                   placeholder="ej. APC 17x12")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    analizar = st.button("Analizar sistema", use_container_width=True)
    st.markdown('<div class="sb-foot">ADF Blades &nbsp;·&nbsp; Motor v0.1</div>', unsafe_allow_html=True)


# ── MAIN ───────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="pg-header">'
    f'<img src="{_ICON_URI}" width="48" height="48" alt=""/>'
    f'<div class="pg-header-text">'
    f'<h1>Analizador de Rotores UAV</h1>'
    f'<p>Motor de an&aacute;lisis aerodin&aacute;mico &mdash; ADF_Blades v0.1</p>'
    f'</div></div>',
    unsafe_allow_html=True,
)

# ── ANÁLISIS ───────────────────────────────────────────────────────────────────
if analizar:
    try:
        if tipo not in _TIPOS_VALIDOS:
            raise ValueError("Tipo de multirrotor no válido.")
        if prioridad not in _PRIORIDADES_VALIDAS:
            raise ValueError("Prioridad no válida.")

        resultado  = calcular_metricas(
            peso_total_kg=peso_kg, num_rotores=num_rotores,
            diametro_in=diametro_in, rpm=rpm,
            altitud_m=altitud_m, temperatura_C=temperatura_C,
        )
        diagnostico = analizar_flags(resultado, prioridad=prioridad)
        config = {
            "Tipo de multirrotor": tipo,
            "Peso total (MTOW)": f"{peso_kg} kg",
            "Número de rotores": num_rotores,
            "Hélice": _sanitizar_texto(nombre_helice),
            "RPM hover": rpm,
            "Altitud operación": f"{altitud_m} m",
            "Temperatura": f"{temperatura_C}°C",
            "Prioridad": prioridad,
        }
        st.session_state["resultado"]   = resultado
        st.session_state["diagnostico"] = diagnostico
        st.session_state["report_bytes"] = generar_informe(
            metricas=resultado, diagnostico=diagnostico, config=config,
        )
    except ValueError as e:
        st.error(f"Parámetro no válido: {e}")
        st.stop()
    except Exception as e:
        logger.error("Error en análisis: %s", e, exc_info=True)
        st.error("Ha ocurrido un error. Revisa los parámetros e inténtalo de nuevo.")
        st.stop()

# ── RESULTADOS ─────────────────────────────────────────────────────────────────
if "resultado" not in st.session_state:
    st.markdown("""
    <div class="empty">
        <div class="empty-ico">
            <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24"
                 fill="none" stroke="#2357C8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
        </div>
        <h3>Listo para analizar</h3>
        <p>Configura los par&aacute;metros en el panel lateral y pulsa <strong>Analizar sistema</strong></p>
    </div>
    """, unsafe_allow_html=True)

else:
    r  = st.session_state["resultado"]
    d  = st.session_state["diagnostico"]
    rb = st.session_state["report_bytes"]

    # — Métricas —
    st.markdown(f"""
    <div class="c-card">
        <div class="sec-label">Métricas calculadas</div>
        <div class="m-grid4">
            <div class="m-card"><div class="m-lbl">Tip Speed</div>
                <div class="m-val">{r['tip_speed_m_s']}<span class="m-unit">m/s</span></div></div>
            <div class="m-card"><div class="m-lbl">Mach Tip</div>
                <div class="m-val">{r['mach_tip']}<span class="m-unit">—</span></div></div>
            <div class="m-card"><div class="m-lbl">Disk Loading</div>
                <div class="m-val">{r['disk_loading_N_m2']}<span class="m-unit">N/m²</span></div></div>
            <div class="m-card"><div class="m-lbl">Coef. Empuje CT</div>
                <div class="m-val">{r['CT_calculado']}<span class="m-unit">—</span></div></div>
        </div>
        <div class="m-grid3">
            <div class="m-card"><div class="m-lbl">Thrust por rotor</div>
                <div class="m-val">{r['thrust_por_rotor_N']}<span class="m-unit">N</span></div></div>
            <div class="m-card"><div class="m-lbl">Potencia ideal hover</div>
                <div class="m-val">{r['potencia_ideal_hover_W']}<span class="m-unit">W</span></div></div>
            <div class="m-card"><div class="m-lbl">Densidad del aire</div>
                <div class="m-val">{r['rho_kg_m3']}<span class="m-unit">kg/m³</span></div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # — Diagnóstico —
    sev       = d["severidad_global"]
    sev_css   = {"critical":"sev-crit","warning":"sev-warn","ok":"sev-ok"}.get(sev,"sev-ok")
    sev_label = {"critical":"CRÍTICO","warning":"ADVERTENCIA","ok":"CORRECTO"}.get(sev, sev.upper())
    fcss      = {"critical":"flag-crit","warning":"flag-warn","info":"flag-info","ok":"flag-ok"}
    flags_html = "".join(
        f'<div class="flag {fcss.get(f["severidad"],"flag-ok")}">'
        f'<div class="f-code">{f["codigo"]}</div>'
        f'<div class="f-msg">{f["mensaje"]}</div></div>'
        for f in d["flags"]
    )
    st.markdown(f"""
    <div class="c-card">
        <div class="sec-label">Diagnóstico</div>
        <span class="sev-pill {sev_css}">● Severidad global: {sev_label}</span>
        {flags_html}
    </div>
    """, unsafe_allow_html=True)

    # — Recomendaciones —
    recs_html = "".join(
        f'<div class="rec"><div class="rec-n">{i}</div><div class="rec-t">{rec}</div></div>'
        for i, rec in enumerate(d["recomendaciones"], 1)
    )
    st.markdown(f"""
    <div class="c-card">
        <div class="sec-label">Recomendaciones</div>
        {recs_html}
    </div>
    """, unsafe_allow_html=True)

    # — Descarga —
    st.download_button(
        label="Descargar informe técnico (Word)",
        data=rb,
        file_name="informe_rotor.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )
