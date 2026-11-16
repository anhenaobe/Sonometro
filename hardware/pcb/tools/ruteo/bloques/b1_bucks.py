"""Bloque 1: bucks U6 (3V3) y U7 (5V), según TI SNVSB49D fig. 12-2 adaptada a 2 capas (lazo de potencia en F.Cu).

Coordenadas KiCad (mm). U7 es el mismo layout que U6 desplazado 21.6 mm en x. Decisiones aprobadas en el punto de
control 2: C29/C39 subidos 0.3 mm, C35/C45 a la izquierda del integrado, y tres puentes cortos en B.Cu bajo el bus
de 24 V (y = 117.4, se rutea en el bloque 2): tronco de 3V3 (x = 139.8) y sensado de FB de U6 (x = 132.7) y U7
(x = 154.3).
- Pin 3 (NC) va unido a SW (pin 12) en la placa (SNVSB49D §12.1 ítem 3 y tabla de pines p.4) con una zona chica de
  SW: con pistas no se puede entrar al centro del pin 12 sin un giro de 90° ni pasar entre los pines 1/2 o 10/11.
- CBOOT (C35/C45) entre BOOT (pin 4) y pin 3. BOOT sale por la izquierda del pin 4 y baja por fuera del SW.
- Todas las pistas >= 0.2 mm; cada quiebre fuera del pad (entrada recta al centro). En los pines del integrado la
  pista sale con el ancho del pad (0.25 mm) y se ensancha fuera de él: así ninguna esquina entre pistas queda fuera
  del cobre del pad.
- Vía GND junto a cada pad GND: condensadores y pines 1, 6 y 11 del integrado (el relleno GND de F.Cu y el cosido
  van en el bloque 9; el plano GND de B.Cu es el bloque gnd_bcu).
- Revisión del dueño: C36/C46 a 3.0 mm del pin 5 aceptado, con VCC de 0.3 mm, la vía GND del condensador pegada a su
  pad y retorno corto en F.Cu de su pad GND al pin AGND (6). Sensado de FB a 0.25 mm (mínimo de la clase Potencia).
"""
DX = 21.6
NETS = {  # red de U6 -> red de U7
    '/SW_3': '/SW_5', 'Net-(U6-BOOT)': 'Net-(U7-BOOT)', 'Net-(U6-VCC)': 'Net-(U7-VCC)',
    'Net-(U6-FB)': 'Net-(U7-FB)', '3V3': '5V', 'GND': 'GND', '24V_PROT': '24V_PROT',
}
VIA = (0.6, 0.3)

# ------------------------------------------------------------------ U6 (las de U7 salen por desplazamiento)
_P6 = [
    # SW: pin 12 -> L1 (corto y ancho); pin 3 -> C35 (solo la corriente de carga de CBOOT)
    ('/SW_3', 0.25, [(129.0, 108.013), (129.0, 106.9)]),
    ('/SW_3', 0.6, [(129.0, 106.9), (129.0, 104.685)]),
    ('/SW_3', 0.25, [(128.1, 108.975), (127.575, 108.975), (127.2, 109.35), (127.2, 110.225), (127.0, 110.425),
                     (126.4, 110.425)]),
    # BOOT: pin 4 -> C35.1
    ('Net-(U6-BOOT)', 0.2, [(128.1, 109.475), (127.75, 109.475), (127.65, 109.575), (127.65, 111.325),
                            (127.0, 111.975), (126.4, 111.975)]),
    # VCC: pin 5 -> C36
    ('Net-(U6-VCC)', 0.25, [(128.5, 110.2), (128.5, 110.7)]),
    ('Net-(U6-VCC)', 0.3, [(128.5, 110.7), (128.5, 114.0)]),
    # AGND: pin 6 -> vía
    ('GND', 0.25, [(129.0, 110.2), (129.0, 111.4), (129.2, 111.6)]),
    # retorno de CVCC (C36.2) al pin AGND por F.Cu, a la derecha de la pista VCC
    ('GND', 0.25, [(129.2, 111.6), (129.85, 112.25), (129.85, 115.4), (129.35, 115.9), (128.5, 115.9)]),
    # FB: pin 7 -> R29.2 -> R30.1
    ('Net-(U6-FB)', 0.2, [(129.5, 110.2), (129.5, 111.0), (131.082, 112.582), (131.75, 112.582)]),
    ('Net-(U6-FB)', 0.2, [(131.75, 112.582), (131.75, 113.2), (131.625, 113.325), (131.625, 114.316)]),
    # VIN: pin 2 -> C29.1 -> C27.1 ; EN (pin 9) con VIN (pin 10) ; pin 10 -> C30.1 -> C28.1
    ('24V_PROT', 0.25, [(128.1, 108.325), (127.4, 108.325)]),
    ('24V_PROT', 0.4, [(127.4, 108.325), (127.075, 108.65), (126.15, 108.65)]),
    ('24V_PROT', 0.5, [(126.15, 108.65), (123.0, 108.65), (121.8, 109.85), (121.8, 111.95)]),
    ('24V_PROT', 0.25, [(129.9, 108.975), (129.9, 108.325)]),
    ('24V_PROT', 0.25, [(129.9, 108.325), (130.4, 108.325)]),
    ('24V_PROT', 0.4, [(130.4, 108.325), (131.025, 108.95), (131.85, 108.95)]),
    ('24V_PROT', 0.5, [(131.85, 108.95), (135.2, 108.95), (136.2, 109.95), (136.2, 111.95)]),
    # PGND: pin 1 -> C29.2 -> C27.2 ; pin 11 -> C30.2
    ('GND', 0.4, [(128.1, 107.675), (128.1, 107.2), (127.65, 106.75)]),       # vía del pin 1 en el quiebre
    ('GND', 0.4, [(127.65, 106.75), (126.15, 106.75)]),
    ('GND', 0.5, [(126.15, 106.75), (125.0, 106.75), (124.9, 106.85), (121.8, 106.85)]),
    ('GND', 0.25, [(129.9, 107.675), (130.4, 107.675)]),
    ('GND', 0.4, [(130.4, 107.675), (131.025, 107.05), (131.85, 107.05)]),
    ('GND', 0.25, [(129.9, 107.675), (129.9, 106.75)]),                      # vía del pin 11
    # vías GND junto a cada pad GND (tramo recto desde el centro del pad)
    ('GND', 0.5, [(121.8, 106.85), (121.8, 105.45)]),             # C27.2 (vía entre CIN y COUT)
    ('GND', 0.5, [(136.2, 106.85), (136.2, 105.45)]),             # C28.2
    ('GND', 0.4, [(126.15, 106.75), (126.15, 105.75)]),           # C29.2
    ('GND', 0.4, [(131.85, 107.05), (131.85, 106.05)]),           # C30.2
    ('GND', 0.5, [(121.0, 104.475), (121.0, 105.45)]),            # C31.2
    ('GND', 0.5, [(124.6, 104.475), (124.6, 105.45)]),            # C32.2
    ('GND', 0.5, [(133.4, 104.475), (133.4, 105.45)]),            # C33.2
    ('GND', 0.5, [(137.0, 104.475), (137.0, 105.45)]),            # C34.2
    ('GND', 0.4, [(128.5, 115.9), (127.3, 115.9)]),               # C36.2
    ('GND', 0.4, [(131.625, 115.966), (130.6, 115.966)]),         # R30.2
]
_V6 = [(129.2, 111.6), (127.65, 106.75), (129.9, 106.75), (121.8, 105.45), (136.2, 105.45), (126.15, 105.75), (131.85, 106.05), (121.0, 105.45),
       (124.6, 105.45), (133.4, 105.45), (137.0, 105.45), (127.3, 115.9), (130.6, 115.966)]
