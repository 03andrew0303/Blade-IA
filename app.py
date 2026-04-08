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
_TIPOS_VALIDOS = {"Quadcóptero", "Hexacóptero", "Octocóptero"}


def _sanitizar_texto(texto: str, max_len: int = 100) -> str:
    texto = texto.strip()
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)
    return texto[:max_len]


# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ADF Blades — Analizador de Rotores UAV",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CUSTOM CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
.main .block-container {
    padding-top: 0;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* Ocultar chrome de Streamlit */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Header ── */
.adf-header {
    background: linear-gradient(135deg, #0F2444 0%, #1E3A5F 55%, #2563EB 100%);
    border-radius: 16px;
    padding: 2.5rem 3rem;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    gap: 1.75rem;
    box-shadow: 0 8px 32px rgba(15,36,68,0.25);
}
.adf-header-text h1 {
    color: white;
    font-size: 1.9rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.025em;
    line-height: 1.2;
}
.adf-header-text p {
    color: rgba(255,255,255,0.65);
    font-size: 0.9rem;
    margin: 0.4rem 0 0 0;
}

/* ── Section title ── */
.section-title {
    font-size: 1rem;
    font-weight: 600;
    color: #1E293B;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #2563EB;
    margin-bottom: 1.25rem;
    letter-spacing: -0.01em;
}

/* ── Metric cards ── */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1rem;
}
.metrics-grid-3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.metric-card {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    transition: box-shadow 0.2s;
}
.metric-card:hover { box-shadow: 0 4px 14px rgba(37,99,235,0.1); }
.metric-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.45rem;
}
.metric-value {
    font-size: 1.7rem;
    font-weight: 700;
    color: #1E293B;
    line-height: 1.1;
}
.metric-unit {
    font-size: 0.85rem;
    font-weight: 400;
    color: #94A3B8;
    margin-left: 0.2rem;
}

