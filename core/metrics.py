import numpy as np

# Constantes físicas
RHO_SEA_LEVEL = 1.225  # kg/m³ densidad aire nivel del mar
G = 9.81               # m/s²

def calcular_densidad_aire(altitud_m: float, temperatura_C: float) -> float:
    """Modelo ISA simplificado"""
    temperatura_K = temperatura_C + 273.15
    presion = 101325 * (1 - 0.0000226 * altitud_m) ** 5.256
    densidad = presion / (287.05 * temperatura_K)
    return densidad

def calcular_metricas(
    peso_total_kg: float,
    num_rotores: int,
    diametro_in: float,
    rpm: float,
    altitud_m: float = 0.0,
    temperatura_C: float = 15.0
) -> dict:
    if not (1 <= num_rotores <= 32):
        raise ValueError(f"num_rotores debe estar entre 1 y 32, recibido: {num_rotores}")
    if not (1 <= rpm <= 50_000):
        raise ValueError(f"rpm debe estar entre 1 y 50 000, recibido: {rpm}")
    if not (0.5 <= diametro_in <= 100):
        raise ValueError(f"diametro_in debe estar entre 0.5 y 100 pulgadas, recibido: {diametro_in}")
    if not (0.01 <= peso_total_kg <= 500):
        raise ValueError(f"peso_total_kg debe estar entre 0.01 y 500 kg, recibido: {peso_total_kg}")
    if not (0 <= altitud_m <= 8_848):
        raise ValueError(f"altitud_m debe estar entre 0 y 8848 m, recibido: {altitud_m}")
    if not (-80 <= temperatura_C <= 80):
        raise ValueError(f"temperatura_C debe estar entre -80 y 80 °C, recibido: {temperatura_C}")

    # Geometría
    diametro_m = diametro_in * 0.0254
    radio_m = diametro_m / 2
    area_disco_m2 = np.pi * radio_m ** 2

    # Condiciones atmosféricas
    rho = calcular_densidad_aire(altitud_m, temperatura_C)

    # Velocidad angular
    omega = rpm * (2 * np.pi / 60)  # rad/s

    # Métricas principales
    tip_speed = omega * radio_m                          # m/s
    velocidad_sonido = np.sqrt(1.4 * 287.05 * (temperatura_C + 273.15))
    mach_tip = tip_speed / velocidad_sonido
    disk_loading = (peso_total_kg * G) / (num_rotores * area_disco_m2)  # N/m²

    # Thrust por rotor necesario para hover
    thrust_por_rotor_N = (peso_total_kg * G) / num_rotores

    # CT desde datos físicos (para comparar con UIUC)
    n_rps = rpm / 60  # revoluciones por segundo
    CT_calculado = thrust_por_rotor_N / (rho * (n_rps ** 2) * (diametro_m ** 4))

    # Potencia ideal hover (actuator disk theory)
    potencia_ideal_W = thrust_por_rotor_N * np.sqrt(
        thrust_por_rotor_N / (2 * rho * area_disco_m2)
    )

    return {
        "diametro_m": round(diametro_m, 4),
        "area_disco_m2": round(area_disco_m2, 4),
        "rho_kg_m3": round(rho, 4),
        "tip_speed_m_s": round(tip_speed, 2),
        "mach_tip": round(mach_tip, 4),
        "disk_loading_N_m2": round(disk_loading, 2),
        "thrust_por_rotor_N": round(thrust_por_rotor_N, 2),
        "CT_calculado": round(CT_calculado, 5),
        "potencia_ideal_hover_W": round(potencia_ideal_W, 2),
    }