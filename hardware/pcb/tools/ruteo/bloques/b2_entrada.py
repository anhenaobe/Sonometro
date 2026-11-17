"""Bloque 2: entrada J5 -> D1 (SS34, polaridad) -> D2 (TVS SMBJ26A) y distribución de 24V_PROT a los bucks y a J1/J7.

Coordenadas KiCad (mm). Decisiones (aprobadas tras el bloque 1):
- Bus de 24 V como franja de zona 24V_PROT en F.Cu (y = 116.9–117.75) con dientes de pista que entran recto al centro
  de cada CIN (C27, C28, C37, C38). El bus llega a los integrados solo a través de CIN -> CHF -> pin VIN (bloque 1).
  Pasa por encima de los tres puentes de B.Cu aprobados (x = 132.7, 139.8 y 154.3).
- Ramificación en pads, no en pista libre: D2.1 reparte hacia el bus (derecha) y hacia J1 (izquierda); J1.1 sigue a J7.1.
- J1.1 -> J7.1 va por la izquierda de J1.2 (junto al borde, a >= 1.35 mm), para dejar libre el lado derecho de J1.2 y
  J7.2 a IEPE_FEED / IEPE_FEED_SV (bloque 3) sin cruces.
- Camino del TVS (J5.1 -> D1 -> D2 -> GND) corto y a 1.0 mm; D2.2 con tres vías GND al plano de B.Cu (retorno a J5.2,
  que es THT y conecta al plano por alivio térmico).
"""
PISTAS = [
    # 24V_IN (en la placa la red se llama Net-(D1-A)): J5.1 -> D1.2 (ánodo), recto
    ('Net-(D1-A)', 1.0, 'F.Cu', [(104.5, 103.6), (111.25, 103.6)]),
    # 24V_PROT: D1.1 (cátodo) -> D2.1
    ('24V_PROT', 1.0, 'F.Cu', [(111.25, 107.6), (111.25, 108.95), (111.75, 109.45), (111.75, 110.95)]),
    # D2.1 -> C27.1 (el bus de los bucks entra por CIN)
    ('24V_PROT', 0.5, 'F.Cu', [(111.75, 110.95), (113.25, 110.95), (114.25, 111.95), (121.8, 111.95)]),
    # dientes del bus: centro de cada CIN -> dentro de la franja
    ('24V_PROT', 0.5, 'F.Cu', [(121.8, 111.95), (121.8, 117.3)]),
    ('24V_PROT', 0.5, 'F.Cu', [(136.2, 111.95), (136.2, 117.3)]),
    ('24V_PROT', 0.5, 'F.Cu', [(143.4, 111.95), (143.4, 117.3)]),
    ('24V_PROT', 0.5, 'F.Cu', [(157.8, 111.95), (157.8, 117.3)]),
    # D2.1 -> J1.1 (habilitación IEPE CH1) y J1.1 -> J7.1 (CH2) por la izquierda de J1.2
    ('24V_PROT', 0.5, 'F.Cu', [(111.75, 110.95), (107.8, 110.95), (104.5, 114.25), (104.5, 116.2)]),
    ('24V_PROT', 0.5, 'F.Cu', [(104.5, 116.2), (102.6, 116.2), (102.1, 116.7), (102.1, 124.3), (104.5, 126.7),
                               (104.5, 128.2)]),
    # GND del TVS: tres vías junto a D2.2. Las laterales bajan 0.55 mm con un quiebre a 45° (bloque 10): el contorno
    # de serigrafía de D2 (D_SMB) terminaba justo sobre ellas.
    ('GND', 0.5, 'F.Cu', [(111.75, 115.25), (110.45, 115.25), (109.9, 115.8)]),
    ('GND', 0.5, 'F.Cu', [(111.75, 115.25), (113.05, 115.25), (113.6, 115.8)]),
    ('GND', 0.5, 'F.Cu', [(111.75, 115.25), (111.75, 117.3)]),
]
VIAS = [('GND', (109.9, 115.8), 0.6, 0.3), ('GND', (113.6, 115.8), 0.6, 0.3), ('GND', (111.75, 117.3), 0.6, 0.3)]
ZONAS = [dict(nombre='BUS_24V', red='24V_PROT', capa='F.Cu', prioridad=1,
              puntos=[(121.3, 116.9), (158.3, 116.9), (158.3, 117.75), (121.3, 117.75)])]