/* ── Severity badge ── */
.sev-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.45rem 1.1rem;
    border-radius: 100px;
    font-weight: 600;
    font-size: 0.82rem;
    margin-bottom: 1.1rem;
    letter-spacing: 0.03em;
}
.sev-ok   { background: #ECFDF5; color: #059669; border: 1px solid #6EE7B7; }
.sev-warn { background: #FFFBEB; color: #D97706; border: 1px solid #FCD34D; }
.sev-crit { background: #FFF1F2; color: #E11D48; border: 1px solid #FDA4AF; }

/* ── Flag cards ── */
.flag-card {
    border-radius: 10px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.55rem;
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    border-left: 4px solid transparent;
}
.flag-ok   { background: #F0FDF4; border-color: #22C55E; }
.flag-info { background: #F0F9FF; border-color: #0EA5E9; }
.flag-warn { background: #FFFBEB; border-color: #F59E0B; }
.flag-crit { background: #FFF1F2; border-color: #F43F5E; }
.flag-code {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    white-space: nowrap;
    min-width: 190px;
}
.flag-ok   .flag-code { color: #16A34A; }
.flag-info .flag-code { color: #0284C7; }
.flag-warn .flag-code { color: #D97706; }
.flag-crit .flag-code { color: #E11D48; }
.flag-msg {
    font-size: 0.875rem;
    color: #374151;
    line-height: 1.45;
}

/* ── Recommendation cards ── */
.rec-card {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.5rem;
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
}
.rec-num {
    background: #2563EB;
    color: white;
    border-radius: 50%;
    width: 22px;
    height: 22px;
    min-width: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    font-weight: 700;
    margin-top: 1px;
}
.rec-text {
    font-size: 0.875rem;
    color: #374151;
    line-height: 1.5;
}

/* ── Analyze button ── */
.stButton > button {
    background: linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.02em !important;
    height: 3rem !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.3) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(37,99,235,0.4) !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: white !important;
    color: #1E3A5F !important;
    border: 2px solid #1E3A5F !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    height: 3rem !important;
    transition: all 0.2s ease !important;
}
.stDownloadButton > button:hover {
    background: #EFF6FF !important;
    border-color: #2563EB !important;
    color: #2563EB !important;
}

/* ── Inputs ── */
label { font-size: 0.83rem !important; font-weight: 500 !important; color: #374151 !important; }
hr { border: none; border-top: 1px solid #E2E8F0; margin: 1.75rem 0; }
</style>
""", unsafe_allow_html=True)

# ── DRONE SVG ICON (base64 para evitar que el parser de markdown lo escape) ────
_DRONE_SVG_RAW = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">'
    '<circle cx="40" cy="40" r="9" fill="rgba(255,255,255,0.95)"/>'
    '<circle cx="40" cy="40" r="4.5" fill="#60A5FA"/>'
    '<line x1="40" y1="40" x2="16" y2="16" stroke="rgba(255,255,255,0.7)" stroke-width="3" stroke-linecap="round"/>'
    '<line x1="40" y1="40" x2="64" y2="16" stroke="rgba(255,255,255,0.7)" stroke-width="3" stroke-linecap="round"/>'
    '<line x1="40" y1="40" x2="16" y2="64" stroke="rgba(255,255,255,0.7)" stroke-width="3" stroke-linecap="round"/>'
    '<line x1="40" y1="40" x2="64" y2="64" stroke="rgba(255,255,255,0.7)" stroke-width="3" stroke-linecap="round"/>'
    '<ellipse cx="16" cy="16" rx="13" ry="4" fill="rgba(255,255,255,0.85)" transform="rotate(-45 16 16)"/>'
    '<ellipse cx="64" cy="16" rx="13" ry="4" fill="rgba(255,255,255,0.85)" transform="rotate(45 64 16)"/>'
    '<ellipse cx="16" cy="64" rx="13" ry="4" fill="rgba(255,255,255,0.85)" transform="rotate(45 16 64)"/>'
    '<ellipse cx="64" cy="64" rx="13" ry="4" fill="rgba(255,255,255,0.85)" transform="rotate(-45 64 64)"/>'
    '</svg>'
)
_DRONE_IMG = (
    '<img src="data:image/svg+xml;base64,'
    + base64.b64encode(_DRONE_SVG_RAW.encode()).decode()
    + '" width="58" height="58" alt="drone icon"/>'
)

# ── HEADER ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="adf-header">'
    f'{_DRONE_IMG}'
    f'<div class="adf-header-text">'
    f'<h1>ADF Blades &mdash; Analizador de Rotores UAV</h1>'
    f'<p>Introduce los par&aacute;metros del sistema para generar el an&aacute;lisis t&eacute;cnico de rendimiento</p>'
    f'</div></div>',
    unsafe_allow_html=True,
)

# ── FORM ───────────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown('<div class="section-title">Configuración del dron</div>', unsafe_allow_html=True)
    tipo = st.selectbox("Tipo de multirrotor", list(_TIPOS_VALIDOS))
    num_rotores = st.number_input("Número de rotores", min_value=4, max_value=8, value=6, step=2)
    peso_kg = st.number_input("Peso total MTOW (kg)", min_value=0.5, max_value=50.0, value=7.7, step=0.1)
    prioridad = st.selectbox("Prioridad de análisis", list(_PRIORIDADES_VALIDAS))

with col2:
    st.markdown('<div class="section-title">Configuración de la hélice</div>', unsafe_allow_html=True)
    diametro_in = st.number_input("Diámetro (pulgadas)", min_value=5.0, max_value=30.0, value=17.0, step=0.5)
    rpm = st.number_input("RPM en hover", min_value=500, max_value=15000, value=3400, step=100)
    altitud_m = st.number_input("Altitud de operación (m)", min_value=0, max_value=5000, value=0, step=100)
    temperatura_C = st.number_input("Temperatura ambiente (°C)", min_value=-20, max_value=50, value=15, step=1)

nombre_helice = st.text_input(
    "Referencia de hélice",
    value="APC 17x12",
    max_chars=100,
    placeholder="ej. APC 17x12, T-Motor 18x6.1 ...",
)

st.markdown("<br>", unsafe_allow_html=True)

# ── ANÁLISIS ───────────────────────────────────────────────────────────────────
if st.button("Analizar sistema", use_container_width=True):
    try:
        if tipo not in _TIPOS_VALIDOS:
            raise ValueError("Tipo de multirrotor no válido.")
        if prioridad not in _PRIORIDADES_VALIDAS:
            raise ValueError("Prioridad no válida.")

        nombre_helice_limpio = _sanitizar_texto(nombre_helice)

        resultado = calcular_metricas(
            peso_total_kg=peso_kg,
            num_rotores=num_rotores,
            diametro_in=diametro_in,
            rpm=rpm,
            altitud_m=altitud_m,
            temperatura_C=temperatura_C
        )

        diagnostico = analizar_flags(resultado, prioridad=prioridad)

        config = {
            "Tipo de multirrotor": tipo,
            "Peso total (MTOW)": f"{peso_kg} kg",
            "Número de rotores": num_rotores,
            "Hélice": nombre_helice_limpio,
            "RPM hover": rpm,
            "Altitud operación": f"{altitud_m} m",
            "Temperatura": f"{temperatura_C}°C",
            "Prioridad": prioridad,
        }

        report_bytes = generar_informe(
            metricas=resultado,
            diagnostico=diagnostico,
            config=config,
        )

        st.session_state["resultado"] = resultado
        st.session_state["diagnostico"] = diagnostico
        st.session_state["report_bytes"] = report_bytes

    except ValueError as e:
        st.error(f"Parámetro no válido: {e}")
        st.stop()
    except Exception as e:
        logger.error("Error en análisis: %s", e, exc_info=True)
        st.error("Ha ocurrido un error durante el análisis. Revisa los parámetros e inténtalo de nuevo.")
        st.stop()

# ── RESULTADOS ─────────────────────────────────────────────────────────────────
if "resultado" in st.session_state:
    resultado = st.session_state["resultado"]
    diagnostico = st.session_state["diagnostico"]
    report_bytes = st.session_state["report_bytes"]

    st.markdown("<hr>", unsafe_allow_html=True)

    # Métricas
    st.markdown('<div class="section-title">Métricas calculadas</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-label">Tip Speed</div>
            <div class="metric-value">{resultado['tip_speed_m_s']}<span class="metric-unit">m/s</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Mach Tip</div>
            <div class="metric-value">{resultado['mach_tip']}<span class="metric-unit">—</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Disk Loading</div>
            <div class="metric-value">{resultado['disk_loading_N_m2']}<span class="metric-unit">N/m²</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Coef. Empuje CT</div>
            <div class="metric-value">{resultado['CT_calculado']}<span class="metric-unit">—</span></div>
        </div>
    </div>
    <div class="metrics-grid-3">
        <div class="metric-card">
            <div class="metric-label">Thrust por rotor</div>
            <div class="metric-value">{resultado['thrust_por_rotor_N']}<span class="metric-unit">N</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Potencia ideal hover</div>
            <div class="metric-value">{resultado['potencia_ideal_hover_W']}<span class="metric-unit">W</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Densidad del aire</div>
            <div class="metric-value">{resultado['rho_kg_m3']}<span class="metric-unit">kg/m³</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Diagnóstico
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Diagnóstico</div>', unsafe_allow_html=True)

    sev = diagnostico["severidad_global"]
    sev_css   = {"critical": "sev-crit", "warning": "sev-warn", "ok": "sev-ok"}.get(sev, "sev-ok")
    sev_label = {"critical": "CRÍTICO",  "warning": "ADVERTENCIA", "ok": "CORRECTO"}.get(sev, sev.upper())
    st.markdown(
        f'<span class="sev-badge {sev_css}">● Severidad global: {sev_label}</span>',
        unsafe_allow_html=True,
    )

    flag_css = {"critical": "flag-crit", "warning": "flag-warn", "info": "flag-info", "ok": "flag-ok"}
    flags_html = "".join(
        f'<div class="flag-card {flag_css.get(f["severidad"], "flag-ok")}">'
        f'<div class="flag-code">{f["codigo"]}</div>'
        f'<div class="flag-msg">{f["mensaje"]}</div>'
        f'</div>'
        for f in diagnostico["flags"]
    )
    st.markdown(flags_html, unsafe_allow_html=True)

    # Recomendaciones
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Recomendaciones</div>', unsafe_allow_html=True)

    recs_html = "".join(
        f'<div class="rec-card">'
        f'<div class="rec-num">{i}</div>'
        f'<div class="rec-text">{rec}</div>'
        f'</div>'
        for i, rec in enumerate(diagnostico["recomendaciones"], 1)
    )
    st.markdown(recs_html, unsafe_allow_html=True)

    # Descarga
    st.markdown("<hr>", unsafe_allow_html=True)
    st.download_button(
        label="Descargar informe técnico (Word)",
        data=report_bytes,
        file_name="informe_rotor.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )
