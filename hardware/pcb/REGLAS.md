# Reglas de layout — Sonómetro IEPE Rev B (2 capas, 90 × 64 mm, JLCPCB)

Resumen de las guías que aplican a esta placa y de cómo quedan cargadas en KiCad.

**Confianza de cada fuente:**
- **[doc]**: leído en el documento primario.
- **[copia]**: leído en una copia de terceros o en un resumen de la página.
- **[sin verificar]**: no se pudo abrir la fuente.

Las reglas del dueño (sección 7) mandan sobre todo lo demás.

Fecha de lectura: 15/11/2026.

---

## 1. Fabricante: JLCPCB, 2 capas, cobre exterior 1 oz, FR-4 de 1.6 mm
Fuente [doc]: <https://jlcpcb.com/capabilities/pcb-capabilities>. Se cita la fila o condición de 2 capas / 1 oz.

| Concepto | Mínimo JLC (2 capas, 1 oz) | Fila / condición en la página | Piso en la placa | Valor de diseño |
|---|---|---|---|---|
| Ancho de pista | 0.10 mm | "1- and 2-layer: 0.10/0.10 mm (4/4 mil)" | 0.10 | 0.2 (0.5 potencia) |
| Separación pista–pista | 0.10 mm | misma fila | 0.10 | 0.2 (0.3 analógica y reloj) |
| Pad–pista | 0.10 mm | "Pad to track clearance (1oz) 0.1mm" | — | 0.2 |
| Pad–pad SMD (redes distintas) | 0.15 mm | "SMD pad to pad clearance (different nets) 0.15mm" | — | 0.2 (regla `pad_a_pad`) |
| Vía (agujero/diámetro) | 0.15/0.25 mm | "2-layer: 0.15mm hole size / 0.25mm via diameter"; 0.3/0.5 es la de 1 capa | 0.15/0.25 | **0.3/0.6** (0.4/0.8 potencia) |
| Anillo de vía | 0.05 (0.075 preferido) [derivado de la nota ①: diám. ≥ agujero + 0.1 (0.15 pref.)] | nota ① | 0.10 | 0.15 |
| Anillo de pad PTH | 0.20 en la tabla; 0.18 mínimo absoluto, 0.25 recomendado | "2-layer: 1 oz: Recommended 0.25 mm…; absolute minimum 0.18 mm" | regla `anillo_pth` 0.20 | según footprint (≥ 0.35) |
| Agujero de vía–pista | 0.20 mm | "Via hole to Track 0.2mm" | 0.20 | ≥ 0.35 (anillo + separación) |
| Agujero PTH–pista | 0.28 mm (0.35 recomendado) | "PTH to Track … minimum 0.28mm" | regla `agujero_pth_a_cobre` 0.28 | ≥ 0.55 |
| Agujero–agujero | 0.2 (vías) / 0.45 (pads) | | 0.25 | — |
| Cobre–borde (fresado) | ≥ 0.2 mm | "≧0.2 mm" | 0.20 | **0.5** (regla `borde`) |
| Puente de máscara (verde) | 0.10 mm | "1oz: Min. pad spacing: 0.10 mm" | — | ≥ 0.25 en todos los footprints |
| Apertura de máscara | 1:1 | "Pad size:soldermask opening can be 1:1"; ≥ 0.09 mm de pistas vecinas | máscara–cobre 0.09 | expansión 0 |
| Serigrafía | línea ≥ 0.15, texto ≥ 1.0 mm (relación 1:6), ≥ 0.15 a pads | | texto 1.0/0.15, separación 0.15 | **1.0 / 0.15** |

**Nota de diseño:** los valores de la última columna van en las clases de red y en `pcb.kicad_dru`, nunca en el mínimo.

## 2. Ensamblaje JLCPCB (PCBA)
Fuentes [doc]: <https://jlcpcb.com/capabilities/pcb-assembly-capabilities>, <https://jlcpcb.com/help/article/how-to-add-edge-rails-fiducials-for-pcb-assembly-order>,
<https://jlcpcb.com/help/article/terms-and-conditions-of-jlcpcb-assembly-service>, guías de KiCad 9/10 de JLC.

- **Tipo de ensamblaje:**
  - **Economic PCBA**: una cara, placa de 10×10 a 470×500 mm, hasta 0402. La placa (90 × 64) entra.
  - Standard pide ≥ 70×70 mm.
- **Cuerpo de componente a borde: ≥ 2.5 mm** sin rieles.
  - Hoy L1/L2 (1.30 mm), C31–C34/C41–C44 (1.35 mm) y R33/C47 (1.85 mm) no lo cumplen. Por eso se piden rieles
    (los términos de JLC dicen que los agregan o modifican por defecto).
