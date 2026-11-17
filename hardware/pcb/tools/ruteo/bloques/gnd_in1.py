"""Plano GND en In1.Cu, entero, en toda la placa (decisión del dueño: 4 capas, In1 = GND entero).

Es la referencia de todas las señales de F.Cu: la regla I de revisar_pistas.py mide la continuidad bajo cada pista
crítica contra este plano. Conexión sólida en vías y pads; alivio térmico solo en pads THT (soldados a mano).
"""
X0, Y0, X1, Y1 = 100.0, 100.0, 190.0, 164.0          # contorno de la placa (Edge.Cuts), mm KiCad
PISTAS = []
VIAS = []
ZONAS = [dict(nombre='GND_IN1', red='GND', capa='In1.Cu', prioridad=0, conexion='alivio_tht',
              puntos=[(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)])]
