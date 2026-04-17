import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import json
import base64
import logging
from http.server import BaseHTTPRequestHandler

from core.metrics import calcular_metricas
from core.rules_engine import analizar_flags
from core.report_generator import generar_informe

logging.basicConfig(level=logging.ERROR)
_log = logging.getLogger(__name__)

_TIPOS      = {"Quadcóptero", "Hexacóptero", "Octocóptero"}
_PRIORIDADES = {"balanced", "ruido", "eficiencia"}


def _san(t: object, n: int = 100) -> str:
    t = str(t).strip()
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', t)[:n]


def _send(h, status: int, body: dict) -> None:
    data = json.dumps(body, ensure_ascii=False).encode()
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(data)))
    h.send_header("Access-Control-Allow-Origin", "*")
    h.end_headers()
    h.wfile.write(data)


class handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass  # suppress access logs

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data   = json.loads(self.rfile.read(length))

            tipo      = _san(data.get("tipo", ""))
            prioridad = _san(data.get("prioridad", "balanced"))

            if tipo not in _TIPOS:
                return _send(self, 400, {"error": f"Tipo no válido: {tipo}"})
            if prioridad not in _PRIORIDADES:
                return _send(self, 400, {"error": f"Prioridad no válida: {prioridad}"})

            resultado = calcular_metricas(
                peso_total_kg = float(data["peso_kg"]),
                num_rotores   = int(data["num_rotores"]),
                diametro_in   = float(data["diametro_in"]),
                rpm           = float(data["rpm"]),
                altitud_m     = float(data.get("altitud_m", 0)),
                temperatura_C = float(data.get("temperatura_C", 15)),
            )
            diagnostico = analizar_flags(resultado, prioridad=prioridad)
            nombre      = _san(data.get("nombre_helice", "APC 17x12"))

            config = {
                "Tipo de multirrotor": tipo,
                "Peso total (MTOW)":   f"{data['peso_kg']} kg",
                "Número de rotores":   data["num_rotores"],
                "Hélice":              nombre,
                "RPM hover":           data["rpm"],
                "Altitud operación":   f"{data.get('altitud_m', 0)} m",
                "Temperatura":         f"{data.get('temperatura_C', 15)}°C",
                "Prioridad":           prioridad,
            }

            rb = generar_informe(metricas=resultado, diagnostico=diagnostico, config=config)

            _send(self, 200, {
                "metricas":   resultado,
                "diagnostico": diagnostico,
                "report_b64": base64.b64encode(rb).decode(),
            })

        except ValueError as e:
            _send(self, 400, {"error": str(e)})
        except Exception as e:
            _log.error("Error: %s", e, exc_info=True)
            _send(self, 500, {"error": "Error interno del servidor"})
