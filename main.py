from core.metrics import calcular_metricas
from core.rules_engine import analizar_flags
from core.report_generator import generar_informe

# Configuración del dron
config = {
    "Tipo de multirrotor": "Hexacóptero",
    "Peso total (MTOW)": "7.7 kg",
    "Número de rotores": 6,
    "Hélice": "APC 17x12",
    "RPM hover": 3400,
    "Altitud operación": "0 m",
    "Temperatura": "15°C",
    "Prioridad": "Ruido",
}

# Motor físico
resultado = calcular_metricas(
    peso_total_kg=7.7,
    num_rotores=6,
    diametro_in=17.0,
    rpm=3400,
    altitud_m=0.0,
    temperatura_C=15.0
)

# Diagnóstico
diagnostico = analizar_flags(resultado, prioridad="ruido")

# Generar informe Word
generar_informe(
    metricas=resultado,
    diagnostico=diagnostico,
    config=config,
    output_path="informe_rotor.docx"
)