- **Fiduciales:** 1 mm de cobre desnudo con 2 mm de apertura de máscara, 3 o 4 cerca de los bordes, a ≥ 3.35 mm
  del borde.
- **Agujeros de herramienta:** 1.152 mm NPTH; JLC los agrega por defecto en los rieles.
- **Archivos:**
  - Gerber: Protel, X2, 4.6 mm, F/B Cu, Mask, Silk, Paste y Edge.Cuts; verificar zonas antes de exportar.
  - Taladros: Excellon, mm, origen absoluto, PTH y NPTH separados.
  - BOM: Comment, Designator, Footprint y código LCSC.
  - CPL: Designator, Mid X, Mid Y, Layer, Rotation; rotación positiva antihoraria. No hay tabla oficial de
    offsets: la rotación se corrige por pieza (ver `fabricacion/rotaciones.md`).

## 3. Reglas por integrado
### LMR36015FBRNXR (U6/U7) — TI SNVSB49D [doc]
- **Variante FB:** FPWM, 1 MHz fijo aun sin carga (tabla de dispositivos, p.3; §9.4.2 y tabla 9-1, p.16).
  - tON-MIN es de 83 ns máx. y tOFF-MIN de 73 ns máx. (p.7).
  - En CALCULOS.md se verifica tON con fSW de 0.85–1.15 MHz.
- **Condensadores:**
  - CIN ≥ 4.7 µF cerámico, de tensión preferiblemente 2 × VIN máx. (§10.2.1.2.6, p.23).
  - 220 nF lo más cerca posible de **cada** par VIN/PGND: pines 2/1 y 10/11 (§12.1 ítem 1, p.34).
  - Lazo de entrada CIN–VIN–PGND corto, ancho y de área mínima (§12.1, p.34; fig. 12-1, p.35).
  - VCC: 1 µF/16 V pegado al pin 5, sin carga externa (§12.1 ítem 2).
- **BOOT y SW:**
  - CBOOT 100 nF corto a BOOT (4) y SW. **SW (12) unido a NC (3) en la placa** (§12.1 ítem 3; tabla de pines, p.4).
  - Cobre de SW corto y de área mínima, sin "espejo" del nodo SW en la otra capa (§12.1 ítem 8; SNVA054C p.9).
- **Realimentación:** RFBT/RFBB pegados a FB (7); el sensado de VOUT lejos de SW (§12.1 ítem 4).
- **Tierra:**
  - Vías GND junto a los condensadores de bypass.
  - VIN, SW y PGND de un lado del plano; lo sensible del otro (§12.1.1, p.35).
- **En 2 capas** (el datasheet y todos los EVM usan 4 capas; no hay guía de TI de 2 capas para RNX):
  - todo el lazo de potencia en F.Cu y B.Cu continuo;
  - TI une los dos VIN por una capa interna (fig. 12-2, p.36). Aquí, si hace falta, va un **puente VIN corto en
    B.Cu debajo de los CIN** (no del integrado), con GND cosido alrededor (SNVA054C; SNVA803 p.2).
- Vías térmicas de 0.3 mm a 1–1.2 mm de paso, **junto** a los pads, no debajo (SNVA054C p.12).
- Colocar los condensadores de entrada en simetría reduce a la mitad la inductancia del lazo (SNVA859A §2.1).
- θJA 72.5 °C/W (JEDEC, §8.4 p.6). Baja a ~40 °C/W con cobre (fig. 10-3, p.25, placa de 4 capas).

### PCM1808 (U4) — TI SLES177B [doc] y EVM SBAU349 [doc]
- **Desacoplo:**
  - VCC (pin 3, 5 V) y VDD (pin 4, 3.3 V): 0.1 µF + 10 µF lo más cerca posible (§10.1.1, p.21).
  - VREF (pin 1): 0.1 µF + 10 µF a AGND, lo más cerca posible (§10.1.4).
- **Tierra:**
  - **AGND (2) y DGND (5) unidos directo debajo del encapsulado** (§10.1.2).
  - **Relleno GND en la capa superior alrededor del chip**, cosido con muchas vías.
  - **GND entre las entradas L y R y alrededor del reloj** (fig. 28, §10.2, p.22).
- **DOUT:** si la línea es larga, buffer cerca del chip; aquí hay R24 en serie junto al ADC (§10.1.5).
- **Lo que hace el EVM:** una sola red GND (sin partir), resistencias en serie en SCKI/BCK/LRCK/DOUT, RC de
  entrada de 100 Ω/10 nF, y entradas analógicas e I2S en bordes opuestos.

