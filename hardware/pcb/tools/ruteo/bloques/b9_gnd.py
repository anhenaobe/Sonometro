"""Bloque 9: relleno GND de F.Cu y vías de cosido (In1.Cu ya es el plano GND entero; B.Cu tiene su zona GND).

- Relleno GND en F.Cu sobre toda la placa, con prioridad 0: cede ante las zonas de 5V, 3V3, 24 V y SW del bloque 1.
  - Conexión sólida a los pads SMD, entre ellos CIN, COUT y los pines PGND de los bucks (pedido del dueño tras el
    bloque 1).
  - Alivio térmico solo en los pads THT, que se sueldan a mano.
  - Islas eliminadas; ancho mínimo 0.25 mm.
- Vías de cosido GND generadas por tools/ruteo/cosido.py (cosido.json):
  - anillo perimetral cada 5 mm;
  - grilla de 2.5 mm en el AFE y el ADC, y de 5 mm en el resto;
  - cada una a >= 0.35 mm de todo pad y con separación de clase a todas las capas.
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
PISTAS = []
VIAS = [('GND', tuple(p), 0.6, 0.3) for p in json.load(open(os.path.join(_HERE, '..', 'cosido.json')))]
ZONAS = [dict(red='GND', capa='F.Cu', prioridad=0, nombre='GND_FCU', conexion='alivio_tht', separacion=0.2,
              ancho_min=0.25, puntos=[(100.0, 100.0), (190.0, 100.0), (190.0, 164.0), (100.0, 164.0)])]
