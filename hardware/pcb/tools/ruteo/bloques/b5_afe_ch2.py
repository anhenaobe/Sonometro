"""Bloque 5, CH2: AFE del RG-50 (U9 TLV9152, U10 MCP4725), con la misma geometría que CH1 desplazada 22.5 mm en y.

Coordenadas KiCad (mm). Todo en F.Cu (redes críticas, política G); In1.Cu es el plano GND.
Colocación aprobada tras el bloque 5:
- colocar_bloque5b.json: R38/R39/R40 en columna en x 141.7 (la de CH1 está en 140.6; aquí el courtyard de J8 llega a
  x 140.90), C57 en el lugar de C56 de CH1 y R43 vertical como R8. Con la colocación anterior el nodo R39-R40 rodeaba
  U10 (SCL y A0 quedaban encerrados) y el grupo C57/R43 obligaba a 3 entradas a 45°.
- colocar_bloque5c.json: TP4, C54, R44, R45 y C55 en el lugar de TP2, C7, R15, R17 y C8 de CH1 (los tres del divisor
  0.2 mm más a la derecha por la columna). Antes, TP4 quedaba encerrado por DC_MON2, C54 y 5V_A, y REST_SV no se
  podía unir en F.Cu. Alineaciones de pads por debajo de 1 µm: C51, C53, R46 (alineacion_bloque5b.json).
Topología:
- Cadena: R38 -> R39 -> R40 en columna; R40.1 -> R41.2 en línea recta. IEPE_SV llega a R38.2 en el bloque 6.
- Nodo SUM (U9A-): R41.1 es el punto de unión (U9.2, R42.1 y C57.1). El enlace C57.1 -> R41.1 tiene el quiebre
  dentro de los pads, como en CH1: excepción aceptada por el dueño tras el bloque 5.
- REST_SV: U9.1 -> R43.1 (arriba); R43.1 -> R44.2 por el hueco entre los pads de R42; R43.1 -> por encima de C54 ->
  TP4 desde arriba; C57.2 -> entre los pads de R37 -> por debajo de R37/C51 -> TP4 desde abajo. REST_SV hacia C14
  sale de TP4 por la derecha en el bloque 6.
- DC_MON2: R44.1 -> C55.1 y R44.1 -> R45.2 (verticales). La cadena R40.1 -> R41.2 pasa centrada entre los pads de R45.
  Hacia la NUCLEO sale de R44.1 por la izquierda en el bloque 7.
- U9B+: U9.5 -> C51.1 -> R37.2 ; U10.VOUT -> R37.1. U9A+: pines 3, 6 y 7 bajo el cuerpo.
- 5V_A: U9.8 -> C54.2 (0.975 mm). Vía a In2.Cu reservada para el bloque 8 en (152.28, 143.4), junto a C54.2.
- 3V3_DAC_SV: U10.3 -> C52.1 -> C53.1 -> R46.1; A0 (U10.6, dirección 0x61) a U10.3 por debajo del cuerpo.
  3V3 (R46.2) llega desde In2.Cu en el bloque 8.
- I2C (bloque 7): salidas reservadas a la derecha de U10: SCL U10.5 -> vía en (148.6, 152.0); SDA U10.4 -> vía en
  (148.0, 152.95).
- Vías GND a >= 0.35 mm de todo pad (JLC tapona las vías en 4 capas) y <= 1.0 mm del pad GND.
"""
F = 'F.Cu'
A = 0.2
P = [
    # cadena de 1 MΩ en columna
    ('Net-(R40-Pad1)', A, F, [(141.7, 145.675), (145.2875, 145.675)]),
    ('Net-(R39-Pad1)', A, F, [(141.7, 147.325), (141.7, 148.925)]),
    ('Net-(R38-Pad1)', A, F, [(141.7, 150.575), (141.7, 152.175)]),
    # nodo SUM (U9A-)
    ('Net-(U9A--)', A, F, [(146.9375, 145.675), (148.69, 145.675)]),
    ('Net-(U9A--)', A, F, [(146.65, 143.75), (146.65, 144.4), (146.9375, 144.6875), (146.9375, 145.675)]),
    ('Net-(U9A--)', A, F, [(145.415, 147.43), (145.415, 147.315), (146.9375, 145.7925), (146.9375, 145.675)]),
    # realimentación R42 + R43
    ('Net-(R42-Pad2)', A, F, [(146.65, 142.1), (147.3, 142.1), (147.9873, 141.4127), (148.5062, 141.4127)]),
    # REST_SV
    ('REST_SV', A, F, [(148.69, 145.025), (148.69, 144.1), (148.5062, 143.9162), (148.5062, 143.0627)]),
    ('REST_SV', A, F, [(148.5062, 143.0627), (148.0, 143.0627), (147.8623, 142.925), (144.9344, 142.925)]),
    ('REST_SV', A, F, [(148.5062, 143.0627), (149.4, 143.0627), (149.82, 142.6427), (149.82, 141.1), (150.23, 140.69),
                       (152.65, 140.69), (153.05, 141.09), (153.05, 142.824), (154.126, 143.9), (154.126, 145.0249)]),
    ('REST_SV', A, F, [(146.965, 147.43), (147.5, 147.43), (147.75, 147.68), (147.75, 149.65), (148.0, 149.9),
                       (152.85, 149.9), (154.126, 148.624), (154.126, 145.0249)]),
    # DC_MON2 (divisor R44/R45 y C55)
    ('DC_MON2', A, F, [(143.2844, 142.925), (143.2844, 140.8876)]),
    ('DC_MON2', A, F, [(143.2844, 142.925), (143.2844, 144.85)]),
    # DAC -> RC -> U9B -> U9A+
    ('Net-(U10-VOUT)', A, F, [(144.3625, 151.05), (144.3625, 150.4), (145.769, 148.9935), (146.925, 148.9935)]),
    ('Net-(U9B-+)', A, F, [(148.575, 148.9935), (150.3313, 148.9935)]),
    ('Net-(U9B-+)', A, F, [(151.31, 146.975), (151.31, 147.4), (150.3313, 148.3787), (150.3313, 148.9935)]),
    ('Net-(U9A-+)', A, F, [(148.69, 146.325), (151.31, 146.325)]),
    ('Net-(U9A-+)', A, F, [(151.31, 145.675), (151.31, 146.325)]),
    # alimentación local
    ('5V_A', 0.3, F, [(151.31, 145.025), (151.31, 144.4), (151.1375, 144.2275), (151.1375, 143.4)]),
    ('/3V3_DAC_SV', 0.3, F, [(144.3625, 152.95), (144.3625, 153.6), (144.25, 153.7125), (144.25, 154.975)]),
    ('/3V3_DAC_SV', 0.3, F, [(144.25, 154.975), (146.0583, 154.975)]),
    ('/3V3_DAC_SV', 0.3, F, [(146.0583, 154.975), (146.0583, 156.9167)]),
    ('/3V3_DAC_SV', 0.25, F, [(146.6375, 151.05), (145.95, 151.05), (145.5, 151.5), (145.5, 152.5), (145.05, 152.95),
                              (144.3625, 152.95)]),                     # A0 = 1 (dirección 0x61), bajo el cuerpo
    # vías GND
    ('GND', 0.3, F, [(148.69, 146.975), (148.69, 147.83)]),             # U9.4
    ('GND', 0.3, F, [(144.3625, 152.0), (143.05, 152.0)]),              # U10.2
    ('GND', 0.4, F, [(151.8812, 148.9935), (151.8812, 147.86)]),        # C51.2
    ('GND', 0.4, F, [(144.25, 156.525), (143.125, 156.525)]),           # C52.2
    ('GND', 0.4, F, [(147.6083, 154.975), (148.71, 154.975)]),          # C53.2
    ('GND', 0.4, F, [(151.1375, 141.85), (152.28, 141.85)]),            # C54.1
    ('GND', 0.4, F, [(143.2844, 146.5), (143.2844, 147.56)]),           # R45.1
    ('GND', 0.4, F, [(144.8344, 140.8876), (145.95, 140.8876)]),        # C55.2
]
PISTAS = [(r, w, l, pts) for r, w, l, pts in P]
V = 0.6, 0.3
VIAS = [('GND', p) + V for p in ((148.69, 147.83), (143.05, 152.0), (151.8812, 147.86), (143.125, 156.525),
                                 (148.71, 154.975), (152.28, 141.85), (143.2844, 147.56), (145.95, 140.8876))]
ZONAS = []
