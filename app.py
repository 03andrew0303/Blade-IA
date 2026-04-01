import streamlit as st
import tempfile
import os
from core.metrics import calcular_metricas
from core.rules_engine import analizar_flags
from core.report_generator import generar_informe

st.set_page_config(
    page_title="Analizador de Rotores UAV",
    page_icon="🚁",
    layout="wide"
)

st.title("🚁 Analizador de Rotores UAV")
st.markdown("Introduce los parámetros del dron para generar el análisis técnico.")

# --- FORMULARIO ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Configuración del dron")
    tipo = st.selectbox("Tipo de multirrotor", ["Quadcóptero", "Hexacóptero", "Octocóptero"])
    num_rotores = st.number_input("Número de rotores", min_value=4, max_value=8, value=6, step=2)
    peso_kg = st.number_input("Peso total MTOW (kg)", min_value=0.5, max_value=50.0, value=7.7, step=0.1)
    prioridad = st.selectbox("Prioridad", ["balanced", "ruido", "eficiencia"])

with col2:
    st.subheader("Configuración de la hélice")
    diametro_in = st.number_input("Diámetro de hélice (pulgadas)", min_value=5.0, max_value=30.0, value=17.0, step=0.5)
    rpm = st.number_input("RPM en hover", min_value=500, max_value=15000, value=3400, step=100)
    altitud_m = st.number_input("Altitud de operación (m)", min_value=0, max_value=5000, value=0, step=100)
    temperatura_C = st.number_input("Temperatura (°C)", min_value=-20, max_value=50, value=15, step=1)

nombre_helice = st.text_input("Descripción de la hélice (ej. APC 17x12)", value="APC 17x12")

# --- ANÁLISIS ---
if st.button("🔍 Analizar", use_container_width=True):
    try:
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
            "Hélice": nombre_helice,
            "RPM hover": rpm,
            "Altitud operación": f"{altitud_m} m",
            "Temperatura": f"{temperatura_C}°C",
            "Prioridad": prioridad,
        }

        # Generate report to a unique temp file to avoid concurrent user collisions
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp_path = tmp.name

        generar_informe(
            metricas=resultado,
            diagnostico=diagnostico,
            config=config,
            output_path=tmp_path
        )

        with open(tmp_path, "rb") as f:
            report_bytes = f.read()

        os.unlink(tmp_path)

        # Persist results in session state so the download button survives reruns
        st.session_state["resultado"] = resultado
        st.session_state["diagnostico"] = diagnostico
        st.session_state["report_bytes"] = report_bytes

    except Exception as e:
        st.error(f"Error durante el análisis: {e}")
        st.stop()

# --- RESULTADOS (rendered from session state so they survive download button click) ---
if "resultado" in st.session_state:
    resultado = st.session_state["resultado"]
    diagnostico = st.session_state["diagnostico"]
    report_bytes = st.session_state["report_bytes"]

    st.divider()
    st.subheader("📊 Métricas calculadas")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tip Speed", f"{resultado['tip_speed_m_s']} m/s")
    m2.metric("Mach Tip", f"{resultado['mach_tip']}")
    m3.metric("Disk Loading", f"{resultado['disk_loading_N_m2']} N/m²")
    m4.metric("CT", f"{resultado['CT_calculado']}")

    m5, m6, m7 = st.columns(3)
    m5.metric("Thrust por rotor", f"{resultado['thrust_por_rotor_N']} N")
    m6.metric("Potencia ideal hover", f"{resultado['potencia_ideal_hover_W']} W")
    m7.metric("Densidad aire", f"{resultado['rho_kg_m3']} kg/m³")

    # --- DIAGNÓSTICO ---
    st.divider()
    st.subheader("🔎 Diagnóstico")

    sev = diagnostico["severidad_global"]
    if sev == "critical":
        st.error("Severidad global: CRÍTICO")
    elif sev == "warning":
        st.warning("Severidad global: ADVERTENCIA")
    else:
        st.success("Severidad global: OK")

    for flag in diagnostico["flags"]:
        if flag["severidad"] == "critical":
            st.error(f"**{flag['codigo']}** — {flag['mensaje']}")
        elif flag["severidad"] == "warning":
            st.warning(f"**{flag['codigo']}** — {flag['mensaje']}")
        elif flag["severidad"] == "info":
            st.info(f"**{flag['codigo']}** — {flag['mensaje']}")
        else:
            st.success(f"**{flag['codigo']}** — {flag['mensaje']}")

    # --- RECOMENDACIONES ---
    st.divider()
    st.subheader("💡 Recomendaciones")
    for i, rec in enumerate(diagnostico["recomendaciones"], 1):
        st.markdown(f"**{i}.** {rec}")

    # --- DESCARGAR INFORME ---
    st.divider()
    st.download_button(
        label="📄 Descargar informe Word",
        data=report_bytes,
        file_name="informe_rotor.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True
    )
