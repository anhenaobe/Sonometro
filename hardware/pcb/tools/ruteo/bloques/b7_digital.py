"""Bloque 7: digital. SAI (I2S) de R22-R24 a la NUCLEO (A1), I2C de los dos DAC a A1, DC_MON y DC_MON2 a A1.

Coordenadas KiCad (mm). Política de capas (chequeo G): SAI (clase Reloj) solo en F.Cu; I2C (Default) y DC_MON/DC_MON2
(nivel DC) pueden ir por In2.Cu y B.Cu. Ninguna pista de B.Cu o In2.Cu pasa debajo de un nodo SUM, del nodo filtrado
del DAC ni de la cadena de 1 MΩ (regla del dueño para los cruces; revisado con tools/ruteo/cruces_capas.py).
- SAI en F.Cu. En el lado de las resistencias el orden es SD, SCK, FS de arriba abajo, y en A1 es FS (1), SD (2),
  SCK (12). SAI_FS sale de R23.1 por arriba y sube por un carril a la izquierda, entre los pads de R22 y de R24
  (0.325 mm a cada lado); SAI_SD sale de R24.1 por arriba; SAI_SCK sale de R22.1 por la derecha y baja por x 171.4.
  Las tres entran a A1 por la izquierda.
- I2C de CH1 (B.Cu):
  - SCL: U2.5 -> vía (148.6, 129.5); R10.1 -> entre R9 y R10 -> vía (147.27, 137.1).
  - SDA: U2.4 -> R11.1 en F.Cu -> vía (151.2, 133.02).
  - Bajan por el corredor entre los dos AFE (y 137.5-138.2), dan la vuelta por x 157.6-158.2 y por debajo de TP7
    (y 144.4-145.0), y suben por x 171.0/171.6 a A1.7/A1.8 por la izquierda.
- I2C de CH2 (In2.Cu): U10.4/U10.5 -> vías (148.0, 152.95) y (148.6, 152.0) -> In2 por y 151.2/152.0 -> suben por
  x 170.4/171.0 -> A1.7/A1.8. En B.Cu tendrían que cruzar DC_MON/DC_MON2, que van de la izquierda de la placa a la
  columna derecha de A1.
- DC_MON (B.Cu): R15.1 -> vía (141.7, 120.58) -> x 139.4, a la izquierda de la cadena de CH1 -> corredor y 139.4 ->
  x 156.3 -> y 146.25, debajo de la columna izquierda de A1 y del cuerpo de la NUCLEO -> A1.27 por la izquierda.
- DC_MON2 (B.Cu): R44.1 -> vía (142.2, 142.925) -> corredor y 140.0 -> x 155.7 -> y 146.85 -> vía (186.6, 146.85) ->
  In2 -> A1.26. DC_MON y DC_MON2 llegan a A1 en orden invertido: el cruce se hace con este tramo en In2, debajo de
  la NUCLEO.
- DC_MON/DC_MON2 quedan a >= 1 mm (borde a borde) de las líneas I2C en todo el recorrido (criterio del chequeo J).
"""
F, B, I2 = 'F.Cu', 'B.Cu', 'In2.Cu'
W = 0.2
PISTAS = [
    # SAI en F.Cu
    ('SAI_FS', W, F, [(169.95, 130.2125), (169.95, 128.18), (168.70, 126.93), (168.70, 124.86), (168.55, 124.71),
                      (168.55, 110.1), (169.55, 109.1), (173.11, 109.1)]),
    ('SAI_SD', W, F, [(169.375, 123.8875), (169.375, 112.4), (170.135, 111.64), (173.11, 111.64)]),
    ('SAI_SCK', W, F, [(169.525, 126.1375), (170.3, 126.1375), (171.4, 127.2375), (171.4, 136.44), (172.0, 137.04),
                       (173.11, 137.04)]),
    # I2C: salidas en F.Cu
    ('I2C_SCL', W, F, [(146.6375, 129.5), (148.6, 129.5)]),                                   # U2.5 -> vía
    ('I2C_SCL', W, F, [(148.2042, 134.3479), (147.6, 134.3479), (147.27, 134.6779), (147.27, 137.1)]),  # R10.1 -> vía
    ('I2C_SDA', W, F, [(146.6375, 130.45), (149.6, 130.45), (150.0375, 130.8875), (150.0375, 133.0229)]),  # U2.4 -> R11.1
    ('I2C_SDA', W, F, [(150.0375, 133.0229), (151.2, 133.0229)]),                             # R11.1 -> vía
    ('I2C_SCL', W, F, [(146.6375, 152.0), (148.6, 152.0)]),                                   # U10.5 -> vía
    ('I2C_SDA', W, F, [(146.6375, 152.95), (148.0, 152.95)]),                                 # U10.4 -> vía
    # I2C de CH1 en B.Cu
    ('I2C_SCL', W, B, [(148.6, 129.5), (148.6, 135.77), (147.27, 137.1)]),
    ('I2C_SCL', W, B, [(147.27, 137.1), (147.27, 137.55), (147.87, 138.15), (157.0, 138.15), (157.6, 138.75),
                       (157.6, 144.4), (158.2, 145.0), (171.0, 145.0), (171.6, 144.4), (171.6, 127.4), (172.12, 126.88),
                       (173.11, 126.88)]),
    ('I2C_SDA', W, B, [(151.2, 133.0229), (151.2, 136.95), (151.8, 137.55), (157.6, 137.55), (158.2, 138.15),
                       (158.2, 143.8), (158.8, 144.4), (170.4, 144.4), (171.0, 143.8), (171.0, 125.0), (171.66, 124.34),
                       (173.11, 124.34)]),
    # I2C de CH2 en In2.Cu
    ('I2C_SDA', W, I2, [(148.0, 152.95), (147.6, 152.55), (147.6, 151.6), (148.0, 151.2), (169.8, 151.2),
                        (170.4, 150.6), (170.4, 125.0), (171.06, 124.34), (173.11, 124.34)]),
    ('I2C_SCL', W, I2, [(148.6, 152.0), (170.4, 152.0), (171.0, 151.4), (171.0, 127.5), (171.62, 126.88),
                        (173.11, 126.88)]),
    # DC_MON / DC_MON2
    ('DC_MON', W, F, [(143.0844, 120.5812), (141.7, 120.5812)]),                              # R15.1 -> vía
    ('DC_MON2', W, F, [(143.2844, 142.925), (142.2, 142.925)]),                               # R44.1 -> vía
    ('DC_MON', W, B, [(141.7, 120.5812), (139.9, 120.5812), (139.4, 121.0812), (139.4, 138.8), (140.0, 139.4),
                      (155.7, 139.4), (156.3, 140.0), (156.3, 145.65), (156.9, 146.25), (184.8, 146.25), (185.4, 145.65),
                      (185.4, 137.96), (186.32, 137.04), (188.35, 137.04)]),
    ('DC_MON2', W, B, [(142.2, 142.925), (142.2, 140.6), (142.8, 140.0), (155.1, 140.0), (155.7, 140.6), (155.7, 146.25),
                       (156.3, 146.85), (186.6, 146.85)]),
    ('DC_MON2', W, I2, [(186.6, 146.85), (186.6, 135.1), (187.2, 134.5), (188.35, 134.5)]),
]
V = 0.6, 0.3
VIAS = [
    ('DC_MON', (141.7, 120.5812)) + V, ('DC_MON2', (142.2, 142.925)) + V, ('DC_MON2', (186.6, 146.85)) + V,
    ('I2C_SCL', (148.6, 129.5)) + V, ('I2C_SCL', (147.27, 137.1)) + V, ('I2C_SDA', (151.2, 133.0229)) + V,
    ('I2C_SCL', (148.6, 152.0)) + V, ('I2C_SDA', (148.0, 152.95)) + V,
]
ZONAS = []
