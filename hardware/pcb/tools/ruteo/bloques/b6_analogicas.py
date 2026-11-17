"""Bloque 6: rutas analógicas largas (IEPE -> AFE CH1, IEPE_SV -> AFE CH2, REST_OUT -> C9, REST_SV -> C14).

Coordenadas KiCad (mm). Todo en F.Cu (redes críticas, política G) sobre el plano GND entero de In1.Cu.
- IEPE (CH1): sale de JP1.2 por la derecha (los lados de arriba y abajo ya los usa el bloque 3), sube por x 124.0
  entre TP5/R4 y el tramo de 24 V de CH2 (J7-Pin_2, x 125.5), cruza a y 127.5 por encima del lazo IEPE_SUP_SV de U8
  (0.83 mm) y entra a R13.2 por la izquierda. Unos 33 mm: el nodo IEPE es la salida del sensor (baja impedancia).
- IEPE_SV (CH2): sale de J8.1 por abajo y va recta a R38.2 por y 153.825, bajo el bloque de PBT de J8 (KH-BNC75-3511:
  cuerpo a 0.5 mm de la placa, el metal no toca; mismo caso que el tramo de 24 V bajo J2, aceptado en el bloque 3).
  Queda a 1.45 mm del pad GND J8.2 y a 0.91 mm del anclaje J8.3.
- REST_OUT: sale de TP2 por la derecha y sube en diagonal por encima de C14; pasa a 0.35 mm por debajo del sensado de
  5V (y 118.5), sube a y 118.7 para pasar sobre la vía GND de R51.2 (0.39 mm) y entra a C9.1 desde arriba.
- REST_SV: sale de TP4 por la derecha, sube por x 156.5 (la vía GND de C16 está en x 157.425) y entra a C14.1 por la
  izquierda, por debajo de REST_OUT (0.40 mm entre las dos diagonales paralelas).
"""
F = 'F.Cu'
PISTAS = [
    ('IEPE', 0.25, F, [(121.8108, 141.9933), (123.2, 141.9933), (124.0, 141.1933), (124.0, 128.4), (124.9, 127.5),
                       (135.425, 127.5), (139.4, 131.475), (140.6, 131.475)]),
    ('IEPE_SV', 0.25, F, [(133.5, 151.45), (133.5, 153.4), (133.925, 153.825), (141.7, 153.825)]),
    ('REST_OUT', 0.2, F, [(154.126, 122.5249), (155.3, 122.5249), (158.7249, 119.1), (161.2, 119.1), (161.6, 118.7),
                          (165.6, 118.7), (166.275, 119.375), (166.275, 120.4775)]),
    ('REST_SV', 0.2, F, [(154.126, 145.0249), (155.3, 145.0249), (156.5, 143.8249), (156.5, 122.1775), (157.4, 121.2775),
                         (158.675, 121.2775)]),
]
VIAS = []
ZONAS = []
