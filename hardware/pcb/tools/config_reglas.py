"""Configura las reglas de diseño del proyecto para el ruteo y la fabricación en JLCPCB.

- Restricciones de placa (piso absoluto del DRC) = mínimos de JLCPCB para 2 capas / 1 oz (ver REGLAS.md).
- Clases de red con los valores de DISEÑO (no los mínimos): Default, Potencia, Conmutado, Analogica, Reloj.
- Severidades: serigrafía, texto, colgantes, ángulo y largo de segmento -> error.
- Escribe pcb.kicad_dru con las reglas que no caben en las clases.
Uso: python tools/config_reglas.py   (KiCad cerrado; modifica pcb.kicad_pro y escribe pcb.kicad_dru)
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..')
PRO = os.path.join(PCB, 'pcb.kicad_pro')
DRU = os.path.join(PCB, 'pcb.kicad_dru')

if glob.glob(os.path.join(PCB, '*.lck')) or glob.glob(os.path.join(PCB, '~*')):
    sys.exit('KiCad tiene el proyecto abierto (hay archivos .lck): ciérralo primero.')

# --- pisos de fabricación JLCPCB, 2 capas, 1 oz (fuentes y filas exactas en REGLAS.md) -------------------
JLC = {
    'min_clearance': 0.10,             # separación pista-pista mínima
    'min_track_width': 0.10,
    'min_via_diameter': 0.25,          # vía 0.15/0.25 (2 capas: ver REGLAS.md)
    'min_through_hole_diameter': 0.15,
    'min_via_annular_width': 0.10,     # decisión: JLC permite 0.05 (0.075 preferido); nuestra vía 0.3/0.6 da 0.15
    'min_hole_clearance': 0.20,        # agujero de vía a pista (PTH 0.28: regla aparte)
    'min_hole_to_hole': 0.25,
    'min_copper_edge_clearance': 0.20,
    'min_silk_clearance': 0.05,        # serigrafía–serigrafía (detecta solapes); a pads 0.15 y a borde 0.3 por regla
    'min_text_height': 1.0,
    'min_text_thickness': 0.15,
    'solder_mask_to_copper_clearance': 0.09,  # JLC: >= 0.09 mm entre apertura de máscara y pistas vecinas
}

NETCLASSES = [
    # nombre, ancho, separación, vía (diám, taladro), patrones
    ('Default', 0.2, 0.2, (0.6, 0.3), []),
    # Potencia/Conmutado: valores reales del ruteo (aprobado tras el bloque 1). 0.25 mm es el ancho mínimo (salida de
    # un pin de 0.25 mm); los tramos se ensanchan según CALCULOS.md. Vía 0.6/0.3. El mínimo lo hace cumplir el .kicad_dru.
    ('Potencia', 0.25, 0.2, (0.6, 0.3),
     ['24V_IN', '24V_PROT', '3V3', '5V', '5V_A', 'GND', '*IEPE_SUP', '*IEPE_SUP_SV', '*3V3_DAC', '*3V3_DAC_SV',
      'Net-(D1-A)']),
    ('Conmutado', 0.25, 0.2, (0.6, 0.3), ['*SW_3', '*SW_5']),
    ('Analogica', 0.2, 0.3, (0.6, 0.3),
     ['IEPE', 'IEPE_SV', 'REST_OUT', 'REST_SV', 'DC_MON', 'DC_MON2', '*SUM*', '*IEPE_DIV*', '*FB_MID*',
      '*DAC_F*', '*DAC_RAW*', '*VSHIFT*', '*AC_LEFT', '*AC_RIGHT', '*ADC_IN*', '*PCM_VREF', '*SET_*', '*OUT_I',
      '*OUT_SV', '*STEP*', '*IEPE_FEED*', 'Net-(U3*', 'Net-(U9*', 'Net-(R16*', 'Net-(R39*', 'Net-(R42*',
      'Net-(U10-VOUT)', 'Net-(U2-VOUT)', 'Net-(R5*', 'Net-(C1*', 'Net-(C48*', 'Net-(JP1*', 'Net-(JP2*',
      'Net-(U4-VIN*', 'Net-(U4-VREF)', 'Net-(R2*', 'Net-(R35*', 'Net-(J7*', 'Net-(J1*', 'Net-(R13-*',
      'Net-(R14-*', 'Net-(R38-*', 'Net-(R4-*', 'Net-(R40-*', 'Net-(R7-*', 'Net-(C9-*']),
    ('Reloj', 0.2, 0.3, (0.6, 0.3),
     ['SAI_SCK', 'SAI_FS', 'SAI_SD', 'Net-(U4-BCK)', 'Net-(U4-DOUT)', 'Net-(U4-LRCK)', 'Net-(U4-SCKI)',
      'Net-(Y1-OUT)']),
]

SEVERITY_ERROR = ['silk_overlap', 'silk_over_copper', 'silk_edge_clearance', 'text_height', 'text_thickness',
                  'track_dangling', 'via_dangling', 'track_angle', 'track_segment_length', 'courtyards_overlap',
                  'lib_footprint_mismatch', 'footprint_symbol_mismatch', 'isolated_copper']

DRU_TEXT = '''(version 1)
# Reglas propias del Sonómetro IEPE Rev B (generado por tools/config_reglas.py; fuentes en REGLAS.md)

# Solo 45°: ángulo interior entre segmentos unidos >= 135° (prohíbe 90° y agudos). Probado en KiCad 10.0.8.
(rule "solo_45"
  (condition "A.Type == 'Track'")
  (constraint track_angle (min 135)))

# Sin segmentos de menos de 0.1 mm.
(rule "segmento_minimo"
  (condition "A.Type == 'Track'")
  (constraint track_segment_length (min 0.1mm)))

# Cobre a borde de placa: 0.5 mm de diseño (JLC permite 0.2).
(rule "borde"
  (constraint edge_clearance (min 0.5mm)))

# Anillo de pads PTH >= 0.20 mm (JLC: 0.20 en la tabla, 0.18 mínimo absoluto, 0.25 recomendado);
# las vías tienen su propio piso (0.10) en la placa.
(rule "anillo_pth"
  (condition "A.Type == 'Pad' && A.Pad_Type == 'Through-hole'")
  (constraint annular_width (min 0.2mm)))

# Agujero PTH a cobre de otra red >= 0.28 mm (JLC; 0.35 recomendado).
(rule "agujero_pth_a_cobre"
  (condition "A.Type == 'Pad' && A.Pad_Type == 'Through-hole'")
  (constraint hole_clearance (min 0.28mm)))

# Pad a pad (dentro de un mismo integrado) 0.2 mm: la clase Analogica (0.3) es para pistas y cobre, no para
# los pads vecinos de un TSSOP/TSOT ya fijados por el land pattern del fabricante.
(rule "pad_a_pad"
  (condition "A.Type == 'Pad' && B.Type == 'Pad'")
  (constraint clearance (min 0.2mm)))

# Serigrafía a pads 0.15 mm (JLC) y a borde 0.3 mm. Probado: el piso de la placa (0.05) solo vale entre
# serigrafías, para que dos líneas de footprints vecinos a 0.075 mm no cuenten como solape.
(rule "serigrafia_a_pad"
  (condition "A.Layer == 'F.SilkS' && B.Type == 'Pad'")
  (constraint silk_clearance (min 0.15mm)))

(rule "serigrafia_a_borde"
  (condition "A.Layer == 'F.SilkS' && B.Layer == 'Edge.Cuts'")
  (constraint silk_clearance (min 0.3mm)))

# 4 capas (JLC, https://jlcpcb.com/capabilities/pcb-capabilities): "Inner layer via hole to copper clearance 0.2mm",
# "Inner layer PTH pad hole to copper clearance 0.3mm". Probadas con una regla de control (0.6 / 1.5 mm).
(rule "agujero_via_a_cobre_interno"
  (layer inner)
  (condition "A.Type == 'Via'")
  (constraint hole_clearance (min 0.2mm)))

(rule "agujero_pth_a_cobre_interno"
  (layer inner)
  (condition "A.Type == 'Pad' && A.Pad_Type == 'Through-hole'")
  (constraint hole_clearance (min 0.3mm)))

# Vías taponadas (JLC tapona por defecto en 4 capas): "vias with a distance less than 0.35mm from the pad cannot be
# plugged with ink" (https://jlcpcb.com/help/article/pcb-via-covering). physical_clearance vale también entre una vía
# y un pad de la misma red. Decisión del dueño: correr las vías a >= 0.35 mm.
(rule "via_tapada_lejos_de_pad"
  (condition "A.Type == 'Via' && B.Type == 'Pad'")
  (constraint physical_clearance (min 0.35mm)))

# Ancho mínimo de las redes de potencia y conmutadas (= ancho de su clase; los anchos mayores salen de CALCULOS.md).
(rule "ancho_minimo_potencia"
  (condition "A.Type == 'Track' && (A.hasNetclass('Potencia') || A.hasNetclass('Conmutado'))")
  (constraint track_width (min 0.25mm)))

# Nodos conmutados de los bucks lejos de lo analógico.
(rule "sw_lejos_de_analogica"
  (condition "A.hasNetclass('Conmutado') && B.hasNetclass('Analogica')")
  (constraint clearance (min 1mm)))

# Relojes I2S/MCLK lejos de lo analógico.
(rule "reloj_lejos_de_analogica"
  (condition "A.hasNetclass('Reloj') && B.hasNetclass('Analogica')")
  (constraint clearance (min 0.5mm)))
'''


def main():
    p = json.load(open(PRO))
    rules = p['board']['design_settings']['rules']
    rules.update(JLC)
    sev = p['board']['design_settings']['rule_severities']
    for k in SEVERITY_ERROR:
        sev[k] = 'error'
    ns = p['net_settings']
    base = dict(ns['classes'][0])
    classes, patterns = [], []
    for i, (name, w, clr, (vd, vh), pats) in enumerate(NETCLASSES):
        c = dict(base)
        c.update(name=name, track_width=w, clearance=clr, via_diameter=vd, via_drill=vh,
                 priority=2147483647 if name == 'Default' else i)
        classes.append(c)
        patterns += [{'netclass': name, 'pattern': pt} for pt in pats]
    ns['classes'] = classes
    ns['netclass_patterns'] = patterns
    ns['netclass_assignments'] = None
    json.dump(p, open(PRO, 'w'), indent=2)
    open(DRU, 'w', encoding='utf-8').write(DRU_TEXT)
    print('pcb.kicad_pro y pcb.kicad_dru actualizados:', [c['name'] for c in classes], len(patterns), 'patrones')


if __name__ == '__main__':
    main()
