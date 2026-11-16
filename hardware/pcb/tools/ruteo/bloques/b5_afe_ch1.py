"""Bloque 5, CH1: AFE del SV 12 (U3 TLV9152, U2 MCP4725), cadena de 1 MΩ, nodo SUM, realimentación, DC_MON.

Coordenadas KiCad (mm). Todo en F.Cu (redes críticas, política G); In1.Cu es el plano GND.
Micro-ajustes (autorizados, <= 0.1 mm, alineacion_bloque5.json):
- C56 +0.08 mm en y: el tramo SUM C56.1 -> R18.1 sale y entra por el eje de los dos pads.
- C7: +0.1 mm (autorizado) y luego 0.35 mm en total respecto del original (aprobado tras el bloque 5,
  colocar_bloque5b.json): queda a 0.975 mm de U3.8 y abre el paso de REST_OUT por encima de C7.
- C4, C6 y R9: alineación de pads por debajo de 1 µm.
Topología:
- Cadena IEPE: R13 -> R14 -> R16 en columna; R16.1 -> R18.2 pasa entre los pads de R17 (DC_MON y GND), centrada.
- Nodo SUM (U3A-): R18.1 es el punto de unión; llegan U3.2 (derecha), R7.1 (arriba) y C56.1 (abajo). Mínimo.
  El enlace C56.1 -> R18.1 tiene el quiebre dentro de los pads: excepción aceptada por el dueño tras el bloque 5.
- REST_OUT: U3.1 -> R8.1 (arriba); R8.1 -> R15.2 por el hueco entre los pads de R7 (centrada, 0.325 mm a cada lado);
  R8.1 -> por encima de C7 -> TP2 desde arriba (no cabe entre U3.8 y C7 sin cortar el desacoplo de U3.8);
  C56.2 -> entre los pads de R12 -> por debajo de R12/C4 -> TP2. Entre U3 y C56/R18 no hay lugar para la
  realimentación (0.74 mm entre R18.1 y los pads de U3). REST_OUT hacia C9 sale de TP2 en el bloque 6.
- U3B+: U3.5 -> C4.1 -> R12.2 ; U2.VOUT -> R12.1. U3A+: pines 3, 6 y 7 bajo el cuerpo.
- 5V_A: U3.8 -> C7.2 (directo en F.Cu). Vía a In2.Cu reservada para el bloque 8 en (152.28, 120.9), junto a C7.2.
- 3V3_DAC: U2.3 -> C5.1 -> C6.1 -> R9.1. 3V3 (R9.2, R10.2, R11.2) llega desde In2.Cu en el bloque 8.
- I2C (bloque 7): salidas reservadas a la derecha de U2: SCL U2.5 -> vía en (148.6, 129.5); SDA U2.4 -> vía en
  (148.0, 130.45). DC_MON sale de R15.1 por la izquierda (bloque 7).
- Vías GND a >= 0.35 mm de todo pad (JLC tapona las vías en 4 capas) y <= 1.0 mm del pad GND.
"""
F = 'F.Cu'
A = 0.2          # Analogica (ancho de la clase)
P = [
    # cadena de 1 MΩ
    ('Net-(R13-Pad1)', A, F, [(140.6, 129.825), (140.6, 128.225)]),
    ('Net-(R14-Pad1)', A, F, [(140.6, 126.575), (140.6, 124.981)]),
    ('Net-(R16-Pad1)', A, F, [(140.6, 123.331), (144.0, 123.331), (144.156, 123.175), (145.2875, 123.175)]),
    # nodo SUM (U3A-)
    ('Net-(U3A--)', A, F, [(146.9375, 123.175), (148.69, 123.175)]),
    ('Net-(U3A--)', A, F, [(146.65, 121.25), (146.65, 121.9), (146.9375, 122.1875), (146.9375, 123.175)]),
    ('Net-(U3A--)', A, F, [(145.415, 124.93), (145.415, 124.815), (146.9375, 123.2925), (146.9375, 123.175)]),
    # realimentación R7 + R8
    ('Net-(R7-Pad2)', A, F, [(146.65, 119.6), (147.3, 119.6), (147.9685, 118.9315), (148.5062, 118.9315)]),
    # REST_OUT
    ('REST_OUT', A, F, [(148.69, 122.525), (148.69, 121.6), (148.5062, 121.4162), (148.5062, 120.5815)]),
    ('REST_OUT', A, F, [(148.5062, 120.5815), (148.0, 120.5815), (147.8435, 120.425), (145.4562, 120.425),
                        (145.3, 120.5812), (144.7344, 120.5812)]),
    ('REST_OUT', A, F, [(148.5062, 120.5815), (149.4, 120.5815), (149.82, 120.1615), (149.82, 118.6), (150.23, 118.19),
                        (152.65, 118.19), (153.05, 118.59), (153.05, 120.324), (154.126, 121.4), (154.126, 122.5249)]),
    ('REST_OUT', A, F, [(146.965, 124.93), (147.5, 124.93), (147.75, 125.18), (147.75, 127.15), (148.0, 127.4),
                        (152.85, 127.4), (154.126, 126.124), (154.126, 122.5249)]),
    # DC_MON (divisor R15/R17 y C8)
    ('DC_MON', A, F, [(143.0844, 120.5812), (143.0844, 118.5438)]),
    ('DC_MON', A, F, [(143.0844, 120.5812), (143.0844, 122.5062)]),
    # DAC -> filtro RC -> buffer U3B -> U3A+
    ('Net-(U2-VOUT)', A, F, [(144.3625, 128.55), (144.3625, 127.9), (145.769, 126.4935), (146.925, 126.4935)]),
    ('Net-(U3B-+)', A, F, [(148.575, 126.4935), (150.3313, 126.4935)]),
    ('Net-(U3B-+)', A, F, [(151.31, 124.475), (151.31, 124.9), (150.3313, 125.8787), (150.3313, 126.4935)]),
    ('Net-(U3A-+)', A, F, [(148.69, 123.825), (151.31, 123.825)]),
    ('Net-(U3A-+)', A, F, [(151.31, 123.175), (151.31, 123.825)]),
    # alimentación local
    ('5V_A', 0.3, F, [(151.31, 122.525), (151.31, 121.9), (151.1375, 121.7275), (151.1375, 120.9)]),
    ('/3V3_DAC', 0.3, F, [(144.3625, 130.45), (144.3625, 132.425)]),
    ('/3V3_DAC', 0.3, F, [(144.3625, 132.425), (146.3375, 132.425)]),
    ('/3V3_DAC', 0.3, F, [(146.3375, 132.425), (146.3375, 134.1958)]),
    # vías GND
    ('GND', 0.3, F, [(148.69, 124.475), (148.69, 125.33)]),             # U3.4
    ('GND', 0.3, F, [(144.3625, 129.5), (143.05, 129.5)]),              # U2.2
    ('GND', 0.3, F, [(146.6375, 128.55), (147.95, 128.55)]),            # U2.6 (A0 = 0)
    ('GND', 0.4, F, [(151.8812, 126.4935), (151.8812, 125.36)]),        # C4.2
    ('GND', 0.4, F, [(144.3625, 133.975), (143.23, 133.975)]),          # C5.2
    ('GND', 0.4, F, [(147.8875, 132.425), (147.8875, 131.29)]),         # C6.2
    ('GND', 0.4, F, [(151.1375, 119.35), (152.28, 119.35)]),            # C7.1
    ('GND', 0.4, F, [(144.6344, 118.5438), (145.75, 118.5438)]),        # C8.2
    ('GND', 0.4, F, [(143.0844, 124.1562), (143.0844, 125.22)]),        # R17.1
]
PISTAS = [(r, w, l, pts) for r, w, l, pts in P]
V = 0.6, 0.3
VIAS = [('GND', p) + V for p in ((148.69, 125.33), (143.05, 129.5), (147.95, 128.55), (151.8812, 125.36),
                                 (143.23, 133.975), (147.8875, 131.29), (152.28, 119.35), (145.75, 118.5438),
                                 (143.0844, 125.22))]
ZONAS = []
