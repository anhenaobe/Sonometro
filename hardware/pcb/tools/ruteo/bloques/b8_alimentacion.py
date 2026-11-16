"""Bloque 8: distribución de 3V3 y 5V_A por In2.Cu (pistas de 0.4 mm; corrientes de 5-20 mA, ver CALCULOS.md).

Coordenadas KiCad (mm). In2.Cu ya lleva los straps MD1/FMT, el I2C de CH2 y un tramo de DC_MON2; nada se cruza.
- 5V_A: R33.2 -> C47.1 -> F.Cu hasta la vía (164.65, 117.0), que queda por debajo del tramo de 3V3 en y 114.
  En In2 se reparte en árbol, con ramas solo en vías:
  - (164.65, 117.0) -> y 117.4, bajo el bus de 24 V -> x 151.0 -> vía junto a C7.2 (152.28, 120.9);
  - (164.65, 117.0) -> x 165.5 -> vía en el quiebre de U4.3 (163.35, 133.3);
  - (163.35, 133.3) -> vía junto a C18.1 (159.35, 136.2) -> x 156.0 -> vía junto a C54.2 (152.28, 143.4).
- 3V3: las vías (139.8, 116.3) y (139.8, 118.5) del tronco de 3V3 (bloque 1) alimentan dos ramas.
  - Izquierda, desde (139.8, 118.5) por x 139.4 (a 0.73 mm en planta de la cadena de CH1):
    - y 135.0 -> vía izquierda de R9.2 (145.0, 135.85). De ella sale la rama de R46.2: y 137.4 -> x 140.7 (a
      0.53 mm en planta de la columna de CH2) -> vía (146.0583, 159.64).
    - R9.2 tiene una segunda vía debajo (146.3375, 136.92), unida a la primera por F.Cu. De ahí, por debajo de la
      vía SCL (147.27, 137.1), sale a la vía de R10.2 (148.2042, 137.07). R11.2 se une a R10.2 en F.Cu.
    - Dos vías en R9.2 porque la regla track_angle del DRC también mira las uniones en vías, y tres pistas en una
      misma vía no pueden quedar todas a >= 135°.
  - Derecha, desde (139.8, 116.3) por y 114, por encima del bus y de la vía de 5V_A, y x 168.5 (entre la rama de
    5V_A en x 165.5 y el I2C de CH2 en x 170.4):
    - R49.1 -> vía (166.15, 129.6062), bajo el cuerpo de U4;
    - C20.1 -> vía (166.95, 131.7187), con un quiebre a 45°;
    (corridas en el bloque 10: estaban bajo el contorno de serigrafía de U4; la rama de 5V_A pasó de x 165.5 a
    165.3 para dejarles 0.35 mm)
    - C13.1 (grupo de U4.4/C11/C12/Y1) -> vía (165.98, 138.5151), rodeando la vía GND de Y1.2.
    Las vías de R49.1/C20.1 reservadas en el bloque 4 quedaban a menos de 0.35 mm del pad (se reservaron antes de la
    regla de vías taponadas); estas son las corregidas.
- GND: vía de C47.2.
"""
F, I2 = 'F.Cu', 'In2.Cu'
P5 = 0.4
P3 = 0.4
PISTAS = [
    # 5V_A en F.Cu: R33.2 -> C47.1 -> vía
    ('5V_A', P5, F, [(162.925, 102.315), (164.65, 102.315)]),
    ('5V_A', P5, F, [(164.65, 102.315), (164.65, 117.0)]),
    # 5V_A: salidas a las vías de cada carga
    ('5V_A', 0.3, F, [(151.1375, 120.9), (152.28, 120.9)]),          # C7.2
    ('5V_A', 0.3, F, [(151.1375, 143.4), (152.28, 143.4)]),          # C54.2
    ('5V_A', 0.3, F, [(159.35, 137.325), (159.35, 136.2)]),          # C18.1
    # 5V_A en In2
    ('5V_A', P5, I2, [(164.65, 117.0), (163.9, 117.0), (163.5, 117.4), (151.6, 117.4), (151.0, 118.0), (151.0, 120.3), (151.6, 120.9),
                      (152.28, 120.9)]),
    ('5V_A', P5, I2, [(164.65, 117.0), (165.3, 117.65), (165.3, 131.35), (163.35, 133.3)]),
    ('5V_A', P5, I2, [(163.35, 133.3), (163.35, 134.0), (161.15, 136.2), (159.35, 136.2)]),
    ('5V_A', P5, I2, [(159.35, 136.2), (156.0, 139.55), (156.0, 142.7), (155.3, 143.4), (152.28, 143.4)]),
    # 3V3: salidas en F.Cu
    ('3V3', 0.3, F, [(146.3375, 135.8458), (146.3375, 136.92)]),      # R9.2 -> vía de abajo (rama a R10/R11)
    ('3V3', 0.3, F, [(146.3375, 135.8458), (145.0, 135.8458)]),       # R9.2 -> vía de la izquierda (llegada y rama a R46)
    ('3V3', 0.3, F, [(148.2042, 135.9979), (148.2042, 137.07)]),      # R10.2
    ('3V3', 0.3, F, [(148.2042, 135.9979), (149.3, 135.9979), (150.0375, 135.2604), (150.0375, 134.6729)]),  # -> R11.2
    ('3V3', 0.3, F, [(146.0583, 158.5667), (146.0583, 159.64)]),      # R46.2
    ('3V3', 0.3, F, [(168.0125, 129.6062), (166.15, 129.6062)]),      # R49.1 -> vía bajo el cuerpo de U4
    ('3V3', 0.3, F, [(168.1147, 131.3687), (167.3, 131.3687), (166.95, 131.7187)]),  # C20.1
    ('3V3', 0.3, F, [(164.829, 138.5151), (165.98, 138.5151)]),       # C13.1
    # 3V3 en In2, rama izquierda
    ('3V3', P3, I2, [(139.8, 118.5), (139.4, 118.9), (139.4, 134.4), (140.0, 135.0), (144.1542, 135.0),
                     (145.0, 135.8458)]),
    ('3V3', P3, I2, [(146.3375, 136.92), (146.3375, 137.45), (146.7375, 137.85), (147.8, 137.85), (148.2042, 137.4458),
                     (148.2042, 137.07)]),
    ('3V3', P3, I2, [(145.0, 135.8458), (145.0, 136.4), (144.0, 137.4), (141.3, 137.4), (140.7, 138.0), (140.7, 159.04),
                     (141.3, 159.64), (146.0583, 159.64)]),
    # 3V3 en In2, rama derecha
    ('3V3', P3, I2, [(139.8, 116.3), (139.8, 114.6), (140.4, 114.0), (167.9, 114.0), (168.5, 114.6), (168.5, 127.2562),
                     (166.15, 129.6062)]),
    ('3V3', P3, I2, [(166.15, 129.6062), (166.15, 130.9187), (166.95, 131.7187)]),
    ('3V3', P3, I2, [(166.95, 131.7187), (167.8, 132.5687), (167.8, 138.9), (167.3, 139.4), (166.4, 139.4),
                     (165.98, 138.98), (165.98, 138.5151)]),
    # GND de C47
    ('GND', 0.4, F, [(166.2, 102.315), (167.32, 102.315)]),
]
V = 0.6, 0.3
VIAS = [
    ('5V_A', (164.65, 117.0)) + V, ('5V_A', (152.28, 120.9)) + V, ('5V_A', (163.35, 133.3)) + V,
    ('5V_A', (159.35, 136.2)) + V, ('5V_A', (152.28, 143.4)) + V,
    ('3V3', (145.0, 135.8458)) + V, ('3V3', (146.3375, 136.92)) + V, ('3V3', (148.2042, 137.07)) + V,
    ('3V3', (146.0583, 159.64)) + V,
    ('3V3', (166.15, 129.6062)) + V, ('3V3', (166.95, 131.7187)) + V, ('3V3', (165.98, 138.5151)) + V,
    ('GND', (167.32, 102.315)) + V,
]
ZONAS = []
