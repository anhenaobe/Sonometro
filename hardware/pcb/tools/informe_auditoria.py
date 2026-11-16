"""Genera fabricacion/auditoria_piezas.md a partir de tools/out/auditoria_jlc.json, alternativas_jlc.json y
auditoria_footprints.json (correr antes auditoria_jlc.py, alternativas_jlc.py y auditoria_footprints.py)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
FAB = os.path.join(HERE, '..', 'fabricacion')
os.makedirs(FAB, exist_ok=True)
A = json.load(open(os.path.join(OUT, 'auditoria_jlc.json'), encoding='utf-8'))
F = json.load(open(os.path.join(OUT, 'auditoria_footprints.json')))
T = json.load(open(os.path.join(HERE, 'target.json')))

# Propuestas (solo propuestas: el dueño aprueba en el punto de control 2)
PROP = [
    ('U3, U9', 'TLV9062IDDFR (C2867884): stock **2 en JLC y 0 en LCSC** para 2 piezas',
     'TLV9152IDDFR **C2861011** (stock 542). Verificado en TI SBOS986E: pinout DDF idéntico (OUT1, IN1−, IN1+, V−, '
     'IN2+, IN2−, OUT2, V+; fig. 5-4, p.6), alimentación 2.7–16 V, entrada rail-to-rail (V−)−0.1 a (V+)+0.1 V '
     '(p.11), 4.5 MHz y 10.8 nV/√Hz. Nota: el par de entrada principal llega a (V+)−2 V = 3.0 V con 5V_A; VSHIFT '
     'del RG-50 = 2.5 V (bien). Alternativa: TLV9002IDDFR C2862620 (stock 2331, 1 MHz; datasheet sin revisar).',
     'no (mismo TSOT-23-8)', 'riesgo'),
    ('C27, C28, C37, C38 (CIN)', 'C5750X7R2A475K230KA (C2168733): **stock 0**',
     'PSA FS55X475K101EGG **C153031** (4.7 µF 100 V X7R 2220, stock 11 756). Mismo valor, tensión y tamaño.',
     'no', 'riesgo'),
    ('C31–C34, C41–C44 (COUT)', 'C3225X7R1C156M250AB (C2167855): **stock 0**',
     'TDK C3225X7R1C156MT000N **C694469** (15 µF 16 V X7R 1210, stock 1338). Misma serie TDK.', 'no', 'riesgo'),
    ('C36, C46 (VCC)', 'C0805C225K5RACTU: **no está en el catálogo**',
     'Samsung CL21B225KOFNNNE **C28234** (2.2 µF 16 V X7R 0805, stock 73 051). El datasheet pide 1 µF/16 V. '
     'Basic más barato: C23630 (0603, cambia el footprint).', 'no (con C28234)', 'riesgo'),
    ('R33', 'CRCW0603010RJNEAHP: **no está en el catálogo**', '**C22859** 10 Ω 1 % 0603 (basic).', 'no', 'riesgo'),
    ('R2, R3', 'RTT031500FTP (C103302): **stock 11**', '**C22808** 150 Ω 1 % 0603 (basic, la misma de R48).',
     'no', 'riesgo'),
    ('R10, R11', 'SCR0603F4K7 (C3016318): **stock 19**', '**C23162** 4.7 kΩ 1 % 0603 (basic).', 'no', 'riesgo'),
    ('C10, C19', 'sin LCSC; el MPN existe como C3854899 (extended)', '**C15195** 10 nF 50 V X7R 0402 (basic).',
     'no', 'costo'),
    ('R1, R36', 'sin LCSC; el MPN existe como C481926 (extended)', '**C25077** 10 Ω 0402 (basic).', 'no', 'costo'),
    ('R9, R19–R24, R35, R46', 'FRC0603J101 TS 5 % (extended)', '**C22775** 100 Ω 1 % 0603 (basic).', 'no',
     'costo'),
    ('R4, R5, R12, R15, R17, R37, R44, R45, R49–R51', 'FRC0603J103TS 5 % (extended)',
     '**C25804** 10 kΩ 1 % 0603 (basic). Mejora: los divisores DC_MON quedan a 1 %.', 'no', 'costo'),
    ('R6', 'FRC0603J102 TS 5 % (extended)', '**C21190** 1 kΩ 1 % (basic).', 'no', 'costo'),
    ('R7, R8, R42, R43', 'RC0603FR-0749K9L (extended)', '**C23184** 49.9 kΩ 1 % (basic).', 'no', 'costo'),
    ('R29, R31', 'RC0603FR-07100KL (extended)', '**C25803** 100 kΩ 1 % (basic).', 'no', 'costo'),
    ('R34', 'RC0603FR-0715KL (extended)', '**C22809** 15 kΩ 1 % (basic).', 'no', 'costo'),
    ('C5, C9, C11, C14, C15, C18, C47, C52', 'TCC0603X5R106K100CT (extended)',
     '**C19702** CL10A106KP8NNNC 10 µF 10 V X5R 0603 (basic).', 'no', 'costo'),
    ('C29, C30, C39, C40 (CHF)', 'C0805C224K1RACTU 100 V (extended)',
     '**C5378** CL21B224KBFNNNE 220 nF 50 V X7R 0805 (basic; 50 V ≥ 2 × 24 V).', 'no', 'costo'),
]

L = []
w = L.append
w('# Auditoría de piezas para JLCPCB (PCBA Economic)\n')
w('Generado por `tools/informe_auditoria.py` con la API pública del buscador de piezas de JLCPCB '
  '(consulta del 15/11/2026; stock en vivo, cambia a diario) y los footprints de EasyEDA/JLC bajados con '
  '`easyeda2kicad`. **Nada de esto se ha cambiado en el diseño: son propuestas para aprobar.**\n')
w('## 1. Estado de cada pieza que monta JLC\n')
w('| Refs | Valor | MPN del diseño | LCSC | Origen del código | Tipo | Stock | MPN coincide |')
w('|---|---|---|---|---|---|---|---|')
ext = set()
for it in A:
    f = it['found'] or {}
    if f.get('type', '').startswith('extended') and 'preferred' not in f.get('type', ''):
        ext.add(f.get('lcsc'))
    w(f"| {', '.join(it['refs'])} | {it['value']} | {it['mpn']} | {f.get('lcsc', '**no encontrado**')} | "
      f"{it['lcsc_source'] or '—'} | {f.get('type', '—')} | {f.get('stock', '—')} | "
      f"{'sí' if it['mpn_match'] else ('no (ver nota)' if it['mpn_match'] is False else '—')} |")
w('\nStock confirmado en la API de LCSC (wmsc.lcsc.com, 15/11/2026) para las piezas en riesgo: TLV9062IDDFR 0, '
  'C5750X7R2A475K230KA 0, C3225X7R1C156M250AB 0, RTT031500FTP 0, SCR0603F4K7 0, LMR36015FBRNXR 27. La cifra de '
  '3989 TLV9062 que dio una búsqueda web anterior era un resultado viejo.\n')
w('\nNota: U4 figura como PCM1808PW en el diseño y C55513 es PCM1808PW**R** (la misma pieza en carrete).\n')
w(f'Piezas *extended* distintas hoy (sin contar *preferred*): **{len(ext)}**. En Economic, JLC cobra una carga '
  'de alimentador por cada una (≈ USD 3.07 según su página de precios).\n')
w('## 2. Propuestas de cambio (requieren aprobación)\n')
w('| Refs | Problema | Propuesta | ¿Cambia footprint? | Motivo |')
w('|---|---|---|---|---|')
for refs, prob, prop, fpc, why in PROP:
    w(f'| {refs} | {prob} | {prop} | {fpc} | {why} |')
w('\nSi se aceptan todas, las piezas *extended* bajan a las que no tienen equivalente basic: 390k, 365k, '
  '191k, 54.9k, 43.2k y 24.9k (1 %), SMBJ26A, el oscilador, LT3092, MCP4725, PCM1808, TLV9152/9002, '
  'LMR36015, las dos bobinas Coilcraft, CIN y COUT.\n')
w('**Riesgos de stock aunque no se cambie nada:** LMR36015FBRNXR **27** unidades (se necesitan 2), L2 '
  'XAL4040-103MEC 189, R16/R40 191k 224, R30 43.2k 168, MCP4725 377. Conviene pedir pronto o reservarlas en la '
  'biblioteca de piezas de JLC.\n')
w('## 3. Footprints de KiCad contra el footprint de JLC/EasyEDA de esa pieza exacta\n')
w('Se emparejan los pads por número y se busca el giro *d* y la traslación *t* que llevan el footprint de KiCad '
  'sobre el de JLC. *err* es el máximo desvío de posición de pad después de alinear; *Δtam* es la máxima '
  'diferencia de tamaño de pad. Si en una pieza polarizada la numeración no coincidiera, aparecería en '
  '"sin pareja" o con un error grande.\n')
w('| LCSC | Footprint KiCad | Footprint JLC | d (°) | t (mm) | err (mm) | Δtam (mm) | Pads sin pareja |')
w('|---|---|---|---|---|---|---|---|')
for r in sorted(F, key=lambda r: r['kicad']):
    if 'error' in r:
        w(f"| {r['lcsc']} | {r['kicad'].split(':')[1]} | — | — | — | — | — | {r['error']} |")
        continue
    w(f"| {r['lcsc']} | {r['kicad'].split(':')[1]} | {r['jlc']} | {r['giro_d']} | ({r['tx']:+.2f}, {r['ty']:+.2f}) "
      f"| {r['error_pos_max']:.3f} | {r['dif_tam_pad_max']:.3f} | {', '.join(r['sin_pareja']) or '—'} |")
w('''
**Lectura:**
- **Pasivos (R/C 0402–2220), diodos SMA/SMB, oscilador y bobinas:** misma orientación (d = 0°; la XAL4040 da
  180°, que en una bobina de 2 pads no importa), pin 1 y cátodo en el mismo lado, posiciones a ≤ 0.2 mm. Las
  diferencias de tamaño de pad (≤ 0.5 mm) son las de los distintos land patterns IPC (KiCad usa el nominal);
  no afectan el ensamblaje.
- **Integrados:** JLC los dibuja girados respecto a KiCad, y **el giro depende de la pieza exacta, no del
  encapsulado**:
  - TSSOP-14 (PCM1808): 90°;
  - SOT-23-6 (MCP4725): 90°;
  - TSOT-23-8: 90° (TLV9062), 180° (LT3092 y TLV9152) y 0° (TLV9002);
  - RNX (LMR36015): 90° y 0.14 mm de desplazamiento.

  Esto va a la tabla de rotaciones del CPL (`fabricacion/rotaciones.md`), por código LCSC.
- **TSOT-23-8 propuesto** (`Sonometro:TSOT-23-8_Pad0.40x1.22mm_P0.65mm_ADI`):
  - pads de 0.40 × 1.22 mm, filas a 2.62 mm (dibujo ADI LTC 05-08-1637);
  - 0.25 mm entre pads (antes 0.15);
  - puente de máscara 0.25 mm con apertura 1:1, o 0.15 mm si se usara la expansión de 0.05 mm del dibujo TI DDF
    (JLC pide 0.10 en verde);
  - JLC dibuja 0.364 × 1.222 (LT3092) y 0.40 × 0.90 (TLV9062): el nuestro cubre los dos.
- **Pendiente:** C3016318 (R10/R11) no se pudo comparar (la API de EasyEDA limitó las consultas). Es un 0603
  igual a los demás y además se propone reemplazarla.

## 4. Lo que va soldado a mano (no lo monta JLC)
| Refs | Pieza | LCSC (para comprar) | Nota |
|---|---|---|---|
| A1 | 2 tiras hembra 1×15 de 2.54 mm (KH-2.54FH-1X15P-H8.5) + NUCLEO-L432KC | C2932676 (×2) | zócalo; la NUCLEO va enchufada |
| J1, J5, J7 | bornera de 2 vías de 5.0 mm (JL126-50002G01) | C394556 | THT |
| J2, J8 | BNC hembra a 90° (KH-BNC75-3511) | C2837588 | THT; el barril sale por el borde inferior |
| JP1, JP2 | header 1×2 de 2.54 mm + jumper | — | THT |
| TP1–TP7 | punto de prueba (pad con agujero) | — | sin componente |
''')
open(os.path.join(FAB, 'auditoria_piezas.md'), 'w', encoding='utf-8').write('\n'.join(L))
print('escrito', os.path.join(FAB, 'auditoria_piezas.md'), '| extended hoy:', len(ext))