### TLV9062 (U3/U9; propuesta TLV9152) — TI SBOS839N [doc]
- 0.1 µF cerámico de V+ a GND lo más cerca posible.
- Resistencias de realimentación y de entrada junto a la entrada inversora.
- Entradas cortas y lejos de las alimentaciones y salidas. Si una pista ruidosa cruza, que sea a 90° (§8.4.1, p.27).
- Nodo de 1 MΩ: el anillo de guarda es sugerido; no se pone (el DC lo corrige el lazo DAC). Limpiar la placa
  después de soldar (§8.4.1).

### MCP4725 (U2/U10) — Microchip DS22039D [doc]
- 0.1 µF (+10 µF) a ≤ 4 mm de VDD. VDD es también la referencia del DAC: su ruido pasa a la salida (§8.3, p.34).
- VSS y las tierras de sus condensadores a la zona analógica, con baja impedancia (§3.2, §8.4).
- Pull-ups I2C de 1–10 kΩ (§8.1). Aquí hay 4.7 kΩ.

### LT3092 (U1/U8) — ADI 3092fc/Rev D [copia]
- **Pines (TS8):** OUT 2–4, SET 5, IN 7–8, NC 1/6.
- No necesita condensadores para ser estable. Bypass de entrada de 0.1–1 µF.
- Anillo de guarda en SET unido a OUT: 10 nA de fuga dan 0.1 % de error. **Opcional**; no se pone si complica el
  ruteo (decisión del dueño).
- **Land pattern recomendado** (LTC DWG 05-08-1637 Rev A, Rev D p.22 [doc]): pads de 0.40 × 1.22 mm, paso 0.65,
  filas a 2.62 mm entre centros. → footprint propuesto `Sonometro:TSOT-23-8_Pad0.40x1.22mm_P0.65mm_ADI`.
- θJA 57 °C/W (TS8).

## 4. Tierra y retorno
- **Un solo plano GND, sin cortes ni ranuras bajo las pistas.** Las holguras de las vías no deben cortar el
  retorno (TI SLYT499, p.8 [doc]).
- **El plano se reparte por zonas** (SLYT512, pp. 5–6 [doc]):
  - lo analógico se rutea solo sobre su zona y lo digital sobre la suya, en todas las capas;
  - la unión de tierras va debajo del convertidor;
  - la alimentación entra por el lado digital.
- **Convertidor (MT-031 [copia]):**
  - AGND y DGND al plano con conexiones mínimas.
  - El oscilador de muestreo se trata como analógico y va junto a SCKI (U4/Y1 ya están así).
  - No se toma el reloj del MCU.
- **Desacoplo (MT-101 [doc]):** 0.01–0.1 µF lo más cerca posible del pin, unido al plano con vía o pista corta.

## 5. IPC-2221B
- **Separación, tabla 6-1, columna B2** (externo, sin recubrimiento, hasta 3050 m; Manizales ≈ 2150 m) [copia, dos
  fuentes coinciden: ayuda de Altair Pollex y SFCircuits]:

  | Tensión | Separación |
  |---|---|
  | 0–15 V | 0.1 mm |
  | 16–30 V | 0.1 mm |
  | 31–50 V | 0.6 mm |

  - El TVS limita la tensión continua de 24V_PROT a < 29 V, así que va en la fila de 16–30 V. Se diseña con
    0.2 mm o más.
  - El recorte de 42 V del TVS es transitorio.
- **Ampacidad:** I = 0.048 · ΔT^0.44 · A^0.725 (externo; A en mil², ΔT en °C). Es un ajuste a las curvas de IPC-2221,
  hoy reemplazadas por IPC-2152 [copia: calculadora de DigiKey y mbedded.ninja].
  - Con 5–20 mA, el ancho lo fija la geometría y no la corriente (ver CALCULOS.md).

## 6. Diseños de referencia
- **LMR36015-Q1 EVM** (SNVU636, SNVU580) y LMR33630 (SNVU583), todos de 4 capas:
  - capa superior inundada de GND;
  - VIN en islas a cada lado del integrado;
  - SW como un cuello angosto del pin 12 a la bobina;
  - unas 4 vías GND por cada pad de COUT.
- **PCM1808 EVM** (SBAU349): ver la sección 3.
- **CN-0540** (ADI): no se pudo abrir el layout (analog.com sin respuesta) [sin verificar].

