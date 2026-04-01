_PRIORIDADES_VALIDAS = {"balanced", "ruido", "eficiencia"}


def analizar_flags(metricas: dict, prioridad: str = "balanced") -> dict:
    """
    Analiza las métricas calculadas y devuelve flags de diagnóstico.
    prioridad: "ruido" | "eficiencia" | "balanced"
    """
    if prioridad not in _PRIORIDADES_VALIDAS:
        raise ValueError(
            f"prioridad debe ser una de {_PRIORIDADES_VALIDAS}, recibido: {prioridad!r}"
        )

    flags = []
    recomendaciones = []

    tip_speed = metricas["tip_speed_m_s"]
    mach_tip = metricas["mach_tip"]
    disk_loading = metricas["disk_loading_N_m2"]
    CT = metricas["CT_calculado"]

    # --- TIP SPEED ---
    if tip_speed > 120:
        flags.append({
            "codigo": "TIP_SPEED_CRITICO",
            "severidad": "critical",
            "valor": tip_speed,
            "mensaje": f"Tip speed {tip_speed} m/s: riesgo compresibilidad y ruido severo"
        })
    elif tip_speed > 90:
        flags.append({
            "codigo": "TIP_SPEED_WARNING",
            "severidad": "warning",
            "valor": tip_speed,
            "mensaje": f"Tip speed {tip_speed} m/s: ruido elevado, considerar reducir RPM o aumentar diámetro"
        })
    elif tip_speed < 50:
        flags.append({
            "codigo": "TIP_SPEED_BAJO",
            "severidad": "info",
            "valor": tip_speed,
            "mensaje": f"Tip speed {tip_speed} m/s: Reynolds bajo, posible pérdida de eficiencia"
        })
    else:
        flags.append({
            "codigo": "TIP_SPEED_OK",
            "severidad": "ok",
            "valor": tip_speed,
            "mensaje": f"Tip speed {tip_speed} m/s: rango óptimo"
        })

    # --- MACH TIP ---
    if mach_tip > 0.60:
        flags.append({
            "codigo": "MACH_CRITICO",
            "severidad": "critical",
            "valor": mach_tip,
            "mensaje": f"Mach tip {mach_tip}: ondas de choque, ruido impulsivo severo"
        })
    elif mach_tip > 0.35:
        flags.append({
            "codigo": "MACH_WARNING",
            "severidad": "warning",
            "valor": mach_tip,
            "mensaje": f"Mach tip {mach_tip}: efectos compresibles significativos"
        })
    elif mach_tip > 0.25:
        flags.append({
            "codigo": "MACH_ATENCION",
            "severidad": "info",
            "valor": mach_tip,
            "mensaje": f"Mach tip {mach_tip}: inicio efectos compresibles, monitorizar"
        })
    else:
        flags.append({
            "codigo": "MACH_OK",
            "severidad": "ok",
            "valor": mach_tip,
            "mensaje": f"Mach tip {mach_tip}: flujo incompresible, correcto"
        })

    # --- DISK LOADING ---
    if disk_loading > 400:
        flags.append({
            "codigo": "DISK_LOADING_CRITICO",
            "severidad": "critical",
            "valor": disk_loading,
            "mensaje": f"Disk loading {disk_loading} N/m²: consumo excesivo, autonomía muy reducida"
        })
    elif disk_loading > 250:
        flags.append({
            "codigo": "DISK_LOADING_WARNING",
            "severidad": "warning",
            "valor": disk_loading,
            "mensaje": f"Disk loading {disk_loading} N/m²: considerar aumentar diámetro de hélice"
        })
    elif disk_loading < 100:
        flags.append({
            "codigo": "DISK_LOADING_OK",
            "severidad": "ok",
            "valor": disk_loading,
            "mensaje": f"Disk loading {disk_loading} N/m²: excelente eficiencia en hover"
        })
    else:
        flags.append({
            "codigo": "DISK_LOADING_ACEPTABLE",
            "severidad": "ok",
            "valor": disk_loading,
            "mensaje": f"Disk loading {disk_loading} N/m²: rango típico inspección, aceptable"
        })

    # --- CT ---
    if CT > 0.15:
        flags.append({
            "codigo": "CT_ALTO",
            "severidad": "warning",
            "valor": CT,
            "mensaje": f"CT {CT}: hélice muy cargada, posible separación en raíz de pala"
        })
    elif CT < 0.03:
        flags.append({
            "codigo": "CT_BAJO",
            "severidad": "info",
            "valor": CT,
            "mensaje": f"CT {CT}: hélice infrautilizada, margen de eficiencia disponible"
        })
    else:
        flags.append({
            "codigo": "CT_OK",
            "severidad": "ok",
            "valor": CT,
            "mensaje": f"CT {CT}: coeficiente de empuje en rango operativo normal"
        })

    # --- RECOMENDACIONES según prioridad ---
    if prioridad == "ruido":
        if tip_speed > 80:
            recomendaciones.append("Reducir RPM un 10-15% aumentando diámetro de hélice")
        if mach_tip > 0.25:
            recomendaciones.append("Considerar hélice con sweep en tip para reducir ruido impulsivo")
        recomendaciones.append("Evaluar hélice de 3 palas: distribuye carga acústica mejor que 2 palas")

    elif prioridad == "eficiencia":
        if disk_loading > 200:
            recomendaciones.append("Aumentar diámetro de hélice para reducir disk loading")
        recomendaciones.append("Hélice de 2 palas optimiza eficiencia en hover")
        recomendaciones.append("Verificar pitch/diameter ratio en rango 0.65-0.80")

    else:  # balanced
        recomendaciones.append("Hélice de 3 palas: mejor compromiso ruido/eficiencia")
        if tip_speed > 85:
            recomendaciones.append("Reducir tip speed a 70-80 m/s para equilibrio óptimo")
        if disk_loading > 200:
            recomendaciones.append("Considerar aumentar diámetro si el airframe lo permite")

    # Severidad global
    severidades = [f["severidad"] for f in flags]
    if "critical" in severidades:
        severidad_global = "critical"
    elif "warning" in severidades:
        severidad_global = "warning"
    else:
        severidad_global = "ok"

    return {
        "severidad_global": severidad_global,
        "flags": flags,
        "recomendaciones": recomendaciones
    }