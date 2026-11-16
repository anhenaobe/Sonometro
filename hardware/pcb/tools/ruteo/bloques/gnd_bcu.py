"""Plano GND de B.Cu en toda la placa (pedido del dueño tras el bloque 1: existe desde ahora y se rellena en cada
verificación, para que el DRC de la placa real quede en 0 en cada parada). El relleno GND de F.Cu y el cosido van al
final (bloque 9).
- Prioridad 0: cualquier otra zona de B.Cu tiene precedencia; los puentes aprobados en B.Cu lo cortan localmente.
- Conexión: sólida en pads SMD y vías; alivio térmico solo en pads THT (conectores y la NUCLEO, soldados a mano).
- El borde lo respeta la regla 'borde' (0.5 mm) del .kicad_dru.
"""
X0, Y0, X1, Y1 = 100.0, 100.0, 190.0, 164.0          # contorno de la placa (Edge.Cuts), mm KiCad
PISTAS = []
VIAS = []
ZONAS = [dict(nombre='GND_BCU', red='GND', capa='B.Cu', prioridad=0, conexion='alivio_tht',
              puntos=[(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)])]