## 7. Reglas del dueño (obligatorias) y cómo se verifican
| Regla | Verificación |
|---|---|
| Solo 45°; nada de 90° ni ángulos agudos, en pistas ni en uniones pista–pad | DRC nativo `track_angle (min 135)` (probado en KiCad 10.0.8: marca 90° y 45° interiores) + `revisar_pistas.py` (orientación de cada segmento y unión pista–pad) |
| Sin stubs, segmentos sueltos ni pistas duplicadas | DRC `track_dangling`/`via_dangling` en error + `revisar_pistas.py` |
| Segmentos ≥ 0.1 mm | DRC `track_segment_length (min 0.1mm)` (probado) |
| Entrar a los pads por el centro y en línea recta; teardrops al final | `revisar_pistas.py`; teardrops con la API (si no se generan sin GUI, un clic en KiCad) |
| Desacoplo pegado al pin, lazo mínimo, vía GND junto al pad | se coloca al rutear cada bloque; `revisar_pistas.py` mide las distancias |
| Alimentación y tierra con zonas; prioridades; alivios térmicos en THT; sin islas | `zonas.py`; DRC `isolated_copper` en error |
| Ninguna señal cruza un corte del plano; retorno continuo bajo las críticas | `revisar_pistas.py` contra el relleno de B.Cu. B.Cu solo para I2C/DC_MON/DC_MON2 en la zona digital (más las excepciones aprobadas) |
| Analógicas cortas, lejos de reloj y conmutación, sin correr paralelas a lo digital | clases y reglas `sw_lejos_de_analogica` (1 mm) y `reloj_lejos_de_analogica` (0.5 mm) + chequeo de paralelismo |
| Cosido GND alrededor de zonas sensibles y bordes de planos | `zonas.py` |
| Serigrafía: 1.0/0.15 mm, 0° y 90°, nunca sobre pads, vías, máscara ni cuerpos; pin 1 y polaridad visibles | `serigrafia.py`; DRC `silk_*` y `text_*` en **error** |

## 8. Configuración en KiCad (`tools/config_reglas.py`)
- **Pisos de la placa** = sección 1 (columna "Piso en la placa").
- **Clases de red:**

  | Clase | Ancho | Separación | Vía | Redes |
  |---|---|---|---|---|
  | Default | 0.2 | 0.2 | 0.3/0.6 | I2C, MD/FMT, BOOT/FB/VCC de los bucks |
  | Potencia | 0.25 | 0.2 | 0.3/0.6 | 24V_*, 3V3, 5V, 5V_A, 3V3_DAC*, IEPE_SUP*, GND |
  | Conmutado | 0.25 | 0.2 | 0.3/0.6 | SW_3, SW_5 |

  Potencia y Conmutado se cambiaron tras el bloque 1, a pedido del dueño. Antes eran 0.5 mm y vía 0.4/0.8.
  - Ahora tienen los valores reales del ruteo: 0.25 mm es la salida de un pin de 0.25 mm.
  - Los tramos más anchos (SW a L 0.6, VIN/PGND 0.4–0.5, troncos 0.5) salen de CALCULOS.md.
  - El mínimo lo hace cumplir la regla `ancho_minimo_potencia`.
  | Analogica | 0.2 | 0.3 | 0.3/0.6 | IEPE*, REST*, DC_MON*, SUM/divisores, DAC_F, AC/ADC_IN, VREF, SET/OUT de los LT3092 |
  | Reloj | 0.2 | 0.3 | 0.3/0.6 | SAI_*, BCK/LRCK/DOUT/SCKI del PCM1808, salida de Y1 |

- **`pcb.kicad_dru`** (cada regla probada por separado contra una regla de control, para que ninguna falle en
  silencio): `solo_45`, `segmento_minimo`, `borde`, `anillo_pth`, `agujero_pth_a_cobre`, `pad_a_pad`,
  `ancho_minimo_potencia`, `sw_lejos_de_analogica`, `reloj_lejos_de_analogica`.
  - Prueba de control de `ancho_minimo_potencia`: en la placa del bloque 1, con el sensado de FB todavía a 0.2 mm,
    marcó exactamente esos 9 segmentos.
- **Plano GND de B.Cu** (`tools/ruteo/bloques/gnd_bcu.py`): existe desde el bloque 1 y se rellena en cada
  verificación (`kicad-cli pcb drc --refill-zones --save-board`). Conexión sólida en SMD y vías; alivio térmico
  solo en THT.
- **Vías tapadas con máscara (tenting)** en las dos caras: está en la configuración de la placa y ninguna vía la
  anula. Comprobado en los Gerber de máscara contra una copia de control sin tenting: la copia tiene 32 aperturas
  más, todas en coordenadas de vía, y la placa real no tiene ninguna. La expansión de máscara de los pads es 0, así
  que una vía a 0.10 mm de un pad queda con 0.10 mm de máscara entre la apertura y el anillo.
- **Severidades en error:** silk_overlap, silk_over_copper, silk_edge_clearance, text_height, text_thickness,
  track_dangling, via_dangling, track_angle, track_segment_length, courtyards_overlap, lib_footprint_mismatch,
  footprint_symbol_mismatch, isolated_copper.