_Z6 = [
    dict(nombre='SW_3_PIN3', red='/SW_3', capa='F.Cu', prioridad=3,
         puntos=[(127.95, 108.7), (129.25, 108.7), (129.25, 109.2), (127.95, 109.2)]),
]


def _shift(pts, d):
    return [(round(x + d, 4), y) for x, y in pts]


PISTAS = []
VIAS = []
ZONAS = []
for red, w, pts in _P6:
    PISTAS.append((red, w, 'F.Cu', pts))
    PISTAS.append((NETS[red], w, 'F.Cu', _shift(pts, DX)))
for p in _V6:
    VIAS.append(('GND', p) + VIA)
    VIAS.append(('GND', (round(p[0] + DX, 4), p[1])) + VIA)
for z in _Z6:
    ZONAS.append(z)
    ZONAS.append(dict(z, nombre='SW_5_PIN3', red=NETS[z['red']], puntos=_shift(z['puntos'], DX)))

# ------------------------------------------------------------------ salidas y puentes aprobados
ZONAS += [
    dict(nombre='VOUT_3V3', red='3V3', capa='F.Cu', prioridad=2,
         puntos=[(119.4, 100.55), (138.6, 100.55), (138.6, 103.3), (119.4, 103.3)]),
    dict(nombre='VOUT_5V', red='5V', capa='F.Cu', prioridad=2,
         puntos=[(141.0, 100.55), (161.9, 100.55), (161.9, 103.3), (141.0, 103.3)]),
]
PISTAS += [
    # tronco de 3V3: desde C34.1 por el canal entre bloques, puente bajo el bus de 24 V, enlace bajo el bus
    ('3V3', 0.5, 'F.Cu', [(137.0, 101.525), (138.6, 101.525), (139.8, 102.725), (139.8, 116.3)]),
    ('3V3', 0.5, 'B.Cu', [(139.8, 116.3), (139.8, 118.5)]),
    ('3V3', 0.5, 'F.Cu', [(139.8, 118.5), (132.7, 118.5)]),
    # sensado de FB de U6 (3V3): puente bajo el bus y subida por el corredor junto a R29/R30 hasta R29.1
    ('3V3', 0.3, 'B.Cu', [(132.7, 118.5), (132.7, 116.35)]),
    ('3V3', 0.25, 'F.Cu', [(132.7, 116.35), (132.7, 111.233), (132.4, 110.933), (131.75, 110.933)]),
    # sensado de FB de U7 (5V): desde R33.1 (salida de 5V) por la franja libre a la derecha del bloque
    ('5V', 0.25, 'F.Cu', [(161.275, 102.315), (161.275, 118.0), (160.775, 118.5), (154.3, 118.5)]),
    ('5V', 0.3, 'B.Cu', [(154.3, 118.5), (154.3, 116.35)]),
    ('5V', 0.25, 'F.Cu', [(154.3, 116.35), (154.3, 111.233), (154.0, 110.933), (153.35, 110.933)]),
]
VIAS += [('3V3', (139.8, 116.3)) + VIA, ('3V3', (139.8, 118.5)) + VIA, ('3V3', (132.7, 118.5)) + VIA,
         ('3V3', (132.7, 116.35)) + VIA, ('5V', (154.3, 118.5)) + VIA, ('5V', (154.3, 116.35)) + VIA]
